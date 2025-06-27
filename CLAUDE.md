# Claude Bot Infrastructure

This is a containerized automation system that integrates Claude Code with GitHub repositories to automate development tasks. The bot monitors GitHub issues, executes tasks using Claude Code, and creates pull requests with automated code changes.

## 🚀 Quick Start

```bash
# 1. Clone and configure
git clone <your-repo>
cd claude-bot-infrastructure

# 2. Set up secrets (choose one method)
cp config/examples/.env.example .env
# Edit .env with your secrets

# 3. Start the bot
docker-compose up -d

# 4. Monitor status
docker logs claude-orchestrator -f
```

## 📁 Project Structure

```
claude-bot-infrastructure/
├── src/claude_bot/          # Core application code
│   ├── orchestrator/        # Bot orchestration logic
│   ├── executors/          # Task execution (GitHub, PR handling)
│   ├── platform/           # Multi-platform support
│   ├── security/           # Secret management
│   ├── monitoring/         # Status reporting & health checks
│   └── utils/              # Shared utilities
├── deployment/             # All deployment configurations
│   ├── docker/            # Docker Compose files
│   ├── azure/             # Azure-specific deployment
│   └── scripts/           # Deployment scripts
├── config/                # Configuration files
│   ├── default/          # Default configurations
│   ├── environments/     # Environment-specific configs
│   ├── templates/        # Workflow templates
│   └── examples/         # Example configurations
├── docs/                 # Documentation
├── tests/               # All testing
└── apps/               # Standalone applications
```

## 🔧 Development Commands

### Container Operations
```bash
# Development mode (live code changes)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Production mode
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# With secure secrets
docker-compose -f docker-compose.yml -f deployment/docker/docker-compose.secure.yml up -d

# With Azure integration
docker-compose -f docker-compose.yml -f deployment/docker/docker-compose.azure.yml up -d
```

### Bot Execution
```bash
# One-time setup (run first)
python3 src/tools/setup_labels.py

# Run individual components
python3 -m claude_bot.executors.github_task_executor
python3 -m claude_bot.executors.pr_feedback_handler  
python3 -m claude_bot.orchestrator.bot_orchestrator

# Check status and queue
python3 src/tools/bot_status.py

# Add manual tasks
python3 src/tools/add_task.py "Task Name" "Description for Claude"
```

## 📖 Documentation

- **[Getting Started](docs/getting-started/)** - Installation and first bot setup
- **[Guides](docs/guides/)** - How-to guides for specific features
- **[Reference](docs/reference/)** - Technical documentation
- **[Examples](docs/examples/)** - Example projects and configurations

### Key Documents
- **[Secret Management](docs/guides/secret-management.md)** - Secure credential handling
- **[Azure Setup](docs/guides/azure-setup.md)** - Enterprise Azure deployment
- **[Multi-Platform](docs/guides/multi-platform.md)** - Supporting multiple tech stacks
- **[Architecture](docs/reference/architecture.md)** - System design and components

## 🔐 Secret Management

Choose the approach that fits your needs:

| Use Case | Method | Command |
|----------|--------|---------|
| **Development** | `.env` file | `docker-compose up -d` |
| **Production** | Docker Secrets | `deployment/scripts/setup-secrets.sh` |
| **Enterprise** | Azure Key Vault | `deployment/azure/setup-azure.sh` |

**How it works:** The orchestrator and workers run in the same container, so configuring secrets once automatically provides them to all components.

## 🏗️ Architecture

The system uses a **multi-agent orchestration pattern**:

- **Orchestrator** (`src/claude_bot/orchestrator/`): Master coordinator managing workflows
- **Executors** (`src/claude_bot/executors/`): Handle issue → code → PR pipeline  
- **Platform Manager** (`src/claude_bot/platform/`): Multi-platform support (Node.js, .NET, Python)
- **Security** (`src/claude_bot/security/`): Secure secret management
- **Monitoring** (`src/claude_bot/monitoring/`): Status reporting and health checks

## 🔄 Git Workflow

The bot creates feature branches and never modifies main branches directly. All changes go through pull requests with structured commit messages and auto-generated PR descriptions.

## 🏷️ GitHub Integration

Uses GitHub labels for workflow tracking:
- `claude-bot` (configurable): Triggers bot processing
- `bot:queued`, `bot:in-progress`, `bot:completed`, `bot:failed`: Status tracking

The bot responds to PR review comments and @mentions for iterative improvements.

## 🐳 Multi-Platform Support

Supports multiple independent bot instances for different project types:

```bash
# Node.js bot (default)
docker-compose --profile nodejs up -d

# .NET 8 + Node.js bot  
docker-compose --profile dotnet up -d

# Run multiple bots simultaneously
docker-compose --profile nodejs --profile dotnet up -d
```

## 📊 Monitoring

Access the status dashboard at `http://localhost:8080` after starting the bot.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes in the `src/` directory
4. Add tests in `tests/`
5. Update documentation in `docs/`
6. Submit a pull request

## 📄 License

[Your license here]