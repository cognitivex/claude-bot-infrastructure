#!/usr/bin/env python3
"""
Secure Worker Initialization
Ensures workers get secrets through secure channels instead of environment variables.
"""

import os
import sys
from pathlib import Path

from claude_bot.security.secrets_loader import SecretsLoader

class SecureWorkerInit:
    """Initialize worker with secrets from secure sources."""
    
    def __init__(self):
        self.secrets_loader = SecretsLoader()
        self.secrets = {}
        
    def load_secrets(self) -> bool:
        """Load secrets from secure sources."""
        try:
            self.secrets = self.secrets_loader.load_all()
            
            # Set environment variables for tools that expect them
            for key, value in self.secrets.items():
                if value:
                    os.environ[key] = value
                    
            return True
        except Exception as e:
            print(f"❌ Failed to load secrets: {e}")
            return False
            
    def setup_github_auth(self) -> bool:
        """Set up GitHub CLI authentication securely."""
        github_token = self.secrets.get('GITHUB_TOKEN')
        if not github_token:
            print("❌ GitHub token not available")
            return False
            
        try:
            # Write token to gh CLI config securely
            import subprocess
            result = subprocess.run(
                ['gh', 'auth', 'login', '--with-token'],
                input=github_token,
                text=True,
                capture_output=True
            )
            
            if result.returncode == 0:
                print("✅ GitHub CLI authentication configured")
                return True
            else:
                print(f"❌ GitHub CLI auth failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error setting up GitHub auth: {e}")
            return False
            
    def setup_claude_client(self):
        """Set up Claude Code client with API key."""
        api_key = self.secrets.get('ANTHROPIC_API_KEY')
        if not api_key:
            print("❌ Anthropic API key not available")
            return None
            
        # Set environment for claude-code CLI
        os.environ['ANTHROPIC_API_KEY'] = api_key
        print("✅ Claude Code client configured")
        return api_key
        
    def initialize_worker(self) -> bool:
        """Complete worker initialization with all secrets."""
        print("🔐 Initializing worker with secure secrets...")
        
        # Load secrets from secure sources
        if not self.load_secrets():
            return False
            
        # Set up authentication for external services
        if not self.setup_github_auth():
            return False
            
        if not self.setup_claude_client():
            return False
            
        print("✅ Worker initialization completed securely")
        return True

def init_secure_worker() -> bool:
    """Initialize current worker process with secure secret access."""
    worker_init = SecureWorkerInit()
    return worker_init.initialize_worker()

if __name__ == "__main__":
    success = init_secure_worker()
    sys.exit(0 if success else 1)