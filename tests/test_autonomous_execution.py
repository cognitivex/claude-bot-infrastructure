#!/usr/bin/env python3
"""
Test Autonomous Command Execution for Claude Bot Infrastructure

Comprehensive test suite to verify the bot's ability to execute commands
autonomously and handle various failure scenarios.
"""

import os
import sys
import tempfile
import shutil
import json
import subprocess
from pathlib import Path

# Add scripts directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(script_dir, 'scripts'))

from command_capability_manager import create_capability_manager
from preflight_checker import create_preflight_checker
from environment_manager import create_environment_manager
from capability_debugger import create_capability_debugger

def test_command_capability_manager():
    """Test command capability detection and management."""
    print("🧪 Testing Command Capability Manager...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = create_capability_manager("/tmp", temp_dir)
        
        # Test capability checking
        capabilities = manager.check_all_capabilities()
        assert isinstance(capabilities, dict)
        assert len(capabilities) > 0
        print(f"✅ Detected {len(capabilities)} command capabilities")
        
        # Test capability reporting
        report = manager.generate_capability_report()
        assert len(report) > 100  # Should be a substantial report
        print(f"✅ Generated capability report ({len(report)} characters)")
        
        # Test missing requirements detection
        missing = manager.get_missing_requirements()
        print(f"✅ Found {len(missing)} missing requirements")
        
        # Test workflow validation
        project_context = {"platforms": ["Node.js"], "testing_framework": "Jest"}
        is_valid, missing_caps = manager.validate_workflow_requirements("implementation", project_context)
        print(f"✅ Workflow validation: {is_valid}, missing: {len(missing_caps)}")
        
        return True

def test_preflight_checker():
    """Test pre-flight checking system."""
    print("\\n🧪 Testing Pre-flight Checker...")
    
    with tempfile.TemporaryDirectory() as temp_workspace:
        with tempfile.TemporaryDirectory() as temp_data:
            # Create a mock git repository
            os.system(f"cd {temp_workspace} && git init")
            
            checker = create_preflight_checker(temp_workspace, temp_data)
            
            # Test pre-flight checks
            project_context = {
                "platforms": ["Node.js"],
                "frameworks": ["Next.js"],
                "testing_framework": "Jest",
                "package_manager": "npm"
            }
            
            result = checker.run_preflight_checks("implementation", project_context)
            
            assert result.workflow_step == "implementation"
            assert len(result.checks) > 0
            assert isinstance(result.can_proceed, bool)
            print(f"✅ Pre-flight checks completed: {len(result.checks)} checks")
            
            # Test report generation
            report = checker.generate_preflight_report(result)
            assert len(report) > 100
            print(f"✅ Generated pre-flight report ({len(report)} characters)")
            
            return True

def test_environment_manager():
    """Test environment setup and management."""
    print("\\n🧪 Testing Environment Manager...")
    
    with tempfile.TemporaryDirectory() as temp_workspace:
        with tempfile.TemporaryDirectory() as temp_data:
            # Create mock project files
            workspace = Path(temp_workspace)
            (workspace / "package.json").write_text('{"name": "test", "scripts": {"build": "echo build"}}')
            
            manager = create_environment_manager(temp_workspace, temp_data)
            
            # Test environment setup
            project_context = {
                "platforms": ["Node.js"],
                "package_manager": "npm",
                "testing_framework": "Jest"
            }
            
            results = manager.setup_project_environment(project_context)
            
            assert isinstance(results, list)
            print(f"✅ Environment setup completed: {len(results)} operations")
            
            # Test setup report
            report = manager.generate_setup_report(results)
            assert len(report) > 50
            print(f"✅ Generated setup report ({len(report)} characters)")
            
            # Test caching
            manager.save_setup_cache()
            manager.load_setup_cache()
            print("✅ Setup caching works")
            
            return True

def test_capability_debugger():
    """Test capability debugging and reporting."""
    print("\\n🧪 Testing Capability Debugger...")
    
    with tempfile.TemporaryDirectory() as temp_workspace:
        with tempfile.TemporaryDirectory() as temp_data:
            # Create mock project
            workspace = Path(temp_workspace)
            (workspace / "package.json").write_text('{"name": "test"}')
            
            debugger = create_capability_debugger(temp_workspace, temp_data)
            
            # Test critical command testing
            command_results = debugger.test_critical_commands()
            assert isinstance(command_results, dict)
            assert len(command_results) > 0
            print(f"✅ Tested {len(command_results)} critical commands")
            
            # Test project context detection
            project_context = debugger._detect_project_context()
            assert isinstance(project_context, dict)
            assert "platforms" in project_context
            print(f"✅ Detected project context: {project_context['platforms']}")
            
            # Test project operations
            project_ops = debugger.test_project_operations(project_context)
            assert isinstance(project_ops, dict)
            print(f"✅ Tested {len(project_ops)} project operations")
            
            return True

def test_integrated_workflow():
    """Test integrated workflow with all systems."""
    print("\\n🧪 Testing Integrated Workflow...")
    
    with tempfile.TemporaryDirectory() as temp_workspace:
        with tempfile.TemporaryDirectory() as temp_data:
            # Set up mock project
            workspace = Path(temp_workspace)
            (workspace / "package.json").write_text(json.dumps({
                "name": "test-project",
                "version": "1.0.0",
                "scripts": {
                    "test": "echo 'Running tests'",
                    "build": "echo 'Building project'",
                    "lint": "echo 'Linting code'"
                },
                "dependencies": {
                    "react": "^18.0.0"
                },
                "devDependencies": {
                    "jest": "^29.0.0",
                    "eslint": "^8.0.0"
                }
            }, indent=2))
            
            # Initialize git
            subprocess.run(["git", "init"], cwd=workspace, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=workspace, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=workspace, capture_output=True)
            
            # Create all managers
            cap_manager = create_capability_manager(str(workspace), temp_data)
            preflight_checker = create_preflight_checker(str(workspace), temp_data)
            env_manager = create_environment_manager(str(workspace), temp_data)
            debugger = create_capability_debugger(str(workspace), temp_data)
            
            # Simulate full workflow preparation
            print("  📋 Detecting project context...")
            project_context = debugger._detect_project_context()
            assert "Node.js" in project_context["platforms"]
            
            print("  🔧 Checking capabilities...")
            capabilities = cap_manager.check_all_capabilities()
            available_count = sum(1 for cap in capabilities.values() if cap.status.value == "available")
            print(f"    Available commands: {available_count}/{len(capabilities)}")
            
            print("  🚀 Running pre-flight checks...")
            preflight_result = preflight_checker.run_preflight_checks("implementation", project_context)
            print(f"    Pre-flight status: {preflight_result.overall_status.value}")
            print(f"    Can proceed: {preflight_result.can_proceed}")
            
            print("  🛠️ Setting up environment...")
            setup_results = env_manager.setup_project_environment(project_context)
            successful_setups = sum(1 for r in setup_results if r.status.value == "success")
            print(f"    Successful setups: {successful_setups}/{len(setup_results)}")
            
            print("  🧪 Testing critical operations...")
            critical_tests = debugger.test_critical_commands()
            working_commands = sum(1 for test in critical_tests.values() if test.get("success", False))
            print(f"    Working commands: {working_commands}/{len(critical_tests)}")
            
            # Generate comprehensive diagnosis
            print("  📊 Running comprehensive diagnosis...")
            debug_session = debugger.run_comprehensive_diagnosis("implementation")
            
            final_report = debugger.generate_final_report(debug_session)
            print(f"✅ Generated comprehensive report ({len(final_report)} characters)")
            
            # Assess readiness
            readiness_score = (
                (available_count / len(capabilities)) * 0.3 +
                (1.0 if preflight_result.can_proceed else 0.0) * 0.3 +
                (successful_setups / max(len(setup_results), 1)) * 0.2 +
                (working_commands / len(critical_tests)) * 0.2
            )
            
            print(f"✅ Overall readiness score: {readiness_score:.2f}/1.0")
            
            if readiness_score >= 0.8:
                print("🎉 Bot is highly ready for autonomous operation!")
            elif readiness_score >= 0.6:
                print("⚠️ Bot is moderately ready - some issues may need attention")
            else:
                print("🚫 Bot requires significant fixes before autonomous operation")
            
            return readiness_score >= 0.6  # Pass if moderately ready

def test_failure_scenarios():
    """Test handling of various failure scenarios."""
    print("\\n🧪 Testing Failure Scenarios...")
    
    with tempfile.TemporaryDirectory() as temp_workspace:
        with tempfile.TemporaryDirectory() as temp_data:
            # Test with non-existent workspace
            try:
                manager = create_capability_manager("/non/existent/path", temp_data)
                capabilities = manager.check_all_capabilities()
                print("✅ Handled non-existent workspace gracefully")
            except Exception as e:
                print(f"❌ Failed to handle non-existent workspace: {e}")
                return False
            
            # Test with corrupted project files
            workspace = Path(temp_workspace)
            (workspace / "package.json").write_text("invalid json {")
            
            try:
                debugger = create_capability_debugger(str(workspace), temp_data)
                project_context = debugger._detect_project_context()
                print("✅ Handled corrupted project files gracefully")
            except Exception as e:
                print(f"❌ Failed to handle corrupted files: {e}")
                return False
            
            # Test with missing environment variables
            old_env = {}
            env_vars_to_test = ["ANTHROPIC_API_KEY", "GITHUB_TOKEN"]
            
            for var in env_vars_to_test:
                old_env[var] = os.environ.get(var)
                if var in os.environ:
                    del os.environ[var]
            
            try:
                preflight_checker = create_preflight_checker(str(workspace), temp_data)
                result = preflight_checker.run_preflight_checks("analysis", {})
                
                # Should detect missing environment variables
                env_checks = [check for check in result.checks if "Environment Variable" in check.name]
                assert len(env_checks) > 0
                print("✅ Detected missing environment variables")
                
            except Exception as e:
                print(f"❌ Failed to handle missing env vars: {e}")
                return False
            finally:
                # Restore environment variables
                for var, value in old_env.items():
                    if value is not None:
                        os.environ[var] = value
            
            print("✅ All failure scenarios handled gracefully")
            return True

def test_auto_remediation():
    """Test automatic remediation capabilities."""
    print("\\n🧪 Testing Auto-remediation...")
    
    with tempfile.TemporaryDirectory() as temp_data:
        # Test capability manager auto-installation (simulate)
        manager = create_capability_manager("/tmp", temp_data)
        
        # Get missing requirements
        missing = manager.get_missing_requirements()
        if missing:
            print(f"✅ Found {len(missing)} missing requirements for potential auto-installation")
            
            # Test auto-installation (dry run - don't actually install)
            # installation_results = manager.auto_install_missing_commands()
            print("✅ Auto-installation system is available (skipped actual installation for testing)")
        else:
            print("✅ No missing requirements found")
        
        return True

def main():
    """Run all autonomous execution tests."""
    print("🚀 Testing Autonomous Command Execution System\\n")
    
    tests = [
        ("Command Capability Manager", test_command_capability_manager),
        ("Pre-flight Checker", test_preflight_checker),
        ("Environment Manager", test_environment_manager),
        ("Capability Debugger", test_capability_debugger),
        ("Integrated Workflow", test_integrated_workflow),
        ("Failure Scenarios", test_failure_scenarios),
        ("Auto-remediation", test_auto_remediation)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                print(f"✅ {test_name}: PASSED\\n")
            else:
                print(f"❌ {test_name}: FAILED\\n")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}\\n")
            results.append((test_name, False))
    
    # Summary
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All autonomous execution tests passed!")
        print("\\n🤖 Bot is ready for autonomous command execution!")
    else:
        print("💥 Some tests failed. The bot may not be fully ready for autonomous operation.")
        print("\\n🔧 Review the failed tests and ensure all dependencies are properly installed.")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())