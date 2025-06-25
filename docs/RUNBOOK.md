# Claude Bot Infrastructure - Operations Runbook

This runbook provides step-by-step procedures for common operational tasks and incident response.

## Table of Contents

1. [Emergency Contacts](#emergency-contacts)
2. [System Overview](#system-overview)
3. [Common Operations](#common-operations)
4. [Incident Response](#incident-response)
5. [Troubleshooting Procedures](#troubleshooting-procedures)
6. [Recovery Procedures](#recovery-procedures)

## Emergency Contacts

| Role | Contact | When to Contact |
|------|---------|----------------|
| On-Call Engineer | See PagerDuty | System down, critical errors |
| Team Lead | team-lead@company.com | Escalation needed |
| Security Team | security@company.com | Security incidents |
| Infrastructure | infra@company.com | Infrastructure issues |

## System Overview

### Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   GitHub API    │────▶│   Claude Bot    │────▶│  Anthropic API  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │  Status Web UI  │
                        └─────────────────┘
```

### Key Components

1. **Claude Bot Container**: Main bot logic
2. **Status Web**: Dashboard and API
3. **Data Volumes**: Persistent storage
4. **Metrics**: Prometheus integration

### Critical Paths

- GitHub webhook → Bot → Issue processing → PR creation
- Status reporter → Web dashboard → Health monitoring

## Common Operations

### Starting the System

```bash
# Full system startup
cd /opt/claude-bot-infrastructure
docker-compose --profile nodejs up -d

# Verify startup
docker-compose ps
docker-compose logs --tail=50 claude-bot
```

### Stopping the System

```bash
# Graceful shutdown
docker-compose stop

# Full shutdown
docker-compose down

# Emergency stop
docker kill claude-bot
```

### Viewing Logs

```bash
# Real-time logs
docker-compose logs -f claude-bot

# Last 100 lines
docker-compose logs --tail=100 claude-bot

# Logs from specific time
docker-compose logs --since="2024-01-01T00:00:00" claude-bot

# Search logs
docker-compose logs claude-bot | grep ERROR
```

### Checking Health

```bash
# Container health
docker ps --format "table {{.Names}}\t{{.Status}}"

# Application health
curl -s http://localhost:8080/api/health | jq .

# Metrics
curl -s http://localhost:8000/metrics | grep claude_bot_health
```

### Manual Task Execution

```bash
# Run status reporter manually
docker-compose exec claude-bot python3 /bot/scripts/status_reporter.py

# Check configuration
docker-compose exec claude-bot python3 /bot/scripts/config_manager.py

# List queued tasks
docker-compose exec claude-bot ls -la /bot/data/queue/
```

## Incident Response

### Severity Levels

| Level | Description | Response Time | Examples |
|-------|-------------|---------------|----------|
| P1 | Critical | 15 minutes | Bot completely down, data loss |
| P2 | High | 1 hour | Partial outage, high error rate |
| P3 | Medium | 4 hours | Performance degradation |
| P4 | Low | Next business day | Minor issues |

### Initial Response Checklist

1. **Acknowledge alert** in monitoring system
2. **Assess impact** - How many users/repos affected?
3. **Check logs** for obvious errors
4. **Notify stakeholders** if P1/P2
5. **Begin troubleshooting** using procedures below

## Troubleshooting Procedures

### Bot Not Processing Issues

**Symptoms:**
- New issues with bot label not being processed
- Queue not emptying

**Diagnosis:**
```bash
# Check if bot is running
docker ps | grep claude-bot

# Check logs for errors
docker-compose logs --tail=100 claude-bot | grep ERROR

# Check queue status
docker-compose exec claude-bot ls -la /bot/data/queue/

# Verify GitHub connectivity
docker-compose exec claude-bot gh auth status
```

**Resolution:**
1. If container is down: `docker-compose up -d claude-bot`
2. If API errors: Check API keys in environment
3. If queue full: Check for processing errors in logs
4. If GitHub auth failed: Verify GITHUB_TOKEN is valid

### High Memory Usage

**Symptoms:**
- Container using >2GB RAM
- OOM kills
- Slow performance

**Diagnosis:**
```bash
# Check memory usage
docker stats claude-bot --no-stream

# Check for memory leaks
docker-compose exec claude-bot ps aux | sort -nrk 4 | head

# Review task processing
docker-compose logs --tail=1000 claude-bot | grep "task_duration"
```

**Resolution:**
1. Restart container: `docker-compose restart claude-bot`
2. Reduce concurrent tasks: `MAX_CONCURRENT_TASKS=2`
3. Increase memory limit in docker-compose.yml
4. Check for infinite loops in task processing

### API Rate Limiting

**Symptoms:**
- 429 errors in logs
- "Rate limit exceeded" messages
- Slow task processing

**Diagnosis:**
```bash
# Check rate limit status
docker-compose logs claude-bot | grep -i "rate limit"

# Check metrics
curl -s http://localhost:8000/metrics | grep api_rate_limit
```

**Resolution:**
1. Increase check intervals:
   ```bash
   ISSUE_CHECK_INTERVAL=30
   PR_CHECK_INTERVAL=60
   ```
2. Reduce concurrent tasks
3. Implement backoff in code
4. Consider using multiple API keys (if allowed)

### Container Restart Loop

**Symptoms:**
- Container constantly restarting
- Status shows "Restarting (1)"

**Diagnosis:**
```bash
# Check exit code
docker ps -a | grep claude-bot

# Check logs
docker logs claude-bot --tail=50

# Check health check
docker inspect claude-bot | jq '.[0].State.Health'
```

**Resolution:**
1. Check environment variables are set correctly
2. Verify volume permissions: `ls -la /var/lib/docker/volumes/`
3. Check disk space: `df -h`
4. Temporarily disable health check to debug

## Recovery Procedures

### Full System Recovery

1. **Stop all containers**
   ```bash
   docker-compose down
   ```

2. **Backup current data**
   ```bash
   tar -czf backup-$(date +%Y%m%d-%H%M%S).tar.gz /var/lib/docker/volumes/claude-bot-infrastructure_bot-data
   ```

3. **Clear problematic data**
   ```bash
   # Remove stuck tasks
   docker run --rm -v claude-bot-infrastructure_bot-data:/data alpine \
     find /data/queue -name "*.json" -mtime +1 -delete
   ```

4. **Restart system**
   ```bash
   docker-compose --profile nodejs up -d
   ```

5. **Verify recovery**
   ```bash
   docker-compose ps
   curl http://localhost:8080/api/health
   ```

### Data Corruption Recovery

1. **Identify corrupted files**
   ```bash
   docker-compose exec claude-bot python3 -c "
   import json
   import os
   for f in os.listdir('/bot/data/queue'):
       try:
           with open(f'/bot/data/queue/{f}') as file:
               json.load(file)
       except:
           print(f'Corrupted: {f}')
   "
   ```

2. **Move corrupted files**
   ```bash
   docker-compose exec claude-bot mkdir -p /bot/data/corrupted
   docker-compose exec claude-bot mv /bot/data/queue/corrupted*.json /bot/data/corrupted/
   ```

3. **Restart processing**
   ```bash
   docker-compose restart claude-bot
   ```

### Emergency API Key Rotation

1. **Generate new API keys** in respective services

2. **Update environment**
   ```bash
   # Edit .env file
   vim .env
   
   # Or use docker secrets
   echo "new_api_key" | docker secret create anthropic_api_key_v2 -
   ```

3. **Restart services**
   ```bash
   docker-compose restart claude-bot
   ```

4. **Verify new keys work**
   ```bash
   docker-compose logs --tail=50 claude-bot | grep -i auth
   ```

## Maintenance Procedures

### Daily Checks

- [ ] Review error logs: `docker-compose logs claude-bot | grep ERROR`
- [ ] Check queue size: `ls /bot/data/queue | wc -l`
- [ ] Verify health endpoint: `curl http://localhost:8080/api/health`

### Weekly Maintenance

- [ ] Review metrics trends
- [ ] Clean old processed tasks
- [ ] Check disk usage
- [ ] Review API usage vs limits

### Monthly Maintenance

- [ ] Rotate logs
- [ ] Update dependencies
- [ ] Review and update documentation
- [ ] Test recovery procedures

## Monitoring Queries

### Useful Prometheus Queries

```promql
# Error rate
rate(claude_bot_errors_total[5m])

# Task processing time (95th percentile)
histogram_quantile(0.95, rate(claude_bot_task_duration_seconds_bucket[5m]))

# Queue depth
claude_bot_tasks_queued

# API success rate
rate(claude_bot_api_calls_total{status="success"}[5m]) / 
rate(claude_bot_api_calls_total[5m])
```

### Log Queries

```bash
# Find all errors in last hour
docker-compose logs --since="1h" claude-bot | grep ERROR

# Find specific task
docker-compose logs claude-bot | grep "task_id_here"

# Performance issues
docker-compose logs claude-bot | grep -E "duration.*[0-9]{4,}"
```

## Post-Incident Review

After resolving any P1/P2 incident:

1. **Document timeline** of events
2. **Identify root cause**
3. **List action items** to prevent recurrence
4. **Update runbook** with new procedures
5. **Share learnings** with team

## Additional Resources

- [Deployment Guide](DEPLOYMENT.md)
- [Architecture Documentation](ARCHITECTURE.md)
- [API Documentation](API.md)
- [Security Guide](SECURITY.md)