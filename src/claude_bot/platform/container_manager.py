#!/usr/bin/env python3
"""
Container Manager for Claude Bot Infrastructure

Manages Docker container lifecycle for dynamic worker spawning.
Handles container creation, monitoring, and cleanup using Docker API.
"""

import docker
import json
import os
import sys
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import threading
import subprocess

# Add the scripts directory to Python path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from platform_manager import PlatformManager
from work_queue import WorkItem, TaskStatus
from github_secrets_manager import create_github_secrets_manager

@dataclass
class WorkerSpec:
    """Specification for a worker container."""
    task_id: str
    platforms: Dict[str, str]
    image_name: str
    container_name: str
    environment: Dict[str, str]
    volumes: Dict[str, str]
    command: List[str]
    resource_limits: Optional[Dict[str, Any]] = None

@dataclass
class WorkerInfo:
    """Information about a running worker."""
    container_id: str
    container_name: str
    task_id: str
    worker_id: str
    status: str
    created_at: datetime
    platforms: Dict[str, str]
    last_heartbeat: Optional[datetime] = None

class ContainerManager:
    """Manages Docker containers for dynamic worker spawning."""
    
    def __init__(self, workspace_dir: str = "/workspace", 
                 data_dir: str = "/bot/data",
                 base_image: str = "claude-bot-dynamic",
                 max_workers: int = 5):
        """
        Initialize container manager.
        
        Args:
            workspace_dir: Path to workspace directory
            data_dir: Path to bot data directory
            base_image: Base Docker image name for workers
            max_workers: Maximum number of concurrent workers
        """
        self.workspace_dir = Path(workspace_dir)
        self.data_dir = Path(data_dir)
        self.base_image = base_image
        self.max_workers = max_workers
        
        # Initialize Docker client
        try:
            self.docker_client = docker.from_env()
            self.docker_client.ping()
        except Exception as e:
            raise RuntimeError(f"Failed to connect to Docker: {e}")
        
        # Initialize platform manager
        self.platform_manager = PlatformManager()
        
        # Initialize secrets manager
        self.secrets_manager = None
        
        # Worker tracking
        self.active_workers: Dict[str, WorkerInfo] = {}
        self._lock = threading.Lock()
        
        # Logging
        self.logger = logging.getLogger(__name__)
        
        # Create data directories
        self.workers_dir = self.data_dir / "workers"
        self.workers_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Container manager initialized with max {max_workers} workers")
    
    def setup_secure_secrets(self, repo: str) -> bool:
        """Set up secure secrets management for the given repository."""
        try:
            self.secrets_manager = create_github_secrets_manager(repo, str(self.data_dir))
            
            # Retrieve secrets from GitHub or fallback sources
            secrets = self.secrets_manager.get_github_repository_secrets()
            
            if secrets:
                # Create secure secret files for Docker secrets
                secret_files = self.secrets_manager.create_secure_secret_files(secrets)
                self.logger.info(f"✅ Set up secure secrets for {len(secret_files)} secrets")
                return True
            else:
                self.logger.warning("No secrets found - workers may not function properly")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to set up secure secrets: {e}")
            return False
    
    def can_spawn_worker(self) -> bool:
        """Check if we can spawn a new worker."""
        with self._lock:
            return len(self.active_workers) < self.max_workers
    
    def create_worker_spec(self, work_item: WorkItem) -> WorkerSpec:
        """Create a worker specification for a work item."""
        
        # Determine platforms needed
        platforms = work_item.platform_requirements or {"nodejs": "18.16.0"}
        
        # Generate unique container name
        timestamp = int(time.time())
        container_name = f"claude-worker-{work_item.task_id[:8]}-{timestamp}"
        
        # Build image name with platform specification
        platform_string = ",".join([f"{k}:{v}" for k, v in platforms.items()])
        image_name = f"{self.base_image}:latest"
        
        # Environment variables for worker
        environment = {
            "TASK_ID": work_item.task_id,
            "ISSUE_NUMBER": str(work_item.issue_number) if work_item.issue_number else "",
            "REPO": work_item.repo,
            "ENABLED_PLATFORMS": platform_string,
            "WORKER_MODE": "true",
        }
        
        # Add secure secrets if secrets manager is available
        if self.secrets_manager:
            # Use secure file-based secrets instead of environment variables
            secrets = self.secrets_manager.get_github_repository_secrets()
            secure_env = self.secrets_manager.create_worker_environment(secrets, f"worker-{work_item.task_id[:8]}")
            environment.update(secure_env)
        else:
            # Fallback to environment variables (less secure)
            environment.update({
                "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", ""),
                "GITHUB_TOKEN": os.getenv("GITHUB_TOKEN", ""),
                "GIT_AUTHOR_NAME": os.getenv("GIT_AUTHOR_NAME", "Claude Bot"),
                "GIT_AUTHOR_EMAIL": os.getenv("GIT_AUTHOR_EMAIL", "bot@claude.ai"),
            })
        
        # Volumes for workspace and data sharing
        volumes = {
            str(self.workspace_dir): {"bind": "/workspace", "mode": "rw"},
            str(self.data_dir): {"bind": "/bot/data", "mode": "rw"},
        }
        
        # Add secure secrets mounting if secrets manager is available
        if self.secrets_manager:
            secrets_dir = self.data_dir / "secrets"
            volumes[str(secrets_dir)] = {"bind": "/run/secrets", "mode": "ro"}
        
        # Command to run in container
        command = [
            "python3", "/bot/scripts/worker_executor.py",
            "--task-id", work_item.task_id,
            "--workspace", "/workspace",
            "--data", "/bot/data"
        ]
        
        # Resource limits
        resource_limits = {
            "mem_limit": "2g",
            "cpu_quota": 100000,  # 1 CPU
            "cpu_period": 100000
        }
        
        return WorkerSpec(
            task_id=work_item.task_id,
            platforms=platforms,
            image_name=image_name,
            container_name=container_name,
            environment=environment,
            volumes=volumes,
            command=command,
            resource_limits=resource_limits
        )
    
    def build_worker_image(self, platforms: Dict[str, str]) -> bool:
        """Build a worker image with specified platforms."""
        try:
            # Use existing dynamic Dockerfile system
            dockerfile_path = Path(".devcontainer/Dockerfile.dynamic")
            
            if not dockerfile_path.exists():
                self.logger.error(f"Dynamic Dockerfile not found at {dockerfile_path}")
                return False
            
            # Build arguments
            build_args = {
                "ENABLED_PLATFORMS": ",".join([f"{k}:{v}" for k, v in platforms.items()])
            }
            
            self.logger.info(f"Building worker image with platforms: {platforms}")
            
            # Build image
            image, build_logs = self.docker_client.images.build(
                path=".",
                dockerfile=str(dockerfile_path),
                tag=f"{self.base_image}:latest",
                buildargs=build_args,
                pull=True,
                rm=True
            )
            
            self.logger.info(f"Successfully built worker image: {image.id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to build worker image: {e}")
            return False
    
    def spawn_worker(self, work_item: WorkItem) -> Optional[str]:
        """Spawn a worker container for a work item."""
        
        if not self.can_spawn_worker():
            self.logger.warning("Cannot spawn worker: maximum workers reached")
            return None
        
        try:
            # Create worker specification
            worker_spec = self.create_worker_spec(work_item)
            
            # Ensure worker image exists
            if not self._ensure_worker_image(worker_spec.platforms):
                self.logger.error("Failed to ensure worker image")
                return None
            
            # Create and start container
            container = self.docker_client.containers.run(
                image=worker_spec.image_name,
                name=worker_spec.container_name,
                command=worker_spec.command,
                environment=worker_spec.environment,
                volumes=worker_spec.volumes,
                detach=True,
                remove=True,  # Auto-remove when stopped
                network_mode="bridge",
                **worker_spec.resource_limits
            )
            
            # Create worker info
            worker_info = WorkerInfo(
                container_id=container.id,
                container_name=worker_spec.container_name,
                task_id=work_item.task_id,
                worker_id=f"worker-{work_item.task_id[:8]}",
                status="running",
                created_at=datetime.now(),
                platforms=worker_spec.platforms
            )
            
            # Register worker
            with self._lock:
                self.active_workers[container.id] = worker_info
            
            # Save worker info to file
            worker_file = self.workers_dir / f"{worker_info.worker_id}.json"
            with open(worker_file, 'w') as f:
                json.dump({
                    "container_id": container.id,
                    "container_name": worker_spec.container_name,
                    "task_id": work_item.task_id,
                    "worker_id": worker_info.worker_id,
                    "created_at": worker_info.created_at.isoformat(),
                    "platforms": worker_spec.platforms,
                    "work_item": work_item.to_dict()
                }, f, indent=2)
            
            self.logger.info(f"Spawned worker {worker_info.worker_id} for task {work_item.task_id}")
            return container.id
            
        except Exception as e:
            self.logger.error(f"Failed to spawn worker for task {work_item.task_id}: {e}")
            return None
    
    def _ensure_worker_image(self, platforms: Dict[str, str]) -> bool:
        """Ensure worker image exists for specified platforms."""
        try:
            # Check if image exists
            try:
                self.docker_client.images.get(f"{self.base_image}:latest")
                return True
            except docker.errors.ImageNotFound:
                pass
            
            # Build image if it doesn't exist
            return self.build_worker_image(platforms)
            
        except Exception as e:
            self.logger.error(f"Failed to ensure worker image: {e}")
            return False
    
    def monitor_workers(self) -> Dict[str, str]:
        """Monitor active workers and return their status."""
        status_updates = {}
        
        with self._lock:
            for container_id, worker_info in list(self.active_workers.items()):
                try:
                    container = self.docker_client.containers.get(container_id)
                    
                    # Update status
                    old_status = worker_info.status
                    worker_info.status = container.status
                    
                    if old_status != worker_info.status:
                        status_updates[worker_info.task_id] = worker_info.status
                        self.logger.info(f"Worker {worker_info.worker_id} status changed: {old_status} -> {worker_info.status}")
                    
                    # Clean up completed/failed workers
                    if worker_info.status in ["exited", "dead"]:
                        self._cleanup_worker(container_id, worker_info)
                        
                except docker.errors.NotFound:
                    # Container was removed
                    self._cleanup_worker(container_id, worker_info)
                    status_updates[worker_info.task_id] = "removed"
                    
                except Exception as e:
                    self.logger.error(f"Error monitoring worker {worker_info.worker_id}: {e}")
        
        return status_updates
    
    def _cleanup_worker(self, container_id: str, worker_info: WorkerInfo):
        """Clean up a worker that has finished."""
        try:
            # Remove from active workers
            if container_id in self.active_workers:
                del self.active_workers[container_id]
            
            # Clean up worker file
            worker_file = self.workers_dir / f"{worker_info.worker_id}.json"
            if worker_file.exists():
                worker_file.unlink()
            
            self.logger.info(f"Cleaned up worker {worker_info.worker_id}")
            
        except Exception as e:
            self.logger.error(f"Error cleaning up worker {worker_info.worker_id}: {e}")
    
    def stop_worker(self, task_id: str) -> bool:
        """Stop a worker by task ID."""
        try:
            with self._lock:
                for container_id, worker_info in self.active_workers.items():
                    if worker_info.task_id == task_id:
                        container = self.docker_client.containers.get(container_id)
                        container.stop(timeout=30)
                        self.logger.info(f"Stopped worker {worker_info.worker_id} for task {task_id}")
                        return True
                
                self.logger.warning(f"No active worker found for task {task_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to stop worker for task {task_id}: {e}")
            return False
    
    def get_worker_logs(self, task_id: str) -> Optional[str]:
        """Get logs from a worker by task ID."""
        try:
            with self._lock:
                for container_id, worker_info in self.active_workers.items():
                    if worker_info.task_id == task_id:
                        container = self.docker_client.containers.get(container_id)
                        logs = container.logs(tail=1000).decode('utf-8')
                        return logs
                
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get logs for task {task_id}: {e}")
            return None
    
    def get_worker_stats(self) -> Dict[str, Any]:
        """Get statistics about workers."""
        with self._lock:
            stats = {
                "active_workers": len(self.active_workers),
                "max_workers": self.max_workers,
                "workers": []
            }
            
            for worker_info in self.active_workers.values():
                stats["workers"].append({
                    "worker_id": worker_info.worker_id,
                    "task_id": worker_info.task_id,
                    "status": worker_info.status,
                    "created_at": worker_info.created_at.isoformat(),
                    "platforms": worker_info.platforms
                })
            
            return stats
    
    def cleanup_stale_workers(self, timeout_minutes: int = 60) -> int:
        """Clean up workers that have been running too long."""
        cleanup_count = 0
        cutoff_time = datetime.now() - timedelta(minutes=timeout_minutes)
        
        with self._lock:
            for container_id, worker_info in list(self.active_workers.items()):
                if worker_info.created_at < cutoff_time:
                    try:
                        container = self.docker_client.containers.get(container_id)
                        container.stop(timeout=10)
                        self._cleanup_worker(container_id, worker_info)
                        cleanup_count += 1
                        self.logger.info(f"Cleaned up stale worker {worker_info.worker_id}")
                    except Exception as e:
                        self.logger.error(f"Error cleaning up stale worker {worker_info.worker_id}: {e}")
        
        return cleanup_count
    
    def shutdown(self):
        """Shutdown all workers and cleanup."""
        self.logger.info("Shutting down container manager...")
        
        with self._lock:
            for container_id, worker_info in list(self.active_workers.items()):
                try:
                    container = self.docker_client.containers.get(container_id)
                    container.stop(timeout=10)
                    self._cleanup_worker(container_id, worker_info)
                except Exception as e:
                    self.logger.error(f"Error stopping worker {worker_info.worker_id}: {e}")
        
        self.logger.info("Container manager shutdown complete")

# Example usage and testing
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Create container manager
    container_manager = ContainerManager(
        workspace_dir="/tmp/test_workspace",
        data_dir="/tmp/test_data",
        base_image="claude-bot-dynamic",
        max_workers=2
    )
    
    # Create test work item
    from work_queue import WorkItem, TaskPriority
    
    work_item = WorkItem(
        issue_number=123,
        title="Test Container Spawn",
        description="Test spawning a worker container",
        repo="test/repo",
        platform_requirements={"nodejs": "18.16.0"},
        priority=TaskPriority.HIGH
    )
    
    # Test worker spawning
    print("Testing worker spawn...")
    container_id = container_manager.spawn_worker(work_item)
    
    if container_id:
        print(f"Spawned worker: {container_id}")
        
        # Monitor for a bit
        for i in range(5):
            time.sleep(2)
            status_updates = container_manager.monitor_workers()
            if status_updates:
                print(f"Status updates: {status_updates}")
            
            stats = container_manager.get_worker_stats()
            print(f"Worker stats: {stats}")
    
    # Cleanup
    container_manager.shutdown()