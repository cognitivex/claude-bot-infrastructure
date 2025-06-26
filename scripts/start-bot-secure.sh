#!/bin/bash
# Secure Bot Startup Script with Secrets Management
# This wrapper loads secrets securely before starting the bot

set -euo pipefail

# Load secrets from secure sources
echo "🔐 Loading secrets securely..."

# Try to load secrets using the Python loader
if [ -x "/bot/scripts/secrets-loader.py" ]; then
    # Validate secrets are available
    if python3 /bot/scripts/secrets-loader.py --validate-only; then
        echo "✅ Secrets validated successfully"
        
        # Export secrets to environment
        eval "$(python3 /bot/scripts/secrets-loader.py)"
    else
        echo "❌ Failed to load required secrets"
        echo "Please ensure secrets are configured in one of:"
        echo "  - Docker secrets (/run/secrets/)"
        echo "  - AWS Secrets Manager"
        echo "  - HashiCorp Vault"
        echo "  - Azure Key Vault"
        echo "  - 1Password CLI"
        echo "  - Secure .env file (chmod 600)"
        exit 1
    fi
else
    # Fallback to basic file-based secrets
    if [ -f "/run/secrets/github_token" ]; then
        export GITHUB_TOKEN=$(cat /run/secrets/github_token)
        echo "✅ Loaded GITHUB_TOKEN from Docker secret"
    elif [ -n "${GITHUB_TOKEN_FILE:-}" ] && [ -f "$GITHUB_TOKEN_FILE" ]; then
        export GITHUB_TOKEN=$(cat "$GITHUB_TOKEN_FILE")
        echo "✅ Loaded GITHUB_TOKEN from file"
    fi
    
    if [ -f "/run/secrets/anthropic_api_key" ]; then
        export ANTHROPIC_API_KEY=$(cat /run/secrets/anthropic_api_key)
        echo "✅ Loaded ANTHROPIC_API_KEY from Docker secret"
    elif [ -n "${ANTHROPIC_API_KEY_FILE:-}" ] && [ -f "$ANTHROPIC_API_KEY_FILE" ]; then
        export ANTHROPIC_API_KEY=$(cat "$ANTHROPIC_API_KEY_FILE")
        echo "✅ Loaded ANTHROPIC_API_KEY from file"
    fi
fi

# Validate required secrets are present
if [ -z "${GITHUB_TOKEN:-}" ]; then
    echo "❌ Error: GITHUB_TOKEN not found in any secure location"
    exit 1
fi

if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    echo "❌ Error: ANTHROPIC_API_KEY not found in any secure location"
    exit 1
fi

# Mask secrets in logs
export GITHUB_TOKEN_MASKED="${GITHUB_TOKEN:0:10}...${GITHUB_TOKEN: -4}"
export ANTHROPIC_API_KEY_MASKED="${ANTHROPIC_API_KEY:0:10}...${ANTHROPIC_API_KEY: -4}"

echo "✅ Secrets loaded successfully"
echo "  - GITHUB_TOKEN: $GITHUB_TOKEN_MASKED"
echo "  - ANTHROPIC_API_KEY: $ANTHROPIC_API_KEY_MASKED"

# Clear any secrets from command history
history -c 2>/dev/null || true

# Start the main bot script
echo "🚀 Starting bot with secure configuration..."
exec /bot/scripts/start-bot.sh "$@"