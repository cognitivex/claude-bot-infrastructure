# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Claude Bot Infrastructure - a containerized automation system that integrates Claude Code with GitHub repositories to automate development tasks. The bot monitors GitHub issues, executes tasks using Claude Code, and creates pull requests with automated code changes.

## Architecture

The system follows a multi-agent orchestration pattern:

- **Bot Orchestrator** (`bot-orchestrator.py`): Master coordinator managing both issue processing and PR feedback cycles
- **GitHub Task Executor** (`github-task-executor.py`): Handles issue → code → PR pipeline
- **PR Feedback Handler** (`pr-feedback-handler.py`): Processes code review feedback and applies changes
- **Support Scripts**: Label setup, status monitoring, and task management

## Development Commands

### Container Operations
```bash
# Start the bot infrastructure
docker-compose up -d

# View bot logs
docker logs claude-bot-infrastructure_claude-bot_1

# Access bot shell
docker exec -it claude-bot-infrastructure_claude-bot_1 bash

# Stop services
docker-compose down
```

### Bot Execution
```bash
# One-time setup (run first)
python scripts/setup-labels.py

# Run individual components
python scripts/github-task-executor.py    # Process issues only
python scripts/pr-feedback-handler.py     # Handle PR feedback only
python scripts/bot-orchestrator.py        # Full automation cycle

# Check status and queue
python scripts/bot-status.py

# Add manual tasks
python scripts/add-task.py "Task Name" "Description for Claude"
```

## Configuration

### Required Environment Variables
- `ANTHROPIC_API_KEY`: Claude Code API access
- `GITHUB_TOKEN`: GitHub repository access
- `PROJECT_PATH`: Target repository path
- `TARGET_REPO`: GitHub repository (owner/name format)
- `GIT_AUTHOR_NAME` and `GIT_AUTHOR_EMAIL`: Git commit attribution

### Key Configuration Files
- `.env`: Environment variables (copy from `.env.example`)
- `config/project-config.example.yml`: Project-specific settings including build commands, test commands, and bot behavior

## Git Workflow

The bot creates feature branches and never modifies main branches directly. All changes go through pull requests with structured commit messages and auto-generated PR descriptions.

## GitHub Integration

Uses GitHub labels for workflow tracking:
- `claude-bot` (configurable): Triggers bot processing
- `bot:queued`, `bot:in-progress`, `bot:completed`, `bot:failed`: Status tracking

The bot responds to PR review comments and @mentions for iterative improvements.

## Docker Architecture

Multi-stage Docker setup with:
- Development container for Claude Code execution
- Production bot container for automation scripts
- Volume mounting for project code, git config, and persistent data
- Alpine-based Node.js environment with Python automation layer

### Independent Bot Services

The infrastructure supports multiple independent bot instances for different project types:

#### Default Node.js Bot
```bash
# Start default Node.js bot
docker-compose --profile nodejs up -d
# or
docker-compose up -d claude-bot
```

#### .NET 8 + Node.js 10.13 Bot
```bash
# Set up .NET environment
cp .env.dotnet.example .env.dotnet
cp config/project-config.dotnet.yml config/project-config.yml

# Start .NET bot (independent instance)
docker-compose --profile dotnet up -d
# or
docker-compose up -d claude-bot-dotnet
```

#### Running Multiple Bots Simultaneously
```bash
# Run both bots for different projects
docker-compose --profile nodejs --profile dotnet up -d

# Check status of both instances
docker logs claude-bot
docker logs claude-bot-dotnet
```

**Key Features:**
- Completely independent Docker containers
- Separate data volumes and caches
- Different environment configurations
- No shared dependencies or conflicts
- .NET bot includes: .NET 8 SDK, Entity Framework tools, Node.js 10.13, and Claude Code with Node.js 18