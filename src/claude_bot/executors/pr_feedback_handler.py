#!/usr/bin/env python3
"""
PR Feedback Handler - Monitors and responds to PR comments and reviews
"""

import os
import sys
import json
import subprocess
import argparse
from datetime import datetime, timedelta
from pathlib import Path

class PRFeedbackHandler:
    def __init__(self, workspace_dir="/workspace", data_dir="/.bot/data", repo=None):
        self.workspace_dir = workspace_dir
        self.data_dir = Path(data_dir)
        self.repo = repo or self.get_repo_from_git()
        self.processed_dir = self.data_dir / "pr_feedback"
        
        # Bot identifiers
        self.bot_signatures = [
            "Claude Bot",
            "Automated fix by Claude Bot",
            "🤖 Claude Bot"
        ]
        
        # Keywords that trigger bot responses
        self.trigger_keywords = [
            "@claude-bot",
            "claude bot",
            "bot please",
            "bot fix",
            "bot update",
            "bot change"
        ]
        
        # Create directories
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
            return False, "", str(e)
    
    def is_bot_created_pr(self, pr_data):
        """Check if PR was created by the bot"""
        pr_body = pr_data.get('body', '')
        return any(signature in pr_body for signature in self.bot_signatures)
    
    def should_respond_to_comment(self, comment):
        """Check if bot should respond to this comment"""
        comment_body = comment.get('body', '').lower()
        
        # Check for trigger keywords
        if any(keyword in comment_body for keyword in self.trigger_keywords):
            return True
            
        # Check if it's a review comment requesting changes
        if comment.get('state') == 'CHANGES_REQUESTED':
            return True
            
        return False
    
    def get_bot_prs_with_activity(self, hours_back=24):
        """Get bot-created PRs with recent activity (comments/reviews)"""
        if not self.repo:
            return []
        
        # Get all open PRs
        cmd = f'gh pr list --repo {self.repo} --state open --json number,title,body,createdAt'
        success, output, _ = self.run_command(cmd)
        
        if not success:
            return []
        
        try:
            all_prs = json.loads(output)
            bot_prs = [pr for pr in all_prs if self.is_bot_created_pr(pr)]
            
            # Check each PR for recent activity
            active_prs = []
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            
            for pr in bot_prs:
                pr_number = pr['number']
                
                # Get PR comments
                cmd = f'gh pr view {pr_number} --repo {self.repo} --json comments,reviews'
                success, pr_details, _ = self.run_command(cmd)
                
                if success:
                    try:
                        details = json.loads(pr_details)
                        
                        # Check comments
                        comments = details.get('comments', [])
                        reviews = details.get('reviews', [])
                        
                        recent_activity = []
                        
                        # Process comments
                        for comment in comments:
                            comment_time = datetime.fromisoformat(comment['createdAt'].replace('Z', '+00:00'))
                            if comment_time > cutoff_time and self.should_respond_to_comment(comment):
                                recent_activity.append({
                                    'type': 'comment',
                                    'data': comment,
                                    'created_at': comment_time
                                })
                        
                        # Process reviews
                        for review in reviews:
                            if review.get('state') == 'CHANGES_REQUESTED':
                                review_time = datetime.fromisoformat(review['createdAt'].replace('Z', '+00:00'))
                                if review_time > cutoff_time:
                                    recent_activity.append({
                                        'type': 'review',
                                        'data': review,
                                        'created_at': review_time
                                    })
                        
                        if recent_activity:
                            pr['recent_activity'] = recent_activity
                            active_prs.append(pr)
                            
                    except json.JSONDecodeError:
                        continue
            
            return active_prs
            
        except json.JSONDecodeError:
            return []
    
    def extract_feedback_instructions(self, activity_list):
        """Extract actionable feedback from comments and reviews"""
        instructions = []
        
        for activity in activity_list:
            if activity['type'] == 'comment':
                comment = activity['data']
                body = comment.get('body', '')
                
                # Extract specific instructions
                lines = body.split('\n')
                for line in lines:
                    line = line.strip()
                    if any(keyword in line.lower() for keyword in self.trigger_keywords):
                        # Clean up the instruction
                        instruction = line
                        for keyword in self.trigger_keywords:
                            instruction = instruction.replace(keyword, '').strip()
                        if instruction:
                            instructions.append(instruction)
            
            elif activity['type'] == 'review':
                review = activity['data']
                if review.get('body'):
                    instructions.append(f"Review feedback: {review['body']}")
        
        return instructions
    
    def checkout_pr_branch(self, pr_number):
        """Checkout the PR branch for making changes"""
        # Get PR branch name
        cmd = f'gh pr view {pr_number} --repo {self.repo} --json headRefName'
        success, output, _ = self.run_command(cmd)
        
        if not success:
            return None
        
        try:
            pr_data = json.loads(output)
            branch_name = pr_data['headRefName']
            
            # Fetch and checkout the branch
            self.run_command("git fetch origin")
            success, _, _ = self.run_command(f"git checkout {branch_name}")
            
            if success:
                # Pull latest changes
                self.run_command(f"git pull origin {branch_name}")
                return branch_name
            
        except json.JSONDecodeError:
            pass
        
        return None
    
    def apply_feedback(self, pr_number, instructions):
        """Apply feedback using Claude Code"""
        # Combine all feedback into a single task
        feedback_text = "\n".join([f"- {instruction}" for instruction in instructions])
        
        task_description = f"""
Based on the code review feedback for PR #{pr_number}, please make the following changes:

{feedback_text}

Please:
1. Review the current code
2. Apply the requested changes
3. Ensure the changes follow the existing code patterns
4. Make sure the code still works correctly after the changes
"""
        
        # Execute with Claude
        escaped_desc = task_description.replace('"', '\\"')
        cmd = f'claude-code --no-interactive "{escaped_desc}"'
        
        success, output, error = self.run_command(cmd)
        
        if success:
            print(f"✅ Applied feedback using Claude Code")
            return True, output
        else:
            print(f"❌ Failed to apply feedback: {error}")
            return False, error
    
    def commit_and_push_changes(self, pr_number, branch_name):
        """Commit and push the feedback changes"""
        # Stage all changes
        self.run_command("git add -A")
        
        # Check if there are changes
        success, output, _ = self.run_command("git status --porcelain")
        
        if not output.strip():
            print("No changes to commit after applying feedback")
            return False
        
        # Commit changes
        commit_msg = f"Address PR #{pr_number} feedback\n\nAutomatically applied code review feedback using Claude Bot"
        success, _, _ = self.run_command(f'git commit -m "{commit_msg}"')
        
        if not success:
            return False
        
        # Push changes
        success, _, _ = self.run_command(f"git push origin {branch_name}")
        
        if success:
            print(f"✅ Pushed feedback changes to {branch_name}")
            return True
        
        return False
    
    def add_pr_comment(self, pr_number, message):
        """Add a comment to the PR"""
        cmd = f'gh pr comment {pr_number} --repo {self.repo} --body "{message}"'
        success, _, _ = self.run_command(cmd)
        return success
    
    def process_pr_feedback(self, pr_data):
        """Process feedback for a single PR"""
        pr_number = pr_data['number']
        pr_title = pr_data['title']
        recent_activity = pr_data['recent_activity']
        
        print(f"\n=== Processing PR #{pr_number}: {pr_title} ===")
        
        # Check if we've already processed recent feedback
        processed_file = self.processed_dir / f"pr_{pr_number}_feedback.json"
        
        if processed_file.exists():
            with open(processed_file, 'r') as f:
                processed_data = json.load(f)
                last_processed = datetime.fromisoformat(processed_data.get('last_processed', '2000-01-01'))
                
                # Skip if we've processed feedback more recently than the latest activity
                latest_activity = max(activity['created_at'] for activity in recent_activity)
                if last_processed >= latest_activity:
                    print(f"✅ Already processed recent feedback for PR #{pr_number}")
                    return True
        
        try:
            # Extract feedback instructions
            instructions = self.extract_feedback_instructions(recent_activity)
            
            if not instructions:
                print(f"No actionable feedback found for PR #{pr_number}")
                return True
            
            print(f"Found {len(instructions)} feedback items:")
            for i, instruction in enumerate(instructions, 1):
                print(f"  {i}. {instruction}")
            
            # Checkout PR branch
            branch_name = self.checkout_pr_branch(pr_number)
            if not branch_name:
                raise Exception("Failed to checkout PR branch")
            
            # Apply feedback
            success, result = self.apply_feedback(pr_number, instructions)
            if not success:
                raise Exception(f"Failed to apply feedback: {result}")
            
            # Commit and push changes
            if self.commit_and_push_changes(pr_number, branch_name):
                # Add comment to PR
                self.add_pr_comment(pr_number, 
                    "🤖 I've addressed the code review feedback. Please review the updated changes.")
                
                # Mark as processed
                processed_data = {
                    'pr_number': pr_number,
                    'last_processed': datetime.now().isoformat(),
                    'instructions_applied': instructions,
                    'status': 'completed'
                }
                
                with open(processed_file, 'w') as f:
                    json.dump(processed_data, f, indent=2)
                
                print(f"✅ Successfully processed feedback for PR #{pr_number}")
                return True
            else:
                raise Exception("Failed to commit and push changes")
                
        except Exception as e:
            print(f"❌ Error processing PR #{pr_number}: {e}")
            
            # Add comment about the error
            self.add_pr_comment(pr_number, 
                f"🤖 I encountered an error while trying to address the feedback: {str(e)}\n\nPlease check the feedback and try again.")
            
            return False
        
        finally:
            # Always return to main branch
            self.run_command("git checkout main")
    
    def run(self, hours_back=24):
        """Main execution - process PR feedback"""
        print("🔍 PR Feedback Handler started")
        print(f"Repository: {self.repo}")
        print(f"Looking for activity in the last {hours_back} hours")
        
        if not self.repo:
            print("❌ Repository not configured")
            return
        
        # Get PRs with recent activity
        active_prs = self.get_bot_prs_with_activity(hours_back)
        
        if not active_prs:
            print("✅ No bot PRs with recent feedback found")
            return
        
        print(f"📋 Found {len(active_prs)} PRs with recent feedback")
        
        # Process each PR
        for pr_data in active_prs:
            self.process_pr_feedback(pr_data)
            print("-" * 60)

def main():
    parser = argparse.ArgumentParser(description='PR Feedback Handler for Claude Bot')
    parser.add_argument('--workspace', default='/workspace', help='Workspace directory')
    parser.add_argument('--data', default='/.bot/data', help='Bot data directory')
    parser.add_argument('--repo', help='GitHub repository (owner/repo)')
    parser.add_argument('--hours', type=int, default=24, help='Hours back to check for activity')
    
    args = parser.parse_args()
    
    handler = PRFeedbackHandler(args.workspace, args.data, args.repo)
    handler.run(args.hours)

if __name__ == "__main__":
    main()