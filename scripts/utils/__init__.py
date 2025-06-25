"""
Utility modules for Claude Bot Infrastructure
Provides common functionality for error handling, retries, and logging
"""

from .retry_handler import (
    retry_with_backoff,
    safe_request,
    api_retry,
    github_api_retry,
    file_operation_retry,
    github_circuit_breaker,
    web_dashboard_circuit_breaker,
    RetryError,
    CircuitBreakerError
)
from .logger import get_logger, setup_logging, correlation_context, log_function_call

__all__ = [
    'retry_with_backoff',
    'safe_request', 
    'api_retry',
    'github_api_retry',
    'file_operation_retry',
    'github_circuit_breaker',
    'web_dashboard_circuit_breaker',
    'RetryError',
    'CircuitBreakerError',
    'get_logger',
    'setup_logging',
    'correlation_context',
    'log_function_call'
]