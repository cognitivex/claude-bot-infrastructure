#!/usr/bin/env python3
"""
Security Module for Claude Bot Infrastructure
Implements rate limiting, access control, and security best practices
"""

import time
import hashlib
import hmac
import secrets
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
import logging
import re
import os

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter implementation"""
    
    def __init__(self, rate: int, per: int = 3600):
        """
        Initialize rate limiter
        
        Args:
            rate: Number of allowed requests
            per: Time period in seconds (default: 3600 = 1 hour)
        """
        self.rate = rate
        self.per = per
        self.allowance = rate
        self.last_check = time.time()
    
    def is_allowed(self, tokens: int = 1) -> Tuple[bool, float]:
        """
        Check if request is allowed under rate limit
        
        Returns:
            Tuple of (is_allowed, seconds_until_reset)
        """
        current = time.time()
        time_passed = current - self.last_check
        self.last_check = current
        
        # Replenish tokens based on time passed
        self.allowance += time_passed * (self.rate / self.per)
        if self.allowance > self.rate:
            self.allowance = self.rate
        
        if self.allowance < tokens:
            # Calculate when tokens will be available
            tokens_needed = tokens - self.allowance
            seconds_until_available = tokens_needed * (self.per / self.rate)
            return False, seconds_until_available
        
        self.allowance -= tokens
        return True, 0


class SecurityManager:
    """Manages security policies and access control"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.rate_limiters: Dict[str, RateLimiter] = {}
        self.allowed_repositories: Set[str] = set()
        self.blocked_patterns: List[re.Pattern] = []
        self.webhook_secrets: Dict[str, str] = {}
        
        self._init_from_config()
    
    def _init_from_config(self):
        """Initialize security settings from configuration"""
        # Rate limiting
        rate_limit = self.config.get('rate_limit_per_hour', 100)
        self.default_rate_limiter = RateLimiter(rate_limit, 3600)
        
        # Allowed repositories
        allowed_repos = self.config.get('allowed_repositories', [])
        if allowed_repos:
            self.allowed_repositories = set(allowed_repos)
        
        # Blocked patterns (for preventing malicious inputs)
        self.blocked_patterns = [
            re.compile(r'\.\./', re.IGNORECASE),  # Path traversal
            re.compile(r'[;&|]', re.IGNORECASE),  # Command injection
            re.compile(r'<script', re.IGNORECASE),  # XSS
            re.compile(r'javascript:', re.IGNORECASE),  # XSS
            re.compile(r'--\s*(drop|delete|truncate)', re.IGNORECASE),  # SQL injection
        ]
        
        # Additional custom patterns
        custom_patterns = self.config.get('blocked_patterns', [])
        for pattern in custom_patterns:
            try:
                self.blocked_patterns.append(re.compile(pattern, re.IGNORECASE))
            except re.error as e:
                logger.error(f"Invalid regex pattern '{pattern}': {e}")
    
    def check_rate_limit(self, identifier: str, tokens: int = 1) -> Tuple[bool, float]:
        """
        Check if request is allowed under rate limit
        
        Args:
            identifier: Unique identifier (e.g., user, IP, API key)
            tokens: Number of tokens to consume
            
        Returns:
            Tuple of (is_allowed, seconds_until_reset)
        """
        if identifier not in self.rate_limiters:
            rate_limit = self.config.get(f'rate_limit_{identifier}', 
                                        self.config.get('rate_limit_per_hour', 100))
            self.rate_limiters[identifier] = RateLimiter(rate_limit, 3600)
        
        return self.rate_limiters[identifier].is_allowed(tokens)
    
    def is_repository_allowed(self, repository: str) -> bool:
        """Check if repository is in allowed list"""
        if not self.allowed_repositories:
            # If no allowed list is configured, allow all
            return True
        
        return repository in self.allowed_repositories
    
    def validate_input(self, input_string: str, input_type: str = "general") -> Tuple[bool, Optional[str]]:
        """
        Validate input for security issues
        
        Args:
            input_string: String to validate
            input_type: Type of input (general, path, command, etc.)
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not input_string:
            return True, None
        
        # Check against blocked patterns
        for pattern in self.blocked_patterns:
            if pattern.search(input_string):
                return False, f"Input contains blocked pattern: {pattern.pattern}"
        
        # Type-specific validation
        if input_type == "path":
            # Ensure path doesn't escape allowed directories
            if ".." in input_string or input_string.startswith("/"):
                return False, "Path traversal attempt detected"
        
        elif input_type == "command":
            # Block dangerous shell characters
            dangerous_chars = [';', '|', '&', '$', '`', '\n', '\r']
            for char in dangerous_chars:
                if char in input_string:
                    return False, f"Dangerous character '{char}' in command"
        
        elif input_type == "repository":
            # Validate repository format
            if not re.match(r'^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$', input_string):
                return False, "Invalid repository format"
        
        return True, None
    
    def sanitize_path(self, path: str, base_dir: str = "/") -> Optional[str]:
        """
        Sanitize file path to prevent directory traversal
        
        Args:
            path: Path to sanitize
            base_dir: Base directory to restrict paths to
            
        Returns:
            Sanitized path or None if invalid
        """
        # Remove any .. components
        path = os.path.normpath(path)
        
        # Ensure path is within base directory
        full_path = os.path.abspath(os.path.join(base_dir, path))
        base_dir = os.path.abspath(base_dir)
        
        if not full_path.startswith(base_dir):
            logger.warning(f"Path traversal attempt: {path}")
            return None
        
        return full_path
    
    def generate_webhook_secret(self, webhook_id: str) -> str:
        """Generate a secure webhook secret"""
        secret = secrets.token_urlsafe(32)
        self.webhook_secrets[webhook_id] = secret
        return secret
    
    def verify_webhook_signature(self, webhook_id: str, payload: bytes, signature: str) -> bool:
        """
        Verify webhook signature using HMAC
        
        Args:
            webhook_id: Webhook identifier
            payload: Request payload bytes
            signature: Provided signature
            
        Returns:
            True if signature is valid
        """
        secret = self.webhook_secrets.get(webhook_id)
        if not secret:
            logger.error(f"No secret found for webhook {webhook_id}")
            return False
        
        expected_signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    def redact_sensitive_data(self, text: str) -> str:
        """Redact sensitive information from text"""
        # Redact API keys
        text = re.sub(r'(api[_-]?key\s*[:=]\s*)[\w-]+', r'\1[REDACTED]', text, flags=re.IGNORECASE)
        text = re.sub(r'(token\s*[:=]\s*)[\w-]+', r'\1[REDACTED]', text, flags=re.IGNORECASE)
        
        # Redact passwords
        text = re.sub(r'(password\s*[:=]\s*)[\S]+', r'\1[REDACTED]', text, flags=re.IGNORECASE)
        
        # Redact email addresses
        text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[EMAIL]', text)
        
        # Redact credit card numbers
        text = re.sub(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', '[CC_NUMBER]', text)
        
        return text


class AccessControl:
    """Role-based access control implementation"""
    
    def __init__(self):
        self.permissions: Dict[str, Set[str]] = {
            'admin': {'*'},  # All permissions
            'developer': {
                'issues.read', 'issues.write',
                'pulls.read', 'pulls.write',
                'code.read', 'code.write',
                'status.read'
            },
            'readonly': {
                'issues.read',
                'pulls.read',
                'code.read',
                'status.read'
            }
        }
        
        self.user_roles: Dict[str, str] = {}
    
    def set_user_role(self, user: str, role: str):
        """Assign role to user"""
        if role not in self.permissions:
            raise ValueError(f"Unknown role: {role}")
        self.user_roles[user] = role
    
    def has_permission(self, user: str, permission: str) -> bool:
        """Check if user has specific permission"""
        role = self.user_roles.get(user)
        if not role:
            return False
        
        role_permissions = self.permissions.get(role, set())
        
        # Check for wildcard permission
        if '*' in role_permissions:
            return True
        
        # Check specific permission
        return permission in role_permissions
    
    def require_permission(self, permission: str):
        """Decorator to require permission for function execution"""
        def decorator(func):
            def wrapper(self, *args, **kwargs):
                user = kwargs.get('user') or getattr(self, 'current_user', None)
                if not user:
                    raise PermissionError("No user context available")
                
                if not self.has_permission(user, permission):
                    raise PermissionError(f"User {user} lacks permission: {permission}")
                
                return func(self, *args, **kwargs)
            return wrapper
        return decorator


class AuditLogger:
    """Security audit logging"""
    
    def __init__(self, log_file: Optional[str] = None):
        self.log_file = log_file or "/bot/logs/security_audit.log"
        self.events: deque = deque(maxlen=1000)  # Keep last 1000 events in memory
    
    def log_event(self, event_type: str, user: str, details: Dict[str, Any]):
        """Log security event"""
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': event_type,
            'user': user,
            'details': details
        }
        
        self.events.append(event)
        
        # Also log to file
        try:
            with open(self.log_file, 'a') as f:
                f.write(f"{event['timestamp']} [{event['type']}] User: {event['user']} - {event['details']}\n")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
    
    def get_recent_events(self, event_type: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get recent security events"""
        events = list(self.events)
        
        if event_type:
            events = [e for e in events if e['type'] == event_type]
        
        return events[-limit:]


if __name__ == "__main__":
    # Example usage
    config = {
        'rate_limit_per_hour': 10,
        'allowed_repositories': ['owner/repo1', 'owner/repo2']
    }
    
    security = SecurityManager(config)
    
    # Test rate limiting
    print("🔒 Testing rate limiting...")
    for i in range(12):
        allowed, wait_time = security.check_rate_limit("test_user")
        if allowed:
            print(f"  Request {i+1}: ✅ Allowed")
        else:
            print(f"  Request {i+1}: ❌ Blocked (wait {wait_time:.1f}s)")
        time.sleep(0.1)
    
    # Test input validation
    print("\n🔍 Testing input validation...")
    test_inputs = [
        ("normal input", "general"),
        ("../../etc/passwd", "path"),
        ("rm -rf /; echo hacked", "command"),
        ("owner/valid-repo", "repository"),
        ("<script>alert('xss')</script>", "general")
    ]
    
    for input_str, input_type in test_inputs:
        valid, error = security.validate_input(input_str, input_type)
        status = "✅ Valid" if valid else f"❌ Invalid: {error}"
        print(f"  '{input_str}' ({input_type}): {status}")
    
    # Test access control
    print("\n🔐 Testing access control...")
    access = AccessControl()
    access.set_user_role("alice", "developer")
    access.set_user_role("bob", "readonly")
    
    permissions = ["issues.read", "issues.write", "admin.delete"]
    for user in ["alice", "bob"]:
        print(f"\n  User: {user}")
        for perm in permissions:
            has_perm = access.has_permission(user, perm)
            print(f"    {perm}: {'✅' if has_perm else '❌'}")
    
    print("\n✅ Security module test complete")