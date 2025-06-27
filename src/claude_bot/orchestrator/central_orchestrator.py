#!/usr/bin/env python3
"""
Central Orchestrator for Claude Bot Infrastructure

Master coordinator that monitors GitHub issues, manages work queue,
and spawns dynamic worker containers to process tasks in parallel.
"""

import time
import json
import schedule
import argparse
import sys
import os
import threading
import logging
from datetime import datetime, timedelta
from pathlib import Path
import signal

# Add the scripts directory to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Import our modules
from work_queue import create_work_queue, WorkItem, TaskStatus, TaskPriority
from container_manager import ContainerManager
from platform_manager import PlatformManager
from status_reporter import StatusReporter
from workflow_manager import create_workflow_manager, WorkflowStep, WorkflowStatus

class CentralOrchestrator:
    """Central orchestrator for distributed Claude Bot system."""
    
    def __init__(self, workspace_dir="/workspace", data_dir="/bot/data", 
                 repo=None, bot_id=None, max_workers=3):
        """
        Initialize central orchestrator.
        
        Args:
            workspace_dir: Path to workspace directory
            data_dir: Path to bot data directory  
            repo: GitHub repository (owner/repo format)
            bot_id: Bot identifier for status reporting
            max_workers: Maximum concurrent workers
        """
        self.workspace_dir = workspace_dir
        self.data_dir = Path(data_dir)
        self.repo = repo
        self.bot_id = bot_id or os.getenv('BOT_ID', 'claude-orchestrator')
        self.max_workers = max_workers
        
        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.work_queue = create_work_queue("file", queue_dir=str(self.data_dir / "queue"))
        self.workflow_manager = create_workflow_manager(str(self.data_dir))
        self.container_manager = ContainerManager(
            workspace_dir=workspace_dir,
            data_dir=str(self.data_dir),
            max_workers=max_workers
        )
        self.platform_manager = PlatformManager()
        
        # Initialize status reporter
        self.status_reporter = StatusReporter(
            bot_id=self.bot_id,
            data_dir=str(self.data_dir),
            status_web_url=os.getenv('STATUS_WEB_URL')
        )
        
        # Bot configuration
        self.bot_label = os.getenv('BOT_LABEL', 'claude-bot')
        
        # Orchestrator state
        self.running = False
        self.stats = {
            "started_at": None,
            "tasks_processed": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "workers_spawned": 0
        }
        
        # Threading
        self._shutdown_event = threading.Event()
        self._lock = threading.Lock()
        
        # Logging
        self.logger = logging.getLogger(__name__)
        
        print(f"🚀 Central Orchestrator initialized")
        print(f"Bot ID: {self.bot_id}")
        print(f"Repository: {self.repo}")
        print(f"Max workers: {self.max_workers}")
        print(f"Bot label: {self.bot_label}")
    
    def get_repo_from_git(self):
        """Get repository name from git remote"""
        try:
            import subprocess
            result = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                capture_output=True,
                text=True,
                cwd=self.workspace_dir
            )
            if result.returncode == 0:
                url = result.stdout.strip()
                if "github.com" in url:
                    parts = url.split("/")[-2:]
                    repo_name = parts[1].replace(".git", "")
                    return f"{parts[0]}/{repo_name}"
            return None
        except Exception as e:
            self.logger.error(f"Error getting repo: {e}")
            return None
    
    def discover_github_issues(self) -> list:
        """Discover GitHub issues that need processing."""
        if not self.repo:
            self.logger.warning("No repository configured for issue discovery")
            return []
        
        try:
            import subprocess
            
            # Get issues with bot label that aren't completed or failed
            cmd = f'gh issue list --repo {self.repo} --label "{self.bot_label}" --state open --json number,title,body,labels,createdAt'
            
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                cwd=self.workspace_dir
            )
            
            if result.returncode != 0:
                self.logger.error(f"Error fetching issues: {result.stderr}")
                return []
            
            issues = json.loads(result.stdout)
            
            # Filter out issues already processed or in progress
            new_issues = []
            for issue in issues:
                labels = [label['name'] for label in issue.get('labels', [])]
                
                # Skip if already completed, failed, or in progress
                if any(status in labels for status in ['bot:completed', 'bot:failed', 'bot:in-progress']):
                    continue
                
                # Check if already in our work queue
                existing_task = self._find_existing_task(issue['number'])
                if not existing_task:
                    new_issues.append(issue)
            
            self.logger.info(f"Discovered {len(new_issues)} new issues")
            return new_issues
            
        except Exception as e:
            self.logger.error(f"Failed to discover GitHub issues: {e}")
            return []
    
    def _find_existing_task(self, issue_number) -> bool:
        """Check if a workflow for this issue already exists."""
        try:
            # Check active workflows for this issue
            active_workflows = self.workflow_manager.list_active_workflows()
            for workflow in active_workflows:
                if workflow.issue_number == issue_number and workflow.repo == self.repo:
                    return True
            return False
        except Exception:
            return False
    
    def create_workflows(self, issues: list) -> list:
        """Convert GitHub issues to workflows."""
        workflow_ids = []
        
        for issue in issues:
            try:
                # Detect platform requirements
                issue_text = f"{issue.get('title', '')} {issue.get('body', '')}"
                platform_requirements = self._detect_platform_requirements(issue_text)
                
                # Determine priority based on labels
                priority = self._determine_priority(issue.get('labels', []))
                
                # Create workflow context
                context = {
                    "platform_requirements": platform_requirements,
                    "priority": priority.value if hasattr(priority, 'value') else str(priority),
                    "labels": [label['name'] for label in issue.get('labels', [])],
                    "created_at": issue.get('createdAt'),
                    "discovered_by": self.bot_id
                }
                
                workflow_id = self.workflow_manager.create_workflow(
                    issue_number=issue['number'],
                    repo=self.repo,
                    title=issue['title'],
                    description=issue.get('body', ''),
                    context=context
                )
                
                workflow_ids.append(workflow_id)
                self.logger.info(f"Created workflow {workflow_id} for issue #{issue['number']}: {issue['title']}")
                
            except Exception as e:
                self.logger.error(f"Failed to create workflow for issue #{issue.get('number', 'unknown')}: {e}")
        
        return workflow_ids
    
    def _detect_platform_requirements(self, text: str) -> dict:
        """Detect platform requirements from issue text."""
        # Simple keyword-based detection
        # In a real implementation, this could be more sophisticated
        requirements = {}
        
        text_lower = text.lower()
        
        # Node.js detection
        if any(keyword in text_lower for keyword in ['node', 'npm', 'javascript', 'typescript', 'react', 'vue', 'angular']):
            requirements['nodejs'] = '18.16.0'
        
        # .NET detection
        if any(keyword in text_lower for keyword in ['.net', 'dotnet', 'csharp', 'c#', 'asp.net']):
            requirements['dotnet'] = '8.0'
        
        # Python detection
        if any(keyword in text_lower for keyword in ['python', 'django', 'flask', 'fastapi', 'pip']):
            requirements['python'] = '3.11'
        
        # Java detection
        if any(keyword in text_lower for keyword in ['java', 'maven', 'gradle', 'spring']):
            requirements['java'] = '17'
        
        # Default to Node.js if nothing detected
        if not requirements:
            requirements['nodejs'] = '18.16.0'
        
        return requirements
    
    def _determine_priority(self, labels: list) -> TaskPriority:
        """Determine task priority from GitHub labels."""
        label_names = [label.get('name', '').lower() for label in labels]
        
        if any(priority in label_names for priority in ['urgent', 'critical', 'p0']):
            return TaskPriority.URGENT
        elif any(priority in label_names for priority in ['high', 'important', 'p1']):
            return TaskPriority.HIGH
        elif any(priority in label_names for priority in ['low', 'minor', 'p3']):
            return TaskPriority.LOW
        else:
            return TaskPriority.MEDIUM
    
    def enqueue_work_items(self, work_items: list) -> int:
        """Add work items to the queue."""
        enqueued_count = 0
        
        for work_item in work_items:
            try:
                if self.work_queue.enqueue(work_item):
                    enqueued_count += 1
                    self.logger.info(f"Enqueued task {work_item.task_id}")
            except Exception as e:
                self.logger.error(f"Failed to enqueue work item {work_item.task_id}: {e}")
        
        return enqueued_count
    
    def process_workflow_queue(self):
        """Process pending workflow steps by spawning workers."""
        try:
            # Get workflow statistics
            workflow_stats = self.workflow_manager.get_workflow_stats()
            active_workflows = len([w for w in self.workflow_manager.list_active_workflows() 
                                  if w.status in [WorkflowStatus.PENDING, WorkflowStatus.IN_PROGRESS]])
            
            if active_workflows == 0:
                return
            
            # Check how many workers we can spawn
            worker_stats = self.container_manager.get_worker_stats()
            active_workers = worker_stats['active_workers']
            available_slots = self.max_workers - active_workers
            
            if available_slots <= 0:
                self.logger.debug(f"All worker slots occupied ({active_workers}/{self.max_workers})")
                return
            
            self.logger.info(f"Processing workflows: {active_workflows} active, {active_workers} workers, {available_slots} slots available")
            
            # Spawn workers for available workflow steps
            spawned = 0
            for _ in range(min(available_slots, active_workflows)):
                # Get next workflow step
                next_step = self.workflow_manager.get_next_work_item()
                if not next_step:
                    break
                if self._spawn_workflow_worker(next_step):
                    spawned += 1
                    with self._lock:
                        self.stats['workers_spawned'] += 1
                else:
                    break
            
            if spawned > 0:
                self.logger.info(f"Spawned {spawned} new workers")
                
        except Exception as e:
            self.logger.error(f"Error processing workflow queue: {e}")
    
    def _spawn_workflow_worker(self, workflow_step: dict) -> bool:
        """Spawn a workflow worker for a specific workflow step."""
        try:
            # Create work item from workflow step for container spawning
            work_item = WorkItem(
                task_id=workflow_step["task_id"],
                title=workflow_step["title"],
                description=workflow_step["description"],
                repo=workflow_step["repo"],
                platform_requirements=workflow_step["context"].get("platform_requirements", {"nodejs": "18.16.0"})
            )
            
            # Spawn worker with workflow context
            container_id = self.container_manager.spawn_worker(
                work_item, 
                worker_script="workflow_worker.py",
                environment_vars={
                    "WORKFLOW_ID": workflow_step["workflow_id"],
                    "TASK_ID": workflow_step["task_id"]
                }
            )
            
            if container_id:
                # Mark workflow step as assigned to worker
                self.workflow_manager.mark_step_in_progress(
                    workflow_step["workflow_id"], 
                    container_id
                )
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to spawn workflow worker: {e}")
            return False
    
    def monitor_workers(self):
        """Monitor active workers and update task status."""
        try:
            status_updates = self.container_manager.monitor_workers()
            
            for task_id, status in status_updates.items():
                self.logger.info(f"Worker status update - Task {task_id}: {status}")
                
                # Update stats based on worker completion
                if status in ["exited", "removed"]:
                    # Try to determine if task completed successfully
                    task = self.work_queue.get_task(task_id)
                    if task:
                        with self._lock:
                            if task.status == TaskStatus.COMPLETED:
                                self.stats['tasks_completed'] += 1
                            elif task.status == TaskStatus.FAILED:
                                self.stats['tasks_failed'] += 1
                
        except Exception as e:
            self.logger.error(f"Error monitoring workers: {e}")
    
    def cleanup_stale_resources(self):
        """Clean up stale tasks and workers."""
        try:
            # Cleanup stale queue tasks
            stale_tasks = self.work_queue.cleanup_stale_tasks(timeout_minutes=30)
            if stale_tasks > 0:
                self.logger.info(f"Cleaned up {stale_tasks} stale queue tasks")
            
            # Cleanup stale workers
            stale_workers = self.container_manager.cleanup_stale_workers(timeout_minutes=60)
            if stale_workers > 0:
                self.logger.info(f"Cleaned up {stale_workers} stale workers")
                
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    def update_status(self):
        """Update orchestrator status."""
        try:
            # Gather stats
            queue_stats = self.work_queue.get_queue_stats()
            worker_stats = self.container_manager.get_worker_stats()
            
            orchestrator_stats = {
                **self.stats,
                "queue": queue_stats,
                "workers": worker_stats,
                "last_updated": datetime.now().isoformat()
            }
            
            # Update status reporter with orchestrator stats
            self.status_reporter.orchestrator_stats = orchestrator_stats
            self.status_reporter.generate_and_publish()
            
        except Exception as e:
            self.logger.error(f"Failed to update status: {e}")
    
    def run_discovery_cycle(self):
        """Run a complete discovery and workflow creation cycle."""
        try:
            self.logger.info("🔍 Running discovery cycle")
            
            # Discover new GitHub issues
            issues = self.discover_github_issues()
            
            if issues:
                # Convert to workflows
                workflow_ids = self.create_workflows(issues)
                
                if workflow_ids:
                    with self._lock:
                        self.stats['tasks_processed'] += len(workflow_ids)
                    
                    self.logger.info(f"✅ Discovery cycle completed: {len(workflow_ids)} new workflows created")
                else:
                    self.logger.info("✅ Discovery cycle completed: no new workflows created")
            else:
                self.logger.info("✅ Discovery cycle completed: no new issues found")
                
        except Exception as e:
            self.logger.error(f"Error in discovery cycle: {e}")
    
    def run_processing_cycle(self):
        """Run a complete processing cycle."""
        try:
            self.logger.debug("⚙️ Running processing cycle")
            
            # Process workflow queue (spawn workers)
            self.process_workflow_queue()
            
            # Monitor active workers
            self.monitor_workers()
            
        except Exception as e:
            self.logger.error(f"Error in processing cycle: {e}")
    
    def start_orchestration(self, discovery_interval=10, processing_interval=2, 
                          cleanup_interval=60, status_interval=30):
        """Start the orchestration loop."""
        
        if not self.repo:
            # Try to detect repo
            self.repo = self.get_repo_from_git()
            if not self.repo:
                self.logger.error("No repository configured and couldn't detect from git")
                return
        
        self.running = True
        with self._lock:
            self.stats['started_at'] = datetime.now().isoformat()
        
        print(f"🚀 Starting Central Orchestrator")
        print(f"Discovery interval: {discovery_interval} minutes")
        print(f"Processing interval: {processing_interval} minutes") 
        print(f"Cleanup interval: {cleanup_interval} minutes")
        print(f"Status interval: {status_interval} minutes")
        
        # Schedule tasks
        schedule.every(discovery_interval).minutes.do(self.run_discovery_cycle)
        schedule.every(processing_interval).minutes.do(self.run_processing_cycle)
        schedule.every(cleanup_interval).minutes.do(self.cleanup_stale_resources)
        schedule.every(status_interval).minutes.do(self.update_status)
        
        # Run initial cycles
        self.run_discovery_cycle()
        self.run_processing_cycle()
        self.update_status()
        
        print("🔄 Orchestrator started. Press Ctrl+C to stop")
        self.logger.info("Central orchestrator started")
        
        try:
            while self.running and not self._shutdown_event.is_set():
                schedule.run_pending()
                time.sleep(30)  # Check every 30 seconds
                
        except KeyboardInterrupt:
            print("\\n🛑 Orchestrator stopped by user")
        
        self.shutdown()
    
    def shutdown(self):
        """Graceful shutdown of the orchestrator."""
        print("🛑 Shutting down Central Orchestrator...")
        self.logger.info("Shutting down central orchestrator")
        
        self.running = False
        self._shutdown_event.set()
        
        # Shutdown container manager (stops all workers)
        self.container_manager.shutdown()
        
        # Final status update
        try:
            self.update_status()
        except Exception as e:
            self.logger.error(f"Error during final status update: {e}")
        
        print("✅ Orchestrator shutdown complete")
        self.logger.info("Central orchestrator shutdown complete")

def setup_signal_handlers(orchestrator):
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        print(f"\\nReceived signal {signum}, shutting down...")
        orchestrator.shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def main():
    parser = argparse.ArgumentParser(description='Claude Bot Central Orchestrator')
    parser.add_argument('--workspace', default='/workspace', help='Workspace directory')
    parser.add_argument('--data', default='/bot/data', help='Bot data directory')
    parser.add_argument('--repo', help='GitHub repository (owner/repo)')
    parser.add_argument('--bot-id', help='Bot identifier for status reporting')
    parser.add_argument('--max-workers', type=int, default=3, help='Maximum concurrent workers')
    parser.add_argument('--bot-label', default='claude-bot', help='GitHub label to watch for')
    parser.add_argument('--discovery-interval', type=int, default=10, help='Issue discovery interval in minutes')
    parser.add_argument('--processing-interval', type=int, default=2, help='Queue processing interval in minutes')
    parser.add_argument('--cleanup-interval', type=int, default=60, help='Cleanup interval in minutes')
    parser.add_argument('--status-interval', type=int, default=30, help='Status update interval in minutes')
    parser.add_argument('--once', action='store_true', help='Run once and exit (no continuous orchestration)')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Set bot label environment variable
    if args.bot_label:
        os.environ['BOT_LABEL'] = args.bot_label
    
    # Create orchestrator
    orchestrator = CentralOrchestrator(
        workspace_dir=args.workspace,
        data_dir=args.data,
        repo=args.repo,
        bot_id=args.bot_id,
        max_workers=args.max_workers
    )
    
    # Setup signal handlers
    setup_signal_handlers(orchestrator)
    
    if args.once:
        # Run once and exit
        print("Running single orchestration cycle...")
        orchestrator.run_discovery_cycle()
        orchestrator.run_processing_cycle()
        orchestrator.update_status()
        print("Single cycle completed")
    else:
        # Start continuous orchestration
        orchestrator.start_orchestration(
            discovery_interval=args.discovery_interval,
            processing_interval=args.processing_interval,
            cleanup_interval=args.cleanup_interval,
            status_interval=args.status_interval
        )

if __name__ == "__main__":
    main()