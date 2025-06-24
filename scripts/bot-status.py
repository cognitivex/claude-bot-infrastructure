#!/usr/bin/env python3
"""
Check Claude Bot status and queue
"""

import json
from pathlib import Path
from datetime import datetime

def check_status(data_dir="/bot/data"):
    """Display bot status and queue information"""
    data_path = Path(data_dir)
    queue_dir = data_path / "queue"
    completed_dir = data_path / "completed"
    
    print("=== Claude Bot Status ===")
    print(f"Data directory: {data_dir}")
    print()
    
    # Check queued tasks
    queued_tasks = list(queue_dir.glob("*.json"))
    print(f"Queued tasks: {len(queued_tasks)}")
    
    if queued_tasks:
        print("\nQueued Tasks:")
        for task_file in sorted(queued_tasks):
            try:
                with open(task_file, 'r') as f:
                    task = json.load(f)
                print(f"  - {task['name']} (Priority: {task.get('priority', 'medium')})")
                print(f"    Created: {task['created_at']}")
            except:
                print(f"  - Error reading {task_file.name}")
    
    # Check completed tasks
    completed_tasks = list(completed_dir.glob("*.json"))
    print(f"\nCompleted tasks: {len(completed_tasks)}")
    
    if completed_tasks:
        print("\nRecent Completed Tasks (last 5):")
        for task_file in sorted(completed_tasks)[-5:]:
            try:
                with open(task_file, 'r') as f:
                    task = json.load(f)
                print(f"  - {task['name']}")
                print(f"    Completed: {task.get('completed_at', 'Unknown')}")
                print(f"    Branch: {task.get('branch', 'Unknown')}")
            except:
                print(f"  - Error reading {task_file.name}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Check Claude Bot status')
    parser.add_argument('--data', default='/bot/data', help='Bot data directory')
    
    args = parser.parse_args()
    check_status(args.data)

if __name__ == "__main__":
    main()