#!/usr/bin/env python3
"""
Secure Secrets Loader for Claude Bot Infrastructure

Supports multiple secret backends:
- Environment variables
- Docker secrets
- AWS Secrets Manager
- HashiCorp Vault
- Azure Key Vault
- 1Password CLI
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SecretsLoader:
    """Load secrets from various secure backends."""
    
    def __init__(self):
        self.secrets: Dict[str, str] = {}
        
    def load_all(self) -> Dict[str, str]:
        """Load secrets from all available sources in priority order."""
        # Priority order (first found wins)
        loaders = [
            self.load_from_docker_secrets,
            self.load_from_aws_secrets_manager,
            self.load_from_hashicorp_vault,
            self.load_from_azure_keyvault,
            self.load_from_1password,
            self.load_from_env_files,
            self.load_from_env_vars,
        ]
        
        required_secrets = {
            'GITHUB_TOKEN': None,
            'ANTHROPIC_API_KEY': None,
        }
        
        for loader in loaders:
            try:
                found_secrets = loader()
                for key, value in found_secrets.items():
                    if key in required_secrets and required_secrets[key] is None:
                        required_secrets[key] = value
                        logger.info(f"✓ Loaded {key} from {loader.__name__}")
                        
                # Check if all required secrets are found
                if all(v is not None for v in required_secrets.values()):
                    logger.info("✅ All required secrets loaded successfully")
                    return required_secrets
            except Exception as e:
                logger.debug(f"Loader {loader.__name__} failed: {e}")
                continue
                
        # Check what's missing
        missing = [k for k, v in required_secrets.items() if v is None]
        if missing:
            logger.error(f"❌ Missing required secrets: {', '.join(missing)}")
            sys.exit(1)
            
        return required_secrets
        
    def load_from_env_vars(self) -> Dict[str, str]:
        """Load from environment variables (least secure)."""
        return {
            'GITHUB_TOKEN': os.environ.get('GITHUB_TOKEN', ''),
            'ANTHROPIC_API_KEY': os.environ.get('ANTHROPIC_API_KEY', ''),
        }
        
    def load_from_env_files(self) -> Dict[str, str]:
        """Load from .env files with proper permissions check."""
        secrets = {}
        env_files = ['.env', '.env.local', '.env.production']
        
        for env_file in env_files:
            env_path = Path(env_file)
            if env_path.exists():
                # Check file permissions
                stat_info = env_path.stat()
                if stat_info.st_mode & 0o077:
                    logger.warning(f"⚠️  {env_file} has overly permissive permissions!")
                    
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            if key in ['GITHUB_TOKEN', 'ANTHROPIC_API_KEY']:
                                secrets[key] = value.strip('"\'')
                                
        return secrets
        
    def load_from_docker_secrets(self) -> Dict[str, str]:
        """Load from Docker secrets (recommended for Docker deployments)."""
        secrets = {}
        secret_mappings = {
            'github_token': 'GITHUB_TOKEN',
            'anthropic_api_key': 'ANTHROPIC_API_KEY',
        }
        
        for file_name, env_name in secret_mappings.items():
            secret_file = Path(f'/run/secrets/{file_name}')
            if secret_file.exists():
                secrets[env_name] = secret_file.read_text().strip()
                
        # Also check _FILE environment variables
        for env_name in ['GITHUB_TOKEN', 'ANTHROPIC_API_KEY']:
            file_var = f"{env_name}_FILE"
            if file_var in os.environ:
                secret_file = Path(os.environ[file_var])
                if secret_file.exists():
                    secrets[env_name] = secret_file.read_text().strip()
                    
        return secrets
        
    def load_from_aws_secrets_manager(self) -> Dict[str, str]:
        """Load from AWS Secrets Manager."""
        if not os.environ.get('AWS_REGION'):
            return {}
            
        try:
            import boto3
            client = boto3.client('secretsmanager')
            
            secrets = {}
            secret_names = {
                'claude-bot/github-token': 'GITHUB_TOKEN',
                'claude-bot/anthropic-api-key': 'ANTHROPIC_API_KEY',
            }
            
            for secret_name, env_name in secret_names.items():
                try:
                    response = client.get_secret_value(SecretId=secret_name)
                    secret_value = response.get('SecretString', '')
                    if secret_value:
                        # Handle both plain text and JSON secrets
                        try:
                            secret_dict = json.loads(secret_value)
                            secrets[env_name] = secret_dict.get('value', secret_value)
                        except json.JSONDecodeError:
                            secrets[env_name] = secret_value
                except client.exceptions.ResourceNotFoundException:
                    continue
                    
            return secrets
        except ImportError:
            logger.debug("boto3 not installed, skipping AWS Secrets Manager")
            return {}
        except Exception as e:
            logger.debug(f"AWS Secrets Manager error: {e}")
            return {}
            
    def load_from_hashicorp_vault(self) -> Dict[str, str]:
        """Load from HashiCorp Vault."""
        vault_addr = os.environ.get('VAULT_ADDR')
        vault_token = os.environ.get('VAULT_TOKEN')
        
        if not (vault_addr and vault_token):
            return {}
            
        try:
            import hvac
            client = hvac.Client(url=vault_addr, token=vault_token)
            
            if not client.is_authenticated():
                return {}
                
            secrets = {}
            secret_paths = {
                'secret/data/claude-bot/github-token': 'GITHUB_TOKEN',
                'secret/data/claude-bot/anthropic-api-key': 'ANTHROPIC_API_KEY',
            }
            
            for path, env_name in secret_paths.items():
                try:
                    response = client.secrets.kv.v2.read_secret_version(
                        path=path.replace('secret/data/', '')
                    )
                    secrets[env_name] = response['data']['data']['value']
                except Exception:
                    continue
                    
            return secrets
        except ImportError:
            logger.debug("hvac not installed, skipping HashiCorp Vault")
            return {}
        except Exception as e:
            logger.debug(f"Vault error: {e}")
            return {}
            
    def load_from_azure_keyvault(self) -> Dict[str, str]:
        """Load from Azure Key Vault."""
        keyvault_name = os.environ.get('AZURE_KEYVAULT_NAME')
        
        if not keyvault_name:
            return {}
            
        try:
            from azure.keyvault.secrets import SecretClient
            from azure.identity import DefaultAzureCredential
            
            keyvault_uri = f"https://{keyvault_name}.vault.azure.net"
            credential = DefaultAzureCredential()
            client = SecretClient(vault_url=keyvault_uri, credential=credential)
            
            secrets = {}
            secret_names = {
                'github-token': 'GITHUB_TOKEN',
                'anthropic-api-key': 'ANTHROPIC_API_KEY',
            }
            
            for secret_name, env_name in secret_names.items():
                try:
                    secret = client.get_secret(secret_name)
                    secrets[env_name] = secret.value
                except Exception:
                    continue
                    
            return secrets
        except ImportError:
            logger.debug("azure-keyvault not installed, skipping Azure Key Vault")
            return {}
        except Exception as e:
            logger.debug(f"Azure Key Vault error: {e}")
            return {}
            
    def load_from_1password(self) -> Dict[str, str]:
        """Load from 1Password CLI."""
        if not shutil.which('op'):
            return {}
            
        try:
            # Check if signed in
            result = subprocess.run(['op', 'whoami'], capture_output=True, text=True)
            if result.returncode != 0:
                return {}
                
            secrets = {}
            item_refs = {
                'op://Private/Claude Bot/github_token': 'GITHUB_TOKEN',
                'op://Private/Claude Bot/anthropic_api_key': 'ANTHROPIC_API_KEY',
            }
            
            for ref, env_name in item_refs.items():
                try:
                    result = subprocess.run(
                        ['op', 'read', ref],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    secrets[env_name] = result.stdout.strip()
                except subprocess.CalledProcessError:
                    continue
                    
            return secrets
        except Exception as e:
            logger.debug(f"1Password error: {e}")
            return {}
            
    def export_to_env(self, secrets: Dict[str, str]) -> None:
        """Export secrets as environment variables."""
        for key, value in secrets.items():
            os.environ[key] = value
            
    def write_env_file(self, secrets: Dict[str, str], path: str = '.env.secrets') -> None:
        """Write secrets to a secure env file."""
        env_path = Path(path)
        with open(env_path, 'w') as f:
            f.write("# Auto-generated secrets file - DO NOT COMMIT\n")
            for key, value in secrets.items():
                f.write(f"{key}={value}\n")
                
        # Set secure permissions
        env_path.chmod(0o600)
        logger.info(f"✓ Wrote secrets to {path} with secure permissions")


def main():
    """Load secrets and optionally export them."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Secure secrets loader')
    parser.add_argument('--export', action='store_true', 
                       help='Export as environment variables')
    parser.add_argument('--write-env', metavar='PATH',
                       help='Write to env file')
    parser.add_argument('--validate-only', action='store_true',
                       help='Only validate secrets availability')
    
    args = parser.parse_args()
    
    loader = SecretsLoader()
    secrets = loader.load_all()
    
    if args.validate_only:
        print("✅ All required secrets are available")
        return 0
        
    if args.export:
        loader.export_to_env(secrets)
        print("✅ Secrets exported to environment")
        
    if args.write_env:
        loader.write_env_file(secrets, args.write_env)
        
    # Output for shell evaluation if neither flag is set
    if not args.export and not args.write_env:
        for key, value in secrets.items():
            print(f"export {key}='{value}'")
            
    return 0


if __name__ == '__main__':
    sys.exit(main())