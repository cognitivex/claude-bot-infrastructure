# Secure Secrets Management for Claude Bot

## Overview

The Claude Bot infrastructure now supports secure secret management that can retrieve secrets from multiple sources and provide them securely to workers. This guide explains how secrets flow from sources to workers.

## How Secrets Work

### Current Architecture

```
GitHub Repository Secrets → Orchestrator → Workers (via Docker Secrets)
         ↓
Environment Variables → Orchestrator → Workers (fallback)
         ↓
External Secret Stores → Orchestrator → Workers (secure)
```

### Secret Sources (Priority Order)

1. **Docker Secrets** (Most Secure)
2. **AWS Secrets Manager** 
3. **HashiCorp Vault**
4. **Azure Key Vault**
5. **1Password CLI**
6. **Environment Files** (.env)
7. **Environment Variables** (Least Secure)

## GitHub Repository Secrets Integration

### ⚠️ Important Limitation

**GitHub repository secrets cannot be directly retrieved** by the bot due to GitHub's security model. However, there are secure ways to use them:

### Method 1: GitHub Actions (Recommended)

```yaml
# .github/workflows/claude-bot-deployment.yml
name: Claude Bot Deployment

on:
  workflow_dispatch:
  schedule:
    - cron: '0 */6 * * *'

jobs:
  deploy-bot:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      
      - name: Deploy Claude Bot
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GIT_AUTHOR_NAME: ${{ secrets.GIT_AUTHOR_NAME }}
          GIT_AUTHOR_EMAIL: ${{ secrets.GIT_AUTHOR_EMAIL }}
        run: |
          # Secrets are securely passed to the environment
          docker-compose up -d claude-orchestrator
```

### Method 2: Deployment Keys + External Secrets

```bash
# Use deployment keys to access a separate secrets repository
# or external secret management service
```

## Setting Up Secure Secrets

### 1. Basic Setup (Environment Variables)

```bash
# .env file (set permissions to 600)
ANTHROPIC_API_KEY=your_anthropic_key
GITHUB_TOKEN=your_github_token
GIT_AUTHOR_NAME="Claude Bot"
GIT_AUTHOR_EMAIL="bot@claude.ai"
```

### 2. Docker Secrets Setup (Recommended)

```bash
# Create secure secret files
python3 scripts/github_secrets_manager.py --repo owner/repo --action create-files

# Generate secure docker-compose configuration
python3 scripts/github_secrets_manager.py --repo owner/repo --action create-compose

# Start with secure secrets
docker-compose -f docker-compose.yml -f docker-compose.secrets.yml up -d
```

### 3. AWS Secrets Manager

```bash
# Set up AWS credentials
export AWS_REGION=us-east-1

# Create secrets in AWS Secrets Manager
aws secretsmanager create-secret --name "claude-bot/anthropic-api-key" --secret-string "your_key"
aws secretsmanager create-secret --name "claude-bot/github-token" --secret-string "your_token"

# Bot will automatically retrieve from AWS
```

### 4. HashiCorp Vault

```bash
# Set up Vault connection
export VAULT_ADDR=https://vault.example.com
export VAULT_TOKEN=your_vault_token

# Store secrets in Vault
vault kv put secret/claude-bot/anthropic-api-key value=your_key
vault kv put secret/claude-bot/github-token value=your_token
```

## How the Orchestrator Provides Secrets to Workers

### Secure Method (Docker Secrets)

1. **Orchestrator loads secrets** from configured sources
2. **Creates encrypted secret files** in `/bot/data/secrets/`
3. **Mounts secrets directory** to workers at `/run/secrets/`
4. **Workers read secrets from files** (not environment variables)

```python
# In worker code
def load_secret(name):
    secret_file = f"/run/secrets/{name.lower()}"
    if os.path.exists(secret_file):
        return open(secret_file).read().strip()
    return os.getenv(name)  # Fallback
```

### Environment Variable Method (Fallback)

1. **Orchestrator reads secrets** from environment
2. **Passes secrets as environment variables** to workers
3. **Workers access via os.getenv()**

⚠️ **Less secure**: Secrets visible in `docker inspect` and process lists

## Worker Secret Access Pattern

Workers automatically detect and use the most secure method available:

```python
class WorkerSecretsLoader:
    def get_secret(self, name):
        # Priority order:
        # 1. Docker secrets file
        # 2. Environment variable with _FILE suffix (pointing to file)
        # 3. Direct environment variable
        
        # Check for Docker secrets
        secret_file = f"/run/secrets/{name.lower()}"
        if os.path.exists(secret_file):
            return open(secret_file).read().strip()
        
        # Check for file reference
        file_var = f"{name}_FILE"
        if file_var in os.environ:
            file_path = os.environ[file_var]
            if os.path.exists(file_path):
                return open(file_path).read().strip()
        
        # Fallback to environment variable
        return os.getenv(name)
```

## Security Best Practices

### ✅ Recommended

- Use Docker Secrets or external secret management
- Set file permissions to 600 on secret files
- Use GitHub Actions for CI/CD with repository secrets
- Rotate secrets regularly
- Use separate secrets for different environments

### ❌ Avoid

- Committing secrets to git repositories
- Using overly permissive file permissions
- Passing secrets as command line arguments
- Logging secret values

## Configuration Examples

### GitHub Actions with Repository Secrets

```yaml
# Required repository secrets:
# - ANTHROPIC_API_KEY
# - GITHUB_TOKEN  
# - GIT_AUTHOR_NAME (optional)
# - GIT_AUTHOR_EMAIL (optional)

name: Claude Bot Deployment
on:
  workflow_dispatch:
  
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy Bot
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: docker-compose up -d
```

### Docker Compose with Secrets

```yaml
# docker-compose.secrets.yml (auto-generated)
version: '3.8'
services:
  claude-orchestrator:
    secrets:
      - anthropic_api_key
      - github_token
    environment:
      - SECRETS_MODE=docker_secrets

secrets:
  anthropic_api_key:
    file: ./data/secrets/anthropic_api_key
  github_token:
    file: ./data/secrets/github_token
```

### AWS Secrets Manager Integration

```bash
# Environment setup
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key

# Secrets will be automatically retrieved
docker-compose up -d claude-orchestrator
```

## Troubleshooting

### Validate Secret Setup

```bash
# Check which secrets are available
python3 scripts/github_secrets_manager.py --repo owner/repo --action validate

# Test secret loading
python3 scripts/secrets_loader.py --validate-only
```

### Common Issues

1. **"No secrets found"**
   - Check environment variables are set
   - Verify external secret service configuration
   - Ensure file permissions are correct

2. **"Permission denied"** 
   - Set secret files to 600 permissions
   - Check Docker has access to mounted directories

3. **"Secrets visible in docker inspect"**
   - Switch from environment variables to Docker secrets
   - Use the secure configuration generator

## Migration Guide

### From Environment Variables to Docker Secrets

```bash
# 1. Generate secure configuration
python3 scripts/github_secrets_manager.py --repo owner/repo --action create-compose

# 2. Stop current deployment
docker-compose down

# 3. Start with secure secrets
docker-compose -f docker-compose.yml -f docker-compose.secrets.yml up -d

# 4. Verify secrets are secure
python3 scripts/github_secrets_manager.py --repo owner/repo --action validate
```

This secure secret management ensures that sensitive information like API keys and tokens are protected while still being accessible to the workers that need them. The system automatically chooses the most secure method available and provides fallbacks for different deployment scenarios.