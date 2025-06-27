#!/usr/bin/env python3
"""
Workflow Manager for Claude Bot Infrastructure

Manages multi-step workflows for autonomous issue resolution.
Tracks workflow state and coordinates between different workflow steps.
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

class WorkflowStep(Enum):
    ANALYSIS = "analysis"
    PLANNING = "planning"
    IMPLEMENTATION = "implementation"
    PR_CREATION = "pr_creation"
    FEEDBACK_HANDLING = "feedback_handling"
    COMPLETION = "completion"

class WorkflowStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WAITING_FOR_FEEDBACK = "waiting_for_feedback"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"

@dataclass
class WorkflowState:
    workflow_id: str
    issue_number: int
    repo: str
    title: str
    description: str
    current_step: WorkflowStep
    status: WorkflowStatus
    created_at: datetime
    updated_at: datetime
    step_history: List[Dict[str, Any]]
    context: Dict[str, Any]
    retry_count: int = 0
    max_retries: int = 2
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        data['current_step'] = self.current_step.value
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'WorkflowState':
        """Create from dictionary."""
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        data['current_step'] = WorkflowStep(data['current_step'])
        data['status'] = WorkflowStatus(data['status'])
        return cls(**data)

class WorkflowManager:
    """Manages multi-step autonomous workflows for issue resolution."""
    
    def __init__(self, data_dir: str = "/bot/data"):
        self.data_dir = Path(data_dir)
        self.workflows_dir = self.data_dir / "workflows"
        self.workflows_dir.mkdir(parents=True, exist_ok=True)
        
        # Workflow step configuration
        self.step_configs = {
            WorkflowStep.ANALYSIS: {
                "template": "/bot/config/workflow-templates/01-issue-analysis.md",
                "max_duration": timedelta(hours=1),
                "next_step": WorkflowStep.PLANNING,
                "can_wait_for_feedback": True
            },
            WorkflowStep.PLANNING: {
                "template": "/bot/config/workflow-templates/02-planning-breakdown.md",
                "max_duration": timedelta(hours=2),
                "next_step": WorkflowStep.IMPLEMENTATION,
                "can_wait_for_feedback": True
            },
            WorkflowStep.IMPLEMENTATION: {
                "template": "/bot/config/workflow-templates/03-implementation.md",
                "max_duration": timedelta(hours=8),
                "next_step": WorkflowStep.PR_CREATION,
                "can_wait_for_feedback": False
            },
            WorkflowStep.PR_CREATION: {
                "template": "/bot/config/workflow-templates/04-pr-creation-feedback.md",
                "max_duration": timedelta(hours=1),
                "next_step": WorkflowStep.FEEDBACK_HANDLING,
                "can_wait_for_feedback": False
            },
            WorkflowStep.FEEDBACK_HANDLING: {
                "template": "/bot/config/workflow-templates/04-pr-creation-feedback.md",
                "max_duration": timedelta(days=7),
                "next_step": WorkflowStep.COMPLETION,
                "can_wait_for_feedback": True
            },
            WorkflowStep.COMPLETION: {
                "template": None,
                "max_duration": timedelta(hours=1),
                "next_step": None,
                "can_wait_for_feedback": False
            }
        }
    
    def create_workflow(self, issue_number: int, repo: str, title: str, 
                       description: str, context: Dict[str, Any] = None) -> str:
        """Create a new workflow for an issue."""
        workflow_id = f"workflow-{repo.replace('/', '-')}-{issue_number}-{int(datetime.now().timestamp())}"
        
        workflow = WorkflowState(
            workflow_id=workflow_id,
            issue_number=issue_number,
            repo=repo,
            title=title,
            description=description,
            current_step=WorkflowStep.ANALYSIS,
            status=WorkflowStatus.PENDING,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            step_history=[],
            context=context or {},
            retry_count=0
        )
        
        self._save_workflow(workflow)
        return workflow_id
    
    def get_workflow(self, workflow_id: str) -> Optional[WorkflowState]:
        """Get workflow by ID."""
        workflow_file = self.workflows_dir / f"{workflow_id}.json"
        if not workflow_file.exists():
            return None
        
        try:
            with open(workflow_file, 'r') as f:
                data = json.load(f)
            return WorkflowState.from_dict(data)
        except Exception as e:
            print(f"Error loading workflow {workflow_id}: {e}")
            return None
    
    def update_workflow(self, workflow_id: str, status: WorkflowStatus = None,
                       context_updates: Dict[str, Any] = None, 
                       step_result: Dict[str, Any] = None) -> bool:
        """Update workflow status and context."""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return False
        
        workflow.updated_at = datetime.now()
        
        if status:
            workflow.status = status
        
        if context_updates:
            workflow.context.update(context_updates)
        
        if step_result:
            workflow.step_history.append({
                "step": workflow.current_step.value,
                "timestamp": datetime.now().isoformat(),
                "result": step_result
            })
        
        self._save_workflow(workflow)
        return True
    
    def advance_workflow(self, workflow_id: str, step_result: Dict[str, Any] = None) -> bool:
        """Advance workflow to next step."""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return False
        
        # Record current step completion
        if step_result:
            workflow.step_history.append({
                "step": workflow.current_step.value,
                "timestamp": datetime.now().isoformat(),
                "result": step_result,
                "status": "completed"
            })
        
        # Advance to next step
        next_step = self.step_configs[workflow.current_step]["next_step"]
        if next_step:
            workflow.current_step = next_step
            workflow.status = WorkflowStatus.PENDING
            workflow.retry_count = 0
            
            # If we just advanced to completion step, mark as completed
            if workflow.current_step == WorkflowStep.COMPLETION:
                workflow.status = WorkflowStatus.COMPLETED
        else:
            workflow.status = WorkflowStatus.COMPLETED
        
        workflow.updated_at = datetime.now()
        self._save_workflow(workflow)
        return True
    
    def retry_current_step(self, workflow_id: str, error_message: str = None) -> bool:
        """Retry the current step if retries are available."""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return False
        
        if workflow.retry_count >= workflow.max_retries:
            workflow.status = WorkflowStatus.FAILED
            workflow.context["failure_reason"] = f"Max retries exceeded: {error_message}"
        else:
            workflow.retry_count += 1
            workflow.status = WorkflowStatus.PENDING
            workflow.context["last_error"] = error_message
            
            # Record retry in history
            workflow.step_history.append({
                "step": workflow.current_step.value,
                "timestamp": datetime.now().isoformat(),
                "result": {"error": error_message, "retry": workflow.retry_count},
                "status": "retry"
            })
        
        workflow.updated_at = datetime.now()
        self._save_workflow(workflow)
        return workflow.status != WorkflowStatus.FAILED
    
    def get_next_work_item(self, worker_capabilities: Dict[str, str] = None) -> Optional[Dict[str, Any]]:
        """Get next workflow step that needs processing."""
        # Find pending workflows
        for workflow_file in self.workflows_dir.glob("*.json"):
            workflow = self.get_workflow(workflow_file.stem)
            if not workflow:
                continue
            
            # Skip if not pending or if blocked
            if workflow.status not in [WorkflowStatus.PENDING]:
                continue
            
            # Check if workflow has timed out
            if self._is_workflow_timed_out(workflow):
                self.retry_current_step(workflow.workflow_id, "Workflow step timed out")
                continue
            
            # Check if worker has required capabilities (if any specified)
            if not self._worker_can_handle_step(workflow, worker_capabilities):
                continue
            
            # Return work item for this step
            return {
                "workflow_id": workflow.workflow_id,
                "task_id": f"{workflow.workflow_id}-{workflow.current_step.value}",
                "workflow_step": workflow.current_step.value,
                "issue_number": workflow.issue_number,
                "repo": workflow.repo,
                "title": workflow.title,
                "description": workflow.description,
                "template_path": self.step_configs[workflow.current_step]["template"],
                "context": workflow.context,
                "step_history": workflow.step_history,
                "retry_count": workflow.retry_count
            }
        
        return None
    
    def mark_step_in_progress(self, workflow_id: str, worker_id: str) -> bool:
        """Mark current step as in progress."""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return False
        
        workflow.status = WorkflowStatus.IN_PROGRESS
        workflow.context["current_worker"] = worker_id
        workflow.context["step_started_at"] = datetime.now().isoformat()
        workflow.updated_at = datetime.now()
        
        self._save_workflow(workflow)
        return True
    
    def mark_step_waiting_for_feedback(self, workflow_id: str, feedback_context: Dict[str, Any] = None) -> bool:
        """Mark current step as waiting for human feedback."""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return False
        
        if not self.step_configs[workflow.current_step]["can_wait_for_feedback"]:
            return False
        
        workflow.status = WorkflowStatus.WAITING_FOR_FEEDBACK
        workflow.context["feedback_requested_at"] = datetime.now().isoformat()
        if feedback_context:
            workflow.context.update(feedback_context)
        
        workflow.updated_at = datetime.now()
        self._save_workflow(workflow)
        return True
    
    def list_active_workflows(self) -> List[WorkflowState]:
        """List all active workflows."""
        workflows = []
        for workflow_file in self.workflows_dir.glob("*.json"):
            workflow = self.get_workflow(workflow_file.stem)
            if workflow and workflow.status != WorkflowStatus.COMPLETED:
                workflows.append(workflow)
        
        return sorted(workflows, key=lambda w: w.created_at, reverse=True)
    
    def get_workflow_stats(self) -> Dict[str, Any]:
        """Get workflow statistics."""
        stats = {
            "total_workflows": 0,
            "by_status": {},
            "by_step": {},
            "average_duration": None,
            "completion_rate": 0
        }
        
        workflows = []
        for workflow_file in self.workflows_dir.glob("*.json"):
            workflow = self.get_workflow(workflow_file.stem)
            if workflow:
                workflows.append(workflow)
        
        if not workflows:
            return stats
        
        stats["total_workflows"] = len(workflows)
        
        # Count by status
        for workflow in workflows:
            status = workflow.status.value
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
        
        # Count by current step
        for workflow in workflows:
            step = workflow.current_step.value
            stats["by_step"][step] = stats["by_step"].get(step, 0) + 1
        
        # Calculate completion rate
        completed = stats["by_status"].get("completed", 0)
        stats["completion_rate"] = (completed / len(workflows)) * 100 if workflows else 0
        
        return stats
    
    def _save_workflow(self, workflow: WorkflowState):
        """Save workflow to disk."""
        workflow_file = self.workflows_dir / f"{workflow.workflow_id}.json"
        with open(workflow_file, 'w') as f:
            json.dump(workflow.to_dict(), f, indent=2)
    
    def _is_workflow_timed_out(self, workflow: WorkflowState) -> bool:
        """Check if current step has timed out."""
        if workflow.status != WorkflowStatus.IN_PROGRESS:
            return False
        
        step_config = self.step_configs[workflow.current_step]
        max_duration = step_config["max_duration"]
        
        step_started = workflow.context.get("step_started_at")
        if not step_started:
            return False
        
        started_time = datetime.fromisoformat(step_started)
        return datetime.now() - started_time > max_duration
    
    def _worker_can_handle_step(self, workflow: WorkflowState, 
                               worker_capabilities: Dict[str, str] = None) -> bool:
        """Check if worker can handle the current workflow step."""
        # For now, assume all workers can handle all steps
        # In the future, could check platform requirements, etc.
        return True

def create_workflow_manager(data_dir: str = "/bot/data") -> WorkflowManager:
    """Factory function to create a workflow manager."""
    return WorkflowManager(data_dir)

if __name__ == "__main__":
    # Test the workflow manager
    manager = WorkflowManager("/tmp/test_workflows")
    
    # Create a test workflow
    workflow_id = manager.create_workflow(
        issue_number=123,
        repo="test/repo",
        title="Test Issue",
        description="This is a test issue",
        context={"priority": "high"}
    )
    
    print(f"Created workflow: {workflow_id}")
    
    # Get next work item
    work_item = manager.get_next_work_item()
    print(f"Next work item: {work_item}")
    
    # Advance workflow
    manager.advance_workflow(workflow_id, {"analysis_result": "Issue analyzed"})
    
    # Check stats
    stats = manager.get_workflow_stats()
    print(f"Workflow stats: {stats}")