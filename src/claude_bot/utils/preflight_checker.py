#!/usr/bin/env python3
"""
Pre-flight Checker for Claude Bot Infrastructure

Validates that all necessary capabilities are available before executing workflow steps.
Provides detailed diagnostics and automatic remediation when possible.
"""

import os
import sys
import json
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

# Add scripts directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from command_capability_manager import create_capability_manager, CommandStatus

class PreflightStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    BLOCKED = "blocked"

@dataclass
class PreflightCheck:
    """Represents a single pre-flight check."""
    name: str
    description: str
    status: PreflightStatus
    details: str = ""
    remediation: Optional[str] = None
    critical: bool = True

@dataclass
class PreflightResult:
    """Results of a complete pre-flight check."""
    workflow_step: str
    overall_status: PreflightStatus
    checks: List[PreflightCheck]
    can_proceed: bool
    recommendations: List[str]
    timestamp: str

class PreflightChecker:
    """Performs comprehensive pre-flight checks before workflow execution."""
    
    def __init__(self, workspace_dir="/workspace", data_dir="/bot/data"):
        self.workspace_dir = Path(workspace_dir)
        self.data_dir = Path(data_dir)
        self.capability_manager = create_capability_manager(str(self.workspace_dir), str(self.data_dir))
        
    def run_preflight_checks(self, workflow_step: str, project_context: Dict[str, Any], 
                           workflow_context: Dict[str, Any] = None) -> PreflightResult:
        """Run all pre-flight checks for a workflow step."""
        checks = []
        workflow_context = workflow_context or {}
        
        print(f"🔍 Running pre-flight checks for {workflow_step} step...")
        
        # 1. Basic environment checks
        checks.extend(self._check_basic_environment())
        
        # 2. Command availability checks
        checks.extend(self._check_command_availability(workflow_step, project_context))
        
        # 3. Git repository checks
        checks.extend(self._check_git_repository())
        
        # 4. GitHub authentication checks
        checks.extend(self._check_github_authentication())
        
        # 5. Claude Code authentication checks
        checks.extend(self._check_claude_authentication())
        
        # 6. Project-specific checks
        checks.extend(self._check_project_requirements(project_context))
        
        # 7. Workflow step-specific checks
        checks.extend(self._check_workflow_step_requirements(workflow_step, project_context, workflow_context))
        
        # 8. Permission and access checks
        checks.extend(self._check_permissions())
        
        # Determine overall status
        overall_status = self._determine_overall_status(checks)
        can_proceed = self._can_proceed(checks)
        recommendations = self._generate_recommendations(checks)
        
        result = PreflightResult(
            workflow_step=workflow_step,
            overall_status=overall_status,
            checks=checks,
            can_proceed=can_proceed,
            recommendations=recommendations,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
        )
        
        return result
    
    def _check_basic_environment(self) -> List[PreflightCheck]:
        """Check basic environment requirements."""
        checks = []
        
        # Check workspace directory
        if self.workspace_dir.exists() and self.workspace_dir.is_dir():
            checks.append(PreflightCheck(
                name="Workspace Directory",
                description="Workspace directory exists and is accessible",
                status=PreflightStatus.PASSED,
                details=f"Workspace: {self.workspace_dir}",
                critical=True
            ))
        else:
            checks.append(PreflightCheck(
                name="Workspace Directory",
                description="Workspace directory check",
                status=PreflightStatus.FAILED,
                details=f"Workspace directory {self.workspace_dir} does not exist or is not accessible",
                remediation="Ensure workspace directory is properly mounted",
                critical=True
            ))
        
        # Check data directory
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            test_file = self.data_dir / "preflight_test"
            test_file.write_text("test")
            test_file.unlink()
            
            checks.append(PreflightCheck(
                name="Data Directory",
                description="Data directory exists and is writable",
                status=PreflightStatus.PASSED,
                details=f"Data directory: {self.data_dir}",
                critical=True
            ))
        except Exception as e:
            checks.append(PreflightCheck(
                name="Data Directory",
                description="Data directory access check",
                status=PreflightStatus.FAILED,
                details=f"Cannot write to data directory: {str(e)}",
                remediation="Check data directory permissions",
                critical=True
            ))
        
        # Check environment variables
        required_env_vars = ["ANTHROPIC_API_KEY", "GITHUB_TOKEN"]
        for env_var in required_env_vars:
            if os.getenv(env_var):
                checks.append(PreflightCheck(
                    name=f"Environment Variable: {env_var}",
                    description=f"{env_var} is set",
                    status=PreflightStatus.PASSED,
                    details="Environment variable configured",
                    critical=True
                ))
            else:
                checks.append(PreflightCheck(
                    name=f"Environment Variable: {env_var}",
                    description=f"{env_var} check",
                    status=PreflightStatus.FAILED,
                    details=f"Required environment variable {env_var} is not set",
                    remediation=f"Set {env_var} environment variable",
                    critical=True
                ))
        
        return checks
    
    def _check_command_availability(self, workflow_step: str, project_context: Dict[str, Any]) -> List[PreflightCheck]:
        """Check availability of required commands."""
        checks = []
        
        # Get fresh capability check
        capabilities = self.capability_manager.check_all_capabilities()
        
        # Validate workflow requirements
        is_valid, missing_caps = self.capability_manager.validate_workflow_requirements(workflow_step, project_context)
        
        if is_valid:
            checks.append(PreflightCheck(
                name="Command Requirements",
                description="All required commands are available",
                status=PreflightStatus.PASSED,
                details="All workflow step requirements satisfied",
                critical=True
            ))
        else:
            checks.append(PreflightCheck(
                name="Command Requirements",
                description="Required commands check",
                status=PreflightStatus.FAILED,
                details=f"Missing requirements: {', '.join(missing_caps)}",
                remediation="Install missing commands or use auto-installation",
                critical=True
            ))
        
        # Check critical commands individually
        critical_commands = ["git", "gh", "claude-code"]
        for cmd_name in critical_commands:
            if cmd_name in capabilities:
                capability = capabilities[cmd_name]
                if capability.status == CommandStatus.AVAILABLE:
                    version_info = f" v{capability.current_version}" if capability.current_version else ""
                    checks.append(PreflightCheck(
                        name=f"Command: {capability.requirement.name}",
                        description=f"{capability.requirement.name} is available",
                        status=PreflightStatus.PASSED,
                        details=f"Available at {capability.path}{version_info}",
                        critical=True
                    ))
                else:
                    checks.append(PreflightCheck(
                        name=f"Command: {capability.requirement.name}",
                        description=f"{capability.requirement.name} availability",
                        status=PreflightStatus.FAILED,
                        details=capability.error_message or f"Status: {capability.status.value}",
                        remediation=capability.requirement.install_cmd or "Manual installation required",
                        critical=True
                    ))
        
        return checks
    
    def _check_git_repository(self) -> List[PreflightCheck]:
        """Check git repository status."""
        checks = []
        
        try:
            # Check if we're in a git repository
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.workspace_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                checks.append(PreflightCheck(
                    name="Git Repository",
                    description="Working directory is a git repository",
                    status=PreflightStatus.PASSED,
                    details=f"Git directory: {result.stdout.strip()}",
                    critical=True
                ))
            else:
                checks.append(PreflightCheck(
                    name="Git Repository",
                    description="Git repository check",
                    status=PreflightStatus.FAILED,
                    details="Working directory is not a git repository",
                    remediation="Initialize git repository or check workspace path",
                    critical=True
                ))
                return checks
            
            # Check git remote
            result = subprocess.run(
                ["git", "remote", "-v"],
                cwd=self.workspace_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and result.stdout.strip():
                checks.append(PreflightCheck(
                    name="Git Remote",
                    description="Git remote is configured",
                    status=PreflightStatus.PASSED,
                    details="Remote repository configured",
                    critical=True
                ))
            else:
                checks.append(PreflightCheck(
                    name="Git Remote",
                    description="Git remote check",
                    status=PreflightStatus.WARNING,
                    details="No git remote configured",
                    remediation="Configure git remote origin",
                    critical=False
                ))
            
            # Check git user configuration
            git_configs = ["user.name", "user.email"]
            for config in git_configs:
                result = subprocess.run(
                    ["git", "config", config],
                    cwd=self.workspace_dir,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    checks.append(PreflightCheck(
                        name=f"Git Config: {config}",
                        description=f"Git {config} is configured",
                        status=PreflightStatus.PASSED,
                        details=f"{config}: {result.stdout.strip()}",
                        critical=True
                    ))
                else:
                    checks.append(PreflightCheck(
                        name=f"Git Config: {config}",
                        description=f"Git {config} check",
                        status=PreflightStatus.FAILED,
                        details=f"Git {config} is not configured",
                        remediation=f"Set git {config} using environment variables",
                        critical=True
                    ))
            
        except Exception as e:
            checks.append(PreflightCheck(
                name="Git Repository",
                description="Git repository access",
                status=PreflightStatus.FAILED,
                details=f"Error checking git repository: {str(e)}",
                remediation="Check git installation and repository setup",
                critical=True
            ))
        
        return checks
    
    def _check_github_authentication(self) -> List[PreflightCheck]:
        """Check GitHub CLI authentication."""
        checks = []
        
        try:
            # Check GitHub CLI authentication
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                checks.append(PreflightCheck(
                    name="GitHub Authentication",
                    description="GitHub CLI is authenticated",
                    status=PreflightStatus.PASSED,
                    details="GitHub authentication verified",
                    critical=True
                ))
                
                # Test GitHub API access
                result = subprocess.run(
                    ["gh", "api", "user"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    user_data = json.loads(result.stdout)
                    username = user_data.get("login", "unknown")
                    checks.append(PreflightCheck(
                        name="GitHub API Access",
                        description="GitHub API is accessible",
                        status=PreflightStatus.PASSED,
                        details=f"Authenticated as: {username}",
                        critical=True
                    ))
                else:
                    checks.append(PreflightCheck(
                        name="GitHub API Access",
                        description="GitHub API access test",
                        status=PreflightStatus.WARNING,
                        details="API access test failed but authentication exists",
                        critical=False
                    ))
                    
            else:
                checks.append(PreflightCheck(
                    name="GitHub Authentication",
                    description="GitHub CLI authentication check",
                    status=PreflightStatus.FAILED,
                    details="GitHub CLI is not authenticated",
                    remediation="Run 'gh auth login' or set GITHUB_TOKEN",
                    critical=True
                ))
        
        except subprocess.TimeoutExpired:
            checks.append(PreflightCheck(
                name="GitHub Authentication",
                description="GitHub authentication check",
                status=PreflightStatus.WARNING,
                details="GitHub authentication check timed out",
                critical=False
            ))
        except Exception as e:
            checks.append(PreflightCheck(
                name="GitHub Authentication",
                description="GitHub authentication access",
                status=PreflightStatus.FAILED,
                details=f"Error checking GitHub authentication: {str(e)}",
                remediation="Check GitHub CLI installation and authentication",
                critical=True
            ))
        
        return checks
    
    def _check_claude_authentication(self) -> List[PreflightCheck]:
        """Check Claude Code authentication."""
        checks = []
        
        try:
            # Test Claude Code basic functionality
            result = subprocess.run(
                ["claude-code", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                checks.append(PreflightCheck(
                    name="Claude Code",
                    description="Claude Code is available and responding",
                    status=PreflightStatus.PASSED,
                    details=f"Version: {result.stdout.strip()}",
                    critical=True
                ))
            else:
                checks.append(PreflightCheck(
                    name="Claude Code",
                    description="Claude Code availability",
                    status=PreflightStatus.FAILED,
                    details="Claude Code is not responding properly",
                    remediation="Check Claude Code installation and ANTHROPIC_API_KEY",
                    critical=True
                ))
        
        except subprocess.TimeoutExpired:
            checks.append(PreflightCheck(
                name="Claude Code",
                description="Claude Code response",
                status=PreflightStatus.WARNING,
                details="Claude Code response timed out",
                critical=False
            ))
        except Exception as e:
            checks.append(PreflightCheck(
                name="Claude Code",
                description="Claude Code access",
                status=PreflightStatus.FAILED,
                details=f"Error checking Claude Code: {str(e)}",
                remediation="Check Claude Code installation",
                critical=True
            ))
        
        return checks
    
    def _check_project_requirements(self, project_context: Dict[str, Any]) -> List[PreflightCheck]:
        """Check project-specific requirements."""
        checks = []
        
        platforms = project_context.get("platforms", [])
        
        # Check Node.js projects
        if "Node.js" in platforms:
            package_json = self.workspace_dir / "package.json"
            if package_json.exists():
                checks.append(PreflightCheck(
                    name="Node.js Project Structure",
                    description="package.json exists",
                    status=PreflightStatus.PASSED,
                    details="Node.js project structure verified",
                    critical=False
                ))
                
                # Check if node_modules exists or can be installed
                node_modules = self.workspace_dir / "node_modules"
                if not node_modules.exists():
                    checks.append(PreflightCheck(
                        name="Node.js Dependencies",
                        description="Node.js dependencies check",
                        status=PreflightStatus.WARNING,
                        details="node_modules not found - dependencies may need installation",
                        remediation="Run npm install before implementation",
                        critical=False
                    ))
            else:
                checks.append(PreflightCheck(
                    name="Node.js Project Structure",
                    description="Node.js project structure",
                    status=PreflightStatus.WARNING,
                    details="Node.js detected but package.json not found",
                    critical=False
                ))
        
        # Check Python projects
        if "Python" in platforms:
            python_files = ["requirements.txt", "pyproject.toml", "setup.py", "Pipfile"]
            python_config_found = any((self.workspace_dir / f).exists() for f in python_files)
            
            if python_config_found:
                checks.append(PreflightCheck(
                    name="Python Project Structure",
                    description="Python project configuration found",
                    status=PreflightStatus.PASSED,
                    details="Python project structure verified",
                    critical=False
                ))
            else:
                checks.append(PreflightCheck(
                    name="Python Project Structure",
                    description="Python project structure",
                    status=PreflightStatus.WARNING,
                    details="Python detected but no configuration files found",
                    critical=False
                ))
        
        # Check .NET projects
        if ".NET" in platforms:
            csproj_files = list(self.workspace_dir.glob("**/*.csproj"))
            if csproj_files:
                checks.append(PreflightCheck(
                    name=".NET Project Structure",
                    description=".NET project files found",
                    status=PreflightStatus.PASSED,
                    details=f"Found {len(csproj_files)} .csproj files",
                    critical=False
                ))
        
        return checks
    
    def _check_workflow_step_requirements(self, workflow_step: str, project_context: Dict[str, Any], 
                                        workflow_context: Dict[str, Any]) -> List[PreflightCheck]:
        """Check requirements specific to the workflow step."""
        checks = []
        
        if workflow_step == "analysis":
            # Analysis step needs read access to files
            checks.append(PreflightCheck(
                name="Analysis Requirements",
                description="Analysis step requirements",
                status=PreflightStatus.PASSED,
                details="Analysis step ready - no special requirements",
                critical=False
            ))
        
        elif workflow_step == "planning":
            # Planning step might need to create planning artifacts
            checks.append(PreflightCheck(
                name="Planning Requirements",
                description="Planning step requirements",
                status=PreflightStatus.PASSED,
                details="Planning step ready",
                critical=False
            ))
        
        elif workflow_step == "implementation":
            # Implementation needs write access and build tools
            checks.extend(self._check_implementation_requirements(project_context))
        
        elif workflow_step == "pr_creation":
            # PR creation needs branch and push permissions
            checks.extend(self._check_pr_requirements(workflow_context))
        
        elif workflow_step == "feedback_handling":
            # Feedback handling needs PR monitoring capabilities
            checks.append(PreflightCheck(
                name="Feedback Handling Requirements",
                description="Feedback handling capabilities",
                status=PreflightStatus.PASSED,
                details="Feedback handling ready",
                critical=False
            ))
        
        return checks
    
    def _check_implementation_requirements(self, project_context: Dict[str, Any]) -> List[PreflightCheck]:
        """Check implementation-specific requirements."""
        checks = []
        
        # Check testing framework availability
        testing_framework = project_context.get("testing_framework")
        if testing_framework:
            test_commands = {
                "Jest": "npx jest --version",
                "pytest": "pytest --version",
                "Vitest": "npx vitest --version"
            }
            
            if testing_framework in test_commands:
                try:
                    result = subprocess.run(
                        test_commands[testing_framework].split(),
                        cwd=self.workspace_dir,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if result.returncode == 0:
                        checks.append(PreflightCheck(
                            name=f"Testing Framework: {testing_framework}",
                            description=f"{testing_framework} is available",
                            status=PreflightStatus.PASSED,
                            details=f"{testing_framework} ready for testing",
                            critical=False
                        ))
                    else:
                        checks.append(PreflightCheck(
                            name=f"Testing Framework: {testing_framework}",
                            description=f"{testing_framework} availability",
                            status=PreflightStatus.WARNING,
                            details=f"{testing_framework} not available",
                            remediation="Install testing framework dependencies",
                            critical=False
                        ))
                except Exception:
                    checks.append(PreflightCheck(
                        name=f"Testing Framework: {testing_framework}",
                        description=f"{testing_framework} check",
                        status=PreflightStatus.WARNING,
                        details=f"Could not verify {testing_framework} availability",
                        critical=False
                    ))
        
        return checks
    
    def _check_pr_requirements(self, workflow_context: Dict[str, Any]) -> List[PreflightCheck]:
        """Check PR creation requirements."""
        checks = []
        
        # Check if we can create branches
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.workspace_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                current_branch = result.stdout.strip()
                checks.append(PreflightCheck(
                    name="Git Branch Operations",
                    description="Git branch operations available",
                    status=PreflightStatus.PASSED,
                    details=f"Current branch: {current_branch}",
                    critical=True
                ))
            else:
                checks.append(PreflightCheck(
                    name="Git Branch Operations",
                    description="Git branch operations",
                    status=PreflightStatus.FAILED,
                    details="Cannot determine current git branch",
                    critical=True
                ))
        except Exception as e:
            checks.append(PreflightCheck(
                name="Git Branch Operations",
                description="Git branch access",
                status=PreflightStatus.FAILED,
                details=f"Error checking git branch: {str(e)}",
                critical=True
            ))
        
        return checks
    
    def _check_permissions(self) -> List[PreflightCheck]:
        """Check file system and execution permissions."""
        checks = []
        
        # Check workspace write permissions
        try:
            test_file = self.workspace_dir / "preflight_write_test"
            test_file.write_text("test")
            test_file.unlink()
            
            checks.append(PreflightCheck(
                name="Workspace Write Permissions",
                description="Workspace is writable",
                status=PreflightStatus.PASSED,
                details="Write permissions verified",
                critical=True
            ))
        except Exception as e:
            checks.append(PreflightCheck(
                name="Workspace Write Permissions",
                description="Workspace write access",
                status=PreflightStatus.FAILED,
                details=f"Cannot write to workspace: {str(e)}",
                remediation="Check workspace directory permissions",
                critical=True
            ))
        
        return checks
    
    def _determine_overall_status(self, checks: List[PreflightCheck]) -> PreflightStatus:
        """Determine overall status from individual checks."""
        failed_critical = any(check.status == PreflightStatus.FAILED and check.critical for check in checks)
        failed_any = any(check.status == PreflightStatus.FAILED for check in checks)
        warning_any = any(check.status == PreflightStatus.WARNING for check in checks)
        
        if failed_critical:
            return PreflightStatus.BLOCKED
        elif failed_any:
            return PreflightStatus.FAILED
        elif warning_any:
            return PreflightStatus.WARNING
        else:
            return PreflightStatus.PASSED
    
    def _can_proceed(self, checks: List[PreflightCheck]) -> bool:
        """Determine if workflow can proceed based on checks."""
        critical_failures = [check for check in checks 
                           if check.status == PreflightStatus.FAILED and check.critical]
        return len(critical_failures) == 0
    
    def _generate_recommendations(self, checks: List[PreflightCheck]) -> List[str]:
        """Generate recommendations based on check results."""
        recommendations = []
        
        failed_checks = [check for check in checks if check.status == PreflightStatus.FAILED]
        warning_checks = [check for check in checks if check.status == PreflightStatus.WARNING]
        
        if failed_checks:
            recommendations.append("🚨 Critical issues must be resolved before proceeding:")
            for check in failed_checks:
                if check.critical and check.remediation:
                    recommendations.append(f"  • {check.name}: {check.remediation}")
        
        if warning_checks:
            recommendations.append("⚠️ Consider addressing these warnings:")
            for check in warning_checks:
                if check.remediation:
                    recommendations.append(f"  • {check.name}: {check.remediation}")
        
        if not failed_checks and not warning_checks:
            recommendations.append("✅ All checks passed - ready for autonomous operation")
        
        return recommendations
    
    def generate_preflight_report(self, result: PreflightResult) -> str:
        """Generate a detailed pre-flight report."""
        report = [
            f"🚀 Pre-flight Check Report - {result.workflow_step}",
            "=" * 60,
            f"Timestamp: {result.timestamp}",
            f"Overall Status: {result.overall_status.value.upper()}",
            f"Can Proceed: {'✅ YES' if result.can_proceed else '❌ NO'}",
            "",
            "📋 Check Results:",
            ""
        ]
        
        # Group checks by status
        passed = [c for c in result.checks if c.status == PreflightStatus.PASSED]
        warnings = [c for c in result.checks if c.status == PreflightStatus.WARNING]
        failed = [c for c in result.checks if c.status == PreflightStatus.FAILED]
        
        # Passed checks
        if passed:
            report.append(f"✅ Passed ({len(passed)}):")
            for check in passed:
                critical_mark = " (critical)" if check.critical else ""
                report.append(f"  • {check.name}{critical_mark}")
                if check.details:
                    report.append(f"    {check.details}")
            report.append("")
        
        # Warning checks
        if warnings:
            report.append(f"⚠️ Warnings ({len(warnings)}):")
            for check in warnings:
                critical_mark = " (critical)" if check.critical else ""
                report.append(f"  • {check.name}{critical_mark}")
                if check.details:
                    report.append(f"    {check.details}")
                if check.remediation:
                    report.append(f"    💡 {check.remediation}")
            report.append("")
        
        # Failed checks
        if failed:
            report.append(f"❌ Failed ({len(failed)}):")
            for check in failed:
                critical_mark = " (CRITICAL)" if check.critical else ""
                report.append(f"  • {check.name}{critical_mark}")
                if check.details:
                    report.append(f"    {check.details}")
                if check.remediation:
                    report.append(f"    🔧 {check.remediation}")
            report.append("")
        
        # Recommendations
        if result.recommendations:
            report.append("💡 Recommendations:")
            report.extend(result.recommendations)
        
        return "\\n".join(report)

def create_preflight_checker(workspace_dir="/workspace", data_dir="/bot/data") -> PreflightChecker:
    """Factory function to create a pre-flight checker."""
    return PreflightChecker(workspace_dir, data_dir)

if __name__ == "__main__":
    # Test the pre-flight checker
    checker = PreflightChecker("/tmp/test_workspace", "/tmp/test_data")
    
    # Mock project context
    project_context = {
        "platforms": ["Node.js"],
        "frameworks": ["Next.js"],
        "testing_framework": "Jest",
        "package_manager": "npm"
    }
    
    print("🔍 Running pre-flight checks...")
    result = checker.run_preflight_checks("implementation", project_context)
    
    print(checker.generate_preflight_report(result))
    
    if result.can_proceed:
        print("\\n✅ Ready to proceed with workflow step!")
    else:
        print("\\n❌ Cannot proceed - resolve critical issues first.")