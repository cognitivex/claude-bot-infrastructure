#!/bin/bash
# Quick status check for Claude Bot
# Usage: ./status.sh [container_name]

CONTAINER_NAME=${1:-claude-bot-dotnet}

echo "🤖 Claude Bot Status Check"
echo "=========================="
echo

# Check container status
echo "📦 Container Status:"
if docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -q "^$CONTAINER_NAME"; then
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep "^$CONTAINER_NAME"
    echo "✅ Container is running"
else
    echo "❌ Container '$CONTAINER_NAME' is not running"
    echo
    echo "Available Claude Bot containers:"
    docker ps -a --format "table {{.Names}}\t{{.Status}}" | grep claude-bot || echo "No Claude Bot containers found"
    exit 1
fi

echo

# Check bot data directory
echo "📁 Bot Data Status:"
if docker exec "$CONTAINER_NAME" test -d /bot/data 2>/dev/null; then
    echo "✅ Bot data directory exists"
    
    # Check queue
    QUEUE_COUNT=$(docker exec "$CONTAINER_NAME" find /bot/data/queue -name "*.json" 2>/dev/null | wc -l)
    echo "📋 Queued tasks: $QUEUE_COUNT"
    
    # Check processed
    PROCESSED_COUNT=$(docker exec "$CONTAINER_NAME" find /bot/data/processed -name "*.json" 2>/dev/null | wc -l)
    echo "✅ Processed tasks: $PROCESSED_COUNT"
else
    echo "❌ Bot data directory not accessible"
fi

echo

# Check GitHub connectivity
echo "🔐 GitHub Connectivity:"
if docker exec "$CONTAINER_NAME" gh auth status >/dev/null 2>&1; then
    echo "✅ GitHub authentication working"
    REPO=$(docker exec "$CONTAINER_NAME" printenv TARGET_REPO 2>/dev/null || echo "Unknown")
    echo "📁 Target repository: $REPO"
else
    echo "❌ GitHub authentication issue"
fi

echo

# Show last few log lines
echo "📝 Recent Activity:"
echo "==================="
docker logs --tail=5 --timestamps "$CONTAINER_NAME"

echo
echo "💡 Commands:"
echo "  Monitor live activity: ./monitor.sh"
echo "  View detailed status:  python3 scripts/monitor_activity.py --once"
echo "  Check bot queue:       docker exec $CONTAINER_NAME bot_status.py"