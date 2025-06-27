#!/usr/bin/env python3
"""
Worker Executor for Claude Bot Infrastructure

Lightweight worker that processes a single task from the work queue
and executes it using Claude Code. Designed to run in ephemeral containers.
"""

import os
import sys
import json
import subprocess
import argparse
import time
from datetime import datetime
from pathlib import Path

# Add the scripts directory to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from work_queue import create_work_queue, WorkItem, TaskStatus
from platform_manager import PlatformManager

class WorkerExecutor:
    """Executes a single task in a worker container."""
    
    def __init__(self, workspace_dir="/workspace", data_dir="/bot/data", 
                 task_id=None, repo=None):
        self.workspace_dir = workspace_dir
        self.data_dir = Path(data_dir)
        self.task_id = task_id
        self.repo = repo or self.get_repo_from_git()
        
        # Initialize work queue
        self.work_queue = create_work_queue("file", queue_dir=str(self.data_dir / "queue"))
        
        # Initialize platform manager
        self.platform_manager = PlatformManager()
        
        # Worker identification
        self.worker_id = os.getenv('HOSTNAME', f'worker-{int(time.time())}')
        
        # Bot configuration - matches original
        self.bot_label = "claude-bot"
        self.status_labels = {
            "queued": "bot:queued",
            "in_progress": "bot:in-progress", 
            "completed": "bot:completed",
            "failed": "bot:failed"
        }
        
        print(f"Worker {self.worker_id} initialized")
        if self.task_id:
            print(f"Assigned to task: {self.task_id}")
        print(f"Repository: {self.repo}")
    
    def get_repo_from_git(self):
        """Get repository name from git remote"""
        try:
            result = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                capture_output=True,
                text=True,
                cwd=self.workspace_dir
            )
            if result.returncode == 0:
                url = result.stdout.strip()
                # Extract owner/repo from various URL formats
                if "github.com" in url:
                    parts = url.split("/")[-2:]
                    repo_name = parts[1].replace(".git", "")
                    return f"{parts[0]}/{repo_name}"
            return None
        except Exception as e:
            print(f"Error getting repo: {e}")
            return None
    
    def run_command(self, cmd, cwd=None):
        """Execute a shell command and return output"""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                cwd=cwd or self.workspace_dir
            )
            return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
        except Exception as e:
            print(f"Exception running command: {e}")
            return False, "", str(e)
    
    def get_work_item(self) -> WorkItem:
        """Get the work item to process."""
        if self.task_id:
            # Get specific task by ID
            work_item = self.work_queue.get_task(self.task_id)
            if not work_item:
                raise Exception(f"Task {self.task_id} not found in queue")
            return work_item
        else:
            # Dequeue next available task
            worker_capabilities = self.get_worker_capabilities()
            work_item = self.work_queue.dequeue(self.worker_id, worker_capabilities)
            if not work_item:
                raise Exception("No compatible tasks available in queue")
            self.task_id = work_item.task_id
            return work_item
    
    def get_worker_capabilities(self) -> dict:
        """Get the platform capabilities of this worker."""
        platforms_env = os.getenv('ENABLED_PLATFORMS', '')
        if not platforms_env:
            return {"nodejs": "18.16.0"}  # Default capability
        
        capabilities = {}
        for platform_spec in platforms_env.split(','):
            if ':' in platform_spec:
                name, version = platform_spec.split(':', 1)
                capabilities[name.strip()] = version.strip()
        
        return capabilities
    
    def update_issue_status(self, issue_number, status, comment=None):
        """Update issue with status label and optional comment"""
        if not self.repo or not issue_number:
            return False
            
        # Remove old status labels
        for old_status, old_label in self.status_labels.items():
            self.run_command(f'gh issue edit {issue_number} --repo {self.repo} --remove-label "{old_label}"')
        
        # Add new status label
        new_label = self.status_labels.get(status)
        if new_label:
            success, _, _ = self.run_command(f'gh issue edit {issue_number} --repo {self.repo} --add-label "{new_label}"')
            
        # Add comment if provided
        if comment:
            self.run_command(f'gh issue comment {issue_number} --repo {self.repo} --body "{comment}"')
            
        return True
    
    def create_branch(self, issue_number, issue_title):
        """Create a new git branch for the issue"""
        # Clean title for branch name
        clean_title = issue_title.lower().replace(' ', '-').replace('/', '-')[:50]
        branch_name = f"bot/issue-{issue_number}-{clean_title}"
        
        # Fetch latest changes
        self.run_command("git fetch origin")
        
        # Create and checkout new branch from main
        success, _, error = self.run_command(f"git checkout -b {branch_name} origin/main")
        
        if success:
            print(f"Created branch: {branch_name}")
            return branch_name
        else:
            print(f"Error creating branch: {error}")
            return None
    
    def execute_claude_task(self, task_description):
        """Execute task using Claude Code"""
        # Escape quotes in the description
        escaped_desc = task_description.replace('"', '\\"')
        cmd = f'claude-code --no-interactive "{escaped_desc}"'
        
        print(f"Executing: {cmd}")
        success, output, error = self.run_command(cmd)
        
        if success:
            print("Claude Code executed successfully")
            return True, output
        else:
            print(f"Claude Code execution failed: {error}")
            return False, error
    
    def commit_changes(self, issue_number, issue_title):
        """Commit all changes made by Claude"""
        # Stage all changes
        self.run_command("git add -A")
        
        # Check if there are changes to commit
        success, output, _ = self.run_command("git status --porcelain")
        
        if output.strip():
            # Commit with descriptive message
            commit_msg = f"Fix #{issue_number}: {issue_title}\n\nAutomated fix by Claude Bot\n\nCloses #{issue_number}"
            success, _, _ = self.run_command(f'git commit -m "{commit_msg}"')
            
            if success:
                print("Changes committed successfully")
                return True
        else:
            print("No changes to commit")
            return False
    
    def create_pull_request(self, branch_name, issue_number, issue_title):
        """Create a pull request using GitHub CLI"""
        pr_title = f"Fix #{issue_number}: {issue_title}"
        pr_body = f"""## Automated Issue Fix

**Issue:** #{issue_number}
**Title:** {issue_title}
**Branch:** {branch_name}
**Executed by:** Claude Bot Worker ({self.worker_id})
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Closes #{issue_number}

---
*This PR was automatically generated by Claude Bot Worker*
"""
        
        # Push branch to remote
        success, _, error = self.run_command(f"git push -u origin {branch_name}")
        
        if not success:
            print(f"Error pushing branch: {error}")
            return False, None
        
        # Create PR
        cmd = f'gh pr create --repo {self.repo} --title "{pr_title}" --body "{pr_body}" --base main'
        success, output, error = self.run_command(cmd)
        
        if success:
            print(f"Pull request created: {output}")
            return True, output
        else:
            print(f"Error creating PR: {error}")
            return False, error
    
    def load_claude_instructions(self) -> str:
        """Load comprehensive Claude instructions."""
        instructions_path = "/bot/config/claude-instructions.md"
        try:
            with open(instructions_path, 'r') as f:
                return f.read()
        except Exception as e:
            print(f"Warning: Could not load Claude instructions from {instructions_path}: {e}")
            # Fallback to basic instructions
            return """
You are Claude Bot, an AI development assistant. Please:
- Write clean, maintainable code following project conventions
- Add appropriate tests for new functionality  
- Follow security best practices
- Provide clear commit messages and documentation
- Ensure backward compatibility when possible
"""
    
    def detect_project_context(self) -> dict:
        """Detect project context and provide relevant information."""
        context = {
            "platforms": [],
            "frameworks": [],
            "testing_framework": None,
            "package_manager": None,
            "build_system": None
        }
        
        try:
            # Check for common project files
            workspace_files = []
            import os
            for root, dirs, files in os.walk(self.workspace_dir):
                # Limit depth to avoid deep scanning
                if root.count(os.sep) - self.workspace_dir.count(os.sep) < 3:
                    workspace_files.extend(files)
            
            # Platform detection
            if "package.json" in workspace_files:
                context["platforms"].append("Node.js")
                context["package_manager"] = "npm"
            if "yarn.lock" in workspace_files:
                context["package_manager"] = "yarn"
            if "pnpm-lock.yaml" in workspace_files:
                context["package_manager"] = "pnpm"
            if any(f.endswith(".csproj") for f in workspace_files):
                context["platforms"].append(".NET")
                context["build_system"] = "MSBuild"
            if "requirements.txt" in workspace_files or "pyproject.toml" in workspace_files:
                context["platforms"].append("Python")
                context["package_manager"] = "pip"
            if "Cargo.toml" in workspace_files:
                context["platforms"].append("Rust")
                context["package_manager"] = "cargo"
            if "go.mod" in workspace_files:
                context["platforms"].append("Go")
                context["package_manager"] = "go mod"
            
            # Framework detection
            if "next.config.js" in workspace_files:
                context["frameworks"].append("Next.js")
            if "nuxt.config.js" in workspace_files:
                context["frameworks"].append("Nuxt.js")
            if "angular.json" in workspace_files:
                context["frameworks"].append("Angular")
            if "vue.config.js" in workspace_files:
                context["frameworks"].append("Vue.js")
            if "vite.config.js" in workspace_files:
                context["frameworks"].append("Vite")
            
            # Testing framework detection
            if "jest.config.js" in workspace_files or any("jest" in f for f in workspace_files):
                context["testing_framework"] = "Jest"
            elif "vitest.config.js" in workspace_files:
                context["testing_framework"] = "Vitest"
            elif "playwright.config.js" in workspace_files:
                context["testing_framework"] = "Playwright"
            elif "cypress.json" in workspace_files:
                context["testing_framework"] = "Cypress"
                
        except Exception as e:
            print(f"Warning: Could not detect project context: {e}")
        
        return context
    
    def process_task(self, work_item: WorkItem) -> bool:
        """Process a single work item."""
        issue_number = work_item.issue_number
        issue_title = work_item.title
        issue_body = work_item.description
        
        print(f"\\n=== Processing Task {work_item.task_id} ===")
        print(f"Issue #{issue_number}: {issue_title}")
        
        try:
            # Update work queue status
            self.work_queue.update_status(work_item.task_id, TaskStatus.IN_PROGRESS)
            
            # Update GitHub issue status
            if issue_number:
                self.update_issue_status(issue_number, 'in_progress', 
                                       f"🤖 Claude Bot Worker ({self.worker_id}) has started working on this issue...")
            
            # Create branch
            branch_name = None
            if issue_number:
                branch_name = self.create_branch(issue_number, issue_title)
                if not branch_name:
                    raise Exception("Failed to create branch")
            
            # Load Claude instructions and project context
            claude_instructions = self.load_claude_instructions()
            project_context = self.detect_project_context()
            
            # Build context information
            context_info = ""
            if project_context["platforms"]:
                context_info += f"\n**Detected Platforms:** {', '.join(project_context['platforms'])}"
            if project_context["frameworks"]:
                context_info += f"\n**Detected Frameworks:** {', '.join(project_context['frameworks'])}"
            if project_context["testing_framework"]:
                context_info += f"\n**Testing Framework:** {project_context['testing_framework']}"
            if project_context["package_manager"]:
                context_info += f"\n**Package Manager:** {project_context['package_manager']}"
            
            # Prepare comprehensive task description for Claude
            task_description = f"""
{claude_instructions}

---

## Current Task

**Repository:** {self.repo}
**Issue #{issue_number}:** {issue_title}

**Issue Description:**
{issue_body}

**Project Context:**{context_info}

**Platform Requirements:** {work_item.platform_requirements}

---

## Task Instructions

Please implement a solution for this GitHub issue following the guidelines above. Ensure you:

1. **Analyze** the existing codebase to understand current patterns and conventions
2. **Implement** the necessary changes with clean, maintainable code
3. **Test** your implementation appropriately
4. **Document** any significant changes or new functionality
5. **Follow** the project's established coding style and practices

Focus on creating a professional, production-ready solution that the development team would be proud to merge.
"""
            
            # Execute task with Claude
            success, claude_output = self.execute_claude_task(task_description)
            if not success:
                raise Exception(f"Claude execution failed: {claude_output}")
            
            # Handle results
            result_data = {"claude_output": claude_output}
            
            if issue_number and branch_name:
                # Commit changes
                if self.commit_changes(issue_number, issue_title):
                    # Create PR
                    pr_success, pr_result = self.create_pull_request(branch_name, issue_number, issue_title)
                    
                    if pr_success:
                        result_data["pr_url"] = pr_result
                        result_data["branch"] = branch_name
                        
                        # Update GitHub issue status
                        comment = f"✅ Claude Bot Worker ({self.worker_id}) has completed the work and created a pull request.\\n\\nPR: {pr_result}\\n\\nPlease review and merge when ready."
                        self.update_issue_status(issue_number, 'completed', comment)
                        
                        print(f"✅ Task {work_item.task_id} completed successfully")
                    else:
                        raise Exception(f"Failed to create PR: {pr_result}")
                else:
                    # No changes needed
                    if issue_number:
                        self.update_issue_status(issue_number, 'completed',
                                               f"✅ Claude Bot Worker ({self.worker_id}) completed the analysis. No code changes were needed.")
                    
                    result_data["message"] = "No code changes were needed"
                    print(f"✅ Task {work_item.task_id} completed - no changes needed")
            else:
                # Task without GitHub issue
                result_data["message"] = "Task completed successfully"
                print(f"✅ Task {work_item.task_id} completed successfully")
            
            # Update work queue with success
            self.work_queue.update_status(work_item.task_id, TaskStatus.COMPLETED, result=result_data)
            return True
            
        except Exception as e:
            print(f"❌ Error processing task {work_item.task_id}: {e}")
            
            # Update work queue with failure
            self.work_queue.update_status(work_item.task_id, TaskStatus.FAILED, error_message=str(e))
            
            # Update GitHub issue status
            if issue_number:
                self.update_issue_status(issue_number, 'failed',
                                       f"❌ Claude Bot Worker ({self.worker_id}) encountered an error: {str(e)}\\n\\nPlease check the issue and try again.")
            
            # Cleanup branch if created
            if branch_name:
                self.run_command("git checkout main")
                self.run_command(f"git branch -D {branch_name}")
            
            return False
        
        finally:
            # Always return to main branch
            self.run_command("git checkout main")
    
    def run(self):
        """Main worker execution."""
        print(f"🤖 Claude Bot Worker {self.worker_id} started")
        print(f"Task ID: {self.task_id}")
        print(f"Repository: {self.repo}")
        print(f"Capabilities: {self.get_worker_capabilities()}")
        
        try:
            # Get work item
            work_item = self.get_work_item()
            print(f"📋 Processing work item: {work_item.task_id}")
            
            # Process the task
            success = self.process_task(work_item)
            
            if success:
                print(f"✅ Worker {self.worker_id} completed successfully")
                return 0
            else:
                print(f"❌ Worker {self.worker_id} failed")
                return 1
                
        except Exception as e:
            print(f"❌ Worker {self.worker_id} error: {e}")
            return 1

def main():
    parser = argparse.ArgumentParser(description='Claude Bot Worker Executor')
    parser.add_argument('--workspace', default='/workspace', help='Workspace directory')
    parser.add_argument('--data', default='/bot/data', help='Bot data directory')
    parser.add_argument('--task-id', help='Specific task ID to process')
    parser.add_argument('--repo', help='GitHub repository (owner/repo)')
    
    args = parser.parse_args()
    
    # Get task ID from environment if not provided
    task_id = args.task_id or os.getenv('TASK_ID')
    
    worker = WorkerExecutor(args.workspace, args.data, task_id, args.repo)
    return worker.run()

if __name__ == "__main__":
    sys.exit(main())