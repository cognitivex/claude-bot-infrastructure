# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Claude Bot Infrastructure - a containerized automation system that integrates Claude Code with GitHub repositories to automate development tasks. The bot monitors GitHub issues, executes tasks using Claude Code, and creates pull requests with automated code changes.

## Architecture

The system follows a distributed orchestrator + dynamic worker pattern:

- **Central Orchestrator** (`central_orchestrator.py`): Master coordinator that monitors GitHub issues, manages work queue, and spawns dynamic workers
- **Dynamic Workers** (`worker_executor.py`): Ephemeral containers that process individual tasks using Claude Code and self-terminate  
- **Work Queue** (`work_queue.py`): Persistent task queue with priority handling and platform compatibility matching
- **Container Manager** (`container_manager.py`): Handles Docker container lifecycle for worker spawning
- **Platform Manager** (`platform_manager.py`): Intelligent platform detection and worker capability matching
- **Status Reporter** (`status_reporter.py`): Multi-worker status aggregation and dashboard updates

## Development Commands

### Central Orchestrator (Recommended)
```bash
# Start the orchestrator infrastructure
docker-compose --profile orchestrator up -d

# View orchestrator logs
docker logs claude-orchestrator -f

# View status dashboard
open http://localhost:8080

# Stop services
docker-compose --profile orchestrator down
```

### Manual Operations
```bash
# One-time setup (run first)
python scripts/setup-labels.py

# Add manual tasks to queue
docker exec claude-orchestrator python3 /bot/scripts/add_task.py "Task Name" "Description for Claude"

# Check orchestrator status
docker exec claude-orchestrator python3 /bot/scripts/status_reporter.py --bot-id claude-orchestrator

# Run single orchestration cycle (testing)
docker exec claude-orchestrator python3 /bot/scripts/central_orchestrator.py --once
```

## Configuration

### Secret Management

The bot supports multiple secret management approaches. **For most users, the simple `.env` approach is recommended.**

#### Simple Setup (Recommended for Most Users)
```bash
# Copy and configure environment file
cp .env.example .env
# Edit .env with your secrets

# Start the bot
docker-compose up -d
```

**How it works:** The orchestrator and workers run in the same Docker container, so configuring the `.env` file automatically provides secrets to all workers.

#### Enhanced Security Options

For production deployments or enterprise requirements:

**Docker Secrets (Better Security)**
```bash
# Set up secure secret files
./setup-secure-secrets.sh

# Start with secure configuration
docker-compose -f docker-compose.yml -f docker-compose.secure.yml up -d
```

**Azure Key Vault (Enterprise)**
```bash
# Set up Azure infrastructure
./setup-azure.sh

# Start with Azure integration
docker-compose -f docker-compose.yml -f docker-compose.azure.yml up -d
```

### Required Secrets
- `ANTHROPIC_API_KEY`: Claude Code API access
- `GITHUB_TOKEN`: GitHub repository access
- `GIT_AUTHOR_NAME` and `GIT_AUTHOR_EMAIL`: Git commit attribution
- `TARGET_REPO`: GitHub repository (owner/name format)

### Which Approach to Choose?

| Use Case | Recommended Approach | Why |
|----------|---------------------|-----|
| **Development/Testing** | `.env` file | Simple, fast setup |
| **Production Deployment** | Docker Secrets | Better security, no env exposure |
| **Enterprise/Compliance** | Azure Key Vault | Centralized, audited, encrypted |
| **Multi-Environment** | Azure Key Vault | Consistent across dev/staging/prod |

### How Workers Get Secrets

In the **default setup**, workers get secrets automatically because they run in the same container as the orchestrator:

```
.env file → Docker Environment → Orchestrator Container → Workers (same process)
```

In **enhanced setups**, workers use the `SecretsLoader` system that tries multiple sources:
1. **Docker Secrets** (`/run/secrets/`) - File-based secrets
2. **Azure Key Vault** - Enterprise secret store  
3. **AWS Secrets Manager** - Cloud-native secrets
4. **Environment Variables** - Fallback for compatibility

### Key Configuration Files
- `.env`: Environment variables (copy from `.env.example`)
- `config/project-config.example.yml`: Project-specific settings including build commands, test commands, and bot behavior
- `data/secrets/`: Secure secret files (Docker secrets)
- `.env.azure`: Azure-specific configuration

## Git Workflow

The bot creates feature branches and never modifies main branches directly. All changes go through pull requests with structured commit messages and auto-generated PR descriptions.

## GitHub Integration

Uses GitHub labels for workflow tracking:
- `claude-bot` (configurable): Triggers bot processing
- `bot:queued`, `bot:in-progress`, `bot:completed`, `bot:failed`: Status tracking

The bot responds to PR review comments and @mentions for iterative improvements.

## Docker Architecture

Distributed orchestrator setup with:
- **Central Orchestrator**: Manages GitHub issue discovery, work queue, and worker lifecycle
- **Dynamic Workers**: On-demand containers with exact platform requirements for each task
- **Redis Queue**: Optional persistent queue backend (file-based queue is default)
- **Multi-Platform Support**: Automatic platform detection and worker specialization

### Orchestrator Deployment

```bash
# Start orchestrator with Redis (recommended)
docker-compose --profile orchestrator up -d

# Start orchestrator with file-based queue only
QUEUE_TYPE=file docker-compose up -d claude-orchestrator

# Monitor orchestrator
docker logs claude-orchestrator -f

# View web dashboard
open http://localhost:8080
```

**Key Features:**
- **Scalable**: Multiple workers process tasks in parallel
- **Resource Efficient**: Workers only exist when needed with exact platform requirements
- **Platform Isolation**: Each task gets precisely the runtime environment it needs
- **Fault Tolerant**: Failed workers don't impact orchestrator or other workers
- **Cost Optimized**: No idle containers with unused platform runtimes