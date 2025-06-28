#!/usr/bin/env python3
"""
Real-time activity monitor for Claude Bot
"""

import time
import json
import os
from pathlib import Path
from datetime import datetime
import subprocess

def clear_screen():
    """Clear terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def get_container_logs(container_name="claude-bot-dotnet", lines=10):
    """Get recent container logs"""
    try:
        result = subprocess.run(
            ["docker", "logs", "--tail", str(lines), container_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout.split('\n')
    except:
        return ["Unable to fetch container logs"]

def check_bot_activity(data_dir="/bot/data"):
    """Check current bot activity and status"""
    data_path = Path(data_dir)
    
    # Create directories if they don't exist
    for subdir in ["queue", "processed", "tasks", "pr_feedback"]:
        (data_path / subdir).mkdir(parents=True, exist_ok=True)
    
    status = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "queued_tasks": 0,
        "processed_tasks": 0,
        "recent_activity": [],
        "queue_items": [],
        "container_logs": []
    }
    
    # Check queued tasks
    queue_dir = data_path / "queue"
    if queue_dir.exists():
        queued_files = list(queue_dir.glob("*.json"))
        status["queued_tasks"] = len(queued_files)
        
        for task_file in sorted(queued_files, key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
            try:
                with open(task_file, 'r') as f:
                    task = json.load(f)
                status["queue_items"].append({
                    "file": task_file.name,
                    "title": task.get("title", "Unknown"),
                    "created": task.get("created_at", "Unknown"),
                    "priority": task.get("priority", "medium")
                })
            except:
                status["queue_items"].append({
                    "file": task_file.name,
                    "title": "Error reading file",
                    "created": "Unknown",
                    "priority": "unknown"
                })
    
    # Check processed tasks
    processed_dir = data_path / "processed"
    if processed_dir.exists():
        processed_files = list(processed_dir.glob("*.json"))
        status["processed_tasks"] = len(processed_files)
        
        # Get recent activity from processed tasks
        for task_file in sorted(processed_files, key=lambda x: x.stat().st_mtime, reverse=True)[:3]:
            try:
                with open(task_file, 'r') as f:
                    task = json.load(f)
                status["recent_activity"].append({
                    "title": task.get("title", "Unknown"),
                    "completed": task.get("completed_at", "Unknown"),
                    "status": task.get("status", "Unknown")
                })
            except:
                pass
    
    # Get container logs
    status["container_logs"] = get_container_logs()
    
    return status

def display_status(status):
    """Display bot status in a formatted way"""
    clear_screen()
    
    print("=" * 80)
    print(f"🤖 CLAUDE BOT ACTIVITY MONITOR - {status['timestamp']}")
    print("=" * 80)
    
    # Summary
    print(f"\n📊 SUMMARY:")
    print(f"   Queued Tasks: {status['queued_tasks']}")
    print(f"   Processed Tasks: {status['processed_tasks']}")
    
    # Queue status
    if status["queue_items"]:
        print(f"\n📋 CURRENT QUEUE:")
        for item in status["queue_items"]:
            priority_icon = "🔴" if item["priority"] == "high" else "🟡" if item["priority"] == "medium" else "🟢"
            print(f"   {priority_icon} {item['title'][:60]}")
            print(f"      Created: {item['created']}")
    else:
        print(f"\n📋 QUEUE: Empty")
    
    # Recent activity
    if status["recent_activity"]:
        print(f"\n🕒 RECENT ACTIVITY:")
        for activity in status["recent_activity"]:
            status_icon = "✅" if activity["status"] == "completed" else "❌" if activity["status"] == "failed" else "⏳"
            print(f"   {status_icon} {activity['title'][:60]}")
            print(f"      Completed: {activity['completed']}")
    
    # Container logs
    print(f"\n📝 RECENT LOGS:")
    for log_line in status["container_logs"][-8:]:
        if log_line.strip():
            print(f"   {log_line}")
    
    print(f"\n{'=' * 80}")
    print("Press Ctrl+C to exit | Refreshing every 10 seconds...")

def monitor_loop(data_dir="/bot/data", refresh_interval=10):
    """Main monitoring loop"""
    try:
        while True:
            status = check_bot_activity(data_dir)
            display_status(status)
            time.sleep(refresh_interval)
    except KeyboardInterrupt:
        clear_screen()
        print("👋 Activity monitoring stopped")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Monitor Claude Bot activity in real-time')
    parser.add_argument('--data', default='/bot/data', help='Bot data directory')
    parser.add_argument('--interval', type=int, default=10, help='Refresh interval in seconds')
    parser.add_argument('--once', action='store_true', help='Run once instead of continuous monitoring')
    
    args = parser.parse_args()
    
    if args.once:
        status = check_bot_activity(args.data)
        display_status(status)
    else:
        monitor_loop(args.data, args.interval)

if __name__ == "__main__":
    main()