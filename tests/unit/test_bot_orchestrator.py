#!/usr/bin/env python3
"""
Unit Tests for Bot Orchestrator
Tests the BotOrchestrator class functionality
"""

import pytest
import os
import sys
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "scripts"))

from scripts.bot_orchestrator import BotOrchestrator


class TestBotOrchestrator:
    """Test BotOrchestrator class"""
    
    def setup_method(self):
        """Set up each test method"""
        self.test_workspace = Path(tempfile.mkdtemp())
        self.test_data_dir = Path(tempfile.mkdtemp())
        self.test_repo = "test/repo"
        
        # Create necessary directories
        (self.test_data_dir / "queue").mkdir(parents=True, exist_ok=True)
        (self.test_data_dir / "processed").mkdir(parents=True, exist_ok=True)
    
    def teardown_method(self):
        """Clean up after each test"""
        import shutil
        if self.test_workspace.exists():
            shutil.rmtree(self.test_workspace)
        if self.test_data_dir.exists():
            shutil.rmtree(self.test_data_dir)
    
    @patch('scripts.bot_orchestrator.GitHubTaskExecutor')
    @patch('scripts.bot_orchestrator.PRFeedbackHandler')
    @patch('scripts.bot_orchestrator.StatusReporter')
    def test_bot_orchestrator_initialization(self, mock_status_reporter, mock_pr_handler, mock_github_executor):
        """Test BotOrchestrator initialization"""
        # Create mocks
        mock_github_executor.return_value = Mock()
        mock_pr_handler.return_value = Mock()
        mock_status_reporter.return_value = Mock()
        
        # Initialize orchestrator
        orchestrator = BotOrchestrator(
            workspace_dir=str(self.test_workspace),
            data_dir=str(self.test_data_dir),
            repo=self.test_repo
        )
        
        # Verify initialization
        assert orchestrator.workspace_dir == str(self.test_workspace)
        assert orchestrator.data_dir == self.test_data_dir
        assert orchestrator.repo == self.test_repo
        assert orchestrator.bot_id == "claude-bot"
        
        # Verify components were created
        mock_github_executor.assert_called_once()
        mock_pr_handler.assert_called_once()
        mock_status_reporter.assert_called_once()
    
    @patch('scripts.bot_orchestrator.GitHubTaskExecutor')
    @patch('scripts.bot_orchestrator.PRFeedbackHandler')
    @patch('scripts.bot_orchestrator.StatusReporter')
    def test_bot_orchestrator_custom_bot_id(self, mock_status_reporter, mock_pr_handler, mock_github_executor):
        """Test BotOrchestrator with custom bot ID"""
        custom_bot_id = "test-bot-123"
        
        # Create mocks
        mock_github_executor.return_value = Mock()
        mock_pr_handler.return_value = Mock()
        mock_status_reporter.return_value = Mock()
        
        # Initialize orchestrator with custom bot ID
        orchestrator = BotOrchestrator(
            workspace_dir=str(self.test_workspace),
            data_dir=str(self.test_data_dir),
            repo=self.test_repo,
            bot_id=custom_bot_id
        )
        
        assert orchestrator.bot_id == custom_bot_id
    
    @patch('scripts.bot_orchestrator.GitHubTaskExecutor')
    @patch('scripts.bot_orchestrator.PRFeedbackHandler')
    @patch('scripts.bot_orchestrator.StatusReporter')
    def test_check_for_new_issues(self, mock_status_reporter, mock_pr_handler, mock_github_executor):
        """Test checking for new issues"""
        # Create mocks
        mock_executor = Mock()
        mock_github_executor.return_value = mock_executor
        mock_pr_handler.return_value = Mock()
        mock_status_reporter.return_value = Mock()
        
        orchestrator = BotOrchestrator(
            workspace_dir=str(self.test_workspace),
            data_dir=str(self.test_data_dir),
            repo=self.test_repo
        )
        
        # Test successful issue check
        mock_executor.check_for_new_issues.return_value = True
        result = orchestrator.check_for_new_issues()
        
        assert result is True
        mock_executor.check_for_new_issues.assert_called_once()
    
    @patch('scripts.bot_orchestrator.GitHubTaskExecutor')
    @patch('scripts.bot_orchestrator.PRFeedbackHandler')
    @patch('scripts.bot_orchestrator.StatusReporter')
    def test_check_for_pr_feedback(self, mock_status_reporter, mock_pr_handler, mock_github_executor):
        """Test checking for PR feedback"""
        # Create mocks
        mock_handler = Mock()
        mock_github_executor.return_value = Mock()
        mock_pr_handler.return_value = mock_handler
        mock_status_reporter.return_value = Mock()
        
        orchestrator = BotOrchestrator(
            workspace_dir=str(self.test_workspace),
            data_dir=str(self.test_data_dir),
            repo=self.test_repo
        )
        
        # Test successful PR feedback check
        mock_handler.check_for_feedback.return_value = True
        result = orchestrator.check_for_pr_feedback()
        
        assert result is True
        mock_handler.check_for_feedback.assert_called_once()
    
    @patch('scripts.bot_orchestrator.GitHubTaskExecutor')
    @patch('scripts.bot_orchestrator.PRFeedbackHandler')
    @patch('scripts.bot_orchestrator.StatusReporter')
    def test_report_status(self, mock_status_reporter, mock_pr_handler, mock_github_executor):
        """Test status reporting"""
        # Create mocks
        mock_reporter = Mock()
        mock_github_executor.return_value = Mock()
        mock_pr_handler.return_value = Mock()
        mock_status_reporter.return_value = mock_reporter
        
        orchestrator = BotOrchestrator(
            workspace_dir=str(self.test_workspace),
            data_dir=str(self.test_data_dir),
            repo=self.test_repo
        )
        
        # Test status reporting
        mock_reporter.generate_and_publish.return_value = {"status": "success"}
        result = orchestrator.report_status()
        
        assert result == {"status": "success"}
        mock_reporter.generate_and_publish.assert_called_once()
    
    @patch('scripts.bot_orchestrator.GitHubTaskExecutor')
    @patch('scripts.bot_orchestrator.PRFeedbackHandler')
    @patch('scripts.bot_orchestrator.StatusReporter')
    @patch('scripts.bot_orchestrator.time.sleep')  # Mock sleep to speed up tests
    def test_run_cycle(self, mock_sleep, mock_status_reporter, mock_pr_handler, mock_github_executor):
        """Test a single run cycle"""
        # Create mocks
        mock_executor = Mock()
        mock_handler = Mock()
        mock_reporter = Mock()
        
        mock_github_executor.return_value = mock_executor
        mock_pr_handler.return_value = mock_handler
        mock_status_reporter.return_value = mock_reporter
        
        # Configure mock returns
        mock_executor.check_for_new_issues.return_value = True
        mock_handler.check_for_feedback.return_value = True
        mock_reporter.generate_and_publish.return_value = {"status": "success"}
        
        orchestrator = BotOrchestrator(
            workspace_dir=str(self.test_workspace),
            data_dir=str(self.test_data_dir),
            repo=self.test_repo
        )
        
        # Test single cycle
        orchestrator.run_cycle()
        
        # Verify all components were called
        mock_executor.check_for_new_issues.assert_called_once()
        mock_handler.check_for_feedback.assert_called_once()
        mock_reporter.generate_and_publish.assert_called_once()
    
    @patch('scripts.bot_orchestrator.GitHubTaskExecutor')
    @patch('scripts.bot_orchestrator.PRFeedbackHandler')
    @patch('scripts.bot_orchestrator.StatusReporter')
    def test_error_handling_in_issue_check(self, mock_status_reporter, mock_pr_handler, mock_github_executor):
        """Test error handling in issue checking"""
        # Create mocks
        mock_executor = Mock()
        mock_github_executor.return_value = mock_executor
        mock_pr_handler.return_value = Mock()
        mock_status_reporter.return_value = Mock()
        
        # Configure mock to raise exception
        mock_executor.check_for_new_issues.side_effect = Exception("GitHub API error")
        
        orchestrator = BotOrchestrator(
            workspace_dir=str(self.test_workspace),
            data_dir=str(self.test_data_dir),
            repo=self.test_repo
        )
        
        # Test that exception is handled gracefully
        result = orchestrator.check_for_new_issues()
        assert result is False  # Should return False on error
    
    @patch('scripts.bot_orchestrator.GitHubTaskExecutor')
    @patch('scripts.bot_orchestrator.PRFeedbackHandler')
    @patch('scripts.bot_orchestrator.StatusReporter')
    def test_error_handling_in_pr_feedback(self, mock_status_reporter, mock_pr_handler, mock_github_executor):
        """Test error handling in PR feedback checking"""
        # Create mocks
        mock_handler = Mock()
        mock_github_executor.return_value = Mock()
        mock_pr_handler.return_value = mock_handler
        mock_status_reporter.return_value = Mock()
        
        # Configure mock to raise exception
        mock_handler.check_for_feedback.side_effect = Exception("GitHub API error")
        
        orchestrator = BotOrchestrator(
            workspace_dir=str(self.test_workspace),
            data_dir=str(self.test_data_dir),
            repo=self.test_repo
        )
        
        # Test that exception is handled gracefully
        result = orchestrator.check_for_pr_feedback()
        assert result is False  # Should return False on error
    
    @patch.dict(os.environ, {'BOT_ID': 'env-test-bot'})
    @patch('scripts.bot_orchestrator.GitHubTaskExecutor')
    @patch('scripts.bot_orchestrator.PRFeedbackHandler')
    @patch('scripts.bot_orchestrator.StatusReporter')
    def test_bot_id_from_environment(self, mock_status_reporter, mock_pr_handler, mock_github_executor):
        """Test that bot ID can be set from environment variable"""
        # Create mocks
        mock_github_executor.return_value = Mock()
        mock_pr_handler.return_value = Mock()
        mock_status_reporter.return_value = Mock()
        
        orchestrator = BotOrchestrator(
            workspace_dir=str(self.test_workspace),
            data_dir=str(self.test_data_dir),
            repo=self.test_repo
        )
        
        assert orchestrator.bot_id == "env-test-bot"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])