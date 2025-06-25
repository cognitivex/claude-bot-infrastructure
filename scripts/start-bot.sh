#!/bin/bash
# Claude Bot Startup Script
# Configures and starts the bot based on environment variables

set -e

echo "🤖 Starting Claude Bot Infrastructure..."

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
PROJECT_PATH=${PROJECT_PATH:-/workspace/repo}
BOT_LABEL=${BOT_LABEL:-claude-bot}
ISSUE_CHECK_INTERVAL=${ISSUE_CHECK_INTERVAL:-15}
PR_CHECK_INTERVAL=${PR_CHECK_INTERVAL:-30}

echo "📁 Project path: $PROJECT_PATH"
echo "🏷️  Bot label: $BOT_LABEL"
echo "⏰ Issue check interval: ${ISSUE_CHECK_INTERVAL}m"
echo "💬 PR check interval: ${PR_CHECK_INTERVAL}m"

# Check if TARGET_REPO is specified
if [ -z "$TARGET_REPO" ]; then
    echo "❌ Error: TARGET_REPO environment variable is required when working with cloned repositories."
    exit 1
fi

# Clone the repository fresh inside the container
echo "📥 Cloning repository $TARGET_REPO..."

# Create fresh workspace in a temp location first
TEMP_CLONE_DIR="/tmp/repo-clone-$$"
mkdir -p "$TEMP_CLONE_DIR"
cd "$TEMP_CLONE_DIR"

# Try to clone with authentication if GITHUB_TOKEN is provided
if [ -n "$GITHUB_TOKEN" ] && [ "$GITHUB_TOKEN" != "dummy_token_for_testing" ]; then
    echo "🔐 Using GitHub token for authentication..."
    git clone "https://${GITHUB_TOKEN}@github.com/${TARGET_REPO}.git" .
else
    echo "⚠️  No valid GitHub token - attempting public clone..."
    git clone "https://github.com/${TARGET_REPO}.git" .
fi

if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to clone repository $TARGET_REPO"
    echo "   Make sure the repository exists and you have access to it"
    echo "   For private repositories, ensure GITHUB_TOKEN is set with proper permissions"
    exit 1
fi

# Move to final location
echo "📁 Moving repository to $PROJECT_PATH..."
mkdir -p "$(dirname "$PROJECT_PATH")"
rm -rf "$PROJECT_PATH" 2>/dev/null || true
mv "$TEMP_CLONE_DIR" "$PROJECT_PATH"
cd "$PROJECT_PATH"

echo "✅ Repository cloned successfully"

# Check if we can access the repository
echo "🔐 Checking GitHub access..."
if ! gh repo view "$TARGET_REPO" > /dev/null 2>&1; then
    echo "❌ Error: Cannot access repository $TARGET_REPO. Check your GITHUB_TOKEN permissions."
    exit 1
fi

# Setup labels if they don't exist
echo "🏷️  Setting up GitHub labels..."
setup_labels.py --repo "$TARGET_REPO" || echo "⚠️  Label setup failed, continuing..."

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
exec bot_orchestrator.py \
    --repo "$TARGET_REPO" \
    --data "/bot/data" \
    --issue-interval "$ISSUE_CHECK_INTERVAL" \
    --pr-interval "$PR_CHECK_INTERVAL"