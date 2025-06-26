#!/usr/bin/env python3
"""
Test Helper Utilities for Claude Bot Infrastructure Tests
Provides common functionality for testing bot operations
"""

import os
import time
import json
import subprocess
import tempfile
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import uuid


class BotTestHelper:
    """Helper class for bot testing operations"""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.test_artifacts = []
        
    def wait_for_bot_ready(self, timeout: int = 60) -> bool:
        """Wait for bot to be ready and responsive"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{self.base_url}/api/status", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("count", 0) > 0:
                        return True
            except requests.RequestException:
                pass
            time.sleep(2)
        return False
    
    def get_bot_status(self) -> Dict[str, Any]:
        """Get current bot status"""
        try:
            response = requests.get(f"{self.base_url}/api/status", timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise Exception(f"Failed to get bot status: {e}")
    
    def wait_for_task_completion(self, task_pattern: str, timeout: int = 300) -> Dict[str, Any]:
        """Wait for a task matching pattern to complete"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = self.get_bot_status()
            
            # Check for completed tasks
            for bot_status in status.get("statuses", []):
                for activity in bot_status.get("recent_activity", []):
                    if task_pattern.lower() in activity.get("title", "").lower():
                        if activity.get("status") == "completed":
                            return activity
                        elif activity.get("status") == "failed":
                            raise Exception(f"Task failed: {activity}")
            
            time.sleep(5)
        
        raise TimeoutError(f"Task '{task_pattern}' did not complete within {timeout} seconds")
    
    def create_test_workspace(self) -> Path:
        """Create a temporary workspace for testing"""
        workspace = Path(tempfile.mkdtemp(prefix="bot_test_"))
        self.test_artifacts.append(workspace)
        return workspace
    
    def cleanup_test_artifacts(self):
        """Clean up all test artifacts"""
        import shutil
        for artifact in self.test_artifacts:
            if artifact.exists():
                if artifact.is_dir():
                    shutil.rmtree(artifact)
                else:
                    artifact.unlink()
        self.test_artifacts.clear()


class DockerTestHelper:
    """Helper class for Docker-related testing"""
    
    @staticmethod
    def is_container_running(name: str) -> bool:
        """Check if a Docker container is running"""
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={name}", "--format", "{{.Names}}"],
                capture_output=True, text=True, check=True
            )
            return name in result.stdout
        except subprocess.CalledProcessError:
            return False
    
    @staticmethod
    def get_container_logs(name: str, lines: int = 50) -> str:
        """Get logs from a Docker container"""
        try:
            result = subprocess.run(
                ["docker", "logs", "--tail", str(lines), name],
                capture_output=True, text=True, check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            return f"Error getting logs: {e.stderr}"
    
    @staticmethod
    def wait_for_container_healthy(name: str, timeout: int = 60) -> bool:
        """Wait for a container to be healthy"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                result = subprocess.run(
                    ["docker", "inspect", "--format", "{{.State.Health.Status}}", name],
                    capture_output=True, text=True, check=True
                )
                if result.stdout.strip() == "healthy":
                    return True
            except subprocess.CalledProcessError:
                pass
            time.sleep(2)
        return False


class TaskTestHelper:
    """Helper class for task-related testing"""
    
    def __init__(self, data_dir: str = "/bot/data"):
        self.data_dir = Path(data_dir)
        self.queue_dir = self.data_dir / "queue"
        self.processed_dir = self.data_dir / "processed"
    
    def create_test_task(self, name: str, description: str, priority: str = "medium") -> str:
        """Create a test task in the queue"""
        task_id = str(uuid.uuid4())
        task = {
            "id": task_id,
            "name": name,
            "description": description,
            "priority": priority,
            "created_at": datetime.now().isoformat(),
            "status": "queued",
            "source": "test"
        }
        
        # Ensure queue directory exists
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        
        # Save task to queue
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{task_id[:8]}.json"
        task_file = self.queue_dir / filename
        
        with open(task_file, 'w') as f:
            json.dump(task, f, indent=2)
        
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task"""
        # Check queue
        for task_file in self.queue_dir.glob("*.json"):
            try:
                with open(task_file, 'r') as f:
                    task = json.load(f)
                    if task.get("id") == task_id:
                        return task
            except (json.JSONDecodeError, IOError):
                continue
        
        # Check processed
        for task_file in self.processed_dir.glob("*.json"):
            try:
                with open(task_file, 'r') as f:
                    task = json.load(f)
                    if task.get("id") == task_id:
                        return task
            except (json.JSONDecodeError, IOError):
                continue
        
        return None
    
    def wait_for_task_status(self, task_id: str, expected_status: str, timeout: int = 300) -> Dict[str, Any]:
        """Wait for a task to reach a specific status"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            task = self.get_task_status(task_id)
            if task and task.get("status") == expected_status:
                return task
            time.sleep(2)
        
        raise TimeoutError(f"Task {task_id} did not reach status '{expected_status}' within {timeout} seconds")
    
    def cleanup_test_tasks(self):
        """Clean up test tasks from queue and processed directories"""
        for directory in [self.queue_dir, self.processed_dir]:
            if directory.exists():
                for task_file in directory.glob("*.json"):
                    try:
                        with open(task_file, 'r') as f:
                            task = json.load(f)
                            if task.get("source") == "test":
                                task_file.unlink()
                    except (json.JSONDecodeError, IOError):
                        continue


class GitHubTestHelper:
    """Helper class for GitHub-related testing"""
    
    def __init__(self, repo: str, token: Optional[str] = None):
        self.repo = repo
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.test_issues = []
        self.test_prs = []
    
    def create_test_issue(self, title: str, body: str, labels: List[str] = None) -> str:
        """Create a test issue on GitHub"""
        if not self.token:
            raise ValueError("GitHub token is required")
        
        if labels is None:
            labels = ["claude-bot-test"]
        
        cmd = [
            "gh", "issue", "create",
            "--repo", self.repo,
            "--title", title,
            "--body", body,
            "--label", ",".join(labels)
        ]
        
        env = os.environ.copy()
        env["GITHUB_TOKEN"] = self.token
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env)
            issue_url = result.stdout.strip()
            self.test_issues.append(issue_url)
            return issue_url
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to create test issue: {e.stderr}")
    
    def close_test_issue(self, issue_url: str) -> bool:
        """Close a test issue"""
        if not self.token:
            return False
        
        issue_number = issue_url.split('/')[-1]
        cmd = ["gh", "issue", "close", issue_number, "--repo", self.repo]
        
        env = os.environ.copy()
        env["GITHUB_TOKEN"] = self.token
        
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True, env=env)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def cleanup_test_artifacts(self):
        """Clean up test issues and PRs"""
        for issue_url in self.test_issues:
            self.close_test_issue(issue_url)
        self.test_issues.clear()
        self.test_prs.clear()


def create_test_environment() -> Dict[str, str]:
    """Create a test environment configuration"""
    return {
        "PROJECT_PATH": ".",
        "TARGET_REPO": os.getenv("GITHUB_REPOSITORY", "test/repo"),
        "BOT_LABEL": "claude-bot-test",
        "ISSUE_CHECK_INTERVAL": "1",
        "PR_CHECK_INTERVAL": "1",
        "GIT_AUTHOR_NAME": "Claude Bot Test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Claude Bot Test",
        "GIT_COMMITTER_EMAIL": "test@example.com"
    }


def setup_test_logging():
    """Set up logging for tests"""
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)