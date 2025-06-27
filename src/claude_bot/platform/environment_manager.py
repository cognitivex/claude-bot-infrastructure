#!/usr/bin/env python3
"""
Environment Manager for Claude Bot Infrastructure

Manages environment setup, dependency installation, and project initialization
to ensure the bot can execute all necessary commands autonomously.
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

class SetupStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    PARTIAL = "partial"

@dataclass
class SetupResult:
    """Result of an environment setup operation."""
    operation: str
    status: SetupStatus
    details: str
    execution_time: float
    error_message: Optional[str] = None

class EnvironmentManager:
    """Manages environment setup for autonomous bot operation."""
    
    def __init__(self, workspace_dir="/workspace", data_dir="/bot/data"):
        self.workspace_dir = Path(workspace_dir)
        self.data_dir = Path(data_dir)
        self.setup_cache_file = self.data_dir / "environment_setup.json"
        self.setup_cache = {}
        self.load_setup_cache()
    
    def setup_project_environment(self, project_context: Dict[str, Any], 
                                 force_reinstall: bool = False) -> List[SetupResult]:
        """Set up the complete project environment."""
        results = []
        platforms = project_context.get("platforms", [])
        
        print(f"🛠️ Setting up environment for platforms: {platforms}")
        
        # Setup Git environment
        results.extend(self._setup_git_environment())
        
        # Setup platform-specific environments
        if "Node.js" in platforms:
            results.extend(self._setup_nodejs_environment(project_context, force_reinstall))
        
        if "Python" in platforms:
            results.extend(self._setup_python_environment(project_context, force_reinstall))
        
        if ".NET" in platforms:
            results.extend(self._setup_dotnet_environment(project_context, force_reinstall))
        
        # Setup testing environment
        results.extend(self._setup_testing_environment(project_context))
        
        # Setup code quality tools
        results.extend(self._setup_code_quality_tools(project_context))
        
        # Cache successful setups
        self._update_setup_cache(results)
        
        return results
    
    def _setup_git_environment(self) -> List[SetupResult]:
        """Set up Git environment with proper configuration."""
        results = []
        start_time = time.time()
        
        try:
            # Configure git user if environment variables are available
            git_configs = [
                ("user.name", os.getenv("GIT_AUTHOR_NAME")),
                ("user.email", os.getenv("GIT_AUTHOR_EMAIL"))
            ]
            
            for config_key, config_value in git_configs:
                if config_value:
                    result = subprocess.run(
                        ["git", "config", config_key, config_value],
                        cwd=self.workspace_dir,
                        capture_output=True,
                        text=True
                    )
                    
                    if result.returncode == 0:
                        results.append(SetupResult(
                            operation=f"Git Config: {config_key}",
                            status=SetupStatus.SUCCESS,
                            details=f"Set {config_key} to {config_value}",
                            execution_time=time.time() - start_time
                        ))
                    else:
                        results.append(SetupResult(
                            operation=f"Git Config: {config_key}",
                            status=SetupStatus.FAILED,
                            details=f"Failed to set {config_key}",
                            execution_time=time.time() - start_time,
                            error_message=result.stderr
                        ))
                else:
                    results.append(SetupResult(
                        operation=f"Git Config: {config_key}",
                        status=SetupStatus.SKIPPED,
                        details=f"Environment variable not set",
                        execution_time=0
                    ))
            
            # Set up git safe directory (for containers)
            result = subprocess.run(
                ["git", "config", "--global", "--add", "safe.directory", str(self.workspace_dir)],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                results.append(SetupResult(
                    operation="Git Safe Directory",
                    status=SetupStatus.SUCCESS,
                    details=f"Added {self.workspace_dir} as safe directory",
                    execution_time=time.time() - start_time
                ))
        
        except Exception as e:
            results.append(SetupResult(
                operation="Git Environment",
                status=SetupStatus.FAILED,
                details="Error setting up git environment",
                execution_time=time.time() - start_time,
                error_message=str(e)
            ))
        
        return results
    
    def _setup_nodejs_environment(self, project_context: Dict[str, Any], 
                                 force_reinstall: bool = False) -> List[SetupResult]:
        """Set up Node.js environment and install dependencies."""
        results = []
        
        # Check if package.json exists
        package_json = self.workspace_dir / "package.json"
        if not package_json.exists():
            results.append(SetupResult(
                operation="Node.js Dependencies",
                status=SetupStatus.SKIPPED,
                details="No package.json found",
                execution_time=0
            ))
            return results
        
        # Determine package manager
        package_manager = project_context.get("package_manager", "npm")
        
        # Check if already installed (unless force reinstall)
        node_modules = self.workspace_dir / "node_modules"
        cache_key = f"nodejs_deps_{package_manager}_{package_json.stat().st_mtime}"
        
        if not force_reinstall and node_modules.exists() and cache_key in self.setup_cache:
            results.append(SetupResult(
                operation="Node.js Dependencies",
                status=SetupStatus.SKIPPED,
                details="Dependencies already installed (cached)",
                execution_time=0
            ))
            return results
        
        # Install dependencies
        start_time = time.time()
        try:
            install_commands = {
                "npm": ["npm", "install"],
                "yarn": ["yarn", "install"],
                "pnpm": ["pnpm", "install"]
            }
            
            cmd = install_commands.get(package_manager, ["npm", "install"])
            
            print(f"📦 Installing Node.js dependencies with {package_manager}...")
            result = subprocess.run(
                cmd,
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            execution_time = time.time() - start_time
            
            if result.returncode == 0:
                results.append(SetupResult(
                    operation="Node.js Dependencies",
                    status=SetupStatus.SUCCESS,
                    details=f"Dependencies installed with {package_manager}",
                    execution_time=execution_time
                ))
                self.setup_cache[cache_key] = True
            else:
                results.append(SetupResult(
                    operation="Node.js Dependencies",
                    status=SetupStatus.FAILED,
                    details=f"Failed to install dependencies with {package_manager}",
                    execution_time=execution_time,
                    error_message=result.stderr
                ))
        
        except subprocess.TimeoutExpired:
            results.append(SetupResult(
                operation="Node.js Dependencies",
                status=SetupStatus.FAILED,
                details="Dependency installation timed out",
                execution_time=time.time() - start_time,
                error_message="Installation exceeded 10 minute timeout"
            ))
        except Exception as e:
            results.append(SetupResult(
                operation="Node.js Dependencies",
                status=SetupStatus.FAILED,
                details="Error during dependency installation",
                execution_time=time.time() - start_time,
                error_message=str(e)
            ))
        
        return results
    
    def _setup_python_environment(self, project_context: Dict[str, Any], 
                                 force_reinstall: bool = False) -> List[SetupResult]:
        """Set up Python environment and install dependencies."""
        results = []
        
        # Check for Python dependency files
        dep_files = ["requirements.txt", "pyproject.toml", "Pipfile"]
        found_files = [f for f in dep_files if (self.workspace_dir / f).exists()]
        
        if not found_files:
            results.append(SetupResult(
                operation="Python Dependencies",
                status=SetupStatus.SKIPPED,
                details="No Python dependency files found",
                execution_time=0
            ))
            return results
        
        # Install dependencies based on found files
        start_time = time.time()
        
        for dep_file in found_files:
            if dep_file == "requirements.txt":
                results.extend(self._install_pip_requirements(force_reinstall))
            elif dep_file == "pyproject.toml":
                results.extend(self._install_pyproject_dependencies(force_reinstall))
            elif dep_file == "Pipfile":
                results.extend(self._install_pipenv_dependencies(force_reinstall))
        
        return results
    
    def _install_pip_requirements(self, force_reinstall: bool = False) -> List[SetupResult]:
        """Install pip requirements."""
        requirements_file = self.workspace_dir / "requirements.txt"
        cache_key = f"pip_requirements_{requirements_file.stat().st_mtime}"
        
        if not force_reinstall and cache_key in self.setup_cache:
            return [SetupResult(
                operation="pip requirements",
                status=SetupStatus.SKIPPED,
                details="Requirements already installed (cached)",
                execution_time=0
            )]
        
        start_time = time.time()
        try:
            print("📦 Installing Python requirements...")
            result = subprocess.run(
                ["pip3", "install", "-r", "requirements.txt"],
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            execution_time = time.time() - start_time
            
            if result.returncode == 0:
                self.setup_cache[cache_key] = True
                return [SetupResult(
                    operation="pip requirements",
                    status=SetupStatus.SUCCESS,
                    details="Python requirements installed",
                    execution_time=execution_time
                )]
            else:
                return [SetupResult(
                    operation="pip requirements",
                    status=SetupStatus.FAILED,
                    details="Failed to install Python requirements",
                    execution_time=execution_time,
                    error_message=result.stderr
                )]
        
        except Exception as e:
            return [SetupResult(
                operation="pip requirements",
                status=SetupStatus.FAILED,
                details="Error installing Python requirements",
                execution_time=time.time() - start_time,
                error_message=str(e)
            )]
    
    def _install_pyproject_dependencies(self, force_reinstall: bool = False) -> List[SetupResult]:
        """Install pyproject.toml dependencies."""
        start_time = time.time()
        try:
            # Try pip install -e . for editable install
            result = subprocess.run(
                ["pip3", "install", "-e", "."],
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            execution_time = time.time() - start_time
            
            if result.returncode == 0:
                return [SetupResult(
                    operation="pyproject dependencies",
                    status=SetupStatus.SUCCESS,
                    details="pyproject.toml dependencies installed",
                    execution_time=execution_time
                )]
            else:
                return [SetupResult(
                    operation="pyproject dependencies",
                    status=SetupStatus.FAILED,
                    details="Failed to install pyproject.toml dependencies",
                    execution_time=execution_time,
                    error_message=result.stderr
                )]
        
        except Exception as e:
            return [SetupResult(
                operation="pyproject dependencies",
                status=SetupStatus.FAILED,
                details="Error installing pyproject.toml dependencies",
                execution_time=time.time() - start_time,
                error_message=str(e)
            )]
    
    def _install_pipenv_dependencies(self, force_reinstall: bool = False) -> List[SetupResult]:
        """Install Pipenv dependencies."""
        start_time = time.time()
        try:
            # Check if pipenv is available
            pipenv_available = shutil.which("pipenv") is not None
            
            if not pipenv_available:
                return [SetupResult(
                    operation="Pipenv dependencies",
                    status=SetupStatus.FAILED,
                    details="Pipenv not available",
                    execution_time=time.time() - start_time,
                    error_message="pipenv command not found"
                )]
            
            result = subprocess.run(
                ["pipenv", "install"],
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            execution_time = time.time() - start_time
            
            if result.returncode == 0:
                return [SetupResult(
                    operation="Pipenv dependencies",
                    status=SetupStatus.SUCCESS,
                    details="Pipenv dependencies installed",
                    execution_time=execution_time
                )]
            else:
                return [SetupResult(
                    operation="Pipenv dependencies",
                    status=SetupStatus.FAILED,
                    details="Failed to install Pipenv dependencies",
                    execution_time=execution_time,
                    error_message=result.stderr
                )]
        
        except Exception as e:
            return [SetupResult(
                operation="Pipenv dependencies",
                status=SetupStatus.FAILED,
                details="Error installing Pipenv dependencies",
                execution_time=time.time() - start_time,
                error_message=str(e)
            )]
    
    def _setup_dotnet_environment(self, project_context: Dict[str, Any], 
                                 force_reinstall: bool = False) -> List[SetupResult]:
        """Set up .NET environment and restore packages."""
        results = []
        
        # Check for .NET project files
        csproj_files = list(self.workspace_dir.glob("**/*.csproj"))
        sln_files = list(self.workspace_dir.glob("**/*.sln"))
        
        if not csproj_files and not sln_files:
            results.append(SetupResult(
                operation=".NET Dependencies",
                status=SetupStatus.SKIPPED,
                details="No .NET project files found",
                execution_time=0
            ))
            return results
        
        start_time = time.time()
        try:
            print("📦 Restoring .NET packages...")
            result = subprocess.run(
                ["dotnet", "restore"],
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            execution_time = time.time() - start_time
            
            if result.returncode == 0:
                results.append(SetupResult(
                    operation=".NET Dependencies",
                    status=SetupStatus.SUCCESS,
                    details=".NET packages restored",
                    execution_time=execution_time
                ))
            else:
                results.append(SetupResult(
                    operation=".NET Dependencies",
                    status=SetupStatus.FAILED,
                    details="Failed to restore .NET packages",
                    execution_time=execution_time,
                    error_message=result.stderr
                ))
        
        except Exception as e:
            results.append(SetupResult(
                operation=".NET Dependencies",
                status=SetupStatus.FAILED,
                details="Error restoring .NET packages",
                execution_time=time.time() - start_time,
                error_message=str(e)
            ))
        
        return results
    
    def _setup_testing_environment(self, project_context: Dict[str, Any]) -> List[SetupResult]:
        """Set up testing environment."""
        results = []
        testing_framework = project_context.get("testing_framework")
        
        if not testing_framework:
            return results
        
        # Testing frameworks are usually installed with project dependencies
        # Just verify they're available
        test_commands = {
            "Jest": ["npx", "jest", "--version"],
            "pytest": ["pytest", "--version"],
            "Vitest": ["npx", "vitest", "--version"]
        }
        
        if testing_framework in test_commands:
            start_time = time.time()
            try:
                result = subprocess.run(
                    test_commands[testing_framework],
                    cwd=self.workspace_dir,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                execution_time = time.time() - start_time
                
                if result.returncode == 0:
                    results.append(SetupResult(
                        operation=f"Testing: {testing_framework}",
                        status=SetupStatus.SUCCESS,
                        details=f"{testing_framework} is available",
                        execution_time=execution_time
                    ))
                else:
                    results.append(SetupResult(
                        operation=f"Testing: {testing_framework}",
                        status=SetupStatus.FAILED,
                        details=f"{testing_framework} not available",
                        execution_time=execution_time,
                        error_message=result.stderr
                    ))
            
            except Exception as e:
                results.append(SetupResult(
                    operation=f"Testing: {testing_framework}",
                    status=SetupStatus.FAILED,
                    details=f"Error checking {testing_framework}",
                    execution_time=time.time() - start_time,
                    error_message=str(e)
                ))
        
        return results
    
    def _setup_code_quality_tools(self, project_context: Dict[str, Any]) -> List[SetupResult]:
        """Set up code quality tools."""
        results = []
        platforms = project_context.get("platforms", [])
        
        # JavaScript/TypeScript code quality tools
        if "Node.js" in platforms:
            tools = ["eslint", "prettier"]
            for tool in tools:
                start_time = time.time()
                try:
                    result = subprocess.run(
                        ["npx", tool, "--version"],
                        cwd=self.workspace_dir,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    execution_time = time.time() - start_time
                    
                    if result.returncode == 0:
                        results.append(SetupResult(
                            operation=f"Code Quality: {tool}",
                            status=SetupStatus.SUCCESS,
                            details=f"{tool} is available",
                            execution_time=execution_time
                        ))
                    else:
                        results.append(SetupResult(
                            operation=f"Code Quality: {tool}",
                            status=SetupStatus.SKIPPED,
                            details=f"{tool} not available (optional)",
                            execution_time=execution_time
                        ))
                
                except Exception:
                    results.append(SetupResult(
                        operation=f"Code Quality: {tool}",
                        status=SetupStatus.SKIPPED,
                        details=f"Could not check {tool} availability",
                        execution_time=time.time() - start_time
                    ))
        
        return results
    
    def run_project_build(self, project_context: Dict[str, Any]) -> List[SetupResult]:
        """Run project build if applicable."""
        results = []
        platforms = project_context.get("platforms", [])
        
        # Node.js build
        if "Node.js" in platforms:
            package_json = self.workspace_dir / "package.json"
            if package_json.exists():
                try:
                    with open(package_json, 'r') as f:
                        package_data = json.load(f)
                    
                    scripts = package_data.get("scripts", {})
                    if "build" in scripts:
                        results.extend(self._run_npm_build(project_context))
                except Exception:
                    pass
        
        # .NET build
        if ".NET" in platforms:
            results.extend(self._run_dotnet_build())
        
        return results
    
    def _run_npm_build(self, project_context: Dict[str, Any]) -> List[SetupResult]:
        """Run npm build."""
        start_time = time.time()
        package_manager = project_context.get("package_manager", "npm")
        
        build_commands = {
            "npm": ["npm", "run", "build"],
            "yarn": ["yarn", "build"],
            "pnpm": ["pnpm", "build"]
        }
        
        cmd = build_commands.get(package_manager, ["npm", "run", "build"])
        
        try:
            print(f"🔨 Running build with {package_manager}...")
            result = subprocess.run(
                cmd,
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            execution_time = time.time() - start_time
            
            if result.returncode == 0:
                return [SetupResult(
                    operation="Project Build",
                    status=SetupStatus.SUCCESS,
                    details=f"Build completed with {package_manager}",
                    execution_time=execution_time
                )]
            else:
                return [SetupResult(
                    operation="Project Build",
                    status=SetupStatus.FAILED,
                    details=f"Build failed with {package_manager}",
                    execution_time=execution_time,
                    error_message=result.stderr
                )]
        
        except Exception as e:
            return [SetupResult(
                operation="Project Build",
                status=SetupStatus.FAILED,
                details="Error during build",
                execution_time=time.time() - start_time,
                error_message=str(e)
            )]
    
    def _run_dotnet_build(self) -> List[SetupResult]:
        """Run dotnet build."""
        start_time = time.time()
        try:
            print("🔨 Running .NET build...")
            result = subprocess.run(
                ["dotnet", "build"],
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            execution_time = time.time() - start_time
            
            if result.returncode == 0:
                return [SetupResult(
                    operation=".NET Build",
                    status=SetupStatus.SUCCESS,
                    details=".NET build completed",
                    execution_time=execution_time
                )]
            else:
                return [SetupResult(
                    operation=".NET Build",
                    status=SetupStatus.FAILED,
                    details=".NET build failed",
                    execution_time=execution_time,
                    error_message=result.stderr
                )]
        
        except Exception as e:
            return [SetupResult(
                operation=".NET Build",
                status=SetupStatus.FAILED,
                details="Error during .NET build",
                execution_time=time.time() - start_time,
                error_message=str(e)
            )]
    
    def load_setup_cache(self):
        """Load setup cache from disk."""
        try:
            if self.setup_cache_file.exists():
                with open(self.setup_cache_file, 'r') as f:
                    self.setup_cache = json.load(f)
        except Exception:
            self.setup_cache = {}
    
    def save_setup_cache(self):
        """Save setup cache to disk."""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            with open(self.setup_cache_file, 'w') as f:
                json.dump(self.setup_cache, f, indent=2)
        except Exception:
            pass
    
    def _update_setup_cache(self, results: List[SetupResult]):
        """Update setup cache with successful operations."""
        for result in results:
            if result.status == SetupStatus.SUCCESS:
                cache_key = f"{result.operation.lower().replace(' ', '_')}_{int(time.time() // 3600)}"  # Hour-based cache
                self.setup_cache[cache_key] = True
        
        self.save_setup_cache()
    
    def generate_setup_report(self, results: List[SetupResult]) -> str:
        """Generate a detailed setup report."""
        report = [
            "🛠️ Environment Setup Report",
            "=" * 50,
            f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]
        
        # Categorize results
        successful = [r for r in results if r.status == SetupStatus.SUCCESS]
        failed = [r for r in results if r.status == SetupStatus.FAILED]
        skipped = [r for r in results if r.status == SetupStatus.SKIPPED]
        
        # Summary
        total_time = sum(r.execution_time for r in results)
        report.append(f"📊 Summary:")
        report.append(f"  • Total operations: {len(results)}")
        report.append(f"  • Successful: {len(successful)}")
        report.append(f"  • Failed: {len(failed)}")
        report.append(f"  • Skipped: {len(skipped)}")
        report.append(f"  • Total execution time: {total_time:.2f}s")
        report.append("")
        
        # Successful operations
        if successful:
            report.append(f"✅ Successful Operations ({len(successful)}):")
            for result in successful:
                report.append(f"  • {result.operation} ({result.execution_time:.2f}s)")
                report.append(f"    {result.details}")
            report.append("")
        
        # Failed operations
        if failed:
            report.append(f"❌ Failed Operations ({len(failed)}):")
            for result in failed:
                report.append(f"  • {result.operation} ({result.execution_time:.2f}s)")
                report.append(f"    {result.details}")
                if result.error_message:
                    report.append(f"    Error: {result.error_message}")
            report.append("")
        
        # Skipped operations
        if skipped:
            report.append(f"⏭️ Skipped Operations ({len(skipped)}):")
            for result in skipped:
                report.append(f"  • {result.operation}")
                report.append(f"    {result.details}")
            report.append("")
        
        # Overall assessment
        if not failed:
            report.append("🎉 Environment setup completed successfully!")
        elif len(failed) < len(successful):
            report.append("⚠️ Environment setup completed with some issues.")
        else:
            report.append("💥 Environment setup failed - multiple critical issues.")
        
        return "\\n".join(report)

def create_environment_manager(workspace_dir="/workspace", data_dir="/bot/data") -> EnvironmentManager:
    """Factory function to create an environment manager."""
    return EnvironmentManager(workspace_dir, data_dir)

if __name__ == "__main__":
    # Test the environment manager
    manager = EnvironmentManager("/tmp/test_workspace", "/tmp/test_data")
    
    # Mock project context
    project_context = {
        "platforms": ["Node.js"],
        "package_manager": "npm",
        "testing_framework": "Jest"
    }
    
    print("🛠️ Setting up environment...")
    results = manager.setup_project_environment(project_context)
    
    print(manager.generate_setup_report(results))