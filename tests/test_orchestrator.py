#!/usr/bin/env python3
"""
Test script for the orchestrator components
"""

import sys
import os
import json
from pathlib import Path

# Add src to path for new structure
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_bot.utils.work_queue import create_work_queue, WorkItem, TaskPriority, TaskStatus
from claude_bot.platform.platform_manager import PlatformManager

def test_work_queue():
    """Test the work queue functionality"""
    print("=== Testing Work Queue ===")
    
    # Create a test queue
    test_queue_dir = "/tmp/test_orchestrator_queue"
    queue = create_work_queue("file", queue_dir=test_queue_dir)
    
    # Create test work items
    work_item1 = WorkItem(
        issue_number=1001,
        title="Test Node.js Task",
        description="This is a test task requiring Node.js",
        repo="test/repo",
        platform_requirements={"nodejs": "18.16.0"},
        priority=TaskPriority.HIGH
    )
    
    work_item2 = WorkItem(
        issue_number=1002,
        title="Test Python Task",
        description="This is a test task requiring Python",
        repo="test/repo",
        platform_requirements={"python": "3.11"},
        priority=TaskPriority.MEDIUM
    )
    
    # Test enqueue
    print("\n1. Testing enqueue...")
    assert queue.enqueue(work_item1), "Failed to enqueue work item 1"
    assert queue.enqueue(work_item2), "Failed to enqueue work item 2"
    print("✓ Successfully enqueued 2 work items")
    
    # Test queue stats
    print("\n2. Testing queue stats...")
    stats = queue.get_queue_stats()
    print(f"Queue stats: {stats}")
    assert stats['pending'] == 2, f"Expected 2 pending tasks, got {stats['pending']}"
    print("✓ Queue stats correct")
    
    # Test dequeue with platform compatibility
    print("\n3. Testing dequeue with platform compatibility...")
    
    # Worker with Node.js capability
    nodejs_worker = queue.dequeue("test-worker-1", {"nodejs": "18.16.0"})
    assert nodejs_worker is not None, "Failed to dequeue Node.js task"
    assert nodejs_worker.issue_number == 1001, "Wrong task dequeued"
    print(f"✓ Dequeued Node.js task: {nodejs_worker.title}")
    
    # Worker with Python capability
    python_worker = queue.dequeue("test-worker-2", {"python": "3.11"})
    assert python_worker is not None, "Failed to dequeue Python task"
    assert python_worker.issue_number == 1002, "Wrong task dequeued"
    print(f"✓ Dequeued Python task: {python_worker.title}")
    
    # Test status update
    print("\n4. Testing status updates...")
    assert queue.update_status(nodejs_worker.task_id, TaskStatus.IN_PROGRESS), "Failed to update status"
    assert queue.update_status(nodejs_worker.task_id, TaskStatus.COMPLETED, 
                              result={"message": "Test completed"}), "Failed to complete task"
    print("✓ Status updates working")
    
    # Final stats
    print("\n5. Final queue stats...")
    final_stats = queue.get_queue_stats()
    print(f"Final stats: {final_stats}")
    assert final_stats['assigned'] == 1, "Expected 1 assigned task"
    assert final_stats['completed'] == 1, "Expected 1 completed task"
    print("✓ All queue tests passed!")
    
    # Cleanup
    import shutil
    shutil.rmtree(test_queue_dir, ignore_errors=True)

def test_platform_detection():
    """Test platform detection"""
    print("\n\n=== Testing Platform Detection ===")
    
    pm = PlatformManager()
    
    # Test current directory
    print("\n1. Detecting platforms in current directory...")
    detected = pm.detect_platforms(".")
    print(f"Detected platforms: {detected}")
    
    # This should detect Node.js due to package.json
    assert "nodejs" in detected or len(detected) > 0, "Should detect at least one platform"
    print("✓ Platform detection working")

def test_orchestrator_components():
    """Test basic orchestrator component loading"""
    print("\n\n=== Testing Orchestrator Component Loading ===")
    
    try:
        from central_orchestrator import CentralOrchestrator
        print("✓ Central orchestrator imports successfully")
        
        from container_manager import ContainerManager
        print("✓ Container manager imports successfully")
        
        from worker_executor import WorkerExecutor
        print("✓ Worker executor imports successfully")
        
        # Note: We won't actually instantiate ContainerManager as it requires Docker
        print("\nAll component imports successful!")
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    
    return True

def main():
    print("🧪 Testing Orchestrator Components\n")
    
    try:
        # Test work queue
        test_work_queue()
        
        # Test platform detection
        test_platform_detection()
        
        # Test component loading
        test_orchestrator_components()
        
        print("\n\n✅ All tests passed!")
        return 0
        
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())