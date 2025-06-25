#!/usr/bin/env python3
"""
Standardized Logging for Claude Bot Infrastructure
Provides consistent logging with correlation IDs and structured formats
"""

import logging
import logging.handlers
import os
import uuid
import json
from datetime import datetime
from pathlib import Path
import threading
from contextlib import contextmanager
from functools import wraps
from typing import Optional, Dict, Any


# Thread-local storage for correlation IDs
_local = threading.local()


def get_correlation_id() -> str:
    """Get the current correlation ID for this thread"""
    if not hasattr(_local, 'correlation_id'):
        _local.correlation_id = str(uuid.uuid4())[:8]
    return _local.correlation_id


def set_correlation_id(correlation_id: str):
    """Set the correlation ID for this thread"""
    _local.correlation_id = correlation_id


@contextmanager
def correlation_context(correlation_id: Optional[str] = None):
    """Context manager for setting correlation ID for a block of code"""
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())[:8]
    
    old_id = getattr(_local, 'correlation_id', None)
    _local.correlation_id = correlation_id
    try:
        yield correlation_id
    finally:
        if old_id is not None:
            _local.correlation_id = old_id
        else:
            delattr(_local, 'correlation_id')


class StructuredFormatter(logging.Formatter):
    """Formatter that outputs structured JSON logs"""
    
    def __init__(self, service_name: str = "claude-bot"):
        super().__init__()
        self.service_name = service_name
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "service": self.service_name,
            "correlation_id": get_correlation_id(),
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        return json.dumps(log_entry, ensure_ascii=False)


class HumanReadableFormatter(logging.Formatter):
    """Formatter for human-readable console output"""
    
    def __init__(self):
        super().__init__()
        self.format_string = (
            "%(asctime)s [%(levelname)s] "
            "[%(correlation_id)s] "
            "%(name)s.%(funcName)s:%(lineno)d - "
            "%(message)s"
        )
    
    def format(self, record: logging.LogRecord) -> str:
        # Add correlation ID to record
        record.correlation_id = get_correlation_id()
        
        # Use color coding for different log levels
        colors = {
            'DEBUG': '\033[36m',    # Cyan
            'INFO': '\033[32m',     # Green  
            'WARNING': '\033[33m',  # Yellow
            'ERROR': '\033[31m',    # Red
            'CRITICAL': '\033[35m'  # Magenta
        }
        reset = '\033[0m'
        
        formatted = super().format(record)
        
        # Add color if supported
        if hasattr(os, 'isatty') and os.isatty(2):  # stderr
            color = colors.get(record.levelname, '')
            formatted = f"{color}{formatted}{reset}"
        
        return formatted


def setup_logging(
    service_name: str = "claude-bot",
    log_level: str = "INFO",
    log_dir: Optional[str] = None,
    console_output: bool = True,
    structured_logs: bool = False
) -> logging.Logger:
    """
    Set up standardized logging for the service
    
    Args:
        service_name: Name of the service for log identification
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files (None to disable file logging)
        console_output: Whether to output logs to console
        structured_logs: Whether to use structured JSON logging
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler()
        if structured_logs:
            console_handler.setFormatter(StructuredFormatter(service_name))
        else:
            console_handler.setFormatter(HumanReadableFormatter())
        logger.addHandler(console_handler)
    
    # File handlers
    if log_dir:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # Main log file with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            log_path / f"{service_name}.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(StructuredFormatter(service_name))
        logger.addHandler(file_handler)
        
        # Error log file
        error_handler = logging.handlers.RotatingFileHandler(
            log_path / f"{service_name}-error.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(StructuredFormatter(service_name))
        logger.addHandler(error_handler)
    
    return logger


def get_logger(name: str = None) -> logging.Logger:
    """Get a logger instance with standardized configuration"""
    if name is None:
        name = "claude-bot"
    
    logger = logging.getLogger(name)
    
    # If logger is not configured, set up basic configuration
    if not logger.handlers:
        setup_logging(service_name=name)
    
    return logger


class LoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that automatically includes correlation ID and extra fields"""
    
    def __init__(self, logger: logging.Logger, extra: Optional[Dict[str, Any]] = None):
        super().__init__(logger, extra or {})
    
    def process(self, msg, kwargs):
        # Add correlation ID and extra fields
        extra_fields = {
            'correlation_id': get_correlation_id(),
            **self.extra
        }
        
        # Add extra fields to the log record
        kwargs.setdefault('extra', {})['extra_fields'] = extra_fields
        
        return msg, kwargs


def log_function_call(logger: Optional[logging.Logger] = None):
    """Decorator to log function calls with timing"""
    def decorator(func):
        nonlocal logger
        if logger is None:
            logger = get_logger()
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = datetime.utcnow()
            
            with correlation_context():
                logger.info(f"Starting {func.__name__}", extra={
                    'function': func.__name__,
                    'args_count': len(args),
                    'kwargs_keys': list(kwargs.keys())
                })
                
                try:
                    result = func(*args, **kwargs)
                    duration = (datetime.utcnow() - start_time).total_seconds()
                    
                    logger.info(f"Completed {func.__name__}", extra={
                        'function': func.__name__,
                        'duration_seconds': duration,
                        'success': True
                    })
                    
                    return result
                    
                except Exception as e:
                    duration = (datetime.utcnow() - start_time).total_seconds()
                    
                    logger.error(f"Failed {func.__name__}: {str(e)}", extra={
                        'function': func.__name__,
                        'duration_seconds': duration,
                        'success': False,
                        'error_type': type(e).__name__
                    }, exc_info=True)
                    
                    raise
        
        return wrapper
    return decorator


if __name__ == "__main__":
    # Example usage
    logger = setup_logging(
        service_name="test-service",
        log_level="DEBUG",
        console_output=True,
        structured_logs=False
    )
    
    with correlation_context("test-123"):
        logger.info("This is a test message")
        logger.warning("This is a warning")
        
        try:
            raise ValueError("Test error")
        except Exception:
            logger.error("An error occurred", exc_info=True)