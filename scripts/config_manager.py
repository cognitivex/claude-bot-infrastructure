#!/usr/bin/env python3
"""
Configuration Manager for Claude Bot Infrastructure
Provides centralized configuration with validation and defaults
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class BotConfig:
    """Bot configuration with defaults and validation"""
    # Core settings
    bot_id: str = field(default_factory=lambda: os.getenv("BOT_ID", "claude-bot"))
    bot_label: str = field(default_factory=lambda: os.getenv("BOT_LABEL", "claude-bot"))
    target_repo: str = field(default_factory=lambda: os.getenv("TARGET_REPO", ""))
    
    # API Keys
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    github_token: str = field(default_factory=lambda: os.getenv("GITHUB_TOKEN", ""))
    
    # Git Configuration
    git_author_name: str = field(default_factory=lambda: os.getenv("GIT_AUTHOR_NAME", "Claude Bot"))
    git_author_email: str = field(default_factory=lambda: os.getenv("GIT_AUTHOR_EMAIL", "claude-bot@example.com"))
    git_committer_name: str = field(default_factory=lambda: os.getenv("GIT_COMMITTER_NAME", "Claude Bot"))
    git_committer_email: str = field(default_factory=lambda: os.getenv("GIT_COMMITTER_EMAIL", "claude-bot@example.com"))
    
    # Intervals
    issue_check_interval: int = field(default_factory=lambda: int(os.getenv("ISSUE_CHECK_INTERVAL", "15")))
    pr_check_interval: int = field(default_factory=lambda: int(os.getenv("PR_CHECK_INTERVAL", "30")))
    status_report_interval: int = field(default_factory=lambda: int(os.getenv("STATUS_REPORT_INTERVAL", "300")))
    
    # Paths
    data_dir: str = field(default_factory=lambda: os.getenv("BOT_DATA_DIR", "/bot/data"))
    log_dir: str = field(default_factory=lambda: os.getenv("BOT_LOG_DIR", "/bot/logs"))
    project_path: str = field(default_factory=lambda: os.getenv("PROJECT_PATH", "/workspace"))
    config_file: str = field(default_factory=lambda: os.getenv("BOT_CONFIG_FILE", "/bot/config/bot-config.yml"))
    
    # Service URLs
    status_web_url: str = field(default_factory=lambda: os.getenv("STATUS_WEB_URL", "http://claude-status-web:5000"))
    prometheus_pushgateway_url: Optional[str] = field(default_factory=lambda: os.getenv("PROMETHEUS_PUSHGATEWAY_URL"))
    
    # Feature flags
    enable_metrics: bool = field(default_factory=lambda: os.getenv("ENABLE_METRICS", "true").lower() == "true")
    enable_structured_logging: bool = field(default_factory=lambda: os.getenv("ENABLE_STRUCTURED_LOGGING", "false").lower() == "true")
    enable_debug_mode: bool = field(default_factory=lambda: os.getenv("DEBUG_MODE", "false").lower() == "true")
    enable_pr_feedback: bool = field(default_factory=lambda: os.getenv("ENABLE_PR_FEEDBACK", "true").lower() == "true")
    
    # Performance settings
    max_concurrent_tasks: int = field(default_factory=lambda: int(os.getenv("MAX_CONCURRENT_TASKS", "3")))
    task_timeout: int = field(default_factory=lambda: int(os.getenv("TASK_TIMEOUT", "3600")))
    api_retry_attempts: int = field(default_factory=lambda: int(os.getenv("API_RETRY_ATTEMPTS", "3")))
    api_retry_delay: float = field(default_factory=lambda: float(os.getenv("API_RETRY_DELAY", "1.0")))
    
    # Security settings
    run_as_user: str = field(default_factory=lambda: os.getenv("RUN_AS_USER", "bot"))
    allowed_repositories: List[str] = field(default_factory=lambda: os.getenv("ALLOWED_REPOSITORIES", "").split(",") if os.getenv("ALLOWED_REPOSITORIES") else [])
    rate_limit_per_hour: int = field(default_factory=lambda: int(os.getenv("RATE_LIMIT_PER_HOUR", "100")))
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        # Required fields
        if not self.anthropic_api_key:
            errors.append("ANTHROPIC_API_KEY is required")
        
        if not self.github_token:
            errors.append("GITHUB_TOKEN is required")
            
        if not self.target_repo:
            errors.append("TARGET_REPO is required")
        
        # Validate intervals
        if self.issue_check_interval < 1:
            errors.append("ISSUE_CHECK_INTERVAL must be at least 1 minute")
            
        if self.pr_check_interval < 1:
            errors.append("PR_CHECK_INTERVAL must be at least 1 minute")
            
        if self.status_report_interval < 60:
            errors.append("STATUS_REPORT_INTERVAL must be at least 60 seconds")
        
        # Validate paths
        for path_name, path_value in [("data_dir", self.data_dir), ("log_dir", self.log_dir)]:
            path = Path(path_value)
            try:
                path.mkdir(parents=True, exist_ok=True)
                if not os.access(path, os.W_OK):
                    errors.append(f"{path_name} ({path_value}) is not writable")
            except Exception as e:
                errors.append(f"Cannot create {path_name} ({path_value}): {e}")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return asdict(self)
    
    def mask_sensitive(self) -> Dict[str, Any]:
        """Return config dict with sensitive values masked"""
        config = self.to_dict()
        sensitive_fields = ['anthropic_api_key', 'github_token']
        
        for field in sensitive_fields:
            if field in config and config[field]:
                config[field] = config[field][:4] + "****" + config[field][-4:] if len(config[field]) > 8 else "****"
        
        return config


class ConfigManager:
    """Manages configuration loading and validation"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or os.getenv("BOT_CONFIG_FILE")
        self._config: Optional[BotConfig] = None
        
    def load_config(self) -> BotConfig:
        """Load configuration from environment and optional config file"""
        # Start with environment variables
        config = BotConfig()
        
        # Override with config file if available
        if self.config_file and Path(self.config_file).exists():
            try:
                with open(self.config_file, 'r') as f:
                    if self.config_file.endswith('.json'):
                        file_config = json.load(f)
                    elif self.config_file.endswith(('.yml', '.yaml')):
                        file_config = yaml.safe_load(f)
                    else:
                        logger.warning(f"Unknown config file format: {self.config_file}")
                        file_config = {}
                
                # Update config with file values (env vars take precedence)
                for key, value in file_config.items():
                    if hasattr(config, key) and not os.getenv(key.upper()):
                        setattr(config, key, value)
                        
            except Exception as e:
                logger.error(f"Error loading config file {self.config_file}: {e}")
        
        # Validate configuration
        errors = config.validate()
        if errors:
            for error in errors:
                logger.error(f"Configuration error: {error}")
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
        
        self._config = config
        return config
    
    def get_config(self) -> BotConfig:
        """Get current configuration, loading if necessary"""
        if self._config is None:
            self.load_config()
        return self._config
    
    def save_config_template(self, output_file: str):
        """Save a configuration template file"""
        template = {
            "bot_id": "claude-bot",
            "bot_label": "claude-bot",
            "target_repo": "owner/repository",
            "git_author_name": "Your Name",
            "git_author_email": "your.email@example.com",
            "issue_check_interval": 15,
            "pr_check_interval": 30,
            "status_report_interval": 300,
            "enable_metrics": True,
            "enable_pr_feedback": True,
            "max_concurrent_tasks": 3,
            "task_timeout": 3600,
            "allowed_repositories": ["owner/repo1", "owner/repo2"],
            "rate_limit_per_hour": 100
        }
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            if output_file.endswith('.json'):
                json.dump(template, f, indent=2)
            else:
                yaml.dump(template, f, default_flow_style=False)
        
        logger.info(f"Configuration template saved to {output_file}")


# Global config instance
_config_manager = ConfigManager()


def get_config() -> BotConfig:
    """Get the global configuration"""
    return _config_manager.get_config()


def reload_config() -> BotConfig:
    """Reload configuration from sources"""
    _config_manager._config = None
    return _config_manager.load_config()


if __name__ == "__main__":
    # Test configuration loading
    import sys
    
    try:
        config = get_config()
        print("✅ Configuration loaded successfully")
        print("\nConfiguration (sensitive values masked):")
        
        masked_config = config.mask_sensitive()
        for key, value in masked_config.items():
            print(f"  {key}: {value}")
        
        # Save template if requested
        if len(sys.argv) > 1 and sys.argv[1] == "--save-template":
            output_file = sys.argv[2] if len(sys.argv) > 2 else "config-template.yml"
            _config_manager.save_config_template(output_file)
            
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)