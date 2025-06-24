# Claude Bot Infrastructure

A reusable, containerized Claude Code bot that can automate tasks for any GitHub repository. The bot monitors GitHub issues, executes tasks using Claude Code, creates pull requests, and responds to code review feedback.

## 🚀 Quick Start

1. **Clone this repository:**
   ```bash
   git clone https://github.com/yourusername/claude-bot-infrastructure.git
   cd claude-bot-infrastructure
   ```

2. **Configure for your project:**
   ```bash
   cp .env.example .env
   # Edit .env and set:
   # - PROJECT_PATH (path to your project)
   # - ANTHROPIC_API_KEY
   # - GITHUB_TOKEN
   # - TARGET_REPO (owner/repo)
   ```

3. **Start the bot:**
   ```bash
   docker-compose up -d
   ```

4. **Setup GitHub labels (one-time):**
   ```bash
   docker exec claude-bot-infrastructure_claude-bot_1 setup-labels.py
   ```

5. **Start monitoring:**
   ```bash
   docker exec claude-bot-infrastructure_claude-bot_1 bot-orchestrator.py
   ```

That's it! Now create GitHub issues with the `claude-bot` label and watch the magic happen.

## 📋 Features

### ✅ Complete GitHub Integration
- **Issue Processing**: Automatically detects and processes labeled issues
- **PR Creation**: Creates branches and pull requests automatically  
- **Code Review Response**: Responds to PR feedback and applies changes
- **Status Tracking**: Updates issues with progress labels and comments

### 🔧 Flexible Configuration
- **Multi-Project Support**: One bot can work with multiple repositories
- **Customizable Labels**: Configure trigger labels and behavior
- **Project-Specific Settings**: Custom build commands, test scripts, etc.
- **Environment-Based Config**: Easy setup via environment variables

### 🤖 Intelligent Automation
- **Claude Code Integration**: Uses Claude's coding capabilities
- **Context-Aware**: Understands project patterns and conventions
- **Feedback Loop**: Continuously improves based on code reviews
- **Safe Operations**: Creates branches, never modifies main directly

## 📁 Repository Structure

```
claude-bot-infrastructure/
├── .devcontainer/
│   ├── docker-compose.yml          # Main container configuration
│   └── Dockerfile.claude-bot       # Bot container setup
├── scripts/                        # Bot automation scripts
│   ├── github-task-executor.py     # Main GitHub issue processor
│   ├── pr-feedback-handler.py      # PR comment/review handler
│   ├── bot-orchestrator.py         # Unified management script
│   ├── setup-labels.py            # GitHub label setup
│   └── ...                        # Additional utilities
├── config/                         # Configuration templates
│   └── project-config.example.yml  # Project-specific settings
├── .env.example                    # Environment configuration template
└── README.md                       # This file
```

## ⚙️ Configuration

### Environment Variables (.env)

**Required:**
- `ANTHROPIC_API_KEY` - Your Claude API key
- `GITHUB_TOKEN` - GitHub personal access token (repo, workflow permissions)
- `PROJECT_PATH` - Path to the project to monitor (e.g., `../my-project`)

**Optional:**
- `TARGET_REPO` - GitHub repository (owner/repo format)
- `BOT_LABEL` - Label that triggers bot action (default: `claude-bot`)
- `GIT_AUTHOR_NAME/EMAIL` - Git commit author information

### Project Configuration (config/project-config.yml)

Customize bot behavior for specific projects:
- Build and test commands
- Source directories to focus on
- Custom Claude instructions
- PR template customization

## 🎯 Usage Workflows

### Basic Issue → PR Workflow

1. **Create GitHub Issue:**
   ```
   Title: Fix loading spinner in user component
   Body: The loading spinner stays visible after data loads
   Labels: claude-bot
   ```

2. **Bot Automatically:**
   - Detects the labeled issue
   - Creates branch: `bot/issue-123-fix-loading-spinner`
   - Runs Claude Code to implement the fix
   - Commits changes with descriptive message
   - Creates pull request
   - Updates issue with PR link and status

3. **Code Review & Feedback:**
   - You review the PR and leave comments
   - Bot detects feedback and applies changes
   - Iterative improvement until ready to merge

### Advanced: Multiple Projects

```bash
# Set up bot for Project A
PROJECT_PATH=../project-a TARGET_REPO=owner/project-a docker-compose up -d bot-a

# Set up bot for Project B  
PROJECT_PATH=../project-b TARGET_REPO=owner/project-b docker-compose up -d bot-b
```

## 🔧 Commands

### Container Management
```bash
# Start bot
docker-compose up -d

# View logs
docker logs claude-bot-infrastructure_claude-bot_1

# Access bot shell
docker exec -it claude-bot-infrastructure_claude-bot_1 bash

# Stop bot
docker-compose down
```

### Bot Operations
```bash
# Setup GitHub labels (run once)
docker exec claude-bot-infrastructure_claude-bot_1 setup-labels.py

# Run full automation (issues + PR feedback)
docker exec claude-bot-infrastructure_claude-bot_1 bot-orchestrator.py

# Process issues only (one-time)
docker exec claude-bot-infrastructure_claude-bot_1 github-task-executor.py

# Handle PR feedback only
docker exec claude-bot-infrastructure_claude-bot_1 pr-feedback-handler.py

# Check bot status
docker exec claude-bot-infrastructure_claude-bot_1 bot-status.py
```

### Background Monitoring
```bash
# Continuous monitoring (recommended)
docker exec claude-bot-infrastructure_claude-bot_1 nohup bot-orchestrator.py > /bot/logs/bot.log 2>&1 &

# Scheduled execution (cron)
# Add to your host crontab:
*/20 * * * * docker exec claude-bot-infrastructure_claude-bot_1 bot-orchestrator.py --once
```

## 🏷️ GitHub Labels

The bot uses these labels to track progress:

- **`claude-bot`** - Main trigger label (add to issues for bot processing)
- **`bot:queued`** - Issue has been queued for processing
- **`bot:in-progress`** - Bot is currently working on the issue
- **`bot:completed`** - Bot has completed the work and created a PR
- **`bot:failed`** - Bot encountered an error and couldn't complete the task

## 🔐 Security & Permissions

### GitHub Token Permissions
Your GitHub token needs:
- `repo` - Full repository access
- `workflow` - GitHub Actions workflow access
- `write:packages` - Package registry access (if needed)

### Safe Operations
- Bot never modifies main/master branch directly
- All changes go through pull requests
- Git commits are properly attributed
- SSH keys and git config are mounted read-only

## 🐛 Troubleshooting

### Common Issues

**Bot not detecting issues:**
- Verify `TARGET_REPO` is correctly set
- Check GitHub token permissions
- Ensure labels are properly configured: `docker exec ... setup-labels.py`

**Claude Code errors:**
- Verify `ANTHROPIC_API_KEY` is valid
- Check API quota/limits
- Review bot logs: `docker logs claude-bot-infrastructure_claude-bot_1`

**Git/GitHub errors:**
- Ensure git credentials are properly mounted
- Check GitHub token expiration
- Verify repository write permissions

### Log Locations
- Container logs: `docker logs <container_name>`
- Bot application logs: `/bot/logs/` (inside container)
- Individual script outputs: `/bot/logs/*.log`

### Debug Mode
```bash
# Run bot commands with verbose output
docker exec claude-bot-infrastructure_claude-bot_1 python -u bot-orchestrator.py --debug
```

## 🤝 Contributing

1. Fork this repository
2. Create a feature branch
3. Test with your own projects
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🔗 Related Projects

- [Claude Code](https://docs.anthropic.com/claude/docs/claude-code) - Official Claude Code documentation
- [GitHub CLI](https://cli.github.com/) - Command line tool for GitHub
- [Docker Compose](https://docs.docker.com/compose/) - Multi-container Docker applications