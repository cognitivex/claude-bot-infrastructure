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
PROJECT_PATH=${PROJECT_PATH:-/workspace}
BOT_LABEL=${BOT_LABEL:-claude-bot}
ISSUE_CHECK_INTERVAL=${ISSUE_CHECK_INTERVAL:-15}
PR_CHECK_INTERVAL=${PR_CHECK_INTERVAL:-30}

echo "📁 Project path: $PROJECT_PATH"
echo "🏷️  Bot label: $BOT_LABEL"
echo "⏰ Issue check interval: ${ISSUE_CHECK_INTERVAL}m"
echo "💬 PR check interval: ${PR_CHECK_INTERVAL}m"

# Detect repository if not specified
if [ -z "$TARGET_REPO" ]; then
    echo "🔍 Detecting repository from git remote..."
    cd "$PROJECT_PATH"
    TARGET_REPO=$(git config --get remote.origin.url | sed -n 's#.*github.com[/:]\\([^/]*\\)/\\([^.]*\\).*#\\1/\\2#p')
    if [ -z "$TARGET_REPO" ]; then
        echo "❌ Error: Could not detect repository. Please set TARGET_REPO environment variable."
        exit 1
    fi
    echo "📁 Detected repository: $TARGET_REPO"
    export TARGET_REPO
fi

# Check if we can access the repository
echo "🔐 Checking GitHub access..."
if ! gh repo view "$TARGET_REPO" > /dev/null 2>&1; then
    echo "❌ Error: Cannot access repository $TARGET_REPO. Check your GITHUB_TOKEN permissions."
    exit 1
fi

# Setup labels if they don't exist
echo "🏷️  Setting up GitHub labels..."
setup-labels.py --repo "$TARGET_REPO" || echo "⚠️  Label setup failed, continuing..."

# Configure git if not already configured
if [ -n "$GIT_AUTHOR_NAME" ] && [ -n "$GIT_AUTHOR_EMAIL" ]; then
    git config --global user.name "$GIT_AUTHOR_NAME"
    git config --global user.email "$GIT_AUTHOR_EMAIL"
fi

echo "✅ Configuration complete!"
echo ""
echo "🚀 Starting bot orchestrator..."
echo "   - Repository: $TARGET_REPO"
echo "   - Issue monitoring: every ${ISSUE_CHECK_INTERVAL} minutes"
echo "   - PR feedback monitoring: every ${PR_CHECK_INTERVAL} minutes"
echo ""

# Start the main bot orchestrator
exec bot-orchestrator.py \
    --repo "$TARGET_REPO" \
    --issue-interval "$ISSUE_CHECK_INTERVAL" \
    --pr-interval "$PR_CHECK_INTERVAL"