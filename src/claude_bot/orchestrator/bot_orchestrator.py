#!/usr/bin/env python3
"""
Bot Orchestrator - Manages both issue processing and PR feedback handling
"""

import time
import schedule
import argparse
import sys
import os
from pathlib import Path

# Import from the new package structure
from claude_bot.executors.github_task_executor import GitHubTaskExecutor
from claude_bot.executors.pr_feedback_handler import PRFeedbackHandler
from claude_bot.monitoring.status_reporter import StatusReporter

class BotOrchestrator:
    def __init__(self, workspace_dir="/workspace", data_dir="/bot/data", repo=None, bot_id=None):
        self.workspace_dir = workspace_dir
        self.data_dir = data_dir
        self.repo = repo
        self.bot_id = bot_id or os.getenv('BOT_ID', 'claude-bot')
        
        # Initialize handlers
        self.issue_executor = GitHubTaskExecutor(workspace_dir, data_dir, repo)
        self.pr_handler = PRFeedbackHandler(workspace_dir, data_dir, repo)
        
        # Initialize status reporter
        self.status_reporter = StatusReporter(
            bot_id=self.bot_id,
            data_dir=data_dir,
            status_web_url=os.getenv('STATUS_WEB_URL')
        )
        
        if repo:
            self.issue_executor.repo = repo
            self.pr_handler.repo = repo
    
    def process_issues(self):
        """Process new GitHub issues"""
        print(f"\n🔍 Checking for new issues at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        try:
            self.issue_executor.run()
        except Exception as e:
            print(f"❌ Error during issue processing: {e}")
        print("✅ Issue processing completed")
    
    def process_pr_feedback(self, hours_back=6):
        """Process PR feedback and comments"""
        print(f"\n💬 Checking for PR feedback at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        try:
            self.pr_handler.run(hours_back)
        except Exception as e:
            print(f"❌ Error during PR feedback processing: {e}")
        print("✅ PR feedback processing completed")
    
    def run_full_cycle(self, pr_hours_back=6):
        """Run both issue processing and PR feedback handling"""
        print("=" * 60)
        print("🤖 Running full bot cycle")
        
        # Process new issues first
        self.process_issues()
        
        # Then handle PR feedback
        self.process_pr_feedback(pr_hours_back)
        
        print("✅ Full cycle completed")
        print("=" * 60)
    
    def update_status(self):
        """Update bot status"""
        try:
            self.status_reporter.generate_and_publish()
        except Exception as e:
            print(f"⚠️  Status update failed: {e}")
    
    def start_watching(self, issue_interval=15, pr_interval=30, pr_hours_back=6, status_interval=5):
        """Start continuous monitoring"""
        print(f"🚀 Starting Bot Orchestrator...")
        print(f"Bot ID: {self.bot_id}")
        print(f"Repository: {self.repo}")
        print(f"Issue check interval: {issue_interval} minutes")
        print(f"PR feedback interval: {pr_interval} minutes")
        print(f"Status update interval: {status_interval} minutes")
        print(f"PR activity window: {pr_hours_back} hours")
        
        # Schedule tasks
        schedule.every(issue_interval).minutes.do(self.process_issues)
        schedule.every(pr_interval).minutes.do(lambda: self.process_pr_feedback(pr_hours_back))
        schedule.every(status_interval).minutes.do(self.update_status)
        
        # Run initial cycle and status update
        self.run_full_cycle(pr_hours_back)
        self.update_status()
        
        print(f"\n🔄 Orchestrator started. Press Ctrl+C to stop")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            print("\n🛑 Bot orchestrator stopped by user")

def main():
    parser = argparse.ArgumentParser(description='Claude Bot Orchestrator - Manages issues and PR feedback')
    parser.add_argument('--workspace', default='/workspace', help='Workspace directory')
    parser.add_argument('--data', default='/.bot/data', help='Bot data directory')
    parser.add_argument('--repo', help='GitHub repository (owner/repo)')
    parser.add_argument('--bot-id', help='Bot identifier for status reporting')
    parser.add_argument('--issue-interval', type=int, default=15, help='Issue check interval in minutes')
    parser.add_argument('--pr-interval', type=int, default=30, help='PR feedback check interval in minutes')
    parser.add_argument('--pr-hours', type=int, default=6, help='Hours back to check for PR activity')
    parser.add_argument('--status-interval', type=int, default=5, help='Status update interval in minutes')
    parser.add_argument('--once', action='store_true', help='Run once and exit (no continuous watching)')
    
    args = parser.parse_args()
    
    # Get repo if not specified
    if not args.repo:
        executor = GitHubTaskExecutor(args.workspace, args.data)
        args.repo = executor.repo
        
        if not args.repo:
            print("❌ Repository not specified and couldn't detect from git remote")
            print("Please specify --repo owner/repository")
            return
    
    orchestrator = BotOrchestrator(args.workspace, args.data, args.repo, args.bot_id)
    
    if args.once:
        # Run once and exit
        orchestrator.run_full_cycle(args.pr_hours)
        orchestrator.update_status()
    else:
        # Start continuous monitoring
        orchestrator.start_watching(args.issue_interval, args.pr_interval, args.pr_hours, args.status_interval)

if __name__ == "__main__":
    main()