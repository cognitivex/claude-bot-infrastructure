#!/usr/bin/env python3
"""
Capability Debugger for Claude Bot Infrastructure

Provides debugging and reporting tools to diagnose command execution issues
and ensure the bot can operate autonomously.
"""

import os
import sys
import json
import subprocess
import time
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Add scripts directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from command_capability_manager import create_capability_manager
from preflight_checker import create_preflight_checker
from environment_manager import create_environment_manager

@dataclass
class DebugSession:
    """Represents a debugging session."""
    timestamp: str
    workspace_dir: str
    project_context: Dict[str, Any]
    capabilities: Dict[str, Any]
    preflight_results: Dict[str, Any]
    environment_setup: List[Any]
    recommendations: List[str]

class CapabilityDebugger:
    """Debugging and reporting tools for bot capabilities."""
    
    def __init__(self, workspace_dir="/workspace", data_dir="/bot/data"):
        self.workspace_dir = Path(workspace_dir)
        self.data_dir = Path(data_dir)
        
        # Initialize managers
        self.capability_manager = create_capability_manager(str(self.workspace_dir), str(self.data_dir))
        self.preflight_checker = create_preflight_checker(str(self.workspace_dir), str(self.data_dir))
        self.environment_manager = create_environment_manager(str(self.workspace_dir), str(self.data_dir))
        
        # Debug output directory
        self.debug_dir = self.data_dir / "debug"
        self.debug_dir.mkdir(parents=True, exist_ok=True)
    
    def run_comprehensive_diagnosis(self, workflow_step: str = "implementation") -> DebugSession:
        """Run a comprehensive diagnosis of bot capabilities."""
        print("🔍 Running comprehensive capability diagnosis...")
        
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        
        # 1. Detect project context
        print("\\n📋 Detecting project context...")
        project_context = self._detect_project_context()
        print(f"Detected platforms: {project_context.get('platforms', [])}")
        print(f"Package manager: {project_context.get('package_manager', 'none')}")
        print(f"Testing framework: {project_context.get('testing_framework', 'none')}")
        
        # 2. Check all capabilities
        print("\\n🔧 Checking command capabilities...")
        capabilities = self.capability_manager.check_all_capabilities()
        capability_report = self.capability_manager.generate_capability_report()
        print(capability_report)
        
        # 3. Run pre-flight checks
        print(f"\\n🚀 Running pre-flight checks for {workflow_step}...")
        preflight_result = self.preflight_checker.run_preflight_checks(workflow_step, project_context)
        preflight_report = self.preflight_checker.generate_preflight_report(preflight_result)
        print(preflight_report)
        
        # 4. Set up environment
        print("\\n🛠️ Testing environment setup...")
        setup_results = self.environment_manager.setup_project_environment(project_context)
        setup_report = self.environment_manager.generate_setup_report(setup_results)
        print(setup_report)
        
        # 5. Generate recommendations
        recommendations = self._generate_comprehensive_recommendations(
            capabilities, preflight_result, setup_results, project_context
        )
        
        # Create debug session
        debug_session = DebugSession(
            timestamp=timestamp,
            workspace_dir=str(self.workspace_dir),
            project_context=project_context,
            capabilities={name: self._capability_to_dict(cap) for name, cap in capabilities.items()},
            preflight_results=self._preflight_result_to_dict(preflight_result),
            environment_setup=[self._setup_result_to_dict(r) for r in setup_results],
            recommendations=recommendations
        )
        
        # Save debug session
        self._save_debug_session(debug_session)
        
        return debug_session
    
    def test_critical_commands(self) -> Dict[str, Any]:
        """Test execution of critical commands."""
        print("🧪 Testing critical command execution...")
        
        critical_tests = {
            "git_version": ["git", "--version"],
            "git_status": ["git", "status"],
            "gh_auth": ["gh", "auth", "status"],
            "claude_version": ["claude-code", "--version"],
            "node_version": ["node", "--version"],
            "npm_version": ["npm", "--version"],
            "python_version": ["python3", "--version"],
            "pip_version": ["pip3", "--version"]
        }
        
        results = {}
        
        for test_name, command in critical_tests.items():
            print(f"  Testing {test_name}...")
            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=self.workspace_dir
                )
                
                results[test_name] = {
                    "success": result.returncode == 0,
                    "stdout": result.stdout.strip() if result.stdout else "",
                    "stderr": result.stderr.strip() if result.stderr else "",
                    "return_code": result.returncode
                }
                
                status = "✅" if result.returncode == 0 else "❌"
                print(f"    {status} {test_name}: {results[test_name]['stdout'][:50]}...")
                
            except subprocess.TimeoutExpired:
                results[test_name] = {
                    "success": False,
                    "error": "Command timed out"
                }
                print(f"    ⏰ {test_name}: Timed out")
            except FileNotFoundError:
                results[test_name] = {
                    "success": False,
                    "error": "Command not found"
                }
                print(f"    🔍 {test_name}: Command not found")
            except Exception as e:
                results[test_name] = {
                    "success": False,
                    "error": str(e)
                }
                print(f"    💥 {test_name}: Error - {str(e)}")
        
        return results
    
    def test_project_operations(self, project_context: Dict[str, Any]) -> Dict[str, Any]:
        """Test project-specific operations."""
        print("🏗️ Testing project operations...")
        
        operations = {}
        platforms = project_context.get("platforms", [])
        
        # Test Node.js operations
        if "Node.js" in platforms:
            operations.update(self._test_nodejs_operations(project_context))
        
        # Test Python operations
        if "Python" in platforms:
            operations.update(self._test_python_operations())
        
        # Test .NET operations
        if ".NET" in platforms:
            operations.update(self._test_dotnet_operations())
        
        # Test Git operations
        operations.update(self._test_git_operations())
        
        return operations
    
    def _test_nodejs_operations(self, project_context: Dict[str, Any]) -> Dict[str, Any]:
        """Test Node.js specific operations."""
        operations = {}
        package_manager = project_context.get("package_manager", "npm")
        
        # Test package manager
        try:
            result = subprocess.run(
                [package_manager, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=self.workspace_dir
            )
            operations["package_manager"] = {
                "success": result.returncode == 0,
                "details": f"{package_manager} version check",
                "output": result.stdout.strip()
            }
        except Exception as e:
            operations["package_manager"] = {
                "success": False,
                "details": f"{package_manager} test failed",
                "error": str(e)
            }
        
        # Test npm scripts (if package.json exists)
        package_json = self.workspace_dir / "package.json"
        if package_json.exists():
            try:
                with open(package_json, 'r') as f:
                    package_data = json.load(f)
                
                scripts = package_data.get("scripts", {})
                operations["npm_scripts"] = {
                    "success": True,
                    "details": f"Found {len(scripts)} npm scripts",
                    "scripts": list(scripts.keys())
                }
            except Exception as e:
                operations["npm_scripts"] = {
                    "success": False,
                    "details": "Failed to read package.json",
                    "error": str(e)
                }
        
        return operations
    
    def _test_python_operations(self) -> Dict[str, Any]:
        """Test Python specific operations."""
        operations = {}
        
        # Test pip list
        try:
            result = subprocess.run(
                ["pip3", "list"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.workspace_dir
            )
            operations["pip_list"] = {
                "success": result.returncode == 0,
                "details": "pip list execution",
                "package_count": len(result.stdout.strip().split("\\n")) - 2 if result.returncode == 0 else 0
            }
        except Exception as e:
            operations["pip_list"] = {
                "success": False,
                "details": "pip list failed",
                "error": str(e)
            }
        
        # Test Python import capabilities
        test_imports = ["json", "os", "sys", "subprocess", "pathlib"]
        successful_imports = 0
        
        for module in test_imports:
            try:
                result = subprocess.run(
                    ["python3", "-c", f"import {module}; print('OK')"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    successful_imports += 1
            except Exception:
                pass
        
        operations["python_imports"] = {
            "success": successful_imports == len(test_imports),
            "details": f"Python import test: {successful_imports}/{len(test_imports)}",
            "successful_imports": successful_imports
        }
        
        return operations
    
    def _test_dotnet_operations(self) -> Dict[str, Any]:
        """Test .NET specific operations."""
        operations = {}
        
        # Test dotnet --info
        try:
            result = subprocess.run(
                ["dotnet", "--info"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.workspace_dir
            )
            operations["dotnet_info"] = {
                "success": result.returncode == 0,
                "details": ".NET info command",
                "output": result.stdout.strip()[:200] + "..." if len(result.stdout) > 200 else result.stdout.strip()
            }
        except Exception as e:
            operations["dotnet_info"] = {
                "success": False,
                "details": ".NET info failed",
                "error": str(e)
            }
        
        return operations
    
    def _test_git_operations(self) -> Dict[str, Any]:
        """Test Git operations."""
        operations = {}
        
        # Test git config
        try:
            result = subprocess.run(
                ["git", "config", "--list"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=self.workspace_dir
            )
            operations["git_config"] = {
                "success": result.returncode == 0,
                "details": "Git configuration check",
                "config_count": len(result.stdout.strip().split("\\n")) if result.returncode == 0 else 0
            }
        except Exception as e:
            operations["git_config"] = {
                "success": False,
                "details": "Git config failed",
                "error": str(e)
            }
        
        # Test git branch
        try:
            result = subprocess.run(
                ["git", "branch"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=self.workspace_dir
            )
            operations["git_branch"] = {
                "success": result.returncode == 0,
                "details": "Git branch listing",
                "branches": result.stdout.strip().split("\\n") if result.returncode == 0 else []
            }
        except Exception as e:
            operations["git_branch"] = {
                "success": False,
                "details": "Git branch failed",
                "error": str(e)
            }
        
        return operations
    
    def _detect_project_context(self) -> Dict[str, Any]:
        """Detect project context for debugging."""
        context = {
            "platforms": [],
            "frameworks": [],
            "testing_framework": None,
            "package_manager": None,
            "build_system": None
        }
        
        try:
            # Check for project files
            files = list(self.workspace_dir.glob("*"))
            file_names = [f.name for f in files if f.is_file()]
            
            # Platform detection
            if "package.json" in file_names:
                context["platforms"].append("Node.js")
                context["package_manager"] = "npm"
            if "yarn.lock" in file_names:
                context["package_manager"] = "yarn"
            if "pnpm-lock.yaml" in file_names:
                context["package_manager"] = "pnpm"
            if any(f.endswith(".csproj") for f in file_names):
                context["platforms"].append(".NET")
            if "requirements.txt" in file_names or "pyproject.toml" in file_names:
                context["platforms"].append("Python")
            
            # Framework detection
            if "next.config.js" in file_names:
                context["frameworks"].append("Next.js")
            if "nuxt.config.js" in file_names:
                context["frameworks"].append("Nuxt.js")
            if "angular.json" in file_names:
                context["frameworks"].append("Angular")
                
        except Exception as e:
            print(f"Warning: Error detecting project context: {e}")
        
        return context
    
    def _generate_comprehensive_recommendations(self, capabilities, preflight_result, 
                                             setup_results, project_context) -> List[str]:
        """Generate comprehensive recommendations."""
        recommendations = []
        
        # Capability recommendations
        missing_caps = [cap for cap in capabilities.values() 
                       if cap.status.value != "available"]
        if missing_caps:
            recommendations.append("🔧 Command Issues:")
            for cap in missing_caps:
                if cap.requirement.install_cmd:
                    recommendations.append(f"  • Install {cap.requirement.name}: {cap.requirement.install_cmd}")
                else:
                    recommendations.append(f"  • Manually install {cap.requirement.name}")
        
        # Pre-flight recommendations
        if preflight_result.recommendations:
            recommendations.extend(preflight_result.recommendations)
        
        # Setup recommendations
        failed_setups = [r for r in setup_results if r.status.value == "failed"]
        if failed_setups:
            recommendations.append("🛠️ Environment Setup Issues:")
            for setup in failed_setups:
                recommendations.append(f"  • {setup.operation}: {setup.details}")
        
        # Project-specific recommendations
        platforms = project_context.get("platforms", [])
        if "Node.js" in platforms:
            package_json = self.workspace_dir / "package.json"
            if not package_json.exists():
                recommendations.append("📦 Consider creating package.json for Node.js project")
        
        if not recommendations:
            recommendations.append("✅ All systems operational - bot ready for autonomous operation")
        
        return recommendations
    
    def _save_debug_session(self, session: DebugSession):
        """Save debug session to file."""
        try:
            debug_file = self.debug_dir / f"debug_session_{session.timestamp}.json"
            
            session_data = {
                "timestamp": session.timestamp,
                "workspace_dir": session.workspace_dir,
                "project_context": session.project_context,
                "capabilities": session.capabilities,
                "preflight_results": session.preflight_results,
                "environment_setup": session.environment_setup,
                "recommendations": session.recommendations
            }
            
            with open(debug_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            
            print(f"\\n💾 Debug session saved to: {debug_file}")
            
        except Exception as e:
            print(f"Warning: Could not save debug session: {e}")
    
    def _capability_to_dict(self, capability) -> Dict[str, Any]:
        """Convert capability object to dictionary."""
        return {
            "name": capability.requirement.name,
            "command": capability.requirement.command,
            "status": capability.status.value,
            "current_version": capability.current_version,
            "path": capability.path,
            "error_message": capability.error_message,
            "last_checked": capability.last_checked
        }
    
    def _preflight_result_to_dict(self, result) -> Dict[str, Any]:
        """Convert preflight result to dictionary."""
        return {
            "workflow_step": result.workflow_step,
            "overall_status": result.overall_status.value,
            "can_proceed": result.can_proceed,
            "checks": [
                {
                    "name": check.name,
                    "description": check.description,
                    "status": check.status.value,
                    "details": check.details,
                    "critical": check.critical,
                    "remediation": check.remediation
                }
                for check in result.checks
            ],
            "recommendations": result.recommendations,
            "timestamp": result.timestamp
        }
    
    def _setup_result_to_dict(self, result) -> Dict[str, Any]:
        """Convert setup result to dictionary."""
        return {
            "operation": result.operation,
            "status": result.status.value,
            "details": result.details,
            "execution_time": result.execution_time,
            "error_message": result.error_message
        }
    
    def generate_final_report(self, session: DebugSession) -> str:
        """Generate a comprehensive final report."""
        report = [
            "🤖 Claude Bot Capability Diagnosis Report",
            "=" * 60,
            f"Timestamp: {session.timestamp}",
            f"Workspace: {session.workspace_dir}",
            "",
            "📋 Project Context:",
            f"  • Platforms: {', '.join(session.project_context.get('platforms', ['None']))}",
            f"  • Package Manager: {session.project_context.get('package_manager', 'None')}",
            f"  • Testing Framework: {session.project_context.get('testing_framework', 'None')}",
            "",
            "🔧 Command Capabilities:",
        ]
        
        # Capability summary
        available = sum(1 for cap in session.capabilities.values() if cap["status"] == "available")
        total = len(session.capabilities)
        report.append(f"  • Available: {available}/{total} ({(available/total*100):.1f}%)")
        
        missing = [cap for cap in session.capabilities.values() if cap["status"] != "available"]
        if missing:
            report.append(f"  • Missing/Issues: {len(missing)} commands")
            for cap in missing[:5]:  # Show first 5
                report.append(f"    - {cap['name']}: {cap['status']}")
        
        report.append("")
        
        # Pre-flight summary
        preflight = session.preflight_results
        report.extend([
            "🚀 Pre-flight Status:",
            f"  • Overall: {preflight['overall_status'].upper()}",
            f"  • Can Proceed: {'✅ YES' if preflight['can_proceed'] else '❌ NO'}",
            f"  • Checks: {len([c for c in preflight['checks'] if c['status'] == 'passed'])}/{len(preflight['checks'])} passed"
        ])
        
        report.append("")
        
        # Environment setup summary
        setup_results = session.environment_setup
        successful = sum(1 for r in setup_results if r["status"] == "success")
        failed = sum(1 for r in setup_results if r["status"] == "failed")
        
        report.extend([
            "🛠️ Environment Setup:",
            f"  • Successful: {successful}",
            f"  • Failed: {failed}",
            f"  • Total Time: {sum(r['execution_time'] for r in setup_results):.2f}s"
        ])
        
        report.append("")
        
        # Recommendations
        report.append("💡 Recommendations:")
        for rec in session.recommendations:
            report.append(f"  {rec}")
        
        report.append("")
        
        # Overall assessment
        if preflight["can_proceed"] and failed == 0:
            report.append("🎉 ASSESSMENT: Bot is ready for autonomous operation!")
        elif preflight["can_proceed"]:
            report.append("⚠️ ASSESSMENT: Bot can operate with minor issues.")
        else:
            report.append("🚫 ASSESSMENT: Bot requires fixes before autonomous operation.")
        
        return "\\n".join(report)

def create_capability_debugger(workspace_dir="/workspace", data_dir="/bot/data") -> CapabilityDebugger:
    """Factory function to create a capability debugger."""
    return CapabilityDebugger(workspace_dir, data_dir)

def main():
    """Main CLI interface for capability debugging."""
    parser = argparse.ArgumentParser(description="Claude Bot Capability Debugger")
    parser.add_argument("--workspace", default="/workspace", help="Workspace directory")
    parser.add_argument("--data", default="/bot/data", help="Data directory")
    parser.add_argument("--workflow-step", default="implementation", help="Workflow step to test")
    parser.add_argument("--test-commands", action="store_true", help="Test critical commands")
    parser.add_argument("--test-project", action="store_true", help="Test project operations")
    
    args = parser.parse_args()
    
    debugger = CapabilityDebugger(args.workspace, args.data)
    
    if args.test_commands:
        print("🧪 Testing critical commands...")
        results = debugger.test_critical_commands()
        print(f"\\nCommand test results: {json.dumps(results, indent=2)}")
        return
    
    if args.test_project:
        print("🏗️ Testing project operations...")
        project_context = debugger._detect_project_context()
        results = debugger.test_project_operations(project_context)
        print(f"\\nProject test results: {json.dumps(results, indent=2)}")
        return
    
    # Run comprehensive diagnosis
    session = debugger.run_comprehensive_diagnosis(args.workflow_step)
    
    # Generate and display final report
    final_report = debugger.generate_final_report(session)
    print("\\n" + final_report)

if __name__ == "__main__":
    main()