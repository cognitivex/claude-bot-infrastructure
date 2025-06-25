#!/usr/bin/env python3
"""
Status Reporter for Claude Bot Infrastructure
Generates and publishes status information to GitHub Pages
"""

import json
import os
import sys
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import requests
import time

class StatusReporter:
    def __init__(self, bot_id, data_dir="/bot/data", status_web_url=None):
        self.bot_id = bot_id
        self.data_dir = Path(data_dir)
        self.status_web_url = status_web_url or "http://claude-status-web:5000"
        self.start_time = datetime.now()
        
    def collect_bot_status(self):
        """Collect current bot status information"""
        now = datetime.now()
        
        # Basic bot information
        status_data = {
            "bot_id": self.bot_id,
            "timestamp": now.isoformat(),
            "status": "unknown",
            "uptime": self._calculate_uptime(),
            "health": "unknown"
        }
        
        # Try to get environment info
        try:
            status_data["repository"] = os.getenv("TARGET_REPO", "unknown")
            status_data["bot_label"] = os.getenv("BOT_LABEL", "claude-bot")
            status_data["environment"] = {
                "node_version": os.getenv("NODE_VERSION", "unknown"),
                "dotnet_env": os.getenv("DOTNET_ENVIRONMENT", "unknown"),
                "check_intervals": {
                    "issues": f"{os.getenv('ISSUE_CHECK_INTERVAL', '15')}m",
                    "prs": f"{os.getenv('PR_CHECK_INTERVAL', '30')}m"
                }
            }
        except Exception as e:
            print(f"Warning: Could not collect environment info: {e}")
        
        # Check queue status
        try:
            queue_dir = self.data_dir / "queue"
            processed_dir = self.data_dir / "processed"
            
            queued_tasks = list(queue_dir.glob("*.json")) if queue_dir.exists() else []
            processed_tasks = list(processed_dir.glob("*.json")) if processed_dir.exists() else []
            
            status_data.update({
                "queued_tasks": len(queued_tasks),
                "processed_tasks": len(processed_tasks),
                "queue_details": self._get_queue_details(queued_tasks),
                "status": "running" if len(queued_tasks) > 0 else "idle"
            })
            
            # Get recent activity
            status_data["recent_activity"] = self._get_recent_activity(processed_tasks)
            
        except Exception as e:
            print(f"Warning: Could not collect queue status: {e}")
            status_data["status"] = "error"
            status_data["error"] = str(e)
        
        # Check container health
        try:
            status_data["health"] = self._check_health()
        except Exception as e:
            print(f"Warning: Could not check health: {e}")
            status_data["health"] = "unknown"
        
        return status_data
    
    def _calculate_uptime(self):
        """Calculate bot uptime"""
        try:
            uptime_delta = datetime.now() - self.start_time
            days = uptime_delta.days
            hours, remainder = divmod(uptime_delta.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            if days > 0:
                return f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        except:
            return "unknown"
    
    def _get_queue_details(self, queued_tasks):
        """Get details about queued tasks"""
        details = {
            "high_priority": 0,
            "medium_priority": 0,
            "low_priority": 0,
            "recent_tasks": []
        }
        
        for task_file in sorted(queued_tasks, key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
            try:
                with open(task_file, 'r') as f:
                    task = json.load(f)
                    priority = task.get("priority", "medium")
                    details[f"{priority}_priority"] += 1
                    details["recent_tasks"].append({
                        "title": task.get("title", "Unknown")[:50],
                        "priority": priority,
                        "created": task.get("created_at", "Unknown")
                    })
            except:
                continue
        
        return details
    
    def _get_recent_activity(self, processed_tasks):
        """Get recent completed activities"""
        activities = []
        
        for task_file in sorted(processed_tasks, key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
            try:
                with open(task_file, 'r') as f:
                    task = json.load(f)
                    activities.append({
                        "title": task.get("title", "Unknown")[:50],
                        "completed_at": task.get("completed_at", "Unknown"),
                        "status": task.get("status", "Unknown"),
                        "branch": task.get("branch", "Unknown")
                    })
            except:
                continue
        
        return activities
    
    def _check_health(self):
        """Check bot health status"""
        try:
            # Check if bot data directory is accessible
            if not self.data_dir.exists():
                return "unhealthy"
            
            # Check if bot has been active recently (within last hour)
            queue_dir = self.data_dir / "queue"
            processed_dir = self.data_dir / "processed"
            
            recent_activity = False
            one_hour_ago = datetime.now() - timedelta(hours=1)
            
            for directory in [queue_dir, processed_dir]:
                if directory.exists():
                    for file_path in directory.glob("*.json"):
                        if datetime.fromtimestamp(file_path.stat().st_mtime) > one_hour_ago:
                            recent_activity = True
                            break
            
            return "healthy" if recent_activity else "idle"
            
        except Exception:
            return "unhealthy"
    
    def save_status_locally(self, status_data):
        """Save status to local file"""
        try:
            status_file = self.data_dir / "status.json"
            status_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(status_file, 'w') as f:
                json.dump(status_data, f, indent=2)
            
            print(f"✅ Status saved locally to {status_file}")
            return True
        except Exception as e:
            print(f"❌ Failed to save status locally: {e}")
            return False
    
    def publish_to_github(self, status_data):
        """[DEPRECATED] GitHub publishing has been removed in favor of web dashboard only"""
        return False
    
    def publish_to_web(self, status_data):
        """Publish status to local web dashboard"""
        try:
            url = f"{self.status_web_url}/api/status/{self.bot_id}"
            headers = {
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, json=status_data, headers=headers, timeout=10)
            
            if response.status_code == 200:
                print(f"✅ Status published to web dashboard")
                return True
            else:
                print(f"❌ Failed to publish to web dashboard: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error publishing to web dashboard: {e}")
            return False
    
    def generate_and_publish(self):
        """Main method to collect status and publish it"""
        print(f"📊 Generating status for bot: {self.bot_id}")
        
        # Collect current status
        status_data = self.collect_bot_status()
        
        # Save locally
        self.save_status_locally(status_data)
        
        # Publish to web dashboard (primary method)
        self.publish_to_web(status_data)
        
        # GitHub publishing has been deprecated - using web dashboard only
        
        # Print summary
        print(f"📈 Status Summary:")
        print(f"   Bot ID: {status_data['bot_id']}")
        print(f"   Status: {status_data['status']}")
        print(f"   Health: {status_data['health']}")
        print(f"   Queued: {status_data.get('queued_tasks', 0)}")
        print(f"   Processed: {status_data.get('processed_tasks', 0)}")
        print(f"   Uptime: {status_data['uptime']}")
        
        return status_data

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Generate and publish Claude Bot status')
    parser.add_argument('--bot-id', default='claude-bot', help='Bot identifier')
    parser.add_argument('--data', default='/bot/data', help='Bot data directory')
    parser.add_argument('--web-url', help='Status web dashboard URL (default: http://claude-status-web:5000)')
    # GitHub publishing has been deprecated
    parser.add_argument('--loop', action='store_true', help='Run continuously every 5 minutes')
    parser.add_argument('--interval', type=int, default=300, help='Loop interval in seconds (default: 300)')
    
    args = parser.parse_args()
    
    # Get configuration from environment if not provided
    web_url = args.web_url or os.getenv('STATUS_WEB_URL')
    
    reporter = StatusReporter(
        bot_id=args.bot_id,
        data_dir=args.data,
        status_web_url=web_url
    )
    
    if args.loop:
        print(f"🔄 Starting continuous status reporting (every {args.interval}s)")
        try:
            while True:
                reporter.generate_and_publish()
                print(f"⏰ Next update in {args.interval} seconds...")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("🛑 Status reporting stopped")
    else:
        reporter.generate_and_publish()

if __name__ == "__main__":
    main()