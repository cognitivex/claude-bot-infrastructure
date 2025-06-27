# Central Orchestrator Setup Guide

This guide explains how to use the new central orchestrator + dynamic worker architecture for the Claude Bot Infrastructure.

## Architecture Overview

The new system transforms from a single-bot-per-container model to a distributed architecture:

- **Central Orchestrator**: Monitors GitHub issues, manages work queue, spawns dynamic workers
- **Dynamic Workers**: Ephemeral containers that process individual tasks and self-terminate
- **Work Queue**: Persistent queue system (file-based or Redis) for task distribution
- **Container Manager**: Handles Docker container lifecycle for workers

## Quick Start

### 1. Start Central Orchestrator (New Architecture)

```bash
# Start orchestrator with Redis (recommended)
docker-compose --profile orchestrator up -d

# Or start orchestrator with file-based queue only
QUEUE_TYPE=file docker-compose --profile orchestrator up -d claude-orchestrator
```

### 2. Start Legacy Single Bot (Old Architecture)

```bash
# For comparison - start legacy single bot
docker-compose --profile dynamic up -d claude-bot-dynamic
```

## Configuration

### Environment Variables

Key environment variables for the orchestrator:

```bash
# Required
ANTHROPIC_API_KEY=your-api-key
GITHUB_TOKEN=your-github-token
TARGET_REPO=owner/repository

# Orchestrator Settings
MAX_WORKERS=3                    # Maximum concurrent workers
DISCOVERY_INTERVAL=10            # Minutes between GitHub issue checks
PROCESSING_INTERVAL=2            # Minutes between queue processing
BOT_LABEL=claude-bot             # GitHub label to watch

# Queue Configuration  
QUEUE_TYPE=file                  # or "redis"
REDIS_URL=redis://redis:6379/0   # When using Redis

# Platform Detection
ENABLED_PLATFORMS=nodejs:18.16.0,python:3.11
AUTO_DETECT_PLATFORMS=true
```

### Configuration File

Detailed settings in `config/orchestrator-config.yml`:
- Worker resource limits
- Platform detection rules
- Priority mapping from GitHub labels
- Monitoring and logging settings

## Usage Commands

### Monitor Orchestrator Status

```bash
# View orchestrator logs
docker logs claude-orchestrator -f

# Check status via API
curl http://localhost:8080/api/status/claude-orchestrator

# Manual status update
docker exec claude-orchestrator python3 /bot/scripts/status_reporter.py --bot-id claude-orchestrator
```

### Manual Task Management

```bash
# Add a manual task
docker exec claude-orchestrator python3 /bot/scripts/add_task.py "Task Name" "Description for Claude"

# Check queue status
docker exec claude-orchestrator python3 -c "
from scripts.work_queue import create_work_queue
queue = create_work_queue('file', queue_dir='/bot/data/queue')
print(queue.get_queue_stats())
"
```

### Worker Management

```bash
# Check active workers
docker ps --filter "name=claude-worker"

# View worker logs
docker logs claude-worker-12345678-timestamp

# Stop a specific worker (workers auto-terminate when complete)
docker stop claude-worker-12345678-timestamp
```

## Architecture Comparison

### Old Architecture (Single Bot)
- One container processes all tasks sequentially
- Platform requirements built into single image
- Limited scalability
- Resource overhead when idle

### New Architecture (Orchestrator + Workers)
- Central orchestrator manages multiple workers
- Workers spawn on-demand with exact platform requirements
- Parallel task processing
- Resource efficient (workers only exist when needed)

## Key Files

### New Components
- `scripts/central_orchestrator.py` - Master coordinator
- `scripts/work_queue.py` - Queue management system
- `scripts/container_manager.py` - Docker container lifecycle
- `scripts/worker_executor.py` - Individual worker logic
- `config/orchestrator-config.yml` - Configuration settings

### Updated Components
- `docker-compose.yml` - Added orchestrator and Redis services
- `scripts/status_reporter.py` - Multi-worker status support

## Monitoring

### Status Dashboard
- Web dashboard: http://localhost:8080
- Shows orchestrator status, queue depth, active workers
- Real-time updates every 30 seconds

### Queue Statistics
- Pending tasks
- Assigned tasks (being processed)
- Completed tasks
- Failed tasks (with retry logic)

### Worker Metrics
- Active worker count
- Worker resource usage
- Task completion rates
- Error rates and retry statistics

## Troubleshooting

### Common Issues

1. **Workers not spawning**
   - Check Docker socket mount: `/var/run/docker.sock:/var/run/docker.sock:ro`
   - Verify base image exists: `docker images | grep claude-bot-dynamic`

2. **Tasks stuck in pending**
   - Check orchestrator logs for errors
   - Verify platform requirements match available workers
   - Check if max_workers limit reached

3. **Redis connection issues**
   - Ensure Redis service is healthy: `docker ps | grep redis`
   - Check Redis logs: `docker logs claude-redis`
   - Fallback to file-based queue: `QUEUE_TYPE=file`

### Debug Mode

```bash
# Start orchestrator in debug mode
docker run -it --rm \
  --env-file .env \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v $(pwd):/workspace \
  claude-bot-dynamic \
  python3 /bot/scripts/central_orchestrator.py --debug --once
```

## Migration from Legacy

To migrate from the old single-bot architecture:

1. Stop legacy bots: `docker-compose down claude-bot claude-bot-dynamic`
2. Update environment variables for orchestrator
3. Start orchestrator: `docker-compose --profile orchestrator up -d`
4. Monitor transition via status dashboard

The orchestrator maintains compatibility with existing GitHub label workflows and produces the same PR/issue management behavior.