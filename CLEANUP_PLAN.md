# Claude Bot Infrastructure Cleanup Plan

This document outlines the comprehensive cleanup and hardening plan for the Claude Bot Infrastructure project.

## Overview

The Claude Bot Infrastructure has accumulated redundant code and potential failure points that need to be addressed to improve maintainability and reliability. This plan is divided into 4 phases, each focusing on specific improvements.

## Phase 1: Remove Redundant Code

**Goal**: Eliminate duplicate functionality and unused code to simplify maintenance.

### Tasks:
1. **Remove GitHub Pages Dashboard** (`dashboard/` folder)
   - The self-hosted Flask dashboard in `status-web/` provides the same functionality
   - GitHub Pages implementation is redundant and unused

2. **Remove Duplicate Docker Compose File** (`docker-compose.dotnet.yml`)
   - Functionality is already included in main `docker-compose.yml` with profiles
   - Having two files creates confusion and maintenance overhead

3. **Clean Up Status Reporter**
   - Remove GitHub publishing code from `scripts/status_reporter.py`
   - Keep only the web dashboard publishing functionality

4. **Clean Up Start Script**
   - Remove debug echo statements from `scripts/start-bot.sh`
   - Keep only essential functionality

### Verification:
- Run `docker-compose --profile nodejs up` to test Node.js bot
- Run `docker-compose --profile dotnet up` to test .NET bot
- Verify status reporting works via web dashboard at http://localhost:8080

## Phase 2: Fix Critical Failure Points

**Goal**: Address container restart loops and permission issues.

### Tasks:
1. **Fix Container Restart Loop**
   - Issue: `start-bot.sh` tries to clone into `/workspace` with permission issues
   - Solution: Mount project as volume instead of cloning
   - Update docker-compose.yml to mount `${PROJECT_PATH}:/workspace`

2. **Add Health Checks**
   - Implement proper health check endpoints for all services
   - Configure Docker health checks with appropriate intervals

3. **Fix Volume Permissions**
   - Ensure all volumes have correct ownership
   - Add init scripts to set permissions on startup

### Verification:
- Containers should start without restart loops
- Health checks should pass for all services
- No permission errors in logs

## Phase 3: Enhance Error Handling

**Goal**: Add comprehensive error handling and recovery mechanisms.

### Tasks:
1. **Add Retry Logic**
   - Implement exponential backoff for API calls
   - Add retry mechanisms for transient failures

2. **Improve Logging**
   - Standardize log formats across all scripts
   - Add log rotation to prevent disk space issues
   - Include correlation IDs for tracking

3. **Add Circuit Breakers**
   - Prevent cascade failures
   - Implement graceful degradation

4. **Handle Edge Cases**
   - Empty queue scenarios
   - Invalid task formats
   - Network timeouts

### Verification:
- Test with various failure scenarios
- Verify proper error messages and recovery
- Check log output is consistent and helpful

## Phase 4: Production Readiness

**Goal**: Prepare the system for production deployment.

### Tasks:
1. **Externalize Configuration**
   - Move all hardcoded values to environment variables
   - Create comprehensive `.env.example`
   - Add configuration validation on startup

2. **Add Monitoring**
   - Implement Prometheus metrics
   - Add performance tracking
   - Create alerting rules

3. **Security Hardening**
   - Run containers as non-root users
   - Implement secrets management
   - Add rate limiting

4. **Documentation**
   - Create operational runbooks
   - Document troubleshooting procedures
   - Add architecture diagrams

### Verification:
- Full system test in production-like environment
- Security scan passes
- Documentation review complete

## Implementation Order

1. **Phase 1** - Immediate cleanup (Low risk, high impact)
2. **Phase 2** - Critical fixes (Medium risk, critical impact)
3. **Phase 3** - Error handling (Medium risk, high impact)
4. **Phase 4** - Production prep (Low risk, long-term impact)

## Success Criteria

- All containers start reliably without restart loops
- No redundant code or unused files
- Comprehensive error handling and logging
- Production-ready configuration and monitoring
- Clear documentation for operations

## Notes

- Each phase should be completed and tested before moving to the next
- Create backups before making significant changes
- Monitor system behavior after each change
- Document any deviations from this plan