#!/usr/bin/env python3
"""
Command Capability Manager for Claude Bot Infrastructure

Ensures the bot has all necessary tools and capabilities to complete autonomous tasks.
Provides command validation, environment setup, and fallback strategies.
"""

import os
import sys
import json
import subprocess
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

class CommandStatus(Enum):
    AVAILABLE = "available"
    MISSING = "missing"
    VERSION_MISMATCH = "version_mismatch"
    PERMISSION_DENIED = "permission_denied"
    ERROR = "error"

@dataclass
class CommandRequirement:
    """Represents a command requirement for the bot."""
    name: str
    command: str
    min_version: Optional[str] = None
    version_check_cmd: Optional[str] = None
    install_cmd: Optional[str] = None
    fallback_commands: List[str] = None
    required_for: List[str] = None
    
    def __post_init__(self):
        if self.fallback_commands is None:
            self.fallback_commands = []
        if self.required_for is None:
            self.required_for = []

@dataclass
class CommandCapability:
    """Represents the current capability status of a command."""
    requirement: CommandRequirement
    status: CommandStatus
    current_version: Optional[str] = None
    path: Optional[str] = None
    error_message: Optional[str] = None
    last_checked: Optional[str] = None

class CommandCapabilityManager:
    """Manages command capabilities for autonomous bot operation."""
    
    def __init__(self, workspace_dir="/workspace", data_dir="/bot/data"):
        self.workspace_dir = Path(workspace_dir)
        self.data_dir = Path(data_dir)
        self.capabilities_cache_file = self.data_dir / "command_capabilities.json"
        
        # Define core command requirements
        self.command_requirements = self._define_command_requirements()
        self.capabilities_cache = {}
        self.load_capabilities_cache()
    
    def _define_command_requirements(self) -> Dict[str, CommandRequirement]:
        """Define all command requirements for autonomous operation."""
        requirements = {
            # Git commands
            "git": CommandRequirement(
                name="Git",
                command="git",
                version_check_cmd="git --version",
                min_version="2.20.0",
                required_for=["branch_creation", "committing", "pushing"]
            ),
            
            # GitHub CLI
            "gh": CommandRequirement(
                name="GitHub CLI",
                command="gh",
                version_check_cmd="gh --version",
                min_version="2.0.0",
                install_cmd="curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg && echo \"deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main\" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null && sudo apt update && sudo apt install gh",
                required_for=["issue_management", "pr_creation", "github_operations"]
            ),
            
            # Claude Code
            "claude-code": CommandRequirement(
                name="Claude Code",
                command="claude-code",
                version_check_cmd="claude-code --version",
                required_for=["code_generation", "implementation"]
            ),
            
            # Node.js ecosystem
            "node": CommandRequirement(
                name="Node.js",
                command="node",
                version_check_cmd="node --version",
                min_version="16.0.0",
                required_for=["nodejs_projects", "package_management"]
            ),
            
            "npm": CommandRequirement(
                name="npm",
                command="npm",
                version_check_cmd="npm --version",
                min_version="8.0.0",
                fallback_commands=["yarn", "pnpm"],
                required_for=["nodejs_projects", "dependency_installation"]
            ),
            
            "yarn": CommandRequirement(
                name="Yarn",
                command="yarn",
                version_check_cmd="yarn --version",
                required_for=["nodejs_projects", "dependency_installation"]
            ),
            
            "pnpm": CommandRequirement(
                name="pnpm",
                command="pnpm",
                version_check_cmd="pnpm --version",
                required_for=["nodejs_projects", "dependency_installation"]
            ),
            
            # Python ecosystem
            "python": CommandRequirement(
                name="Python",
                command="python3",
                version_check_cmd="python3 --version",
                min_version="3.8.0",
                fallback_commands=["python"],
                required_for=["python_projects", "script_execution"]
            ),
            
            "pip": CommandRequirement(
                name="pip",
                command="pip3",
                version_check_cmd="pip3 --version",
                fallback_commands=["pip"],
                required_for=["python_projects", "dependency_installation"]
            ),
            
            # .NET ecosystem
            "dotnet": CommandRequirement(
                name=".NET",
                command="dotnet",
                version_check_cmd="dotnet --version",
                min_version="6.0.0",
                required_for=["dotnet_projects", "compilation"]
            ),
            
            # Build tools
            "make": CommandRequirement(
                name="Make",
                command="make",
                version_check_cmd="make --version",
                required_for=["compilation", "build_systems"]
            ),
            
            # Container tools
            "docker": CommandRequirement(
                name="Docker",
                command="docker",
                version_check_cmd="docker --version",
                min_version="20.0.0",
                required_for=["containerization", "testing"]
            ),
            
            # Testing frameworks
            "jest": CommandRequirement(
                name="Jest",
                command="npx jest",
                version_check_cmd="npx jest --version",
                required_for=["nodejs_testing"]
            ),
            
            "pytest": CommandRequirement(
                name="pytest",
                command="pytest",
                version_check_cmd="pytest --version",
                required_for=["python_testing"]
            ),
            
            # Code quality tools
            "eslint": CommandRequirement(
                name="ESLint",
                command="npx eslint",
                version_check_cmd="npx eslint --version",
                required_for=["code_quality", "linting"]
            ),
            
            "prettier": CommandRequirement(
                name="Prettier",
                command="npx prettier",
                version_check_cmd="npx prettier --version",
                required_for=["code_formatting"]
            ),
            
            # Security scanning
            "npm-audit": CommandRequirement(
                name="npm audit",
                command="npm audit",
                required_for=["security_scanning"]
            )
        }
        
        return requirements
    
    def check_command_availability(self, requirement: CommandRequirement) -> CommandCapability:
        """Check if a command is available and meets requirements."""
        capability = CommandCapability(
            requirement=requirement,
            status=CommandStatus.MISSING,
            last_checked=time.strftime("%Y-%m-%d %H:%M:%S")
        )
        
        try:
            # Check if command exists
            command_path = shutil.which(requirement.command)
            if not command_path:
                # Try fallback commands
                for fallback in requirement.fallback_commands:
                    command_path = shutil.which(fallback)
                    if command_path:
                        capability.requirement.command = fallback
                        break
                
                if not command_path:
                    capability.status = CommandStatus.MISSING
                    capability.error_message = f"Command '{requirement.command}' not found in PATH"
                    return capability
            
            capability.path = command_path
            
            # Check version if required
            if requirement.version_check_cmd:
                try:
                    result = subprocess.run(
                        requirement.version_check_cmd.split(),
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if result.returncode == 0:
                        version_output = result.stdout.strip()
                        capability.current_version = self._extract_version(version_output)
                        
                        if requirement.min_version and capability.current_version:
                            if self._compare_versions(capability.current_version, requirement.min_version) < 0:
                                capability.status = CommandStatus.VERSION_MISMATCH
                                capability.error_message = f"Version {capability.current_version} is below minimum {requirement.min_version}"
                                return capability
                    else:
                        capability.error_message = f"Version check failed: {result.stderr}"
                        
                except subprocess.TimeoutExpired:
                    capability.error_message = "Version check timed out"
                except Exception as e:
                    capability.error_message = f"Version check error: {str(e)}"
            
            # Test basic execution
            try:
                test_result = subprocess.run(
                    [requirement.command, "--help"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if test_result.returncode in [0, 1]:  # Many commands return 1 for --help
                    capability.status = CommandStatus.AVAILABLE
                else:
                    capability.status = CommandStatus.ERROR
                    capability.error_message = f"Command test failed: {test_result.stderr}"
                    
            except subprocess.TimeoutExpired:
                capability.status = CommandStatus.ERROR
                capability.error_message = "Command test timed out"
            except PermissionError:
                capability.status = CommandStatus.PERMISSION_DENIED
                capability.error_message = "Permission denied executing command"
            except Exception as e:
                capability.status = CommandStatus.ERROR
                capability.error_message = f"Command test error: {str(e)}"
                
        except Exception as e:
            capability.status = CommandStatus.ERROR
            capability.error_message = f"Capability check error: {str(e)}"
        
        return capability
    
    def _extract_version(self, version_output: str) -> Optional[str]:
        """Extract version number from command output."""
        import re
        
        # Common version patterns
        patterns = [
            r'v?(\d+\.\d+\.\d+)',
            r'version\s+v?(\d+\.\d+\.\d+)',
            r'(\d+\.\d+\.\d+)',
            r'v?(\d+\.\d+)',
            r'(\d+\.\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, version_output, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _compare_versions(self, current: str, minimum: str) -> int:
        """Compare version strings. Returns -1 if current < minimum, 0 if equal, 1 if current > minimum."""
        def version_tuple(v):
            return tuple(map(int, v.split('.')))
        
        try:
            current_tuple = version_tuple(current)
            minimum_tuple = version_tuple(minimum)
            
            if current_tuple < minimum_tuple:
                return -1
            elif current_tuple > minimum_tuple:
                return 1
            else:
                return 0
        except ValueError:
            return 0  # If we can't parse, assume it's okay
    
    def check_all_capabilities(self) -> Dict[str, CommandCapability]:
        """Check all command capabilities."""
        capabilities = {}
        
        for name, requirement in self.command_requirements.items():
            capabilities[name] = self.check_command_availability(requirement)
        
        self.capabilities_cache = capabilities
        self.save_capabilities_cache()
        return capabilities
    
    def get_missing_requirements(self, required_for: List[str] = None) -> List[CommandCapability]:
        """Get list of missing command requirements."""
        if not self.capabilities_cache:
            self.check_all_capabilities()
        
        missing = []
        for name, capability in self.capabilities_cache.items():
            if capability.status != CommandStatus.AVAILABLE:
                # If filtering by required_for, check if this command is needed
                if required_for:
                    if any(req in capability.requirement.required_for for req in required_for):
                        missing.append(capability)
                else:
                    missing.append(capability)
        
        return missing
    
    def get_available_alternatives(self, command_name: str) -> List[CommandCapability]:
        """Get available alternative commands for a given command."""
        if command_name not in self.command_requirements:
            return []
        
        requirement = self.command_requirements[command_name]
        alternatives = []
        
        for fallback in requirement.fallback_commands:
            if fallback in self.capabilities_cache:
                capability = self.capabilities_cache[fallback]
                if capability.status == CommandStatus.AVAILABLE:
                    alternatives.append(capability)
        
        return alternatives
    
    def auto_install_missing_commands(self) -> Dict[str, bool]:
        """Attempt to automatically install missing commands."""
        installation_results = {}
        missing = self.get_missing_requirements()
        
        for capability in missing:
            requirement = capability.requirement
            if requirement.install_cmd:
                try:
                    print(f"📦 Attempting to install {requirement.name}...")
                    
                    result = subprocess.run(
                        requirement.install_cmd,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=300  # 5 minute timeout
                    )
                    
                    if result.returncode == 0:
                        # Verify installation
                        updated_capability = self.check_command_availability(requirement)
                        if updated_capability.status == CommandStatus.AVAILABLE:
                            installation_results[requirement.name] = True
                            print(f"✅ Successfully installed {requirement.name}")
                        else:
                            installation_results[requirement.name] = False
                            print(f"❌ Installation of {requirement.name} completed but command still not available")
                    else:
                        installation_results[requirement.name] = False
                        print(f"❌ Failed to install {requirement.name}: {result.stderr}")
                        
                except subprocess.TimeoutExpired:
                    installation_results[requirement.name] = False
                    print(f"❌ Installation of {requirement.name} timed out")
                except Exception as e:
                    installation_results[requirement.name] = False
                    print(f"❌ Error installing {requirement.name}: {str(e)}")
            else:
                print(f"⚠️ No installation command available for {requirement.name}")
                installation_results[requirement.name] = False
        
        # Refresh capabilities after installation attempts
        self.check_all_capabilities()
        return installation_results
    
    def generate_capability_report(self, required_for: List[str] = None) -> str:
        """Generate a detailed capability report."""
        if not self.capabilities_cache:
            self.check_all_capabilities()
        
        report = ["📋 Command Capability Report", "=" * 50, ""]
        
        # Filter capabilities if required_for is specified
        relevant_capabilities = {}
        if required_for:
            for name, capability in self.capabilities_cache.items():
                if any(req in capability.requirement.required_for for req in required_for):
                    relevant_capabilities[name] = capability
        else:
            relevant_capabilities = self.capabilities_cache
        
        # Categorize capabilities
        available = []
        missing = []
        issues = []
        
        for name, capability in relevant_capabilities.items():
            if capability.status == CommandStatus.AVAILABLE:
                available.append((name, capability))
            elif capability.status == CommandStatus.MISSING:
                missing.append((name, capability))
            else:
                issues.append((name, capability))
        
        # Available commands
        report.append(f"✅ Available Commands ({len(available)}):")
        for name, capability in available:
            version_info = f" v{capability.current_version}" if capability.current_version else ""
            report.append(f"  • {capability.requirement.name}{version_info} ({capability.path})")
        report.append("")
        
        # Missing commands
        if missing:
            report.append(f"❌ Missing Commands ({len(missing)}):")
            for name, capability in missing:
                required_for_text = ", ".join(capability.requirement.required_for)
                report.append(f"  • {capability.requirement.name} - Required for: {required_for_text}")
                if capability.requirement.install_cmd:
                    report.append(f"    Install: {capability.requirement.install_cmd}")
            report.append("")
        
        # Commands with issues
        if issues:
            report.append(f"⚠️ Commands with Issues ({len(issues)}):")
            for name, capability in issues:
                report.append(f"  • {capability.requirement.name} - {capability.status.value}")
                if capability.error_message:
                    report.append(f"    Error: {capability.error_message}")
            report.append("")
        
        # Summary
        total_needed = len(relevant_capabilities)
        total_working = len(available)
        readiness_percentage = (total_working / total_needed * 100) if total_needed > 0 else 100
        
        report.append(f"📊 Summary:")
        report.append(f"  • Readiness: {readiness_percentage:.1f}% ({total_working}/{total_needed})")
        
        if readiness_percentage < 100:
            report.append(f"  • ⚠️ Bot may not be able to complete all autonomous tasks")
        else:
            report.append(f"  • ✅ Bot is ready for autonomous operation")
        
        return "\\n".join(report)
    
    def validate_workflow_requirements(self, workflow_step: str, project_context: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate that all requirements are met for a specific workflow step."""
        required_capabilities = self._get_workflow_requirements(workflow_step, project_context)
        missing_capabilities = []
        
        for capability_name in required_capabilities:
            if capability_name in self.capabilities_cache:
                capability = self.capabilities_cache[capability_name]
                if capability.status != CommandStatus.AVAILABLE:
                    missing_capabilities.append(f"{capability.requirement.name}: {capability.error_message or capability.status.value}")
            else:
                missing_capabilities.append(f"Unknown requirement: {capability_name}")
        
        return len(missing_capabilities) == 0, missing_capabilities
    
    def _get_workflow_requirements(self, workflow_step: str, project_context: Dict[str, Any]) -> List[str]:
        """Determine which capabilities are required for a specific workflow step."""
        base_requirements = ["git", "gh", "claude-code"]
        
        # Add platform-specific requirements
        platforms = project_context.get("platforms", [])
        
        if "Node.js" in platforms:
            base_requirements.extend(["node", "npm"])
            
            # Add package manager alternatives
            if project_context.get("package_manager") == "yarn":
                base_requirements.append("yarn")
            elif project_context.get("package_manager") == "pnpm":
                base_requirements.append("pnpm")
        
        if "Python" in platforms:
            base_requirements.extend(["python", "pip"])
            
        if ".NET" in platforms:
            base_requirements.append("dotnet")
        
        # Add workflow step specific requirements
        if workflow_step in ["implementation", "pr_creation"]:
            # Testing requirements
            if project_context.get("testing_framework") == "Jest":
                base_requirements.append("jest")
            elif project_context.get("testing_framework") == "pytest":
                base_requirements.append("pytest")
            
            # Code quality requirements
            if "Node.js" in platforms:
                base_requirements.extend(["eslint", "prettier"])
        
        return base_requirements
    
    def load_capabilities_cache(self):
        """Load capabilities cache from disk."""
        try:
            if self.capabilities_cache_file.exists():
                with open(self.capabilities_cache_file, 'r') as f:
                    cache_data = json.load(f)
                
                # Reconstruct capabilities from cache
                for name, data in cache_data.items():
                    if name in self.command_requirements:
                        requirement = self.command_requirements[name]
                        capability = CommandCapability(
                            requirement=requirement,
                            status=CommandStatus(data["status"]),
                            current_version=data.get("current_version"),
                            path=data.get("path"),
                            error_message=data.get("error_message"),
                            last_checked=data.get("last_checked")
                        )
                        self.capabilities_cache[name] = capability
        except Exception as e:
            print(f"Warning: Could not load capabilities cache: {e}")
    
    def save_capabilities_cache(self):
        """Save capabilities cache to disk."""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            
            cache_data = {}
            for name, capability in self.capabilities_cache.items():
                cache_data[name] = {
                    "status": capability.status.value,
                    "current_version": capability.current_version,
                    "path": capability.path,
                    "error_message": capability.error_message,
                    "last_checked": capability.last_checked
                }
            
            with open(self.capabilities_cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
                
        except Exception as e:
            print(f"Warning: Could not save capabilities cache: {e}")

def create_capability_manager(workspace_dir="/workspace", data_dir="/bot/data") -> CommandCapabilityManager:
    """Factory function to create a command capability manager."""
    return CommandCapabilityManager(workspace_dir, data_dir)

if __name__ == "__main__":
    # Test the capability manager
    manager = CommandCapabilityManager("/tmp/test_workspace", "/tmp/test_data")
    
    print("🔍 Checking command capabilities...")
    capabilities = manager.check_all_capabilities()
    
    print("\\n" + manager.generate_capability_report())
    
    missing = manager.get_missing_requirements()
    if missing:
        print(f"\\n⚠️ Found {len(missing)} missing requirements")
        
        # Test auto-installation (commented out for safety)
        # results = manager.auto_install_missing_commands()
        # print(f"Installation results: {results}")
    else:
        print("\\n✅ All requirements satisfied!")