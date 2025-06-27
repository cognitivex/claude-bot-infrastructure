#!/usr/bin/env python3
"""
GitHub Secrets Manager for Claude Bot Infrastructure

Securely retrieves secrets from GitHub repository secrets and provides them
to workers through secure channels (Docker secrets, mounted files).
"""

import os
import sys
import json
import subprocess
import tempfile
import base64
from pathlib import Path
from typing import Dict, List, Optional, Any
from cryptography.fernet import Fernet
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from claude_bot.security.secrets_loader import SecretsLoader

class GitHubSecretsManager:
    """Manages secrets from GitHub repository and provides them securely to workers."""
    
    def __init__(self, repo: str, data_dir: str = "/bot/data"):
        self.repo = repo
        self.data_dir = Path(data_dir)
        self.secrets_dir = self.data_dir / "secrets"
        self.secrets_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize secrets loader as fallback
        self.secrets_loader = SecretsLoader()
        
        # Encryption key for securing secrets at rest
        self.encryption_key = self._get_or_create_encryption_key()
        
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for securing secrets."""
        key_file = self.secrets_dir / ".encryption_key"
        
        if key_file.exists():
            return key_file.read_bytes()
        else:
            # Generate new key
            key = Fernet.generate_key()
            # Store with restrictive permissions
            key_file.write_bytes(key)
            key_file.chmod(0o600)
            logger.info("Generated new encryption key for secrets")
            return key
    
    def get_github_repository_secrets(self) -> Dict[str, str]:
        """Retrieve secrets from GitHub repository using GitHub CLI."""
        secrets = {}
        
        if not self.repo:
            logger.warning("No repository specified")
            return secrets
        
        try:
            # Check if gh CLI is available and authenticated
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                logger.warning("GitHub CLI not authenticated - falling back to environment")
                return self._get_fallback_secrets()
            
            # List repository secrets
            logger.info(f"Retrieving secrets from repository: {self.repo}")
            result = subprocess.run(
                ["gh", "secret", "list", "--repo", self.repo, "--json", "name"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to list repository secrets: {result.stderr}")
                return self._get_fallback_secrets()
            
            try:
                secret_list = json.loads(result.stdout)
            except json.JSONDecodeError:
                logger.error("Failed to parse secret list JSON")
                return self._get_fallback_secrets()
            
            # Define mapping of GitHub secret names to environment variable names
            secret_mappings = {
                "ANTHROPIC_API_KEY": "ANTHROPIC_API_KEY",
                "CLAUDE_API_KEY": "ANTHROPIC_API_KEY",  # Alternative name
                "GITHUB_TOKEN": "GITHUB_TOKEN",
                "BOT_GITHUB_TOKEN": "GITHUB_TOKEN",  # Alternative name
                "GIT_AUTHOR_NAME": "GIT_AUTHOR_NAME",
                "GIT_AUTHOR_EMAIL": "GIT_AUTHOR_EMAIL",
                "BOT_CONFIG": "BOT_CONFIG",  # Optional bot configuration
            }
            
            available_secrets = [secret["name"] for secret in secret_list]
            logger.info(f"Available repository secrets: {available_secrets}")
            
            # Retrieve each mapped secret
            for github_secret_name, env_var_name in secret_mappings.items():
                if github_secret_name in available_secrets:
                    try:
                        # Note: gh secret get doesn't work due to GitHub security
                        # We need to use a different approach
                        logger.warning(f"Cannot directly retrieve secret {github_secret_name} - GitHub doesn't allow secret retrieval")
                        logger.info("Consider using GitHub Actions to pass secrets to the bot")
                    except Exception as e:
                        logger.debug(f"Failed to retrieve secret {github_secret_name}: {e}")
            
            # Since we can't directly retrieve secrets, provide guidance
            if available_secrets:
                logger.info("✅ Repository has secrets configured")
                logger.info("💡 To use repository secrets:")
                logger.info("   1. Run the bot in GitHub Actions")
                logger.info("   2. Use environment variables in workflow")
                logger.info("   3. Or use a deployment key approach")
                
                return self._get_fallback_secrets()
            else:
                logger.warning("No secrets found in repository")
                return self._get_fallback_secrets()
                
        except subprocess.TimeoutExpired:
            logger.error("GitHub CLI command timed out")
            return self._get_fallback_secrets()
        except Exception as e:
            logger.error(f"Error retrieving GitHub secrets: {e}")
            return self._get_fallback_secrets()
    
    def _get_fallback_secrets(self) -> Dict[str, str]:
        """Get secrets from fallback sources when GitHub secrets aren't available."""
        logger.info("Using fallback secret sources")
        return self.secrets_loader.load_all()
    
    def create_secure_secret_files(self, secrets: Dict[str, str]) -> Dict[str, str]:
        """Create secure secret files for Docker secrets mounting."""
        secret_files = {}
        fernet = Fernet(self.encryption_key)
        
        for name, value in secrets.items():
            if not value:
                continue
                
            # Create secure file for this secret
            secret_file = self.secrets_dir / f"{name.lower()}_encrypted"
            
            # Encrypt the secret value
            encrypted_value = fernet.encrypt(value.encode())
            
            # Write encrypted secret to file
            secret_file.write_bytes(encrypted_value)
            secret_file.chmod(0o600)  # Owner read/write only
            
            # Also create unencrypted version for Docker secrets
            docker_secret_file = self.secrets_dir / f"{name.lower()}"
            docker_secret_file.write_text(value)
            docker_secret_file.chmod(0o600)
            
            secret_files[name] = str(docker_secret_file)
            logger.info(f"✅ Created secure file for {name}")
        
        return secret_files
    
    def get_encrypted_secret(self, name: str) -> Optional[str]:
        """Retrieve and decrypt a secret."""
        secret_file = self.secrets_dir / f"{name.lower()}_encrypted"
        
        if not secret_file.exists():
            return None
        
        try:
            fernet = Fernet(self.encryption_key)
            encrypted_data = secret_file.read_bytes()
            decrypted_value = fernet.decrypt(encrypted_data).decode()
            return decrypted_value
        except Exception as e:
            logger.error(f"Failed to decrypt secret {name}: {e}")
            return None
    
    def create_worker_environment(self, secrets: Dict[str, str], 
                                worker_id: str) -> Dict[str, str]:
        """Create environment variables for worker, using secure file references."""
        environment = {}
        
        # Instead of passing secrets directly, use file references
        for name, value in secrets.items():
            if value:
                # Use Docker secrets pattern
                environment[f"{name}_FILE"] = f"/run/secrets/{name.lower()}"
        
        # Add worker identification
        environment["WORKER_ID"] = worker_id
        environment["SECRETS_MODE"] = "docker_secrets"
        
        return environment
    
    def create_docker_secrets_config(self, secrets: Dict[str, str]) -> Dict[str, Any]:
        """Create Docker secrets configuration for docker-compose."""
        secrets_config = {}
        
        for name, value in secrets.items():
            if value:
                secret_name = name.lower()
                secrets_config[secret_name] = {
                    "file": f"./data/secrets/{secret_name}"
                }
        
        return secrets_config
    
    def setup_github_actions_integration(self) -> str:
        """Generate GitHub Actions workflow that can securely pass secrets."""
        workflow_content = f"""
name: Claude Bot Deployment

on:
  workflow_dispatch:
  schedule:
    - cron: '0 */6 * * *'  # Run every 6 hours

jobs:
  deploy-bot:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      
      - name: Set up Docker
        uses: docker/setup-buildx-action@v3
      
      - name: Deploy Claude Bot
        env:
          ANTHROPIC_API_KEY: ${{{{ secrets.ANTHROPIC_API_KEY }}}}
          GITHUB_TOKEN: ${{{{ secrets.GITHUB_TOKEN }}}}
          GIT_AUTHOR_NAME: ${{{{ secrets.GIT_AUTHOR_NAME || 'Claude Bot' }}}}
          GIT_AUTHOR_EMAIL: ${{{{ secrets.GIT_AUTHOR_EMAIL || 'bot@claude.ai' }}}}
          TARGET_REPO: {self.repo}
        run: |
          # Create secure environment file
          echo "ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY" > .env.secure
          echo "GITHUB_TOKEN=$GITHUB_TOKEN" >> .env.secure
          echo "GIT_AUTHOR_NAME=$GIT_AUTHOR_NAME" >> .env.secure
          echo "GIT_AUTHOR_EMAIL=$GIT_AUTHOR_EMAIL" >> .env.secure
          echo "TARGET_REPO=$TARGET_REPO" >> .env.secure
          
          # Set secure permissions
          chmod 600 .env.secure
          
          # Start the bot with secrets
          docker-compose --env-file .env.secure up -d claude-orchestrator
          
          # Monitor for a while
          sleep 3600  # Run for 1 hour
          
          # Cleanup
          docker-compose down
          rm -f .env.secure
      
      - name: Upload logs
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: bot-logs
          path: data/logs/
          retention-days: 7
"""
        
        # Save workflow file
        workflow_dir = Path(".github/workflows")
        workflow_dir.mkdir(parents=True, exist_ok=True)
        
        workflow_file = workflow_dir / "claude-bot-deployment.yml"
        workflow_file.write_text(workflow_content.strip())
        
        logger.info(f"✅ Created GitHub Actions workflow: {workflow_file}")
        return str(workflow_file)
    
    def create_secure_docker_compose_override(self, secrets: Dict[str, str]) -> str:
        """Create docker-compose override with secure secret mounting."""
        secret_files = self.create_secure_secret_files(secrets)
        
        # Create docker-compose.secrets.yml
        compose_config = {
            "version": "3.8",
            "services": {
                "claude-orchestrator": {
                    "secrets": list(secret_files.keys()),
                    "environment": [
                        "SECRETS_MODE=docker_secrets"
                    ]
                }
            },
            "secrets": {}
        }
        
        # Add secret definitions
        for name, file_path in secret_files.items():
            compose_config["secrets"][name.lower()] = {
                "file": file_path
            }
        
        # Write compose file
        compose_file = Path("docker-compose.secrets.yml")
        with open(compose_file, 'w') as f:
            import yaml
            yaml.dump(compose_config, f, default_flow_style=False)
        
        compose_file.chmod(0o600)
        logger.info(f"✅ Created secure docker-compose override: {compose_file}")
        
        return str(compose_file)
    
    def validate_secrets_security(self) -> Dict[str, Any]:
        """Validate the security of the current secrets setup."""
        report = {
            "timestamp": str(datetime.now()),
            "security_issues": [],
            "recommendations": [],
            "score": 0
        }
        
        # Check for .env files with secrets
        for env_file in [".env", ".env.local", ".env.production"]:
            if Path(env_file).exists():
                stat_info = Path(env_file).stat()
                if stat_info.st_mode & 0o077:
                    report["security_issues"].append(f"{env_file} has overly permissive permissions")
                else:
                    report["score"] += 10
        
        # Check secrets directory permissions
        if self.secrets_dir.exists():
            stat_info = self.secrets_dir.stat()
            if stat_info.st_mode & 0o077:
                report["security_issues"].append("Secrets directory has overly permissive permissions")
            else:
                report["score"] += 20
        
        # Check for environment variables in process list
        try:
            result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
            if "ANTHROPIC_API_KEY" in result.stdout or "GITHUB_TOKEN" in result.stdout:
                report["security_issues"].append("Secrets visible in process environment")
            else:
                report["score"] += 20
        except Exception:
            pass
        
        # Recommendations
        if report["score"] < 30:
            report["recommendations"].extend([
                "Use Docker secrets instead of environment variables",
                "Set restrictive file permissions (600) on secret files",
                "Consider using external secret management (Vault, AWS Secrets Manager)",
                "Rotate secrets regularly",
                "Use GitHub Actions for secure CI/CD deployment"
            ])
        
        return report

def create_github_secrets_manager(repo: str, data_dir: str = "/bot/data") -> GitHubSecretsManager:
    """Factory function to create GitHub secrets manager."""
    return GitHubSecretsManager(repo, data_dir)

def main():
    """CLI interface for GitHub secrets management."""
    import argparse
    from datetime import datetime
    
    parser = argparse.ArgumentParser(description="GitHub Secrets Manager")
    parser.add_argument("--repo", required=True, help="GitHub repository (owner/repo)")
    parser.add_argument("--data-dir", default="/bot/data", help="Data directory")
    parser.add_argument("--action", choices=[
        "fetch", "create-files", "create-compose", "validate", "setup-actions"
    ], default="fetch", help="Action to perform")
    
    args = parser.parse_args()
    
    manager = GitHubSecretsManager(args.repo, args.data_dir)
    
    if args.action == "fetch":
        print("🔐 Fetching secrets from GitHub repository...")
        secrets = manager.get_github_repository_secrets()
        if secrets:
            print(f"✅ Retrieved {len(secrets)} secrets")
            for name in secrets.keys():
                print(f"  • {name}")
        else:
            print("❌ No secrets retrieved")
    
    elif args.action == "create-files":
        print("📁 Creating secure secret files...")
        secrets = manager.get_github_repository_secrets()
        secret_files = manager.create_secure_secret_files(secrets)
        print(f"✅ Created {len(secret_files)} secure secret files")
    
    elif args.action == "create-compose":
        print("🐳 Creating secure docker-compose configuration...")
        secrets = manager.get_github_repository_secrets()
        compose_file = manager.create_secure_docker_compose_override(secrets)
        print(f"✅ Created secure compose file: {compose_file}")
    
    elif args.action == "validate":
        print("🔍 Validating secrets security...")
        report = manager.validate_secrets_security()
        print(f"Security Score: {report['score']}/50")
        if report['security_issues']:
            print("🚨 Security Issues:")
            for issue in report['security_issues']:
                print(f"  • {issue}")
        if report['recommendations']:
            print("💡 Recommendations:")
            for rec in report['recommendations']:
                print(f"  • {rec}")
    
    elif args.action == "setup-actions":
        print("⚙️ Setting up GitHub Actions integration...")
        workflow_file = manager.setup_github_actions_integration()
        print(f"✅ Created workflow file: {workflow_file}")
        print("Next steps:")
        print("1. Add required secrets to your GitHub repository")
        print("2. Commit and push the workflow file")
        print("3. Enable GitHub Actions in your repository")

if __name__ == "__main__":
    main()