# Claude Bot Infrastructure Testing Guide

This guide provides comprehensive instructions for testing the independent Docker bot setup.

## Quick Start

1. **Build and verify images:**
   ```bash
   ./scripts/test-build.sh
   ```

2. **Set up test environment:**
   ```bash
   # Copy test configurations
   cp .env.test .env
   cp .env.dotnet.test .env.dotnet
   cp config/project-config.test.yml config/project-config.yml
   
   # Edit files to add your API keys and GitHub repositories
   ```

3. **Start bots:**
   ```bash
   # Node.js bot only
   docker-compose --profile nodejs up -d
   
   # .NET bot only  
   docker-compose --profile dotnet up -d
   
   # Both bots
   docker-compose --profile nodejs --profile dotnet up -d
   ```

4. **Check health:**
   ```bash
   ./scripts/health-check.sh
   ```

## Test Projects

### Node.js Test Project
Location: `test-projects/nodejs-test/`

- **Express.js API** with calculator functions
- **Jest unit tests** 
- **ESLint configuration**
- Designed for testing basic Claude Bot functionality

### .NET Test Project  
Location: `test-projects/dotnet-test/`

- **.NET 8 Web API** with Swagger documentation
- **xUnit unit tests**
- **Node.js 10.13 frontend** assets
- Designed for testing .NET-specific Claude Bot features

## Testing Workflow

### Phase 1: Environment Setup

1. **Build verification:**
   ```bash
   ./scripts/test-build.sh
   ```

2. **Environment configuration:**
   ```bash
   # Configure for your test repositories
   vim .env          # Node.js bot config
   vim .env.dotnet   # .NET bot config
   ```

3. **GitHub setup:**
   - Create test repositories on GitHub
   - Push test projects to repositories
   - Generate GitHub token with repo permissions
   - Update environment files with repository names

### Phase 2: Individual Bot Testing

#### Node.js Bot Test
```bash
# Start Node.js bot
docker-compose --profile nodejs up -d

# Check logs
docker logs claude-bot

# Create test issues
./scripts/create-test-issues.py your-username/nodejs-test-repo --type nodejs

# Monitor bot activity
docker logs -f claude-bot
```

#### .NET Bot Test  
```bash
# Start .NET bot
docker-compose --profile dotnet up -d

# Check logs  
docker logs claude-bot-dotnet

# Create test issues
./scripts/create-test-issues.py your-username/dotnet-test-repo --type dotnet

# Monitor bot activity
docker logs -f claude-bot-dotnet
```

### Phase 3: Concurrent Testing

```bash
# Start both bots
docker-compose --profile nodejs --profile dotnet up -d

# Create issues for both projects
./scripts/create-test-issues.py your-username/nodejs-test-repo --type nodejs
./scripts/create-test-issues.py your-username/dotnet-test-repo --type dotnet

# Monitor both bots
docker logs -f claude-bot &
docker logs -f claude-bot-dotnet &
```

### Phase 4: Health Monitoring

```bash
# Comprehensive health check
./scripts/health-check.sh

# Check resource usage
docker stats

# Verify data persistence
docker exec claude-bot ls -la /bot/data
docker exec claude-bot-dotnet ls -la /bot/data
```

## Test Scenarios

### Generated Test Issues

The `create-test-issues.py` script generates standardized test cases:

#### Node.js Test Issues:
1. **Add division function** - Tests API enhancement
2. **Fix multiplication bug** - Tests bug fixing
3. **Add input validation** - Tests security improvements

#### .NET Test Issues:  
1. **Add health check endpoint** - Tests controller creation
2. **Add Entity Framework** - Tests database integration
3. **Update frontend build** - Tests Node.js 10.13 compatibility

### Manual Test Cases

1. **PR Feedback Testing:**
   - Create PR with intentional issues
   - Add review comments requesting changes
   - Verify bot responds to feedback

2. **Error Handling:**
   - Test with invalid GitHub tokens
   - Test with missing dependencies
   - Test with network connectivity issues

3. **Resource Isolation:**
   - Verify separate data volumes
   - Check that bots don't interfere with each other
   - Test concurrent operation

## Monitoring and Debugging

### Log Analysis
```bash
# View recent logs
docker logs --since=30m claude-bot
docker logs --since=30m claude-bot-dotnet

# Follow logs in real-time
docker logs -f claude-bot

# Search for errors
docker logs claude-bot 2>&1 | grep -i error
```

### Health Checks
```bash
# Full health check
./scripts/health-check.sh

# Quick status check
docker ps --filter "name=claude-bot"

# Resource usage
docker stats --no-stream
```

### Data Inspection
```bash
# View bot data
docker exec claude-bot ls -la /bot/data/
docker exec claude-bot-dotnet ls -la /bot/data/

# Check processed issues
docker exec claude-bot cat /bot/data/processed/issues.json
```

## Cleanup

### Selective Cleanup
```bash
# Interactive cleanup
./scripts/cleanup-test-env.sh

# Stop containers only
./scripts/cleanup-test-env.sh containers

# Remove volumes (data loss!)
./scripts/cleanup-test-env.sh volumes
```

### Complete Cleanup
```bash
# Remove everything
./scripts/cleanup-test-env.sh complete

# Close test GitHub issues
./scripts/cleanup-test-env.sh issues your-username/test-repo
```

## Troubleshooting

### Common Issues

1. **Container won't start:**
   ```bash
   # Check Docker daemon
   docker info
   
   # Check environment variables
   docker-compose config
   ```

2. **GitHub authentication fails:**
   ```bash
   # Test GitHub CLI auth
   docker exec claude-bot gh auth status
   
   # Check token permissions
   docker exec claude-bot gh api user
   ```

3. **Claude Code not working:**
   ```bash
   # Check Anthropic API key
   docker exec claude-bot env | grep ANTHROPIC
   
   # Test Claude CLI
   docker exec claude-bot claude --version
   ```

4. **Bot not processing issues:**
   ```bash
   # Check issue labels
   docker exec claude-bot gh issue list --repo your-repo --label claude-bot-test
   
   # Verify repository access
   docker exec claude-bot gh repo view your-repo
   ```

### Performance Issues

1. **High resource usage:**
   ```bash
   # Check container stats
   docker stats
   
   # Review Docker system usage
   docker system df
   ```

2. **Slow response times:**
   ```bash
   # Check network connectivity
   docker exec claude-bot ping github.com
   
   # Review bot intervals
   grep INTERVAL .env*
   ```

## Best Practices

1. **Use test-specific labels** to avoid conflicts with production
2. **Monitor resource usage** during extended testing
3. **Backup test configurations** before making changes
4. **Use separate repositories** for testing
5. **Clean up regularly** to avoid resource accumulation
6. **Test incrementally** - start with simple scenarios
7. **Document issues** found during testing

## Success Criteria

A successful test should demonstrate:

- ✅ Both bots start independently
- ✅ GitHub integration works correctly
- ✅ Issues are processed and PRs created
- ✅ PR feedback loop functions
- ✅ Runtime environments work (.NET 8, Node.js 10.13)
- ✅ Data persistence across restarts
- ✅ No conflicts between concurrent bots
- ✅ Resource usage is reasonable
- ✅ Error handling works properly