# Quick Start: Creating Docker Secrets from .env

This guide helps you quickly convert your existing `.env` file into secure Docker secrets.

## Prerequisites

1. Docker installed and running
2. Existing `.env` file with your tokens

## Step 1: Check Your .env File

Make sure your `.env` file contains at minimum:

```bash
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx
```

## Step 2: Secure Your .env File

```bash
# Set proper permissions (important!)
chmod 600 .env

# Verify permissions
ls -la .env
# Should show: -rw-------
```

## Step 3: Create Docker Secrets

Run the automated script:

```bash
# Basic usage (uses .env in current directory)
./scripts/create-docker-secrets.sh

# Use a specific env file
./scripts/create-docker-secrets.sh .env.production

# Force recreate existing secrets
./scripts/create-docker-secrets.sh .env true
```

Expected output:
```
🔐 Docker Secrets Creator
[INFO] Reading from: .env
[WARNING] Docker is not in Swarm mode. Initializing Swarm...
[INFO] Processing .env...
[SUCCESS] Created secret: github-token
[INFO]   Value: ghp_xxxxxx...xxxx
[SUCCESS] Created secret: anthropic-api-key
[INFO]   Value: sk-ant-xxx...xxxx

[INFO] Summary:
[INFO]   Created: 2 secrets
[SUCCESS] All required secrets found and created!

✅ Docker secrets created successfully!
```

## Step 4: Deploy with Secrets

Now deploy using the secure configuration:

```bash
# Deploy with secrets
docker-compose -f docker-compose.yml -f docker-compose.secrets.yml --profile dynamic up -d

# Or for legacy profiles
docker-compose -f docker-compose.yml -f docker-compose.secrets.yml --profile nodejs up -d
```

## Step 5: Verify Deployment

```bash
# Check if services are running
docker-compose ps

# Check if secrets are being used
docker-compose logs claude-bot-dynamic | grep "Secrets loaded successfully"

# List all secrets
docker secret ls
```

## Troubleshooting

### "Docker is not running"
```bash
# Start Docker Desktop or Docker daemon
sudo systemctl start docker  # Linux
# Or start Docker Desktop on Mac/Windows
```

### "Swarm not initialized"
The script automatically initializes Docker Swarm mode. This is normal and required for secrets.

### "Secret already exists"
```bash
# Option 1: Force recreate
./scripts/create-docker-secrets.sh .env true

# Option 2: Remove manually first
docker secret rm github-token anthropic-api-key
./scripts/create-docker-secrets.sh
```

### "Permission denied"
```bash
# Fix script permissions
chmod +x scripts/create-docker-secrets.sh

# Fix .env permissions
chmod 600 .env
```

## Security Notes

1. **Never commit .env files** - Already in .gitignore
2. **Secrets are encrypted** - Docker encrypts secrets at rest
3. **Container-only access** - Secrets only visible inside containers
4. **No logs** - Secrets are masked in all output

## What Happens Behind the Scenes

1. Script reads your `.env` file
2. Converts `GITHUB_TOKEN` → `github-token` (Docker naming)
3. Creates encrypted Docker secrets
4. Secrets are mounted at `/run/secrets/` in containers
5. `start-bot-secure.sh` automatically loads them

## Next Steps

After creating secrets:

1. **Delete .env file** (optional for extra security):
   ```bash
   # Backup first if needed
   cp .env .env.backup
   
   # Remove from working directory
   rm .env
   ```

2. **Update secrets** when needed:
   ```bash
   # Update a single secret
   echo -n "new_token_value" | docker secret create github-token-v2 -
   
   # Update in docker-compose.secrets.yml to use new version
   ```

3. **Use multi-platform deployment**:
   ```bash
   ENABLED_PLATFORMS="python:3.11,nodejs:18.16.0" \
   docker-compose -f docker-compose.yml -f docker-compose.secrets.yml \
   --profile dynamic up -d
   ```

That's it! Your secrets are now securely stored in Docker and automatically loaded by the bot. 🔐✨