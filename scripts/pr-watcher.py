#!/usr/bin/env python3
"""
PR Watcher - Continuous monitoring for PR feedback and comments
"""

import time
import schedule
import argparse
from pathlib import Path
from pr_feedback_handler import PRFeedbackHandler

def watch_pr_feedback(workspace_dir, data_dir, repo, interval_minutes, hours_back):
    """Watch PRs for feedback and automatically respond"""
    print(f"🔍 Starting PR feedback watcher...")
    print(f"Repository: {repo}")
    print(f"Check interval: {interval_minutes} minutes")
    print(f"Activity window: {hours_back} hours")
    
    handler = PRFeedbackHandler(workspace_dir, data_dir, repo)
    
    def check_and_process():
        print(f"\n⏰ Checking for PR feedback at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        try:
            handler.run(hours_back)
        except Exception as e:
            print(f"❌ Error during PR feedback processing: {e}")
        print("✅ PR feedback check completed")
    
    # Schedule the task
    schedule.every(interval_minutes).minutes.do(check_and_process)
    
    # Run once immediately
    check_and_process()
    
    # Keep running
    print(f"\n🔄 PR watcher started. Checking every {interval_minutes} minutes...")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute for scheduled tasks
    except KeyboardInterrupt:
        print("\n🛑 PR watcher stopped by user")

def main():
    parser = argparse.ArgumentParser(description='PR Feedback Watcher for Claude Bot')
    parser.add_argument('--workspace', default='/workspace', help='Workspace directory')
    parser.add_argument('--data', default='/.bot/data', help='Bot data directory')
    parser.add_argument('--repo', help='GitHub repository (owner/repo)')
    parser.add_argument('--interval', type=int, default=30, help='Check interval in minutes')
    parser.add_argument('--hours', type=int, default=6, help='Hours back to check for activity')
    
    args = parser.parse_args()
    
    if not args.repo:
        # Try to get repo from git
        handler = PRFeedbackHandler(args.workspace, args.data)
        args.repo = handler.repo
        
        if not args.repo:
            print("❌ Repository not specified and couldn't detect from git remote")
            print("Please specify --repo owner/repository")
            return
    
    watch_pr_feedback(args.workspace, args.data, args.repo, args.interval, args.hours)

if __name__ == "__main__":
    main()