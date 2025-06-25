#!/bin/bash
# Health check script for Claude Bot

# Check if critical directories exist and are accessible
if [ ! -d "/bot/data" ] || [ ! -w "/bot/data" ]; then
    echo "ERROR: /bot/data directory not accessible"
    exit 1
fi

if [ ! -d "/bot/logs" ] || [ ! -w "/bot/logs" ]; then
    echo "ERROR: /bot/logs directory not accessible"
    exit 1
fi

# Check if required environment variables are set
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "ERROR: ANTHROPIC_API_KEY not set"
    exit 1
fi

if [ -z "$GITHUB_TOKEN" ]; then
    echo "ERROR: GITHUB_TOKEN not set"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 not available"
    exit 1
fi

# Check if git is available
if ! command -v git &> /dev/null; then
    echo "ERROR: Git not available"
    exit 1
fi

# Check if we can access the project directory
if [ -n "$PROJECT_PATH" ] && [ ! -d "$PROJECT_PATH" ]; then
    echo "WARNING: Project path $PROJECT_PATH does not exist yet"
    # This is not fatal as it might be mounted later
fi

# Check if status file exists and is recent (updated within last 10 minutes)
STATUS_FILE="/bot/data/status.json"
if [ -f "$STATUS_FILE" ]; then
    # Get file modification time
    if [ $(find "$STATUS_FILE" -mmin -10 | wc -l) -eq 0 ]; then
        echo "WARNING: Status file not updated in last 10 minutes"
        # Not fatal, bot might be idle
    fi
fi

echo "OK: Health check passed"
exit 0