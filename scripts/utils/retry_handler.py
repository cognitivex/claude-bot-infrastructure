#!/usr/bin/env python3
"""
Retry Handler with Exponential Backoff for Claude Bot Infrastructure
Provides robust retry mechanisms for API calls and network operations
"""

import time
import random
import logging
from functools import wraps
from typing import Callable, Any, Optional, Tuple, Type
import requests


class RetryError(Exception):
    """Raised when all retry attempts are exhausted"""
    pass


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open"""
    pass


class CircuitBreaker:
    """Simple circuit breaker implementation"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if self.state == 'OPEN':
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = 'HALF_OPEN'
                else:
                    raise CircuitBreakerError("Circuit breaker is OPEN")
            
            try:
                result = func(*args, **kwargs)
                self.on_success()
                return result
            except Exception as e:
                self.on_failure()
                raise e
        
        return wrapper
    
    def on_success(self):
        """Called when function succeeds"""
        self.failure_count = 0
        self.state = 'CLOSED'
    
    def on_failure(self):
        """Called when function fails"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Decorator for retrying function calls with exponential backoff
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_factor: Factor by which delay increases each retry
        jitter: Add random jitter to prevent thundering herd
        exceptions: Tuple of exceptions that trigger retries
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts - 1:
                        # Last attempt failed, raise the exception
                        break
                    
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                    
                    # Add jitter to prevent thundering herd
                    if jitter:
                        delay = delay * (0.5 + random.random() * 0.5)
                    
                    logging.warning(
                        f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: "
                        f"{str(e)}. Retrying in {delay:.2f}s..."
                    )
                    
                    time.sleep(delay)
            
            # All attempts failed
            raise RetryError(
                f"All {max_attempts} attempts failed for {func.__name__}. "
                f"Last error: {str(last_exception)}"
            ) from last_exception
        
        return wrapper
    return decorator


def safe_request(
    method: str,
    url: str,
    timeout: int = 10,
    **kwargs
) -> requests.Response:
    """
    Make a safe HTTP request with proper error handling
    
    Args:
        method: HTTP method (GET, POST, etc.)
        url: URL to request
        timeout: Request timeout in seconds
        **kwargs: Additional arguments passed to requests
    
    Returns:
        Response object
        
    Raises:
        requests.RequestException: For various HTTP errors
    """
    try:
        response = requests.request(
            method=method,
            url=url,
            timeout=timeout,
            **kwargs
        )
        response.raise_for_status()
        return response
        
    except requests.exceptions.Timeout as e:
        logging.error(f"Request timeout for {url}: {str(e)}")
        raise
        
    except requests.exceptions.ConnectionError as e:
        logging.error(f"Connection error for {url}: {str(e)}")
        raise
        
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP error for {url}: {e.response.status_code} - {str(e)}")
        raise
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error for {url}: {str(e)}")
        raise


# Predefined retry decorators for common scenarios
api_retry = retry_with_backoff(
    max_attempts=3,
    base_delay=1.0,
    exceptions=(requests.RequestException, ConnectionError)
)

github_api_retry = retry_with_backoff(
    max_attempts=5,
    base_delay=2.0,
    max_delay=30.0,
    exceptions=(requests.RequestException,)
)

file_operation_retry = retry_with_backoff(
    max_attempts=3,
    base_delay=0.5,
    exceptions=(IOError, OSError, FileNotFoundError)
)


# Circuit breakers for different services
github_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
web_dashboard_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)


if __name__ == "__main__":
    # Example usage
    import sys
    
    @api_retry
    def test_api_call():
        response = safe_request("GET", "https://httpbin.org/status/500")
        return response.json()
    
    @github_circuit_breaker
    @github_api_retry
    def test_github_api():
        response = safe_request("GET", "https://api.github.com/user")
        return response.json()
    
    # Test the retry mechanism
    try:
        result = test_api_call()
        print(f"Success: {result}")
    except RetryError as e:
        print(f"All retries failed: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")