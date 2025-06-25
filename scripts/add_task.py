#!/usr/bin/env python3
"""
Add a task to the Claude Bot queue
"""

import json
import argparse
from datetime import datetime
from pathlib import Path
import uuid

def add_task(name, description, priority="medium", data_dir="/bot/data"):
    """Add a new task to the queue"""
    queue_dir = Path(data_dir) / "queue"
    queue_dir.mkdir(parents=True, exist_ok=True)
    
    # Create task object
    task = {
        "id": str(uuid.uuid4()),
        "name": name,
        "description": description,
        "priority": priority,
        "created_at": datetime.now().isoformat(),
        "status": "queued"
    }
    
    # Save to queue
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{task['id'][:8]}.json"
    task_file = queue_dir / filename
    
    with open(task_file, 'w') as f:
        json.dump(task, f, indent=2)
    
    print(f"Task added to queue: {name}")
    print(f"Task ID: {task['id']}")
    print(f"File: {task_file}")
    
    return task['id']

def main():
    parser = argparse.ArgumentParser(description='Add task to Claude Bot queue')
    parser.add_argument('name', help='Task name')
    parser.add_argument('description', help='Task description for Claude')
    parser.add_argument('--priority', choices=['low', 'medium', 'high'], 
                       default='medium', help='Task priority')
    parser.add_argument('--data', default='/bot/data', help='Bot data directory')
    
    args = parser.parse_args()
    
    add_task(args.name, args.description, args.priority, args.data)

if __name__ == "__main__":
    main()