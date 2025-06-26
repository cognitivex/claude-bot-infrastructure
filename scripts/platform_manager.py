#!/usr/bin/env python3
"""
Platform Detection and Management System

This module provides intelligent platform detection, version resolution,
and runtime management for the Claude Bot Infrastructure.

Usage:
    python3 platform_manager.py --detect /workspace
    python3 platform_manager.py --validate "nodejs:18.16,dotnet:8.0"
    python3 platform_manager.py --generate-config /workspace --output platforms.detected.yml
"""

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import yaml
import subprocess

class PlatformManager:
    """Manages platform detection, validation, and configuration."""
    
    def __init__(self, config_path: str = "config/platforms.yml"):
        """Initialize platform manager with configuration."""
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.detected_platforms: Dict[str, str] = {}
        
    def _load_config(self) -> Dict[str, Any]:
        """Load platform configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading platform config: {e}", file=sys.stderr)
            return {"platforms": {}}
            
    def detect_platforms(self, workspace_path: str) -> Dict[str, str]:
        """
        Auto-detect platforms and versions from project structure.
        
        Args:
            workspace_path: Path to project workspace
            
        Returns:
            Dictionary mapping platform names to detected versions
        """
        workspace = Path(workspace_path)
        detected = {}
        
        if not workspace.exists() or not workspace.is_dir():
            print(f"Warning: Workspace path {workspace_path} does not exist", file=sys.stderr)
            return detected
            
        print(f"🔍 Scanning {workspace_path} for platforms...")
        
        # Node.js detection
        nodejs_version = self._detect_nodejs(workspace)
        if nodejs_version:
            detected['nodejs'] = nodejs_version
            print(f"  📦 Node.js {nodejs_version}")
            
        # .NET detection
        dotnet_version = self._detect_dotnet(workspace)
        if dotnet_version:
            detected['dotnet'] = dotnet_version
            print(f"  🔷 .NET {dotnet_version}")
            
        # Java detection
        java_version = self._detect_java(workspace)
        if java_version:
            detected['java'] = java_version
            print(f"  ☕ Java {java_version}")
            
        # Python detection
        python_version = self._detect_python(workspace)
        if python_version:
            detected['python'] = python_version
            print(f"  🐍 Python {python_version}")
            
        # Go detection
        go_version = self._detect_go(workspace)
        if go_version:
            detected['golang'] = go_version
            print(f"  🔵 Go {go_version}")
            
        # Rust detection
        rust_version = self._detect_rust(workspace)
        if rust_version:
            detected['rust'] = rust_version
            print(f"  🦀 Rust {rust_version}")
            
        # PHP detection
        php_version = self._detect_php(workspace)
        if php_version:
            detected['php'] = php_version
            print(f"  🐘 PHP {php_version}")
            
        # Ruby detection
        ruby_version = self._detect_ruby(workspace)
        if ruby_version:
            detected['ruby'] = ruby_version
            print(f"  💎 Ruby {ruby_version}")
            
        self.detected_platforms = detected
        return detected
        
    def _detect_nodejs(self, workspace: Path) -> Optional[str]:
        """Detect Node.js version from project files."""
        # Check for Node.js indicators
        indicators = ['package.json', 'yarn.lock', 'pnpm-lock.yaml', '.nvmrc', 'node_modules']
        if not any((workspace / indicator).exists() for indicator in indicators):
            return None
            
        # Try to get version from .nvmrc
        nvmrc = workspace / '.nvmrc'
        if nvmrc.exists():
            try:
                version = nvmrc.read_text().strip()
                if re.match(r'\\d+\\.\\d+(\\.\\d+)?', version):
                    return version
            except Exception:
                pass
                
        # Try to get version from package.json engines
        package_json = workspace / 'package.json'
        if package_json.exists():
            try:
                with open(package_json) as f:
                    data = json.load(f)
                
                engines = data.get('engines', {})
                node_version = engines.get('node', '')
                
                # Extract version number from requirement
                match = re.search(r'(\d+\.\d+\.\d+)', node_version)
                if match:
                    return match.group(1)
                    
                # Extract major.minor from requirement
                match = re.search(r'(\d+\.\d+)', node_version)
                if match:
                    major_minor = match.group(1)
                    # Find best patch version from our supported versions
                    supported = self.config['platforms'].get('nodejs', {}).get('supported_versions', [])
                    for version in supported:
                        if version.startswith(major_minor):
                            return version
            except Exception:
                pass
                
        # Default to LTS version
        return self.config['platforms'].get('nodejs', {}).get('default_version', '18.16.0')
        
    def _detect_dotnet(self, workspace: Path) -> Optional[str]:
        """Detect .NET version from project files."""
        # Check for .NET indicators
        csproj_files = list(workspace.glob('*.csproj'))
        sln_files = list(workspace.glob('*.sln'))
        fsproj_files = list(workspace.glob('*.fsproj'))
        
        if not (csproj_files or sln_files or fsproj_files or (workspace / 'global.json').exists()):
            return None
            
        # Try to get version from global.json
        global_json = workspace / 'global.json'
        if global_json.exists():
            try:
                with open(global_json) as f:
                    data = json.load(f)
                
                sdk_version = data.get('sdk', {}).get('version', '')
                if sdk_version:
                    # Extract major.minor
                    parts = sdk_version.split('.')
                    if len(parts) >= 2:
                        return f"{parts[0]}.{parts[1]}"
            except Exception:
                pass
                
        # Try to get version from project files
        for csproj in csproj_files[:5]:  # Check first 5 project files
            version = self._parse_dotnet_project_version(csproj)
            if version:
                return version
                
        # Default to latest version
        return self.config['platforms'].get('dotnet', {}).get('default_version', '8.0')
        
    def _parse_dotnet_project_version(self, csproj_path: Path) -> Optional[str]:
        """Parse .NET version from project file."""
        try:
            tree = ET.parse(csproj_path)
            root = tree.getroot()
            
            # Look for TargetFramework
            for elem in root.iter():
                if elem.tag in ['TargetFramework', 'TargetFrameworks']:
                    framework = elem.text
                    if framework:
                        # Extract version from framework like "net8.0"
                        match = re.search(r'net(\d+\.\d+)', framework)
                        if match:
                            return match.group(1)
                            
        except Exception:
            pass
        return None
        
    def _detect_java(self, workspace: Path) -> Optional[str]:
        """Detect Java version from project files."""
        # Check for Java indicators
        if not any([
            (workspace / 'pom.xml').exists(),
            (workspace / 'build.gradle').exists(),
            (workspace / 'build.gradle.kts').exists(),
            list(workspace.glob('*.java'))
        ]):
            return None
            
        # Try Maven pom.xml
        pom_xml = workspace / 'pom.xml'
        if pom_xml.exists():
            version = self._parse_maven_java_version(pom_xml)
            if version:
                return version
                
        # Try Gradle build files
        for gradle_file in ['build.gradle', 'build.gradle.kts']:
            gradle_path = workspace / gradle_file
            if gradle_path.exists():
                version = self._parse_gradle_java_version(gradle_path)
                if version:
                    return version
                    
        # Default to LTS version
        return self.config['platforms'].get('java', {}).get('default_version', '17')
        
    def _parse_maven_java_version(self, pom_path: Path) -> Optional[str]:
        """Parse Java version from Maven pom.xml."""
        try:
            tree = ET.parse(pom_path)
            root = tree.getroot()
            
            # Define namespace
            ns = {'maven': 'http://maven.apache.org/POM/4.0.0'}
            
            # Look in properties
            properties = root.find('.//maven:properties', ns)
            if properties is not None:
                for prop_name in ['maven.compiler.source', 'java.version', 'maven.compiler.target']:
                    prop_elem = properties.find(f'maven:{prop_name}', ns)
                    if prop_elem is not None and prop_elem.text:
                        return prop_elem.text.strip()
                        
        except Exception:
            pass
        return None
        
    def _parse_gradle_java_version(self, gradle_path: Path) -> Optional[str]:
        """Parse Java version from Gradle build file."""
        try:
            content = gradle_path.read_text()
            
            # Look for sourceCompatibility
            match = re.search(r'sourceCompatibility\s*=\s*["\']?([\d.]+)["\']?', content)
            if match:
                return match.group(1)
                
            # Look for JavaVersion
            match = re.search(r'JavaVersion\.VERSION_(\d+)', content)
            if match:
                return match.group(1)
                
        except Exception:
            pass
        return None
        
    def _detect_python(self, workspace: Path) -> Optional[str]:
        """Detect Python version from project files."""
        # Check for Python indicators
        if not any([
            (workspace / 'requirements.txt').exists(),
            (workspace / 'pyproject.toml').exists(),
            (workspace / 'setup.py').exists(),
            (workspace / 'Pipfile').exists(),
            (workspace / 'poetry.lock').exists(),
            list(workspace.glob('*.py'))
        ]):
            return None
            
        # Try pyproject.toml
        pyproject = workspace / 'pyproject.toml'
        if pyproject.exists():
            version = self._parse_python_pyproject_version(pyproject)
            if version:
                return version
                
        # Try runtime.txt (Heroku-style)
        runtime_txt = workspace / 'runtime.txt'
        if runtime_txt.exists():
            try:
                content = runtime_txt.read_text().strip()
                match = re.search(r'python-(\d+\.\d+)', content)
                if match:
                    return match.group(1)
            except Exception:
                pass
                
        # Default to current stable version
        return self.config['platforms'].get('python', {}).get('default_version', '3.11')
        
    def _parse_python_pyproject_version(self, pyproject_path: Path) -> Optional[str]:
        """Parse Python version from pyproject.toml."""
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                # Fallback to regex parsing
                return self._parse_python_pyproject_regex(pyproject_path)
                
        try:
            with open(pyproject_path, 'rb') as f:
                data = tomllib.load(f)
                
            requires_python = data.get('project', {}).get('requires-python', '')
            if requires_python:
                # Extract version from requirement like ">=3.8"
                match = re.search(r'(\d+\.\d+)', requires_python)
                if match:
                    return match.group(1)
                    
        except Exception:
            return self._parse_python_pyproject_regex(pyproject_path)
        return None
        
    def _parse_python_pyproject_regex(self, pyproject_path: Path) -> Optional[str]:
        """Parse Python version from pyproject.toml using regex."""
        try:
            content = pyproject_path.read_text()
            match = re.search(r'requires-python\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                version_spec = match.group(1)
                version_match = re.search(r'(\d+\.\d+)', version_spec)
                if version_match:
                    return version_match.group(1)
        except Exception:
            pass
        return None
        
    def _detect_go(self, workspace: Path) -> Optional[str]:
        """Detect Go version from project files."""
        go_mod = workspace / 'go.mod'
        if not go_mod.exists() and not list(workspace.glob('*.go')):
            return None
            
        if go_mod.exists():
            try:
                content = go_mod.read_text()
                match = re.search(r'^go\s+(\d+\.\d+)', content, re.MULTILINE)
                if match:
                    return match.group(1)
            except Exception:
                pass
                
        # Default to stable version
        return self.config['platforms'].get('golang', {}).get('default_version', '1.21')
        
    def _detect_rust(self, workspace: Path) -> Optional[str]:
        """Detect Rust version from project files."""
        if not ((workspace / 'Cargo.toml').exists() or list(workspace.glob('*.rs'))):
            return None
            
        # Try rust-toolchain.toml
        rust_toolchain = workspace / 'rust-toolchain.toml'
        if rust_toolchain.exists():
            version = self._parse_rust_toolchain_version(rust_toolchain)
            if version:
                return version
                
        # Try Cargo.toml
        cargo_toml = workspace / 'Cargo.toml'
        if cargo_toml.exists():
            version = self._parse_cargo_rust_version(cargo_toml)
            if version:
                return version
                
        # Default to stable version
        return self.config['platforms'].get('rust', {}).get('default_version', '1.75')
        
    def _parse_rust_toolchain_version(self, toolchain_path: Path) -> Optional[str]:
        """Parse Rust version from rust-toolchain.toml."""
        try:
            content = toolchain_path.read_text()
            match = re.search(r'channel\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                channel = match.group(1)
                version_match = re.search(r'(\d+\.\d+)', channel)
                if version_match:
                    return version_match.group(1)
        except Exception:
            pass
        return None
        
    def _parse_cargo_rust_version(self, cargo_path: Path) -> Optional[str]:
        """Parse Rust version from Cargo.toml."""
        try:
            content = cargo_path.read_text()
            match = re.search(r'rust-version\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                version = match.group(1)
                version_match = re.search(r'(\d+\.\d+)', version)
                if version_match:
                    return version_match.group(1)
        except Exception:
            pass
        return None
        
    def _detect_php(self, workspace: Path) -> Optional[str]:
        """Detect PHP version from project files."""
        if not ((workspace / 'composer.json').exists() or list(workspace.glob('*.php'))):
            return None
            
        composer_json = workspace / 'composer.json'
        if composer_json.exists():
            try:
                with open(composer_json) as f:
                    data = json.load(f)
                    
                require = data.get('require', {})
                php_req = require.get('php', '')
                
                # Extract version from requirement like "^8.1"
                match = re.search(r'(\d+\.\d+)', php_req)
                if match:
                    return match.group(1)
                    
            except Exception:
                pass
                
        # Default to stable version
        return self.config['platforms'].get('php', {}).get('default_version', '8.2')
        
    def _detect_ruby(self, workspace: Path) -> Optional[str]:
        """Detect Ruby version from project files."""
        if not any([
            (workspace / 'Gemfile').exists(),
            (workspace / '.ruby-version').exists(),
            list(workspace.glob('*.rb'))
        ]):
            return None
            
        # Try .ruby-version
        ruby_version_file = workspace / '.ruby-version'
        if ruby_version_file.exists():
            try:
                version = ruby_version_file.read_text().strip()
                if re.match(r'\d+\.\d+', version):
                    return version
            except Exception:
                pass
                
        # Try Gemfile
        gemfile = workspace / 'Gemfile'
        if gemfile.exists():
            try:
                content = gemfile.read_text()
                match = re.search(r'ruby\s+["\']([^"\']+)["\']', content)
                if match:
                    version = match.group(1)
                    version_match = re.search(r'(\d+\.\d+)', version)
                    if version_match:
                        return version_match.group(1)
            except Exception:
                pass
                
        # Default to stable version
        return self.config['platforms'].get('ruby', {}).get('default_version', '3.2')
        
    def validate_platforms(self, platforms_string: str) -> Tuple[bool, List[str]]:
        """
        Validate platform specifications.
        
        Args:
            platforms_string: Comma-separated platform:version specs
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        try:
            platforms = self._parse_platform_string(platforms_string)
        except Exception as e:
            return False, [f"Failed to parse platforms: {e}"]
            
        for platform_name, version in platforms.items():
            # Check if platform is supported
            if platform_name not in self.config['platforms']:
                issues.append(f"Unsupported platform: {platform_name}")
                continue
                
            platform_config = self.config['platforms'][platform_name]
            
            # Check if version is supported
            if version != 'latest' and version not in platform_config.get('supported_versions', []):
                issues.append(f"Unsupported version {version} for {platform_name}")
                
        # Check for conflicting combinations
        combinations = self.config.get('multi_platform', {}).get('potential_conflicts', [])
        for conflict in combinations:
            conflict_platforms = set(conflict['platforms'])
            if conflict_platforms.issubset(set(platforms.keys())):
                issues.append(f"Potential conflict: {conflict['reason']} - {conflict.get('resolution', 'No resolution provided')}")
                
        return len(issues) == 0, issues
        
    def _parse_platform_string(self, platforms_string: str) -> Dict[str, str]:
        """Parse platform string into dictionary."""
        if not platforms_string or platforms_string.lower() == 'auto':
            return {}
            
        platforms = {}
        for platform_spec in platforms_string.split(','):
            platform_spec = platform_spec.strip()
            if ':' in platform_spec:
                name, version = platform_spec.split(':', 1)
            else:
                name = platform_spec
                version = self.config['platforms'].get(name, {}).get('default_version', 'latest')
                
            platforms[name.strip()] = version.strip()
            
        return platforms
        
    def generate_config(self, workspace_path: str, output_path: Optional[str] = None) -> str:
        """
        Generate platform configuration based on detection results.
        
        Args:
            workspace_path: Path to scan for platforms
            output_path: Where to write the config file
            
        Returns:
            Path to generated config file
        """
        detected = self.detect_platforms(workspace_path)
        
        if not detected:
            print("No platforms detected, generating minimal config", file=sys.stderr)
            detected = {'nodejs': '18.16.0'}  # Fallback
            
        config = {
            'detected_at': self._get_current_timestamp(),
            'workspace_path': str(Path(workspace_path).resolve()),
            'detected_platforms': detected,
            'recommended_platforms': self._format_platforms_string(detected),
            'docker_compose_command': self._generate_docker_compose_command(detected),
            'validation': {
                'is_valid': True,
                'issues': []
            }
        }
        
        # Validate the detected combination
        platforms_string = self._format_platforms_string(detected)
        is_valid, issues = self.validate_platforms(platforms_string)
        config['validation']['is_valid'] = is_valid
        config['validation']['issues'] = issues
        
        # Write config file
        if not output_path:
            output_path = f"platforms.detected.yml"
            
        with open(output_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            
        print(f"Generated platform config: {output_path}")
        return output_path
        
    def _format_platforms_string(self, platforms: Dict[str, str]) -> str:
        """Format platforms dictionary as string."""
        return ','.join([f"{name}:{version}" for name, version in platforms.items()])
        
    def _generate_docker_compose_command(self, platforms: Dict[str, str]) -> str:
        """Generate docker-compose command for detected platforms."""
        platforms_string = self._format_platforms_string(platforms)
        return f"ENABLED_PLATFORMS='{platforms_string}' docker-compose --profile dynamic up -d"
        
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.now().isoformat()


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description='Platform Detection and Management')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Detect command
    detect_parser = subparsers.add_parser('detect', help='Auto-detect platforms')
    detect_parser.add_argument('workspace', help='Path to workspace/project directory')
    detect_parser.add_argument('--config', default='config/platforms.yml', 
                              help='Platform configuration file')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate platform specification')
    validate_parser.add_argument('platforms', help='Platform specification (e.g., "nodejs:18.16,dotnet:8.0")')
    validate_parser.add_argument('--config', default='config/platforms.yml',
                                help='Platform configuration file')
    
    # Generate command
    generate_parser = subparsers.add_parser('generate', help='Generate platform configuration')
    generate_parser.add_argument('workspace', help='Path to workspace/project directory')
    generate_parser.add_argument('--output', help='Output file path')
    generate_parser.add_argument('--config', default='config/platforms.yml',
                                help='Platform configuration file')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
        
    try:
        manager = PlatformManager(args.config)
        
        if args.command == 'detect':
            detected = manager.detect_platforms(args.workspace)
            if detected:
                print(f"\\n🎯 Detected platforms: {manager._format_platforms_string(detected)}")
                print(f"\\n💡 To use: ENABLED_PLATFORMS='{manager._format_platforms_string(detected)}' docker-compose --profile dynamic up -d")
            else:
                print("No platforms detected")
                return 1
                
        elif args.command == 'validate':
            is_valid, issues = manager.validate_platforms(args.platforms)
            if is_valid:
                print(f"✅ Platform specification is valid: {args.platforms}")
            else:
                print(f"❌ Platform specification has issues:")
                for issue in issues:
                    print(f"  - {issue}")
                return 1
                
        elif args.command == 'generate':
            config_path = manager.generate_config(args.workspace, args.output)
            print(f"✅ Generated: {config_path}")
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
        
    return 0


if __name__ == '__main__':
    sys.exit(main())