#!/usr/bin/env python3
"""
Work Queue System for Claude Bot Infrastructure

Manages a persistent queue of tasks that can be processed by distributed workers.
Supports both Redis-based and file-based queue implementations.
"""

import json
import time
import uuid
import os
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import logging

class TaskStatus(Enum):
    """Task status enumeration."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"

class TaskPriority(Enum):
    """Task priority enumeration."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4

class WorkItem:
    """Represents a single work item in the queue."""
    
    def __init__(self, task_id: str = None, issue_number: int = None,
                 title: str = "", description: str = "", repo: str = "",
                 platform_requirements: Dict[str, str] = None,
                 priority: TaskPriority = TaskPriority.MEDIUM,
                 created_at: datetime = None, max_retries: int = 3):
        self.task_id = task_id or str(uuid.uuid4())
        self.issue_number = issue_number
        self.title = title
        self.description = description
        self.repo = repo
        self.platform_requirements = platform_requirements or {}
        self.priority = priority
        self.status = TaskStatus.PENDING
        self.created_at = created_at or datetime.now()
        self.assigned_at: Optional[datetime] = None
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.assigned_to: Optional[str] = None  # Worker ID
        self.retry_count = 0
        self.max_retries = max_retries
        self.error_message: Optional[str] = None
        self.result: Optional[Dict[str, Any]] = None
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert work item to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "issue_number": self.issue_number,
            "title": self.title,
            "description": self.description,
            "repo": self.repo,
            "platform_requirements": self.platform_requirements,
            "priority": self.priority.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "assigned_to": self.assigned_to,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "error_message": self.error_message,
            "result": self.result
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkItem':
        """Create work item from dictionary."""
        item = cls(
            task_id=data["task_id"],
            issue_number=data.get("issue_number"),
            title=data.get("title", ""),
            description=data.get("description", ""),
            repo=data.get("repo", ""),
            platform_requirements=data.get("platform_requirements", {}),
            priority=TaskPriority(data.get("priority", TaskPriority.MEDIUM.value)),
            created_at=datetime.fromisoformat(data["created_at"]),
            max_retries=data.get("max_retries", 3)
        )
        
        item.status = TaskStatus(data.get("status", TaskStatus.PENDING.value))
        item.assigned_at = datetime.fromisoformat(data["assigned_at"]) if data.get("assigned_at") else None
        item.started_at = datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None
        item.completed_at = datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None
        item.assigned_to = data.get("assigned_to")
        item.retry_count = data.get("retry_count", 0)
        item.error_message = data.get("error_message")
        item.result = data.get("result")
        
        return item

class WorkQueue:
    """Base work queue interface."""
    
    def enqueue(self, work_item: WorkItem) -> bool:
        """Add a work item to the queue."""
        raise NotImplementedError
    
    def dequeue(self, worker_id: str, platform_capabilities: Dict[str, str] = None) -> Optional[WorkItem]:
        """Get the next work item from the queue."""
        raise NotImplementedError
    
    def update_status(self, task_id: str, status: TaskStatus, 
                     error_message: str = None, result: Dict[str, Any] = None) -> bool:
        """Update the status of a work item."""
        raise NotImplementedError
    
    def get_task(self, task_id: str) -> Optional[WorkItem]:
        """Get a specific task by ID."""
        raise NotImplementedError
    
    def get_queue_stats(self) -> Dict[str, int]:
        """Get queue statistics."""
        raise NotImplementedError
    
    def cleanup_stale_tasks(self, timeout_minutes: int = 30) -> int:
        """Clean up tasks that have been assigned but not completed."""
        raise NotImplementedError

class FileBasedWorkQueue(WorkQueue):
    """File-based work queue implementation."""
    
    def __init__(self, queue_dir: str = "/bot/data/queue"):
        self.queue_dir = Path(queue_dir)
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for different task states
        self.pending_dir = self.queue_dir / "pending"
        self.assigned_dir = self.queue_dir / "assigned"
        self.completed_dir = self.queue_dir / "completed"
        self.failed_dir = self.queue_dir / "failed"
        
        for dir_path in [self.pending_dir, self.assigned_dir, self.completed_dir, self.failed_dir]:
            dir_path.mkdir(exist_ok=True)
        
        self._lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
    
    def enqueue(self, work_item: WorkItem) -> bool:
        """Add a work item to the pending queue."""
        try:
            with self._lock:
                file_path = self.pending_dir / f"{work_item.task_id}.json"
                with open(file_path, 'w') as f:
                    json.dump(work_item.to_dict(), f, indent=2)
                
                self.logger.info(f"Enqueued task {work_item.task_id}: {work_item.title}")
                return True
        except Exception as e:
            self.logger.error(f"Failed to enqueue task {work_item.task_id}: {e}")
            return False
    
    def dequeue(self, worker_id: str, platform_capabilities: Dict[str, str] = None) -> Optional[WorkItem]:
        """Get the next compatible work item from the queue."""
        try:
            with self._lock:
                # Get all pending tasks
                pending_files = sorted(self.pending_dir.glob("*.json"))
                
                for task_file in pending_files:
                    try:
                        with open(task_file, 'r') as f:
                            task_data = json.load(f)
                        
                        work_item = WorkItem.from_dict(task_data)
                        
                        # Check platform compatibility
                        if self._is_compatible(work_item, platform_capabilities):
                            # Move to assigned directory
                            work_item.status = TaskStatus.ASSIGNED
                            work_item.assigned_at = datetime.now()
                            work_item.assigned_to = worker_id
                            
                            assigned_file = self.assigned_dir / f"{work_item.task_id}.json"
                            with open(assigned_file, 'w') as f:
                                json.dump(work_item.to_dict(), f, indent=2)
                            
                            # Remove from pending
                            task_file.unlink()
                            
                            self.logger.info(f"Assigned task {work_item.task_id} to worker {worker_id}")
                            return work_item
                            
                    except Exception as e:
                        self.logger.error(f"Error processing task file {task_file}: {e}")
                        continue
                
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to dequeue task for worker {worker_id}: {e}")
            return None
    
    def _is_compatible(self, work_item: WorkItem, worker_capabilities: Dict[str, str]) -> bool:
        """Check if a work item is compatible with worker capabilities."""
        if not work_item.platform_requirements:
            return True  # No specific requirements
        
        if not worker_capabilities:
            return False  # Worker has no capabilities but task has requirements
        
        # Check if worker has all required platforms
        for platform, version in work_item.platform_requirements.items():
            if platform not in worker_capabilities:
                return False
            
            # For now, simple version matching. Could be enhanced with semantic versioning
            worker_version = worker_capabilities[platform]
            if version != 'latest' and version != worker_version:
                # Check if versions are compatible (major.minor matching)
                if not self._versions_compatible(version, worker_version):
                    return False
        
        return True
    
    def _versions_compatible(self, required: str, available: str) -> bool:
        """Check if versions are compatible."""
        try:
            req_parts = required.split('.')
            avail_parts = available.split('.')
            
            # Match major.minor versions
            if len(req_parts) >= 2 and len(avail_parts) >= 2:
                return req_parts[0] == avail_parts[0] and req_parts[1] == avail_parts[1]
        except:
            pass
        
        return required == available
    
    def update_status(self, task_id: str, status: TaskStatus, 
                     error_message: str = None, result: Dict[str, Any] = None) -> bool:
        """Update the status of a work item."""
        try:
            with self._lock:
                # Find the task file
                task_file = None
                current_dir = None
                
                for search_dir in [self.pending_dir, self.assigned_dir, self.completed_dir, self.failed_dir]:
                    potential_file = search_dir / f"{task_id}.json"
                    if potential_file.exists():
                        task_file = potential_file
                        current_dir = search_dir
                        break
                
                if not task_file:
                    self.logger.error(f"Task {task_id} not found")
                    return False
                
                # Load and update task
                with open(task_file, 'r') as f:
                    task_data = json.load(f)
                
                work_item = WorkItem.from_dict(task_data)
                work_item.status = status
                
                if status == TaskStatus.IN_PROGRESS:
                    work_item.started_at = datetime.now()
                elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    work_item.completed_at = datetime.now()
                
                if error_message:
                    work_item.error_message = error_message
                
                if result:
                    work_item.result = result
                
                # Determine target directory
                target_dir = self._get_status_directory(status)
                target_file = target_dir / f"{task_id}.json"
                
                # Write updated task
                with open(target_file, 'w') as f:
                    json.dump(work_item.to_dict(), f, indent=2)
                
                # Remove from current directory if different
                if current_dir != target_dir:
                    task_file.unlink()
                
                self.logger.info(f"Updated task {task_id} status to {status.value}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to update task {task_id} status: {e}")
            return False
    
    def _get_status_directory(self, status: TaskStatus) -> Path:
        """Get the directory for a given status."""
        if status == TaskStatus.PENDING:
            return self.pending_dir
        elif status in [TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS]:
            return self.assigned_dir
        elif status == TaskStatus.COMPLETED:
            return self.completed_dir
        elif status in [TaskStatus.FAILED, TaskStatus.RETRY]:
            return self.failed_dir
        else:
            return self.pending_dir
    
    def get_task(self, task_id: str) -> Optional[WorkItem]:
        """Get a specific task by ID."""
        try:
            for search_dir in [self.pending_dir, self.assigned_dir, self.completed_dir, self.failed_dir]:
                task_file = search_dir / f"{task_id}.json"
                if task_file.exists():
                    with open(task_file, 'r') as f:
                        task_data = json.load(f)
                    return WorkItem.from_dict(task_data)
            return None
        except Exception as e:
            self.logger.error(f"Failed to get task {task_id}: {e}")
            return None
    
    def get_queue_stats(self) -> Dict[str, int]:
        """Get queue statistics."""
        try:
            stats = {
                "pending": len(list(self.pending_dir.glob("*.json"))),
                "assigned": len(list(self.assigned_dir.glob("*.json"))),
                "completed": len(list(self.completed_dir.glob("*.json"))),
                "failed": len(list(self.failed_dir.glob("*.json")))
            }
            stats["total"] = sum(stats.values())
            return stats
        except Exception as e:
            self.logger.error(f"Failed to get queue stats: {e}")
            return {"pending": 0, "assigned": 0, "completed": 0, "failed": 0, "total": 0}
    
    def cleanup_stale_tasks(self, timeout_minutes: int = 30) -> int:
        """Clean up tasks that have been assigned but not updated."""
        cleanup_count = 0
        cutoff_time = datetime.now() - timedelta(minutes=timeout_minutes)
        
        try:
            with self._lock:
                for task_file in self.assigned_dir.glob("*.json"):
                    try:
                        with open(task_file, 'r') as f:
                            task_data = json.load(f)
                        
                        work_item = WorkItem.from_dict(task_data)
                        
                        # Check if task is stale
                        if work_item.assigned_at and work_item.assigned_at < cutoff_time:
                            # Move back to pending or failed based on retry count
                            if work_item.retry_count < work_item.max_retries:
                                work_item.retry_count += 1
                                work_item.status = TaskStatus.RETRY
                                work_item.assigned_at = None
                                work_item.assigned_to = None
                                work_item.error_message = f"Task timed out after {timeout_minutes} minutes (retry {work_item.retry_count})"
                                
                                # Move back to pending
                                retry_file = self.pending_dir / f"{work_item.task_id}.json"
                                with open(retry_file, 'w') as f:
                                    json.dump(work_item.to_dict(), f, indent=2)
                            else:
                                # Max retries exceeded, mark as failed
                                work_item.status = TaskStatus.FAILED
                                work_item.completed_at = datetime.now()
                                work_item.error_message = f"Task failed after {work_item.max_retries} retries (timeout)"
                                
                                failed_file = self.failed_dir / f"{work_item.task_id}.json"
                                with open(failed_file, 'w') as f:
                                    json.dump(work_item.to_dict(), f, indent=2)
                            
                            # Remove from assigned directory
                            task_file.unlink()
                            cleanup_count += 1
                            
                            self.logger.info(f"Cleaned up stale task {work_item.task_id}")
                            
                    except Exception as e:
                        self.logger.error(f"Error cleaning up task file {task_file}: {e}")
                        continue
                        
        except Exception as e:
            self.logger.error(f"Failed to cleanup stale tasks: {e}")
        
        return cleanup_count

def create_work_queue(queue_type: str = "file", **kwargs) -> WorkQueue:
    """Factory function to create work queue instances."""
    if queue_type.lower() == "file":
        return FileBasedWorkQueue(**kwargs)
    elif queue_type.lower() == "redis":
        # Redis implementation would go here
        raise NotImplementedError("Redis work queue not yet implemented")
    else:
        raise ValueError(f"Unsupported queue type: {queue_type}")

# Example usage and testing
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Create queue
    queue = create_work_queue("file", queue_dir="/tmp/test_queue")
    
    # Create test work item
    work_item = WorkItem(
        issue_number=123,
        title="Test Issue",
        description="This is a test issue for the work queue",
        repo="test/repo",
        platform_requirements={"nodejs": "18.16.0"},
        priority=TaskPriority.HIGH
    )
    
    # Test enqueue
    print("Testing enqueue...")
    success = queue.enqueue(work_item)
    print(f"Enqueue result: {success}")
    
    # Test queue stats
    print("\nQueue stats:")
    stats = queue.get_queue_stats()
    for status, count in stats.items():
        print(f"  {status}: {count}")
    
    # Test dequeue
    print("\nTesting dequeue...")
    worker_capabilities = {"nodejs": "18.16.0"}
    dequeued_item = queue.dequeue("test-worker-1", worker_capabilities)
    
    if dequeued_item:
        print(f"Dequeued task: {dequeued_item.task_id}")
        
        # Test status update
        print("Testing status update...")
        queue.update_status(dequeued_item.task_id, TaskStatus.IN_PROGRESS)
        queue.update_status(dequeued_item.task_id, TaskStatus.COMPLETED, 
                          result={"pr_url": "https://github.com/test/repo/pull/456"})
    
    # Final stats
    print("\nFinal queue stats:")
    stats = queue.get_queue_stats()
    for status, count in stats.items():
        print(f"  {status}: {count}")