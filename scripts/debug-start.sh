#!/bin/bash
# Debug wrapper script to trace container startup issues

set -x  # Enable command tracing
set -e  # Exit on error

echo "=== DEBUG START ==="
echo "Date: $(date)"
echo "Hostname: $(hostname)"
echo "Current user: $(id)"
echo "Current directory: $(pwd)"
echo "PATH: $PATH"
echo ""

echo "=== ENVIRONMENT VARIABLES ==="
env | grep -E "(PYTHON|PATH|TARGET_REPO|BOT_LABEL)" | sort
echo ""

echo "=== PYTHON ENVIRONMENT ==="
echo "which python3:"
which python3 || echo "python3 not found in PATH"
echo ""
echo "python3 location:"
ls -la /usr/bin/python* 2>/dev/null || echo "No python in /usr/bin"
echo ""
echo "python3 version:"
/usr/bin/python3 --version 2>&1 || echo "Failed to run python3"
echo ""

echo "=== SCRIPT DIRECTORY CHECK ==="
echo "Contents of /bot/scripts:"
ls -la /bot/scripts/*.py 2>/dev/null | head -10 || echo "No scripts found"
echo ""

echo "=== TESTING PYTHON EXECUTION ==="
echo "Test 1 - Direct execution:"
/usr/bin/python3 -c "print('Python works directly')" 2>&1
echo ""

echo "Test 2 - Via env:"
env python3 -c "print('Python works via env')" 2>&1
echo ""

echo "Test 3 - Script execution:"
cd /bot/scripts
/usr/bin/python3 -c "import sys; print(f'Python path: {sys.path[:3]}')" 2>&1
echo ""

echo "=== ATTEMPTING TO START BOT ==="
echo "Running setup-labels.py..."
/usr/bin/python3 setup-labels.py --repo "$TARGET_REPO" 2>&1 || echo "setup-labels failed with: $?"
echo ""

echo "Running bot-orchestrator.py..."
exec /usr/bin/python3 bot-orchestrator.py \
    --repo "$TARGET_REPO" \
    --data "/bot/data" \
    --issue-interval "${ISSUE_CHECK_INTERVAL:-15}" \
    --pr-interval "${PR_CHECK_INTERVAL:-30}" 2>&1