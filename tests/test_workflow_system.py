#!/usr/bin/env python3
"""
Test Script for Multi-Step Workflow System

Tests the new workflow manager, templates, and worker coordination.
"""

import os
import sys
import tempfile
import shutil
import json
from pathlib import Path

# Add src directory to path for new structure
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(script_dir, '..', 'src'))

from claude_bot.orchestrator.workflow_manager import create_workflow_manager, WorkflowStep, WorkflowStatus
from claude_bot.orchestrator.workflow_worker import WorkflowWorker

def test_workflow_manager():
    """Test workflow manager functionality."""
    print("🧪 Testing Workflow Manager...")
    
    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = create_workflow_manager(temp_dir)
        
        # Test workflow creation
        workflow_id = manager.create_workflow(
            issue_number=123,
            repo="test/repo",
            title="Test Issue: Add new feature",
            description="This is a test issue for adding a new feature to the system.",
            context={"priority": "high", "complexity": "moderate"}
        )
        
        print(f"✅ Created workflow: {workflow_id}")
        
        # Test workflow retrieval
        workflow = manager.get_workflow(workflow_id)
        assert workflow is not None
        assert workflow.issue_number == 123
        assert workflow.current_step == WorkflowStep.ANALYSIS
        assert workflow.status == WorkflowStatus.PENDING
        print(f"✅ Retrieved workflow: {workflow.current_step.value}")
        
        # Test getting next work item
        work_item = manager.get_next_work_item()
        assert work_item is not None
        assert work_item["workflow_step"] == "analysis"
        print(f"✅ Got next work item: {work_item['workflow_step']}")
        
        # Test marking step in progress
        manager.mark_step_in_progress(workflow_id, "test-worker")
        workflow = manager.get_workflow(workflow_id)
        assert workflow.status == WorkflowStatus.IN_PROGRESS
        print(f"✅ Marked step in progress: {workflow.status.value}")
        
        # Test advancing workflow
        step_result = {"analysis_complete": True, "requirements_clear": True}
        manager.advance_workflow(workflow_id, step_result)
        workflow = manager.get_workflow(workflow_id)
        assert workflow.current_step == WorkflowStep.PLANNING
        assert workflow.status == WorkflowStatus.PENDING
        print(f"✅ Advanced to next step: {workflow.current_step.value}")
        
        # Test workflow statistics
        stats = manager.get_workflow_stats()
        assert stats["total_workflows"] == 1
        print(f"✅ Workflow stats: {stats}")
        
        return True

def test_workflow_templates():
    """Test that workflow templates exist and are readable."""
    print("\\n🧪 Testing Workflow Templates...")
    
    template_dir = Path("config/workflow-templates")
    templates = [
        "01-issue-analysis.md",
        "02-planning-breakdown.md", 
        "03-implementation.md",
        "04-pr-creation-feedback.md"
    ]
    
    for template in templates:
        template_path = template_dir / template
        if template_path.exists():
            with open(template_path, 'r') as f:
                content = f.read()
                assert len(content) > 100  # Basic sanity check
                print(f"✅ Template {template}: {len(content)} characters")
        else:
            print(f"❌ Template {template}: NOT FOUND")
            return False
    
    return True

def test_workflow_worker_initialization():
    """Test workflow worker initialization."""
    print("\\n🧪 Testing Workflow Worker...")
    
    try:
        # Create temporary directories
        with tempfile.TemporaryDirectory() as temp_workspace:
            with tempfile.TemporaryDirectory() as temp_data:
                # Initialize a git repo in workspace
                os.system(f"cd {temp_workspace} && git init && git remote add origin https://github.com/test/repo.git")
                
                # Test worker initialization
                worker = WorkflowWorker(
                    workspace_dir=temp_workspace,
                    data_dir=temp_data,
                    workflow_id=None,
                    repo="test/repo"
                )
                
                # Test capabilities detection
                capabilities = worker.get_worker_capabilities()
                assert isinstance(capabilities, dict)
                print(f"✅ Worker capabilities: {capabilities}")
                
                # Test project context detection
                context = worker.detect_project_context()
                assert isinstance(context, dict)
                print(f"✅ Project context: {context}")
                
                # Test template loading (with fallback)
                template = worker.get_fallback_template()
                assert len(template) > 50
                print(f"✅ Fallback template: {len(template)} characters")
                
                return True
                
    except Exception as e:
        print(f"❌ Workflow worker test failed: {e}")
        return False

def test_workflow_integration():
    """Test full workflow integration."""
    print("\\n🧪 Testing Workflow Integration...")
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create workflow manager
            manager = create_workflow_manager(temp_dir)
            
            # Create a complete workflow
            workflow_id = manager.create_workflow(
                issue_number=456,
                repo="test/integration",
                title="Integration Test Issue",
                description="Testing the full workflow integration process.",
                context={
                    "platform_requirements": {"nodejs": "18.16.0"},
                    "priority": "medium",
                    "complexity": "simple"
                }
            )
            
            # Simulate workflow progression through all steps
            steps = [
                WorkflowStep.ANALYSIS,
                WorkflowStep.PLANNING, 
                WorkflowStep.IMPLEMENTATION,
                WorkflowStep.PR_CREATION,
                WorkflowStep.FEEDBACK_HANDLING,
                WorkflowStep.COMPLETION
            ]
            
            for i, expected_step in enumerate(steps[:-1]):  # Exclude completion
                workflow = manager.get_workflow(workflow_id)
                assert workflow.current_step == expected_step
                print(f"✅ Step {i+1}: {expected_step.value}")
                
                # Mark in progress
                manager.mark_step_in_progress(workflow_id, f"worker-{i}")
                
                # Complete step
                step_result = {
                    "step": expected_step.value,
                    "completed": True,
                    "worker": f"worker-{i}"
                }
                manager.advance_workflow(workflow_id, step_result)
            
            # Check final state
            workflow = manager.get_workflow(workflow_id)
            assert workflow.status == WorkflowStatus.COMPLETED
            assert len(workflow.step_history) == 5  # All steps except completion
            print(f"✅ Workflow completed with {len(workflow.step_history)} steps")
            
            return True
            
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

def test_error_handling():
    """Test workflow error handling and retry logic."""
    print("\\n🧪 Testing Error Handling...")
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = create_workflow_manager(temp_dir)
            
            # Create workflow
            workflow_id = manager.create_workflow(
                issue_number=789,
                repo="test/error",
                title="Error Test Issue",
                description="Testing error handling and retry logic."
            )
            
            # Mark in progress
            manager.mark_step_in_progress(workflow_id, "error-worker")
            
            # Test retry logic
            workflow = manager.get_workflow(workflow_id)
            initial_retry_count = workflow.retry_count
            
            # Retry current step
            success = manager.retry_current_step(workflow_id, "Simulated error")
            assert success
            
            workflow = manager.get_workflow(workflow_id)
            assert workflow.retry_count == initial_retry_count + 1
            assert workflow.status == WorkflowStatus.PENDING
            print(f"✅ Retry successful: count = {workflow.retry_count}")
            
            # Test max retries exceeded
            for i in range(2):  # Should reach max retries (default 2)
                manager.retry_current_step(workflow_id, f"Error attempt {i+2}")
            
            workflow = manager.get_workflow(workflow_id)
            assert workflow.status == WorkflowStatus.FAILED
            print(f"✅ Max retries reached: status = {workflow.status.value}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

def main():
    """Run all workflow system tests."""
    print("🚀 Testing Multi-Step Workflow System\\n")
    
    tests = [
        ("Workflow Manager", test_workflow_manager),
        ("Workflow Templates", test_workflow_templates),
        ("Workflow Worker", test_workflow_worker_initialization),
        ("Workflow Integration", test_workflow_integration),
        ("Error Handling", test_error_handling)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                print(f"✅ {test_name}: PASSED\\n")
            else:
                print(f"❌ {test_name}: FAILED\\n")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}\\n")
            results.append((test_name, False))
    
    # Summary
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\\n📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All workflow system tests passed!")
        return 0
    else:
        print("💥 Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())