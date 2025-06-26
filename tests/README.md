# Claude Bot Infrastructure Tests

This directory contains comprehensive tests for the Claude Bot Infrastructure project.

## Directory Structure

```
tests/
├── integration/          # Integration tests that test full bot workflows
├── unit/                # Unit tests for individual components
├── fixtures/            # Test data and sample files
├── utils/               # Test utilities and helpers
├── github_actions/      # CI/CD specific test helpers
└── README.md           # This file
```

## Test Types

### Unit Tests (`unit/`)
Fast, isolated tests for individual components:
- `test_bot_orchestrator.py` - Bot orchestration logic
- `test_github_task_executor.py` - GitHub integration logic
- `test_status_reporter.py` - Status reporting functionality
- `test_pr_feedback_handler.py` - PR feedback processing

### Integration Tests (`integration/`)
End-to-end tests that verify complete workflows:
- `test_bot_github_workflow.py` - Full GitHub issue → PR workflow
- `test_bot_docker_environment.py` - Docker environment testing
- `test_bot_api_endpoints.py` - API endpoint testing
- `test_bot_basic_functionality.py` - Basic bot operations

### Test Utilities (`utils/`)
Shared utilities for testing:
- `test_helpers.py` - Common test utilities
- `bot_client.py` - Bot API client for testing
- `github_test_utils.py` - GitHub API testing utilities
- `docker_test_utils.py` - Docker testing helpers

## Running Tests

### Local Testing

```bash
# Run all tests
python -m pytest tests/

# Run only unit tests
python -m pytest tests/unit/

# Run only integration tests
python -m pytest tests/integration/

# Run with coverage
python -m pytest tests/ --cov=scripts --cov-report=html

# Run specific test
python -m pytest tests/unit/test_bot_orchestrator.py -v
```

### GitHub Actions

Tests automatically run on:
- Push to main/develop branches
- Pull requests
- Manual dispatch
- Weekly schedule (Mondays 6 AM UTC)

### Test Environment

Integration tests use a separate test environment:
- Test configuration: `.env.test`
- Test data directory: `tests/data/`
- Test workspace: `tests/workspace/`
- Isolated Docker containers

## Test Configuration

### Environment Variables

Required for integration tests:
- `ANTHROPIC_API_KEY` - Claude Code API access
- `GITHUB_TOKEN` - GitHub API access
- `TARGET_REPO` - Test repository (default: current repo)

### GitHub Repository Secrets

For CI/CD, configure these secrets in your GitHub repository:
- `ANTHROPIC_API_KEY`
- `GITHUB_TOKEN` (or use built-in `GITHUB_TOKEN`)

## Writing Tests

### Unit Test Example

```python
import pytest
from scripts.bot_orchestrator import BotOrchestrator

def test_bot_initialization():
    bot = BotOrchestrator("/workspace", "/data", "test/repo")
    assert bot.workspace_dir == "/workspace"
    assert bot.data_dir.name == "data"
    assert bot.repo == "test/repo"
```

### Integration Test Example

```python
import pytest
from tests.utils.bot_client import BotClient
from tests.utils.github_test_utils import create_test_issue

@pytest.mark.integration
async def test_github_issue_processing():
    # Create test issue
    issue_url = create_test_issue("Test task", "Create a hello.py file")
    
    # Wait for bot to process
    bot_client = BotClient()
    result = await bot_client.wait_for_completion(issue_url, timeout=300)
    
    # Verify result
    assert result.status == "completed"
    assert result.pr_url is not None
```

## Best Practices

1. **Isolation**: Each test should be independent and not affect others
2. **Cleanup**: Always clean up test artifacts (issues, PRs, files)
3. **Timeouts**: Use appropriate timeouts for integration tests
4. **Mocking**: Mock external services in unit tests
5. **Fixtures**: Use pytest fixtures for common test setup
6. **Naming**: Use descriptive test names that explain the behavior being tested

## Troubleshooting

### Common Issues

1. **Docker containers not starting**: Check Docker daemon and available ports
2. **GitHub API rate limits**: Use test tokens with appropriate permissions
3. **Bot not processing tasks**: Check bot logs and configuration
4. **Tests timing out**: Increase timeout values for slow operations

### Debug Commands

```bash
# Check bot status
curl http://localhost:8080/api/status

# View bot logs
docker-compose logs claude-bot

# Check container status
docker-compose ps

# Run tests with verbose output
python -m pytest tests/ -v -s
```