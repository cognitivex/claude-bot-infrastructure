#!/usr/bin/env python3
"""
GitHub Issue-Based Claude Bot Task Executor
Monitors GitHub issues with specific labels and executes them as tasks
"""

import os
import sys
import json
import subprocess
import argparse
from datetime import datetime
from pathlib import Path

# Import secure worker initialization
try:
    from claude_bot.security.secure_worker_init import init_secure_worker
except ImportError:
    print("⚠️  Secure worker initialization not available, using environment variables")
    def init_secure_worker():
        return True

class GitHubTaskExecutor:
    def __init__(self, workspace_dir="/workspace", data_dir="/bot/data", repo=None):
        self.workspace_dir = workspace_dir
        self.data_dir = Path(data_dir)
        self.processed_dir = self.data_dir / "processed"
        self.repo = repo or self.get_repo_from_git()
        
        # Initialize worker with secure secrets
        if not init_secure_worker():
            print("⚠️  Worker initialization failed, some features may not work")
        
        # Bot configuration
        self.bot_label = os.getenv('BOT_LABEL', 'claude-bot')
        self.status_labels = {
            "queued": "bot:queued",
            "in_progress": "bot:in-progress", 
            "completed": "bot:completed",
            "failed": "bot:failed"
        }
        
        # Create directories if they don't exist
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
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
    
    def get_bot_issues(self):
        """Get issues labeled for the bot that aren't completed"""
        if not self.repo:
            print("Repository not configured")
            return []
        
        cmd = f'gh issue list --repo {self.repo} --label "{self.bot_label}" --state open --json number,title,body,labels,createdAt'
        success, output, error = self.run_command(cmd)
        
        if not success:
            print(f"Error fetching issues: {error}")
            return []
        
        try:
            issues = json.loads(output)
            # Filter out issues that are already completed or failed
            active_issues = []
            for issue in issues:
                labels = [label['name'] for label in issue.get('labels', [])]
                if not any(status in labels for status in [self.status_labels['completed'], self.status_labels['failed']]):
                    active_issues.append(issue)
            return active_issues
        except json.JSONDecodeError:
            print("Error parsing issues JSON")
            return []
    
    def update_issue_status(self, issue_number, status, comment=None):
        """Update issue with status label and optional comment"""
        if not self.repo:
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
            
        return success
    
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
**Executed by:** Claude Bot
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Closes #{issue_number}

---
*This PR was automatically generated by Claude Bot*
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
    
    def process_issue(self, issue):
        """Process a single GitHub issue"""
        issue_number = issue['number']
        issue_title = issue['title']
        issue_body = issue.get('body', '')
        
        print(f"\n=== Processing Issue #{issue_number}: {issue_title} ===")
        
        try:
            # Update status to in_progress
            self.update_issue_status(issue_number, 'in_progress', 
                                   "🤖 Claude Bot has started working on this issue...")
            
            # Create branch
            branch_name = self.create_branch(issue_number, issue_title)
            if not branch_name:
                raise Exception("Failed to create branch")
            
            # Prepare task description for Claude
            task_description = f"""
Issue #{issue_number}: {issue_title}

Description:
{issue_body}

Please implement a solution for this issue. Make sure to:
1. Understand the problem described
2. Implement the necessary changes
3. Follow existing code patterns and conventions
4. Add appropriate tests if needed
"""
            
            # Execute task with Claude
            success, claude_output = self.execute_claude_task(task_description)
            if not success:
                raise Exception(f"Claude execution failed: {claude_output}")
            
            # Commit changes
            if not self.commit_changes(issue_number, issue_title):
                # Even if no changes, update status
                self.update_issue_status(issue_number, 'completed',
                                       "✅ Claude Bot completed the analysis. No code changes were needed.")
                return True
            
            # Create PR
            pr_success, pr_result = self.create_pull_request(branch_name, issue_number, issue_title)
            
            if pr_success:
                # Update status to completed with PR link
                comment = f"✅ Claude Bot has completed the work and created a pull request.\n\nPR: {pr_result}\n\nPlease review and merge when ready."
                self.update_issue_status(issue_number, 'completed', comment)
                
                # Save processed issue info
                processed_file = self.processed_dir / f"issue_{issue_number}.json"
                issue_data = {
                    **issue,
                    'processed_at': datetime.now().isoformat(),
                    'branch': branch_name,
                    'pr_url': pr_result,
                    'status': 'completed'
                }
                
                with open(processed_file, 'w') as f:
                    json.dump(issue_data, f, indent=2)
                
                print(f"✅ Issue #{issue_number} completed successfully")
                return True
            else:
                raise Exception(f"Failed to create PR: {pr_result}")
                
        except Exception as e:
            print(f"❌ Error processing issue #{issue_number}: {e}")
            
            # Update status to failed
            self.update_issue_status(issue_number, 'failed',
                                   f"❌ Claude Bot encountered an error: {str(e)}\n\nPlease check the issue and try again.")
            
            # Return to main branch
            self.run_command("git checkout main")
            # Clean up branch if it exists
            self.run_command(f"git branch -D {branch_name}")
            
            return False
        
        finally:
            # Always return to main branch
            self.run_command("git checkout main")
    
    def run(self):
        """Main execution loop"""
        print("🤖 GitHub Claude Bot Task Executor started")
        print(f"Repository: {self.repo}")
        print(f"Bot label: {self.bot_label}")
        
        if not self.repo:
            print("❌ No repository configured. Please set up git remote or specify --repo")
            return
        
        # Get bot issues
        issues = self.get_bot_issues()
        
        if not issues:
            print("✅ No active bot issues found")
            return
        
        print(f"📋 Found {len(issues)} issues to process")
        
        # Process each issue
        for issue in issues:
            self.process_issue(issue)
            print("-" * 60)

def main():
    parser = argparse.ArgumentParser(description='GitHub Claude Bot Task Executor')
    parser.add_argument('--workspace', default='/workspace', help='Workspace directory')
    parser.add_argument('--data', default='/bot/data', help='Bot data directory')
    parser.add_argument('--repo', help='GitHub repository (owner/repo)')
    parser.add_argument('--label', default='claude-bot', help='Bot label to watch for')
    
    args = parser.parse_args()
    
    executor = GitHubTaskExecutor(args.workspace, args.data, args.repo)
    if args.label:
        executor.bot_label = args.label
        
    executor.run()

if __name__ == "__main__":
    main()