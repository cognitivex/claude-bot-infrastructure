#!/usr/bin/env python3
"""
Basic Bot Functionality Integration Tests
Tests fundamental bot operations and workflows
"""

import pytest
import time
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.utils.test_helpers import (
    BotTestHelper,
    DockerTestHelper,
    TaskTestHelper,
    create_test_environment,
    setup_test_logging
)


class TestBotBasicFunctionality:
    """Test basic bot functionality"""
    
    @classmethod
    def setup_class(cls):
        """Set up test class"""
        cls.logger = setup_test_logging()
        cls.bot_helper = BotTestHelper()
        cls.docker_helper = DockerTestHelper()
        cls.task_helper = TaskTestHelper()
        
        # Ensure bot is running
        if not cls.docker_helper.is_container_running("claude-bot"):
            pytest.skip("Bot container is not running. Run 'docker-compose up -d' first.")
    
    def setup_method(self):
        """Set up each test method"""
        # Wait for bot to be ready
        assert self.bot_helper.wait_for_bot_ready(timeout=30), "Bot is not ready"
    
    def teardown_method(self):
        """Clean up after each test"""
        self.task_helper.cleanup_test_tasks()
        self.bot_helper.cleanup_test_artifacts()
    
    def test_bot_status_api(self):
        """Test that bot status API is working"""
        status = self.bot_helper.get_bot_status()
        
        assert "count" in status
        assert "statuses" in status
        assert status["count"] >= 0
        
        if status["count"] > 0:
            bot_status = status["statuses"][0]
            assert "bot_id" in bot_status
            assert "status" in bot_status
            assert "health" in bot_status
            assert "repository" in bot_status
    
    def test_bot_container_health(self):
        """Test that bot container is healthy"""
        assert self.docker_helper.is_container_running("claude-bot"), "Bot container is not running"
        assert self.docker_helper.is_container_running("claude-status-web"), "Status web container is not running"
        
        # Check that status web container is healthy
        assert self.docker_helper.wait_for_container_healthy("claude-status-web", timeout=30), \
            "Status web container is not healthy"
    
    def test_bot_responds_to_simple_task(self):
        """Test that bot can process a simple task"""
        # Create a simple test task
        task_id = self.task_helper.create_test_task(
            name="Test Simple Task",
            description="Create a file called test_output.txt with content 'Hello, Bot!'",
            priority="high"
        )
        
        self.logger.info(f"Created test task: {task_id}")
        
        # Wait for task to be processed (with reasonable timeout)
        try:
            completed_task = self.task_helper.wait_for_task_status(
                task_id, "completed", timeout=180
            )
            assert completed_task["status"] == "completed"
            self.logger.info(f"Task completed successfully: {completed_task}")
            
        except TimeoutError:
            # If task didn't complete, check its current status for debugging
            current_task = self.task_helper.get_task_status(task_id)
            pytest.fail(f"Task did not complete within timeout. Current status: {current_task}")
    
    def test_bot_handles_invalid_task(self):
        """Test that bot handles invalid tasks gracefully"""
        # Create a task with invalid/impossible requirements
        task_id = self.task_helper.create_test_task(
            name="Invalid Task",
            description="Delete the entire universe and create a black hole",
            priority="low"
        )
        
        self.logger.info(f"Created invalid test task: {task_id}")
        
        # Wait for task to be processed or timeout
        start_time = time.time()
        timeout = 60  # Shorter timeout for invalid tasks
        
        while time.time() - start_time < timeout:
            task = self.task_helper.get_task_status(task_id)
            if task and task.get("status") in ["completed", "failed"]:
                # Either outcome is acceptable for an invalid task
                self.logger.info(f"Invalid task handled: {task['status']}")
                return
            time.sleep(2)
        
        # Task should have been processed one way or another
        current_task = self.task_helper.get_task_status(task_id)
        assert current_task is not None, "Task disappeared from queue"
    
    def test_bot_queue_management(self):
        """Test bot's task queue management"""
        initial_status = self.bot_helper.get_bot_status()
        initial_queued = 0
        if initial_status["count"] > 0:
            initial_queued = initial_status["statuses"][0].get("queued_tasks", 0)
        
        # Create multiple tasks
        task_ids = []
        for i in range(3):
            task_id = self.task_helper.create_test_task(
                name=f"Queue Test Task {i+1}",
                description=f"Create a file called queue_test_{i+1}.txt",
                priority="medium"
            )
            task_ids.append(task_id)
        
        # Check that queued count increased
        time.sleep(2)  # Give bot time to detect new tasks
        updated_status = self.bot_helper.get_bot_status()
        if updated_status["count"] > 0:
            current_queued = updated_status["statuses"][0].get("queued_tasks", 0)
            assert current_queued >= initial_queued, "Queue count should have increased"
        
        # Wait for all tasks to be processed
        for task_id in task_ids:
            try:
                self.task_helper.wait_for_task_status(task_id, "completed", timeout=300)
            except TimeoutError:
                self.logger.warning(f"Task {task_id} did not complete within timeout")
    
    @pytest.mark.slow
    def test_bot_performance_basic(self):
        """Test basic bot performance metrics"""
        start_time = time.time()
        
        # Create a simple task and measure time to completion
        task_id = self.task_helper.create_test_task(
            name="Performance Test",
            description="Create a simple text file with timestamp",
            priority="high"
        )
        
        try:
            self.task_helper.wait_for_task_status(task_id, "completed", timeout=120)
            completion_time = time.time() - start_time
            
            # Basic performance assertion (should complete within reasonable time)
            assert completion_time < 120, f"Task took too long to complete: {completion_time}s"
            self.logger.info(f"Task completed in {completion_time:.2f} seconds")
            
        except TimeoutError:
            pytest.fail("Performance test task did not complete within expected time")
    
    def test_bot_error_recovery(self):
        """Test that bot can recover from errors"""
        # Get initial bot status
        initial_status = self.bot_helper.get_bot_status()
        assert initial_status["count"] > 0, "Bot should be reporting status"
        
        # Bot should maintain healthy status even after processing failed tasks
        task_id = self.task_helper.create_test_task(
            name="Error Recovery Test",
            description="Try to access a file that doesn't exist: /nonexistent/file.txt",
            priority="medium"
        )
        
        # Wait for task processing (may fail or succeed)
        time.sleep(30)
        
        # Check that bot is still responsive and healthy
        current_status = self.bot_helper.get_bot_status()
        assert current_status["count"] > 0, "Bot should still be reporting status"
        
        if current_status["count"] > 0:
            bot_status = current_status["statuses"][0]
            # Bot should still be functional (not in error state)
            assert bot_status["health"] in ["healthy", "idle"], \
                f"Bot health should be good, but is: {bot_status['health']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])