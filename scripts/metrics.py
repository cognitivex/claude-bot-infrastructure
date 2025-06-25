#!/usr/bin/env python3
"""
Prometheus Metrics for Claude Bot Infrastructure
Provides monitoring and performance tracking
"""

import time
import functools
from typing import Optional, Dict, Any, Callable
from contextlib import contextmanager
import logging

# Try to import prometheus client, fall back gracefully
try:
    from prometheus_client import (
        Counter, Histogram, Gauge, Summary,
        CollectorRegistry, push_to_gateway,
        generate_latest, CONTENT_TYPE_LATEST
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Dummy implementations for when prometheus_client is not available
    class DummyMetric:
        def labels(self, **kwargs):
            return self
        def inc(self, amount=1):
            pass
        def dec(self, amount=1):
            pass
        def set(self, value):
            pass
        def observe(self, value):
            pass
        def time(self):
            return self
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
    
    Counter = Histogram = Gauge = Summary = lambda *args, **kwargs: DummyMetric()
    CollectorRegistry = lambda: None
    push_to_gateway = lambda *args, **kwargs: None
    generate_latest = lambda registry: b""
    CONTENT_TYPE_LATEST = "text/plain"

logger = logging.getLogger(__name__)


class BotMetrics:
    """Metrics collection for bot operations"""
    
    def __init__(self, bot_id: str = "claude-bot", pushgateway_url: Optional[str] = None):
        self.bot_id = bot_id
        self.pushgateway_url = pushgateway_url
        self.registry = CollectorRegistry() if PROMETHEUS_AVAILABLE else None
        
        # Initialize metrics
        self._init_metrics()
        
    def _init_metrics(self):
        """Initialize all metrics"""
        # Task metrics
        self.tasks_total = Counter(
            'claude_bot_tasks_total',
            'Total number of tasks processed',
            ['bot_id', 'status', 'task_type'],
            registry=self.registry
        )
        
        self.task_duration = Histogram(
            'claude_bot_task_duration_seconds',
            'Task processing duration in seconds',
            ['bot_id', 'task_type'],
            buckets=(5, 10, 30, 60, 120, 300, 600, 1800, 3600),
            registry=self.registry
        )
        
        self.tasks_queued = Gauge(
            'claude_bot_tasks_queued',
            'Number of tasks currently in queue',
            ['bot_id', 'priority'],
            registry=self.registry
        )
        
        # API metrics
        self.api_calls_total = Counter(
            'claude_bot_api_calls_total',
            'Total number of API calls made',
            ['bot_id', 'api', 'status'],
            registry=self.registry
        )
        
        self.api_duration = Histogram(
            'claude_bot_api_duration_seconds',
            'API call duration in seconds',
            ['bot_id', 'api'],
            buckets=(0.1, 0.5, 1, 2, 5, 10, 30),
            registry=self.registry
        )
        
        self.api_rate_limit_remaining = Gauge(
            'claude_bot_api_rate_limit_remaining',
            'Remaining API rate limit',
            ['bot_id', 'api'],
            registry=self.registry
        )
        
        # Error metrics
        self.errors_total = Counter(
            'claude_bot_errors_total',
            'Total number of errors',
            ['bot_id', 'error_type', 'component'],
            registry=self.registry
        )
        
        self.circuit_breaker_state = Gauge(
            'claude_bot_circuit_breaker_state',
            'Circuit breaker state (0=closed, 1=open, 2=half-open)',
            ['bot_id', 'service'],
            registry=self.registry
        )
        
        # System metrics
        self.bot_uptime = Gauge(
            'claude_bot_uptime_seconds',
            'Bot uptime in seconds',
            ['bot_id'],
            registry=self.registry
        )
        
        self.bot_health = Gauge(
            'claude_bot_health',
            'Bot health status (0=unhealthy, 1=healthy)',
            ['bot_id'],
            registry=self.registry
        )
        
        self.memory_usage = Gauge(
            'claude_bot_memory_usage_bytes',
            'Memory usage in bytes',
            ['bot_id'],
            registry=self.registry
        )
        
        # Git metrics
        self.git_operations_total = Counter(
            'claude_bot_git_operations_total',
            'Total number of git operations',
            ['bot_id', 'operation', 'status'],
            registry=self.registry
        )
        
        self.pr_created_total = Counter(
            'claude_bot_pr_created_total',
            'Total number of PRs created',
            ['bot_id', 'repository'],
            registry=self.registry
        )
        
        self.commits_total = Counter(
            'claude_bot_commits_total',
            'Total number of commits made',
            ['bot_id', 'repository'],
            registry=self.registry
        )
    
    @contextmanager
    def measure_duration(self, metric: Histogram, labels: Dict[str, str]):
        """Context manager to measure operation duration"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            metric.labels(**labels).observe(duration)
    
    def track_task(self, task_type: str, status: str):
        """Track task completion"""
        self.tasks_total.labels(
            bot_id=self.bot_id,
            status=status,
            task_type=task_type
        ).inc()
    
    def track_api_call(self, api: str, status: str, duration: float):
        """Track API call metrics"""
        self.api_calls_total.labels(
            bot_id=self.bot_id,
            api=api,
            status=status
        ).inc()
        
        self.api_duration.labels(
            bot_id=self.bot_id,
            api=api
        ).observe(duration)
    
    def track_error(self, error_type: str, component: str):
        """Track error occurrence"""
        self.errors_total.labels(
            bot_id=self.bot_id,
            error_type=error_type,
            component=component
        ).inc()
    
    def update_queue_size(self, priority: str, size: int):
        """Update queue size gauge"""
        self.tasks_queued.labels(
            bot_id=self.bot_id,
            priority=priority
        ).set(size)
    
    def update_health(self, is_healthy: bool):
        """Update bot health status"""
        self.bot_health.labels(bot_id=self.bot_id).set(1 if is_healthy else 0)
    
    def update_uptime(self, uptime_seconds: float):
        """Update bot uptime"""
        self.bot_uptime.labels(bot_id=self.bot_id).set(uptime_seconds)
    
    def update_circuit_breaker(self, service: str, state: str):
        """Update circuit breaker state"""
        state_map = {'CLOSED': 0, 'OPEN': 1, 'HALF_OPEN': 2}
        self.circuit_breaker_state.labels(
            bot_id=self.bot_id,
            service=service
        ).set(state_map.get(state, -1))
    
    def push_metrics(self):
        """Push metrics to Prometheus pushgateway"""
        if not PROMETHEUS_AVAILABLE:
            logger.debug("Prometheus client not available, skipping push")
            return
            
        if not self.pushgateway_url:
            logger.debug("No pushgateway URL configured, skipping push")
            return
        
        try:
            push_to_gateway(
                self.pushgateway_url,
                job=f'claude_bot_{self.bot_id}',
                registry=self.registry
            )
            logger.debug(f"Metrics pushed to {self.pushgateway_url}")
        except Exception as e:
            logger.error(f"Failed to push metrics: {e}")
    
    def get_metrics_text(self) -> bytes:
        """Get metrics in Prometheus text format"""
        if PROMETHEUS_AVAILABLE:
            return generate_latest(self.registry)
        return b"# Prometheus client not available\n"


# Global metrics instance
_metrics: Optional[BotMetrics] = None


def init_metrics(bot_id: str = "claude-bot", pushgateway_url: Optional[str] = None) -> BotMetrics:
    """Initialize global metrics instance"""
    global _metrics
    _metrics = BotMetrics(bot_id, pushgateway_url)
    return _metrics


def get_metrics() -> Optional[BotMetrics]:
    """Get global metrics instance"""
    return _metrics


def track_operation(operation: str, api: Optional[str] = None):
    """Decorator to track operation metrics"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                if _metrics:
                    _metrics.track_error(
                        error_type=type(e).__name__,
                        component=operation
                    )
                raise
            finally:
                duration = time.time() - start_time
                if _metrics:
                    if api:
                        _metrics.track_api_call(api, status, duration)
                    else:
                        _metrics.track_task(operation, status)
        
        return wrapper
    return decorator


class MetricsServer:
    """Simple HTTP server for Prometheus scraping"""
    
    def __init__(self, metrics: BotMetrics, port: int = 8000):
        self.metrics = metrics
        self.port = port
    
    def start(self):
        """Start metrics HTTP server"""
        if not PROMETHEUS_AVAILABLE:
            logger.warning("Prometheus client not available, metrics server disabled")
            return
        
        from http.server import HTTPServer, BaseHTTPRequestHandler
        
        class MetricsHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/metrics':
                    metrics_data = self.server.metrics.get_metrics_text()
                    self.send_response(200)
                    self.send_header('Content-Type', CONTENT_TYPE_LATEST)
                    self.end_headers()
                    self.wfile.write(metrics_data)
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def log_message(self, format, *args):
                # Suppress request logging
                pass
        
        server = HTTPServer(('', self.port), MetricsHandler)
        server.metrics = self.metrics
        
        logger.info(f"Metrics server started on port {self.port}")
        server.serve_forever()


if __name__ == "__main__":
    # Example usage
    import random
    
    # Initialize metrics
    metrics = init_metrics("test-bot", "http://localhost:9091")
    
    # Track some sample metrics
    print("📊 Generating sample metrics...")
    
    # Simulate task processing
    for i in range(10):
        task_type = random.choice(['issue', 'pr_feedback', 'scheduled'])
        status = random.choice(['success', 'success', 'success', 'error'])
        
        with metrics.measure_duration(metrics.task_duration, {'bot_id': 'test-bot', 'task_type': task_type}):
            time.sleep(random.uniform(0.1, 0.5))
        
        metrics.track_task(task_type, status)
    
    # Simulate API calls
    for api in ['github', 'anthropic', 'web_dashboard']:
        for i in range(5):
            status = random.choice(['success', 'success', 'error'])
            duration = random.uniform(0.1, 2.0)
            metrics.track_api_call(api, status, duration)
    
    # Update gauges
    metrics.update_queue_size('high', 2)
    metrics.update_queue_size('medium', 5)
    metrics.update_queue_size('low', 3)
    metrics.update_health(True)
    metrics.update_uptime(3600.0)
    
    # Get metrics output
    print("\n📈 Current metrics:")
    print(metrics.get_metrics_text().decode('utf-8'))
    
    # Push to gateway if configured
    metrics.push_metrics()
    print("\n✅ Metrics example complete")