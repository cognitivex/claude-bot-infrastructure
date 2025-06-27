# Setting Up Claude Bot for a New Repository

This guide shows how to configure the Claude Bot Infrastructure for a new repository using the orchestrator architecture.

## Quick Setup (5 minutes)

### 1. Clone and Configure

```bash
# Clone the bot infrastructure
git clone https://github.com/cognitivex/claude-bot-infrastructure.git
cd claude-bot-infrastructure

# Copy environment template
cp .env.example .env
```

### 2. Edit Environment Variables

Edit `.env` with your repository details:

```bash
# Required: API Keys
ANTHROPIC_API_KEY=your-claude-api-key-here
GITHUB_TOKEN=your-github-token-here

# Your Repository Configuration
TARGET_REPO=your-username/your-repo-name
PROJECT_PATH=/path/to/your/local/repo

# Git Configuration
GIT_AUTHOR_NAME=Your Name
GIT_AUTHOR_EMAIL=your.email@example.com

# Bot Behavior (optional customization)
BOT_LABEL=claude-bot
MAX_WORKERS=3
DISCOVERY_INTERVAL=15    # minutes between GitHub issue checks
```

### 3. Start the Orchestrator

```bash
# Start the bot infrastructure
docker-compose --profile orchestrator up -d

# View logs to confirm it's working
docker logs claude-orchestrator -f

# Check status dashboard
open http://localhost:8080
```

## Platform Detection (Automatic)

The orchestrator automatically detects your project's platform requirements by scanning for:

| Platform | Detection Files | Auto-detected Version |
|----------|----------------|----------------------|
| **Node.js** | `package.json`, `.nvmrc`, `yarn.lock` | From engines field or .nvmrc |
| **.NET** | `*.csproj`, `global.json`, `*.sln` | From TargetFramework or SDK version |
| **Python** | `requirements.txt`, `pyproject.toml` | From requires-python or runtime.txt |
| **Java** | `pom.xml`, `build.gradle` | From compiler source/target |
| **Go** | `go.mod` | From go directive |
| **Rust** | `Cargo.toml` | From rust-version or toolchain |
| **PHP** | `composer.json` | From require.php |
| **Ruby** | `Gemfile`, `.ruby-version` | From ruby version |

## Manual Platform Override

If you need to specify exact platform requirements, create a `.claude-platforms` file in your repo:

```yaml
# .claude-platforms
platforms:
  nodejs: "18.16.0"
  python: "3.11"
  # dotnet: "8.0"
  # java: "17"
```

Or set the environment variable:

```bash
ENABLED_PLATFORMS="nodejs:18.16.0,python:3.11"
```

## Repository-Specific Configuration

### Option 1: Environment Variables (Recommended)

```bash
# Basic Configuration
TARGET_REPO=myorg/myproject
BOT_LABEL=claude-bot
PROJECT_PATH=/home/user/projects/myproject

# Advanced Configuration  
MAX_WORKERS=5                    # More workers for large projects
DISCOVERY_INTERVAL=5             # Check issues every 5 minutes
PROCESSING_INTERVAL=1            # Process queue every minute
QUEUE_TYPE=redis                 # Use Redis instead of file queue
```

### Option 2: Project Configuration File

Create `config/project-config.yml`:

```yaml
project:
  name: "My Project"
  repository: "myorg/myproject"
  platforms:
    auto_detect: true
    override:
      nodejs: "20.0.0"    # Force specific version
  
orchestrator:
  max_workers: 5
  discovery_interval: 10
  
github:
  labels:
    bot_trigger: "claude-bot"
    priority_high: ["urgent", "critical"]
    priority_low: ["documentation", "minor"]
```

## GitHub Repository Setup

### 1. Create GitHub Labels

Run the label setup script:

```bash
docker exec claude-orchestrator python3 /bot/scripts/setup_labels.py
```

This creates the following labels in your repository:
- `claude-bot` - Triggers bot processing
- `bot:queued` - Task queued for processing  
- `bot:in-progress` - Currently being processed
- `bot:completed` - Successfully completed
- `bot:failed` - Processing failed

### 2. Create Test Issue

Create a GitHub issue with:
- Title: "Test Claude Bot Integration"
- Label: `claude-bot`
- Description: "Please create a simple README.md file explaining this project"

### 3. Verify Bot Responds

The orchestrator will:
1. Detect the new issue within 15 minutes (default interval)
2. Analyze platform requirements automatically
3. Spawn appropriate worker container
4. Process the issue with Claude Code
5. Create a pull request with the solution
6. Update issue status

## Monitoring and Management

### Status Dashboard
```bash
# Web dashboard
open http://localhost:8080

# Shows:
# - Queue depth (pending, in-progress, completed)
# - Active workers and their capabilities  
# - Recent activity and completion rates
# - Orchestrator health and uptime
```

### Command Line Monitoring
```bash
# Check orchestrator status
docker logs claude-orchestrator --tail 20

# View queue statistics
docker exec claude-orchestrator python3 -c "
from scripts.work_queue import create_work_queue
queue = create_work_queue('file', queue_dir='/bot/data/queue')
print(queue.get_queue_stats())
"

# Check active workers
docker ps --filter 'name=claude-worker'
```

### Manual Task Management
```bash
# Add a manual task
docker exec claude-orchestrator python3 /bot/scripts/add_task.py \
  "Fix documentation" \
  "Please update the README.md with installation instructions"

# Process queue immediately (don't wait for interval)
docker exec claude-orchestrator python3 /bot/scripts/central_orchestrator.py --once
```

## Advanced Configuration

### Multi-Repository Setup

You can run multiple orchestrators for different repositories:

```bash
# Repository 1
TARGET_REPO=org/repo1 BOT_ID=claude-bot-repo1 docker-compose up -d claude-orchestrator

# Repository 2  
TARGET_REPO=org/repo2 BOT_ID=claude-bot-repo2 docker-compose up -d claude-orchestrator
```

### Custom Worker Scaling

```yaml
# config/orchestrator-config.yml
orchestrator:
  max_workers: 10
  
workers:
  resources:
    memory_limit: "4g"
    cpu_limit: 2.0
    
  platforms:
    nodejs:
      default_version: "20.0.0"
      max_workers: 3
    python:  
      default_version: "3.12"
      max_workers: 2
```

### Priority-Based Processing

Configure GitHub labels for priority handling:

```yaml
# config/orchestrator-config.yml
github:
  priority_labels:
    urgent: ["urgent", "critical", "p0", "hotfix"]
    high: ["high", "important", "p1", "bug"]
    medium: ["enhancement", "feature", "p2"]
    low: ["documentation", "minor", "p3"]
```

## Troubleshooting

### Common Issues

1. **No issues detected**: Check `TARGET_REPO` and `GITHUB_TOKEN` 
2. **Workers not spawning**: Verify Docker socket mount and permissions
3. **Platform detection fails**: Add manual `.claude-platforms` file
4. **Queue not processing**: Check orchestrator logs for errors

### Debug Mode

```bash
# Run orchestrator in debug mode
docker run --rm -it \
  --env-file .env \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v $(pwd):/workspace \
  claude-bot-infrastructure-claude-orchestrator \
  python3 /bot/scripts/central_orchestrator.py --debug --once
```

## Example: Node.js + TypeScript Project

For a typical Node.js TypeScript project:

```bash
# .env
TARGET_REPO=myorg/typescript-api
PROJECT_PATH=/home/user/projects/typescript-api
ANTHROPIC_API_KEY=your-key
GITHUB_TOKEN=your-token
ENABLED_PLATFORMS=nodejs:18.16.0
```

The orchestrator will automatically:
- Detect TypeScript from `tsconfig.json`
- Use Node.js 18.16.0 for workers
- Install dependencies with `npm install`
- Run TypeScript compilation for validation
- Execute Claude Code in the proper environment

That's it! The orchestrator handles the rest automatically.