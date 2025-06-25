#!/usr/bin/env python3
"""
Setup GitHub labels for Claude Bot
Creates the necessary labels for bot task management
"""

import subprocess
import argparse
import json

class LabelSetup:
    def __init__(self, repo=None):
        self.repo = repo or self.get_repo_from_git()
        
        # Define bot labels
        self.labels = [
            {
                "name": "claude-bot",
                "description": "Issues to be processed by Claude Bot",
                "color": "00d4aa"
            },
            {
                "name": "bot:queued",
                "description": "Bot task is queued for processing",
                "color": "fbca04"
            },
            {
                "name": "bot:in-progress",
                "description": "Bot is currently working on this task",
                "color": "0075ca"
            },
            {
                "name": "bot:completed",
                "description": "Bot has completed this task",
                "color": "0e8a16"
            },
            {
                "name": "bot:failed",
                "description": "Bot failed to complete this task",
                "color": "d73a49"
            }
        ]
    
    def get_repo_from_git(self):
        """Get repository name from git remote"""
        try:
            result = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                capture_output=True,
                text=True
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
    
    def run_command(self, cmd):
        """Execute a shell command and return output"""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True
            )
            return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
        except Exception as e:
            return False, "", str(e)
    
    def label_exists(self, label_name):
        """Check if a label already exists"""
        cmd = f'gh label list --repo {self.repo} --json name'
        success, output, _ = self.run_command(cmd)
        
        if success:
            try:
                labels = json.loads(output)
                return any(label['name'] == label_name for label in labels)
            except json.JSONDecodeError:
                return False
        return False
    
    def create_label(self, label):
        """Create a single label"""
        name = label['name']
        description = label['description']
        color = label['color']
        
        if self.label_exists(name):
            print(f"✅ Label '{name}' already exists")
            return True
        
        cmd = f'gh label create "{name}" --description "{description}" --color {color} --repo {self.repo}'
        success, output, error = self.run_command(cmd)
        
        if success:
            print(f"✅ Created label: {name}")
            return True
        else:
            print(f"❌ Failed to create label '{name}': {error}")
            return False
    
    def setup_all_labels(self):
        """Setup all bot labels"""
        if not self.repo:
            print("❌ Repository not configured")
            return False
        
        print(f"🏷️  Setting up Claude Bot labels for {self.repo}")
        
        success_count = 0
        for label in self.labels:
            if self.create_label(label):
                success_count += 1
        
        print(f"\n✅ Setup complete: {success_count}/{len(self.labels)} labels configured")
        
        if success_count == len(self.labels):
            print("\n📝 Usage:")
            print("1. Add the 'claude-bot' label to any issue you want the bot to work on")
            print("2. The bot will automatically add status labels as it processes the issue")
            print("3. Use the issue watcher to monitor for new labeled issues")
            return True
        else:
            print("\n⚠️  Some labels failed to create. Please check GitHub permissions.")
            return False

def main():
    parser = argparse.ArgumentParser(description='Setup GitHub labels for Claude Bot')
    parser.add_argument('--repo', help='GitHub repository (owner/repo)')
    
    args = parser.parse_args()
    
    setup = LabelSetup(args.repo)
    setup.setup_all_labels()

if __name__ == "__main__":
    main()