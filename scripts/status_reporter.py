
#!/usr/bin/env python3
"""
Status Reporter for Claude Bot Infrastructure
Generates and publishes status information with enhanced error handling
"""

import json
import os
import sys
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import requests
import time

# Import our error handling utilities
try:
    from utils import (
        api_retry, web_dashboard_circuit_breaker, safe_request,
        get_logger, correlation_context, log_function_call
    )
except ImportError:
    # Fallback if utils not available
    def api_retry(func):
        return func
    def web_dashboard_circuit_breaker(func):
        return func
    def safe_request(*args, **kwargs):
        return requests.request(*args, **kwargs)
    def get_logger(*args, **kwargs):
        import logging
        return logging.getLogger(__name__)
    def correlation_context(cid=None):
        from contextlib import nullcontext
        return nullcontext()
    def log_function_call(logger=None):
        def decorator(func):
            return func
        return decorator

class StatusReporter:
    def __init__(self, bot_id, data_dir="/bot/data", status_web_url=None):
        self.bot_id = bot_id
        self.data_dir = Path(data_dir)
        self.status_web_url = status_web_url or "http://claude-status-web:5000"
        self.start_time = datetime.now()
        self.logger = get_logger(f"status-reporter-{bot_id}")
        
        # Ensure required directories exist
        self._ensure_directories()
        
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
            task = self._safe_json_load(task_file)
            if task and not task.get("error"):
                priority = task.get("priority", "medium")
                if f"{priority}_priority" in details:
                    details[f"{priority}_priority"] += 1
                details["recent_tasks"].append({
                    "title": task.get("title", "Unknown")[:50],
                    "priority": priority,
                    "created": task.get("created_at", "Unknown")
                })
            else:
                self.logger.warning(f"Skipping invalid task file: {task_file}")
        
        return details
    
    def _get_recent_activity(self, processed_tasks):
        """Get recent completed activities"""
        activities = []
        
        for task_file in sorted(processed_tasks, key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
            task = self._safe_json_load(task_file)
            if task and not task.get("error"):
                activities.append({
                    "title": task.get("title", "Unknown")[:50],
                    "completed_at": task.get("completed_at", "Unknown"),
                    "status": task.get("status", "Unknown"),
                    "branch": task.get("branch", "Unknown")
                })
            else:
                self.logger.warning(f"Skipping invalid processed task: {task_file}")
        
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
    
    @web_dashboard_circuit_breaker
    @api_retry
    @log_function_call()
    def publish_to_web(self, status_data):
        """Publish status to local web dashboard with error handling"""
        url = f"{self.status_web_url}/api/status/{self.bot_id}"
        headers = {
            "Content-Type": "application/json"
        }
        
        self.logger.info(f"Publishing status to web dashboard: {url}")
        
        response = safe_request(
            method="POST",
            url=url,
            json=status_data,
            headers=headers,
            timeout=10
        )
        
        self.logger.info(f"✅ Status published to web dashboard successfully")
        return True
    
    def _ensure_directories(self):
        """Ensure all required directories exist"""
        try:
            directories = [
                self.data_dir,
                self.data_dir / "queue",
                self.data_dir / "processed",
                self.data_dir / "tasks",
                self.data_dir / "pr_feedback"
            ]
            
            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)
                
            self.logger.debug(f"Ensured directories exist: {[str(d) for d in directories]}")
            
        except Exception as e:
            self.logger.error(f"Failed to create directories: {e}", exc_info=True)
            raise
    
    def _safe_json_load(self, file_path: Path) -> dict:
        """Safely load JSON file with error handling"""
        try:
            if not file_path.exists():
                self.logger.warning(f"File does not exist: {file_path}")
                return {}
                
            if file_path.stat().st_size == 0:
                self.logger.warning(f"File is empty: {file_path}")
                return {}
                
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    self.logger.warning(f"File has no content: {file_path}")
                    return {}
                    
                return json.loads(content)
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in {file_path}: {e}")
            return {"error": f"Invalid JSON: {str(e)}"}
            
        except Exception as e:
            self.logger.error(f"Error reading {file_path}: {e}")
            return {"error": f"Read error: {str(e)}"}
    
    def _validate_status_data(self, status_data: dict) -> bool:
        """Validate that status data has required fields"""
        required_fields = ['bot_id', 'timestamp', 'status', 'health']
        
        for field in required_fields:
            if field not in status_data:
                self.logger.error(f"Missing required field in status data: {field}")
                return False
                
        return True
    
    def _create_fallback_status(self, error: str = None) -> dict:
        """Create minimal fallback status when primary collection fails"""
        status = {
            "bot_id": self.bot_id,
            "timestamp": datetime.now().isoformat(),
            "status": "error" if error else "unknown",
            "health": "unhealthy" if error else "unknown",
            "uptime": self._calculate_uptime(),
            "queued_tasks": 0,
            "processed_tasks": 0,
            "fallback": True
        }
        
        if error:
            status["error"] = error
            
        return status
    
    def _log_status_summary(self, status_data: dict):
        """Log status summary with proper formatting"""
        self.logger.info(
            f"📈 Status Summary: Bot={status_data['bot_id']}, "
            f"Status={status_data['status']}, Health={status_data['health']}, "
            f"Queued={status_data.get('queued_tasks', 0)}, "
            f"Processed={status_data.get('processed_tasks', 0)}, "
            f"Uptime={status_data['uptime']}"
        )
    
    @log_function_call()
    def generate_and_publish(self):
        """Main method to collect status and publish it with comprehensive error handling"""
        with correlation_context():
            self.logger.info(f"📊 Generating status for bot: {self.bot_id}")
            
            try:
                # Collect current status
                status_data = self.collect_bot_status()
                
                # Validate status data
                if not self._validate_status_data(status_data):
                    self.logger.error("Invalid status data generated")
                    status_data = self._create_fallback_status()
                
                # Save locally (with fallback)
                try:
                    self.save_status_locally(status_data)
                except Exception as e:
                    self.logger.error(f"Failed to save status locally: {e}")
                    # Continue with publishing even if local save fails
                
                # Publish to web dashboard (with retry and circuit breaker)
                try:
                    self.publish_to_web(status_data)
                except Exception as e:
                    self.logger.error(f"Failed to publish to web dashboard: {e}")
                    # Don't fail the entire operation for web publish failure
                
                # Log summary
                self._log_status_summary(status_data)
                
                return status_data
                
            except Exception as e:
                self.logger.error(f"Critical error in generate_and_publish: {e}", exc_info=True)
                # Return minimal fallback status
                fallback_status = self._create_fallback_status(error=str(e))
                self._log_status_summary(fallback_status)
                return fallback_status

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
