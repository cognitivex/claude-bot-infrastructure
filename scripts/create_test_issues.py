#!/usr/bin/env python3
"""
Test Issue Generator for Claude Bot
Creates standardized test issues for validating bot functionality
"""

import os
import sys
import json
import subprocess
import argparse
from datetime import datetime

class TestIssueGenerator:
    def __init__(self, repo, label="claude-bot-test"):
        self.repo = repo
        self.label = label
        
    def create_issue(self, title, body, labels=None):
        """Create a GitHub issue using gh CLI"""
        if labels is None:
            labels = [self.label]
        else:
            labels = [self.label] + labels
            
        cmd = [
            "gh", "issue", "create",
            "--repo", self.repo,
            "--title", title,
            "--body", body,
            "--label", ",".join(labels)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            issue_url = result.stdout.strip()
            print(f"✅ Created issue: {issue_url}")
            return issue_url
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create issue: {e.stderr}")
            return None
    
    def generate_nodejs_test_issues(self):
        """Generate test issues for Node.js project"""
        issues = []
        
        # Issue 1: Add new function
        title = "Add division function to calculator"
        body = """
Please add a division function to the calculator API.

## Requirements
- Add `divide(a, b)` function to index.js
- Add GET endpoint `/divide/:a/:b` 
- Include division by zero error handling
- Add unit tests for the division function
- Update README with new endpoint documentation

## Acceptance Criteria
- [ ] Division function implemented
- [ ] API endpoint works correctly
- [ ] Error handling for division by zero
- [ ] Tests pass
- [ ] Documentation updated
"""
        issues.append(("nodejs", title, body, ["enhancement"]))
        
        # Issue 2: Fix bug
        title = "Fix multiplication function bug"
        body = """
There's a bug in the multiplication function where it doesn't handle negative numbers correctly.

## Current Behavior
Multiplication with negative numbers returns incorrect results

## Expected Behavior  
Multiplication should work correctly with negative numbers

## Steps to Fix
- Review multiplication function implementation
- Add proper handling for negative numbers
- Add test cases for negative number multiplication
- Verify all existing tests still pass
"""
        issues.append(("nodejs", title, body, ["bug"]))
        
        # Issue 3: Add validation
        title = "Add input validation to API endpoints"
        body = """
Add input validation to all calculator API endpoints to improve error handling.

## Requirements
- Validate that inputs are valid numbers
- Return appropriate error messages for invalid inputs
- Add middleware for validation
- Update tests to cover validation scenarios

## Implementation Details
- Check for NaN values
- Handle empty parameters
- Return 400 status for invalid inputs
- Include helpful error messages
"""
        issues.append(("nodejs", title, body, ["enhancement", "security"]))
        
        return issues
    
    def generate_dotnet_test_issues(self):
        """Generate test issues for .NET project"""
        issues = []
        
        # Issue 1: Add new controller
        title = "Add health check endpoint"
        body = """
Add a health check endpoint to the API for monitoring purposes.

## Requirements
- Create HealthController with GET /api/health endpoint
- Return system status information
- Include .NET version, Node.js version, and uptime
- Add unit tests for health controller
- Update Swagger documentation

## Response Format
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "version": "1.0.0",
  "environment": "Development",
  "dotnetVersion": "8.0",
  "nodeVersion": "10.13"
}
```
"""
        issues.append(("dotnet", title, body, ["enhancement"]))
        
        # Issue 2: Add Entity Framework
        title = "Add database support with Entity Framework"
        body = """
Add Entity Framework Core support for persisting calculation history.

## Requirements
- Add Entity Framework Core packages
- Create CalculationHistory entity
- Create ApplicationDbContext
- Add migration for initial database schema
- Update calculator endpoints to save history
- Add endpoint to retrieve calculation history

## Entity Structure
- Id (int, primary key)
- Operation (string)
- OperandA (double)
- OperandB (double)  
- Result (double)
- Timestamp (DateTime)
"""
        issues.append(("dotnet", title, body, ["enhancement", "database"]))
        
        # Issue 3: Improve frontend
        title = "Update frontend build process"
        body = """
Improve the Node.js 10.13 frontend build process and add more interactive features.

## Requirements
- Enhance npm build script
- Add CSS minification
- Create interactive calculator UI
- Ensure Node.js 10.13 compatibility
- Add error handling in frontend JavaScript
- Update package.json with proper dependencies

## Frontend Features
- HTML form for calculator operations
- Real-time result display
- Error message handling
- Responsive design
"""
        issues.append(("dotnet", title, body, ["enhancement", "frontend"]))
        
        return issues
    
    def generate_all_test_issues(self, project_type="both"):
        """Generate all test issues for specified project type"""
        all_issues = []
        
        if project_type in ["nodejs", "both"]:
            all_issues.extend(self.generate_nodejs_test_issues())
            
        if project_type in ["dotnet", "both"]:
            all_issues.extend(self.generate_dotnet_test_issues())
            
        return all_issues
    
    def create_test_suite(self, project_type="both", dry_run=False):
        """Create a complete test suite of issues"""
        print(f"🧪 Generating test issues for {project_type} project(s)")
        print(f"📁 Repository: {self.repo}")
        print(f"🏷️  Label: {self.label}")
        
        if dry_run:
            print("🔍 DRY RUN MODE - No issues will be created")
        
        issues = self.generate_all_test_issues(project_type)
        created_issues = []
        
        for project, title, body, labels in issues:
            print(f"\n📝 [{project.upper()}] {title}")
            
            if dry_run:
                print("   (Would create issue with labels: {})".format(", ".join([self.label] + labels)))
            else:
                issue_url = self.create_issue(title, body, labels)
                if issue_url:
                    created_issues.append({
                        "project": project,
                        "title": title,
                        "url": issue_url,
                        "labels": [self.label] + labels
                    })
        
        if not dry_run and created_issues:
            # Save created issues to file for reference
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test-issues-{timestamp}.json"
            
            with open(filename, 'w') as f:
                json.dump(created_issues, f, indent=2)
            
            print(f"\n✅ Created {len(created_issues)} test issues")
            print(f"📄 Issue details saved to: {filename}")
        
        return created_issues

def main():
    parser = argparse.ArgumentParser(description="Generate test issues for Claude Bot")
    parser.add_argument("repo", help="GitHub repository (owner/repo format)")
    parser.add_argument("--label", default="claude-bot-test", help="Label for test issues")
    parser.add_argument("--type", choices=["nodejs", "dotnet", "both"], default="both", 
                       help="Project type to generate issues for")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be created without creating issues")
    
    args = parser.parse_args()
    
    # Check if gh CLI is available
    try:
        subprocess.run(["gh", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ GitHub CLI (gh) is not installed or not in PATH")
        print("   Install from: https://cli.github.com/")
        sys.exit(1)
    
    # Check if authenticated
    try:
        subprocess.run(["gh", "auth", "status"], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        print("❌ Not authenticated with GitHub CLI")
        print("   Run: gh auth login")
        sys.exit(1)
    
    generator = TestIssueGenerator(args.repo, args.label)
    generator.create_test_suite(args.type, args.dry_run)

if __name__ == "__main__":
    main()