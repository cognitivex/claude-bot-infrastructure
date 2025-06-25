#!/usr/bin/env python3
"""
Test script for Phase 3 error handling enhancements
Tests retry logic, circuit breakers, logging, and edge cases
"""

import sys
import os
import json
import tempfile
import time
from pathlib import Path

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from utils import (
        retry_with_backoff, safe_request, api_retry,
        get_logger, correlation_context, RetryError,
        github_circuit_breaker, web_dashboard_circuit_breaker
    )
    from status_reporter import StatusReporter
    utils_available = True
except ImportError as e:
    print(f"Utils not available: {e}")
    utils_available = False

def test_retry_mechanism():
    """Test retry mechanism with exponential backoff"""
    print("🧪 Testing retry mechanism...")
    
    if not utils_available:
        print("❌ Utils not available, skipping retry test")
        return False
    
    @retry_with_backoff(max_attempts=3, base_delay=0.1)
    def failing_function():
        print("  Attempting function call...")
        raise ConnectionError("Test connection error")
    
    try:
        failing_function()
        print("❌ Should have failed")
        return False
    except RetryError as e:
        print(f"✅ Retry mechanism worked: {e}")
        return True
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_circuit_breaker():
    """Test circuit breaker functionality"""
    print("🧪 Testing circuit breaker...")
    
    if not utils_available:
        print("❌ Utils not available, skipping circuit breaker test")
        return False
    
    from utils.retry_handler import CircuitBreaker
    
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
    
    @cb
    def test_function():
        raise Exception("Test failure")
    
    # Test failures to trip circuit breaker
    for i in range(3):
        try:
            test_function()
        except Exception:
            pass
    
    # Circuit breaker should be open now
    try:
        test_function()
        print("❌ Circuit breaker should be open")
        return False
    except Exception as e:
        if "Circuit breaker" in str(e):
            print("✅ Circuit breaker opened successfully")
            return True
        else:
            print(f"❌ Unexpected error: {e}")
            return False

def test_logging_with_correlation():
    """Test logging with correlation IDs"""
    print("🧪 Testing logging with correlation IDs...")
    
    if not utils_available:
        print("❌ Utils not available, skipping logging test")
        return False
    
    logger = get_logger("test-logger")
    
    with correlation_context("test-123"):
        logger.info("Test message with correlation ID")
        print("✅ Logging with correlation ID works")
        return True

def test_status_reporter_edge_cases():
    """Test status reporter with various edge cases"""
    print("🧪 Testing status reporter edge cases...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        data_dir = Path(temp_dir) / "bot_data"
        
        # Create test reporter
        reporter = StatusReporter(
            bot_id="test-bot",
            data_dir=str(data_dir),
            status_web_url="http://nonexistent:9999"
        )
        
        # Test with empty directories
        print("  Testing with empty directories...")
        status = reporter.collect_bot_status()
        
        if status.get('bot_id') == 'test-bot':
            print("  ✅ Empty directory handling works")
        else:
            print("  ❌ Empty directory handling failed")
            return False
        
        # Test with invalid JSON files
        print("  Testing with invalid JSON files...")
        queue_dir = data_dir / "queue"
        queue_dir.mkdir(parents=True, exist_ok=True)
        
        # Create invalid JSON file
        invalid_file = queue_dir / "invalid.json"
        invalid_file.write_text("{ invalid json")
        
        # Create empty file
        empty_file = queue_dir / "empty.json"
        empty_file.write_text("")
        
        status = reporter.collect_bot_status()
        
        if status.get('queued_tasks') == 0:
            print("  ✅ Invalid JSON handling works")
        else:
            print("  ❌ Invalid JSON handling failed")
            return False
        
        # Test fallback status creation
        print("  Testing fallback status...")
        try:
            # Force an error in status collection
            original_method = reporter.collect_bot_status
            def error_method():
                raise Exception("Test error")
            reporter.collect_bot_status = error_method
            
            fallback_status = reporter.generate_and_publish()
            
            if fallback_status.get('fallback') and fallback_status.get('status') == 'error':
                print("  ✅ Fallback status creation works")
                return True
            else:
                print("  ❌ Fallback status creation failed")
                return False
                
        except Exception as e:
            print(f"  ❌ Error in fallback test: {e}")
            return False

def test_safe_json_loading():
    """Test safe JSON loading with various edge cases"""
    print("🧪 Testing safe JSON loading...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test reporter
        reporter = StatusReporter("test", str(temp_path))
        
        # Test non-existent file
        result = reporter._safe_json_load(temp_path / "nonexistent.json")
        if result == {}:
            print("  ✅ Non-existent file handling works")
        else:
            print("  ❌ Non-existent file handling failed")
            return False
        
        # Test empty file
        empty_file = temp_path / "empty.json"
        empty_file.write_text("")
        result = reporter._safe_json_load(empty_file)
        if result == {}:
            print("  ✅ Empty file handling works")
        else:
            print("  ❌ Empty file handling failed")
            return False
        
        # Test invalid JSON
        invalid_file = temp_path / "invalid.json"
        invalid_file.write_text("{ invalid")
        result = reporter._safe_json_load(invalid_file)
        if "error" in result:
            print("  ✅ Invalid JSON handling works")
        else:
            print("  ❌ Invalid JSON handling failed")
            return False
        
        # Test valid JSON
        valid_file = temp_path / "valid.json"
        valid_file.write_text('{"test": "data"}')
        result = reporter._safe_json_load(valid_file)
        if result.get("test") == "data":
            print("  ✅ Valid JSON handling works")
            return True
        else:
            print("  ❌ Valid JSON handling failed")
            return False

def main():
    """Run all error handling tests"""
    print("🚀 Starting Phase 3 Error Handling Tests\n")
    
    tests = [
        ("Retry Mechanism", test_retry_mechanism),
        ("Circuit Breaker", test_circuit_breaker), 
        ("Logging with Correlation", test_logging_with_correlation),
        ("Status Reporter Edge Cases", test_status_reporter_edge_cases),
        ("Safe JSON Loading", test_safe_json_loading)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print(f"{'='*50}")
        
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*50}")
    print("TEST SUMMARY")
    print(f"{'='*50}")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(results)} tests")
    
    if passed == len(results):
        print("🎉 All Phase 3 error handling tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed. Check implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())