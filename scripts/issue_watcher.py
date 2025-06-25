#!/usr/bin/env python3
"""
GitHub Issue Watcher - Periodic monitoring for bot tasks
"""

import time
import schedule
import argparse
from pathlib import Path
from github_task_executor import GitHubTaskExecutor

def watch_issues(workspace_dir, data_dir, repo, label, interval_minutes):
    """Watch for GitHub issues and process them"""
    print(f"🔍 Starting issue watcher...")
    print(f"Repository: {repo}")
    print(f"Label: {label}")
    print(f"Check interval: {interval_minutes} minutes")
    
    executor = GitHubTaskExecutor(workspace_dir, data_dir, repo)
    executor.bot_label = label
    
    def check_and_process():
        print(f"\n⏰ Checking for new issues at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        try:
            executor.run()
        except Exception as e:
            print(f"❌ Error during execution: {e}")
        print("✅ Check completed")
    
    # Schedule the task
    schedule.every(interval_minutes).minutes.do(check_and_process)
    
    # Run once immediately
    check_and_process()
    
    # Keep running
    print(f"\n🔄 Watcher started. Checking every {interval_minutes} minutes...")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute for scheduled tasks
    except KeyboardInterrupt:
        print("\n🛑 Watcher stopped by user")

def main():
    parser = argparse.ArgumentParser(description='GitHub Issue Watcher for Claude Bot')
    parser.add_argument('--workspace', default='/workspace', help='Workspace directory')
    parser.add_argument('--data', default='/.bot/data', help='Bot data directory')
    parser.add_argument('--repo', help='GitHub repository (owner/repo)')
    parser.add_argument('--label', default='claude-bot', help='Bot label to watch for')
    parser.add_argument('--interval', type=int, default=15, help='Check interval in minutes')
    
    args = parser.parse_args()
    
    if not args.repo:
        # Try to get repo from git
        executor = GitHubTaskExecutor(args.workspace, args.data)
        args.repo = executor.repo
        
        if not args.repo:
            print("❌ Repository not specified and couldn't detect from git remote")
            print("Please specify --repo owner/repository")
            return
    
    watch_issues(args.workspace, args.data, args.repo, args.label, args.interval)

if __name__ == "__main__":
    main()