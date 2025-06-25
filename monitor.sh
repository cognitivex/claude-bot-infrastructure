#!/bin/bash
# Quick activity monitor for Claude Bot
# Usage: ./monitor.sh [container_name]

CONTAINER_NAME=${1:-claude-bot-dotnet}

echo "🤖 Claude Bot Activity Monitor"
echo "Container: $CONTAINER_NAME"
echo "================================"
echo

# Check if container is running
if ! docker ps --format "table {{.Names}}" | grep -q "^$CONTAINER_NAME$"; then
    echo "❌ Container '$CONTAINER_NAME' is not running"
    echo
    echo "Available containers:"
    docker ps --format "table {{.Names}}\t{{.Status}}" | grep claude-bot
    exit 1
fi

echo "✅ Container is running"
echo

# Show recent logs with timestamps
echo "📝 Recent Activity (last 20 lines):"
echo "------------------------------------"
docker logs --tail=20 --timestamps "$CONTAINER_NAME"

echo
echo "🔄 Live monitoring (press Ctrl+C to exit):"
echo "==========================================="
docker logs -f --timestamps "$CONTAINER_NAME"