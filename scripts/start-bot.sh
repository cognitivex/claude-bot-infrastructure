#!/bin/bash
# Claude Bot Startup Script
# Configures and starts the bot based on environment variables

set -e

echo "🤖 Starting Claude Bot Infrastructure..."

# Fix permissions for mounted volumes
echo "🔧 Setting up permissions..."
mkdir -p /bot/data /bot/logs /workspace
chown -R $(id -u):$(id -g) /bot/data /bot/logs 2>/dev/null || true
chmod -R 755 /bot/data /bot/logs 2>/dev/null || true

# Debug environment
echo "🔍 Debug: Current working directory: $(pwd)"
echo "🔍 Debug: PROJECT_PATH env var: $PROJECT_PATH"

# Check required environment variables
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ Error: ANTHROPIC_API_KEY is required"
    exit 1
fi

if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ Error: GITHUB_TOKEN is required"
    exit 1
fi

# Set default values
PROJECT_PATH=${PROJECT_PATH:-/workspace}
BOT_LABEL=${BOT_LABEL:-claude-bot}
ISSUE_CHECK_INTERVAL=${ISSUE_CHECK_INTERVAL:-15}
PR_CHECK_INTERVAL=${PR_CHECK_INTERVAL:-30}

echo "📁 Project path: $PROJECT_PATH"
echo "🏷️  Bot label: $BOT_LABEL"
echo "⏰ Issue check interval: ${ISSUE_CHECK_INTERVAL}m"
echo "💬 PR check interval: ${PR_CHECK_INTERVAL}m"

# Check if TARGET_REPO is specified
if [ -z "$TARGET_REPO" ]; then
    echo "❌ Error: TARGET_REPO environment variable is required."
    exit 1
fi

# Check if project is mounted or needs to be cloned
if [ -d "$PROJECT_PATH" ] && [ -n "$(ls -A "$PROJECT_PATH" 2>/dev/null)" ]; then
    echo "📁 Using mounted project directory at $PROJECT_PATH"
    cd "$PROJECT_PATH"
    
    # Verify it's a git repository
    if [ ! -d ".git" ]; then
        echo "⚠️  Mounted directory is not a git repository. Initializing..."
        git init
        git remote add origin "https://github.com/${TARGET_REPO}.git"
    fi
    
    # Update the repository
    echo "🔄 Updating repository..."
    if [ -n "$GITHUB_TOKEN" ] && [ "$GITHUB_TOKEN" != "dummy_token_for_testing" ]; then
        git remote set-url origin "https://${GITHUB_TOKEN}@github.com/${TARGET_REPO}.git"
    fi
    
    git fetch origin 2>/dev/null || echo "⚠️  Could not fetch updates (offline mode?)"
    
else
    echo "📥 Cloning repository $TARGET_REPO to $PROJECT_PATH..."
    
    # Ensure parent directory exists
    mkdir -p "$(dirname "$PROJECT_PATH")"
    
    # Clone directly to PROJECT_PATH
    if [ -n "$GITHUB_TOKEN" ] && [ "$GITHUB_TOKEN" != "dummy_token_for_testing" ]; then
        echo "🔐 Using GitHub token for authentication..."
        git clone "https://${GITHUB_TOKEN}@github.com/${TARGET_REPO}.git" "$PROJECT_PATH"
    else
        echo "⚠️  No valid GitHub token - attempting public clone..."
        git clone "https://github.com/${TARGET_REPO}.git" "$PROJECT_PATH"
    fi
    
    if [ $? -ne 0 ]; then
        echo "❌ Error: Failed to clone repository $TARGET_REPO"
        echo "   Make sure the repository exists and you have access to it"
        echo "   For private repositories, ensure GITHUB_TOKEN is set with proper permissions"
        exit 1
    fi
    
    cd "$PROJECT_PATH"
fi

echo "✅ Project ready at $PROJECT_PATH"

# Check if we can access the repository
echo "🔐 Checking GitHub access..."
if ! gh repo view "$TARGET_REPO" > /dev/null 2>&1; then
    echo "❌ Error: Cannot access repository $TARGET_REPO. Check your GITHUB_TOKEN permissions."
    exit 1
fi

# Setup labels if they don't exist
echo "🏷️  Setting up GitHub labels..."
cd /bot/scripts && /usr/bin/python3 setup_labels.py --repo "$TARGET_REPO" || echo "⚠️  Label setup failed, continuing..."

# Configure git if not already configured
if [ -n "$GIT_AUTHOR_NAME" ] && [ -n "$GIT_AUTHOR_EMAIL" ]; then
    # Copy host gitconfig if it exists and we don't have one
    if [ -f "$HOME/.gitconfig.host" ] && [ ! -f "$HOME/.gitconfig" ]; then
        cp "$HOME/.gitconfig.host" "$HOME/.gitconfig"
    fi
    
    # Set user configuration
    git config --global user.name "$GIT_AUTHOR_NAME"
    git config --global user.email "$GIT_AUTHOR_EMAIL"
    
    # Set safe directory for the workspace
    git config --global --add safe.directory "$PROJECT_PATH"
    
    # Ensure we're in the workspace directory
    cd "$PROJECT_PATH"
fi

echo "✅ Configuration complete!"
echo ""
echo "🚀 Starting bot orchestrator..."
echo "   - Repository: $TARGET_REPO"
echo "   - Issue monitoring: every ${ISSUE_CHECK_INTERVAL} minutes"
echo "   - PR feedback monitoring: every ${PR_CHECK_INTERVAL} minutes"
echo ""

# Start the main bot orchestrator
cd /bot/scripts && exec /usr/bin/python3 bot_orchestrator.py \
    --repo "$TARGET_REPO" \
    --data "/bot/data" \
    --issue-interval "$ISSUE_CHECK_INTERVAL" \
    --pr-interval "$PR_CHECK_INTERVAL"