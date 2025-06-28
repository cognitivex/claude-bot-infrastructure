# Secure API Token Setup Guide

This guide covers multiple secure methods to provide API tokens to Claude Bot Infrastructure without exposing them in your codebase.

## 🔒 Security Principles

1. **Never commit tokens** to version control
2. **Use least privilege** - only grant necessary permissions
3. **Rotate regularly** - change tokens periodically
4. **Limit exposure** - use short-lived tokens when possible
5. **Audit access** - monitor token usage

## Quick Start: Local Development

### Method 1: Secure .env File (Simplest)

```bash
# Create .env file with restricted permissions
touch .env
chmod 600 .env  # Only you can read/write

# Add your tokens
cat > .env << 'EOF'
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx
EOF

# Verify permissions
ls -la .env
# Should show: -rw------- (600)

# Deploy
docker-compose --profile dynamic up -d
```

### Method 2: Docker Secrets (Recommended)

```bash
# Create secrets (one-time setup)
echo -n "ghp_xxxxxxxxxxxxxxxxxxxx" | docker secret create github_token -
echo -n "sk-ant-xxxxxxxxxxxx" | docker secret create anthropic_api_key -

# Deploy with secrets
docker-compose -f docker-compose.yml -f docker-compose.secrets.yml --profile dynamic up -d
```

## Production Setup Options

### Option 1: AWS Secrets Manager

```bash
# Store secrets in AWS
aws secretsmanager create-secret \
    --name claude-bot/github-token \
    --secret-string "ghp_xxxxxxxxxxxxxxxxxxxx"

aws secretsmanager create-secret \
    --name claude-bot/anthropic-api-key \
    --secret-string "sk-ant-xxxxxxxxxxxx"

# Configure AWS credentials for the container
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key

# Deploy - secrets loaded automatically
docker-compose --profile dynamic up -d
```

### Option 2: HashiCorp Vault

```bash
# Start Vault (if not already running)
vault server -dev

# Store secrets
vault kv put secret/claude-bot/github-token value="ghp_xxxxxxxxxxxxxxxxxxxx"
vault kv put secret/claude-bot/anthropic-api-key value="sk-ant-xxxxxxxxxxxx"

# Configure Vault access
export VAULT_ADDR='http://127.0.0.1:8200'
export VAULT_TOKEN='your-vault-token'

# Deploy - secrets loaded automatically
docker-compose --profile dynamic up -d
```

### Option 3: Azure Key Vault

```bash
# Create Key Vault
az keyvault create --name claude-bot-kv --resource-group myRG

# Store secrets
az keyvault secret set --vault-name claude-bot-kv \
    --name github-token \
    --value "ghp_xxxxxxxxxxxxxxxxxxxx"

az keyvault secret set --vault-name claude-bot-kv \
    --name anthropic-api-key \
    --value "sk-ant-xxxxxxxxxxxx"

# Configure Azure access
export AZURE_KEYVAULT_NAME=claude-bot-kv

# Deploy - uses managed identity or service principal
docker-compose --profile dynamic up -d
```

### Option 4: 1Password CLI

```bash
# Sign in to 1Password
eval $(op signin)

# Create items (one-time)
op item create --category=Login \
    --title="Claude Bot" \
    --vault=Private \
    github_token="ghp_xxxxxxxxxxxxxxxxxxxx" \
    anthropic_api_key="sk-ant-xxxxxxxxxxxx"

# Deploy - secrets loaded from 1Password
docker-compose --profile dynamic up -d
```

### Option 5: Kubernetes Secrets (for K8s deployments)

```bash
# Create secret
kubectl create secret generic claude-bot-secrets \
    --from-literal=github-token="ghp_xxxxxxxxxxxxxxxxxxxx" \
    --from-literal=anthropic-api-key="sk-ant-xxxxxxxxxxxx"

# Mount in deployment
# See kubernetes/deployment-secure.yaml
```

## Enhanced Security with start-bot-secure.sh

The `start-bot-secure.sh` script provides automatic secret loading with fallback:

```yaml
# docker-compose.override.yml
services:
  claude-bot-dynamic:
    command: /bot/scripts/start-bot-secure.sh
    environment:
      # Optional: specify secret backend priority
      - SECRET_BACKEND=docker,aws,vault,env
```

## Secret Loading Priority

The secrets loader tries sources in this order:
1. Docker secrets (`/run/secrets/`)
2. AWS Secrets Manager
3. HashiCorp Vault  
4. Azure Key Vault
5. 1Password CLI
6. Secure .env files
7. Environment variables (least secure)

## Best Practices by Environment

### Development
- Use `.env` file with `chmod 600`
- Consider 1Password CLI for team sharing
- Never use production tokens

### Staging
- Use cloud provider secrets (AWS/Azure/GCP)
- Implement secret rotation
- Use separate tokens from production

### Production
- Use managed secret services (AWS/Vault/Azure)
- Enable audit logging
- Implement automatic rotation
- Use minimal token permissions
- Consider temporary/scoped tokens

## Token Permission Requirements

### GitHub Token
Minimal scopes needed:
- `repo` - Full repository access
- `workflow` - Update GitHub Actions (if needed)
- `write:discussion` - Comment on issues/PRs

```bash
# Create via GitHub CLI
gh auth token --scopes repo,workflow,write:discussion
```

### Anthropic API Key
- Create at: https://console.anthropic.com/
- Use separate keys for dev/prod
- Set usage limits and alerts

## Security Checklist

- [ ] Tokens are never in version control
- [ ] `.env` file has 600 permissions
- [ ] Using separate tokens for dev/staging/prod
- [ ] Tokens have minimal required permissions
- [ ] Secret rotation schedule in place
- [ ] Audit logging enabled for production
- [ ] Team knows how to access secrets securely
- [ ] Backup plan for secret recovery
- [ ] Regular security reviews scheduled

## Troubleshooting

### "Secrets not found" Error
```bash
# Check available secrets
python3 scripts/secrets-loader.py --validate-only

# Debug secret loading
DEBUG=true python3 scripts/secrets-loader.py
```

### Permission Denied
```bash
# Fix .env permissions
chmod 600 .env

# Fix script permissions  
chmod +x scripts/secrets-loader.py
chmod +x scripts/start-bot-secure.sh
```

### Docker Secrets Not Working
```bash
# Verify secrets exist
docker secret ls

# Check secret content
docker secret inspect github_token

# Recreate if needed
docker secret rm github_token
echo -n "new_token" | docker secret create github_token -
```

## Emergency Token Rotation

If a token is compromised:

```bash
# 1. Revoke compromised token immediately
# GitHub: Settings → Developer settings → Personal access tokens → Delete
# Anthropic: Console → API Keys → Delete

# 2. Create new tokens with new names

# 3. Update secrets (example with Docker)
docker secret rm github_token anthropic_api_key
echo -n "new_github_token" | docker secret create github_token -
echo -n "new_anthropic_key" | docker secret create anthropic_api_key -

# 4. Restart services
docker-compose down
docker-compose -f docker-compose.yml -f docker-compose.secrets.yml up -d

# 5. Verify new tokens work
docker-compose logs -f claude-bot-dynamic
```

## Advanced: Multi-Environment Setup

```bash
# Development secrets
echo -n "ghp_dev_token" | docker secret create github_token_dev -
echo -n "sk-ant-dev_key" | docker secret create anthropic_api_key_dev -

# Production secrets  
echo -n "ghp_prod_token" | docker secret create github_token_prod -
echo -n "sk-ant-prod_key" | docker secret create anthropic_api_key_prod -

# Deploy with environment-specific secrets
ENVIRONMENT=dev docker-compose -f docker-compose.yml -f docker-compose.secrets-dev.yml up -d
ENVIRONMENT=prod docker-compose -f docker-compose.yml -f docker-compose.secrets-prod.yml up -d
```

Remember: Security is not a one-time setup but an ongoing practice. Regularly review and update your security measures.