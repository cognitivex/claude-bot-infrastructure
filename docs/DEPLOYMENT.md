# Claude Bot Infrastructure - Deployment Guide

This guide covers deploying the Claude Bot Infrastructure in production environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Configuration](#configuration)
3. [Deployment Options](#deployment-options)
4. [Security Considerations](#security-considerations)
5. [Monitoring & Observability](#monitoring--observability)
6. [Troubleshooting](#troubleshooting)
7. [Maintenance](#maintenance)

## Prerequisites

### Required

- Docker 20.10+ and Docker Compose 2.0+
- Linux-based host (Ubuntu 20.04+ recommended)
- 2GB+ RAM, 10GB+ disk space
- Valid Anthropic API key
- GitHub Personal Access Token with appropriate permissions

### Optional

- Prometheus for metrics collection
- Grafana for metrics visualization
- Cloudflare Tunnel for secure external access
- SSL certificates for HTTPS

## Configuration

### 1. Environment Variables

Copy the example environment file and configure:

```bash
cp .env.example .env
```

**Required variables:**

```bash
# API Keys
ANTHROPIC_API_KEY=your_key_here
GITHUB_TOKEN=your_token_here

# Project Configuration
TARGET_REPO=owner/repository
BOT_LABEL=claude-bot

# Git Configuration
GIT_AUTHOR_NAME=Your Name
GIT_AUTHOR_EMAIL=your.email@example.com
```

**Production-specific variables:**

```bash
# Environment
ENVIRONMENT=production

# Security
RUN_AS_USER=bot
ALLOWED_REPOSITORIES=owner/repo1,owner/repo2
RATE_LIMIT_PER_HOUR=100

# Monitoring
ENABLE_METRICS=true
ENABLE_STRUCTURED_LOGGING=true
PROMETHEUS_PUSHGATEWAY_URL=http://pushgateway:9091

# Performance
MAX_CONCURRENT_TASKS=5
TASK_TIMEOUT=3600
```

### 2. Configuration File (Optional)

For complex configurations, use a YAML file:

```yaml
# config/production.yml
bot_id: claude-bot-prod
bot_label: claude-bot
target_repo: myorg/myrepo

issue_check_interval: 10
pr_check_interval: 20
status_report_interval: 300

enable_metrics: true
enable_pr_feedback: true

allowed_repositories:
  - myorg/repo1
  - myorg/repo2

rate_limit_per_hour: 200
```

Set the config file path:

```bash
BOT_CONFIG_FILE=/bot/config/production.yml
```

## Deployment Options

### Option 1: Docker Compose (Recommended)

#### Basic Deployment

```bash
# Start all services
docker-compose --profile nodejs up -d

# Or for .NET projects
docker-compose --profile dotnet up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f claude-bot
```

#### Production Docker Compose Override

Create `docker-compose.prod.yml`:

```yaml
services:
  claude-bot:
    restart: always
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "5"
    security_opt:
      - no-new-privileges:true
      - apparmor:docker-default
    read_only: true
    tmpfs:
      - /tmp
      - /run

  status-web:
    restart: always
    expose:
      - "5000"
    networks:
      - internal
      - proxy

networks:
  internal:
    internal: true
  proxy:
    external: true
```

Deploy with override:

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile nodejs up -d
```

### Option 2: Kubernetes

See [`kubernetes/`](../kubernetes/) directory for Kubernetes manifests.

```bash
# Apply configurations
kubectl apply -f kubernetes/namespace.yaml
kubectl apply -f kubernetes/configmap.yaml
kubectl apply -f kubernetes/secrets.yaml
kubectl apply -f kubernetes/deployment.yaml
kubectl apply -f kubernetes/service.yaml
```

### Option 3: Systemd Service

Create `/etc/systemd/system/claude-bot.service`:

```ini
[Unit]
Description=Claude Bot Infrastructure
After=docker.service
Requires=docker.service

[Service]
Type=simple
Restart=always
RestartSec=10
WorkingDirectory=/opt/claude-bot-infrastructure
ExecStart=/usr/local/bin/docker-compose --profile nodejs up
ExecStop=/usr/local/bin/docker-compose down
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable claude-bot
sudo systemctl start claude-bot
```

## Security Considerations

### 1. API Key Management

**Never commit API keys to version control!**

Use environment variables or secrets management:

```bash
# Using Docker secrets
echo "your_api_key" | docker secret create anthropic_api_key -
echo "your_token" | docker secret create github_token -

# Using HashiCorp Vault
export ANTHROPIC_API_KEY=$(vault kv get -field=api_key secret/claude-bot)
```

### 2. Network Security

```yaml
# Restrict network access
services:
  claude-bot:
    networks:
      - internal
    
  status-web:
    networks:
      - internal
      - proxy

networks:
  internal:
    internal: true
  proxy:
    external: true
```

### 3. Container Security

- Run as non-root user (configured by default)
- Use read-only filesystems where possible
- Drop unnecessary capabilities
- Enable AppArmor/SELinux profiles

### 4. Rate Limiting

Configure rate limits to prevent abuse:

```bash
RATE_LIMIT_PER_HOUR=100
API_RETRY_ATTEMPTS=3
API_RETRY_DELAY=2.0
```

### 5. Access Control

Restrict repository access:

```bash
ALLOWED_REPOSITORIES=myorg/repo1,myorg/repo2
```

## Monitoring & Observability

### 1. Prometheus Metrics

Enable metrics collection:

```bash
ENABLE_METRICS=true
PROMETHEUS_PUSHGATEWAY_URL=http://pushgateway:9091
```

Available metrics:

- `claude_bot_tasks_total` - Total tasks processed
- `claude_bot_task_duration_seconds` - Task processing time
- `claude_bot_api_calls_total` - API call counts
- `claude_bot_errors_total` - Error counts
- `claude_bot_health` - Health status

### 2. Logging

Enable structured logging for production:

```bash
ENABLE_STRUCTURED_LOGGING=true
LOG_LEVEL=INFO
```

Ship logs to centralized logging:

```yaml
logging:
  driver: "fluentd"
  options:
    fluentd-address: "localhost:24224"
    tag: "claude-bot"
```

### 3. Health Checks

Health endpoints:

- Bot health: `http://localhost:8080/health`
- Status web: `http://localhost:8080/api/health`

### 4. Alerts

Example Prometheus alert rules:

```yaml
groups:
  - name: claude_bot
    rules:
      - alert: BotDown
        expr: up{job="claude_bot"} == 0
        for: 5m
        annotations:
          summary: "Claude Bot is down"
      
      - alert: HighErrorRate
        expr: rate(claude_bot_errors_total[5m]) > 0.1
        for: 10m
        annotations:
          summary: "High error rate detected"
      
      - alert: TaskQueueBacklog
        expr: claude_bot_tasks_queued > 50
        for: 15m
        annotations:
          summary: "Large task queue backlog"
```

## Troubleshooting

### Common Issues

#### 1. Container Restart Loop

Check logs:
```bash
docker-compose logs --tail=50 claude-bot
```

Common causes:
- Invalid API keys
- Permission issues with volumes
- Network connectivity problems

#### 2. High Memory Usage

Monitor memory:
```bash
docker stats claude-bot
```

Solutions:
- Increase memory limits
- Reduce `MAX_CONCURRENT_TASKS`
- Enable swap on host

#### 3. API Rate Limits

Check metrics:
```bash
curl http://localhost:8000/metrics | grep rate_limit
```

Solutions:
- Reduce check intervals
- Implement backoff strategies
- Use multiple API keys (if allowed)

### Debug Mode

Enable debug logging:

```bash
DEBUG_MODE=true
LOG_LEVEL=DEBUG
```

### Manual Task Execution

Test individual components:

```bash
# Test status reporter
docker-compose exec claude-bot python3 /bot/scripts/status_reporter.py

# Test configuration
docker-compose exec claude-bot python3 /bot/scripts/config_manager.py
```

## Maintenance

### 1. Updates

```bash
# Pull latest changes
git pull origin main

# Rebuild containers
docker-compose build --no-cache

# Restart with new version
docker-compose --profile nodejs up -d
```

### 2. Backup

Backup critical data:

```bash
# Backup volumes
docker run --rm -v claude-bot-infrastructure_bot-data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/bot-data-$(date +%Y%m%d).tar.gz -C /data .
```

### 3. Log Rotation

Configure log rotation:

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "5"
    compress: "true"
```

### 4. Cleanup

Remove old data:

```bash
# Clean processed tasks older than 30 days
find /bot/data/processed -name "*.json" -mtime +30 -delete

# Prune Docker resources
docker system prune -a --volumes
```

## Performance Tuning

### 1. Container Resources

```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
    reservations:
      cpus: '1'
      memory: 1G
```

### 2. Concurrent Tasks

Adjust based on workload:

```bash
MAX_CONCURRENT_TASKS=5  # Increase for more parallelism
TASK_TIMEOUT=3600       # Adjust based on task complexity
```

### 3. Check Intervals

Balance responsiveness vs API usage:

```bash
ISSUE_CHECK_INTERVAL=10    # More frequent for active repos
PR_CHECK_INTERVAL=20       # Less frequent for PR feedback
STATUS_REPORT_INTERVAL=300 # 5 minutes is usually sufficient
```

## Production Checklist

Before going to production:

- [ ] Configure all required environment variables
- [ ] Set up proper secrets management
- [ ] Enable monitoring and alerting
- [ ] Configure log aggregation
- [ ] Set up automated backups
- [ ] Test disaster recovery procedures
- [ ] Document runbooks for common issues
- [ ] Set up on-call rotation
- [ ] Perform security audit
- [ ] Load test the system

## Support

For issues and questions:

1. Check logs: `docker-compose logs`
2. Review metrics: `http://localhost:8000/metrics`
3. Check health: `http://localhost:8080/health`
4. File issues: https://github.com/yourusername/claude-bot-infrastructure/issues