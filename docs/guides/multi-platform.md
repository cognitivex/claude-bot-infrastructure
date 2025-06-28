# Multi-Platform Deployment Guide

This guide covers the new flexible multi-platform deployment system for Claude Bot Infrastructure, which supports any combination of runtime platforms with specific versions.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Platform Specification](#platform-specification)
4. [Deployment Examples](#deployment-examples)
5. [Auto-Detection](#auto-detection)
6. [Backward Compatibility](#backward-compatibility)
7. [Configuration Reference](#configuration-reference)
8. [Troubleshooting](#troubleshooting)

## Overview

The multi-platform system allows you to:

- **Deploy any combination of platforms**: Node.js, .NET, Java, Python, Go, Rust, PHP, Ruby
- **Specify exact versions**: Control runtime versions precisely (e.g., `nodejs:18.16.0`, `dotnet:8.0`)
- **Auto-detect platforms**: Automatically scan your project for required runtimes
- **Maintain backward compatibility**: Existing nodejs/dotnet profiles still work
- **Use flexible configurations**: Environment variables, YAML configs, or command-line arguments

### Supported Platforms

| Platform | Versions Available | Detection Files |
|----------|-------------------|-----------------|
| **Node.js** | 10.13, 14.21, 16.20, 18.16, 20.5 | package.json, yarn.lock, .nvmrc |
| **.NET** | 6.0, 7.0, 8.0, 9.0 | *.csproj, *.sln, global.json |
| **Java** | 8, 11, 17, 21 | pom.xml, build.gradle, *.java |
| **Python** | 3.8, 3.9, 3.10, 3.11, 3.12 | requirements.txt, pyproject.toml |
| **Go** | 1.19, 1.20, 1.21, 1.22 | go.mod, go.sum, *.go |
| **Rust** | 1.68, 1.70, 1.72, 1.75, 1.76 | Cargo.toml, rust-toolchain.toml |
| **PHP** | 7.4, 8.0, 8.1, 8.2, 8.3 | composer.json, *.php |
| **Ruby** | 2.7, 3.0, 3.1, 3.2, 3.3 | Gemfile, .ruby-version, *.rb |

## Quick Start

### 1. Auto-Detection (Recommended)

The simplest way to get started:

```bash
# Auto-detect platforms from your project
./scripts/deploy.sh development auto

# Or just use defaults (auto-detection enabled by default)
./scripts/deploy.sh development
```

### 2. Specify Platforms Manually

```bash
# Single platform
./scripts/deploy.sh development nodejs:18.16.0

# Multiple platforms
./scripts/deploy.sh development "nodejs:18.16.0,dotnet:8.0,python:3.11"

# Complex example
./scripts/deploy.sh production "java:17,nodejs:20.5,rust:1.75"
```

### 3. Use Environment Variables

```bash
# Set in .env file
ENABLED_PLATFORMS=nodejs:18.16.0,dotnet:8.0,python:3.11
AUTO_DETECT_PLATFORMS=true
ENVIRONMENT_PROFILE=standard

# Then deploy
docker-compose --profile dynamic up -d
```

## Platform Specification

### Format

Platform specifications use the format: `platform:version`

```bash
# Single platform
nodejs:18.16.0

# Multiple platforms (comma-separated)
nodejs:18.16.0,dotnet:8.0,python:3.11

# Mixed versions
java:17,nodejs:20.5,python:3.12,rust:1.75
```

### Version Resolution

- **Exact version**: `nodejs:18.16.0` - Use exactly this version
- **Major.minor**: `dotnet:8.0` - Use latest patch version of 8.0
- **Default**: `java` - Use the platform's default version
- **Latest**: `python:latest` - Use the most recent supported version

### Auto-Detection

When using `auto` or enabling `AUTO_DETECT_PLATFORMS=true`, the system:

1. Scans your project directory for platform indicators
2. Attempts to detect required versions from config files
3. Falls back to sensible defaults if version detection fails
4. Validates the combination for conflicts

## Deployment Examples

### Full-Stack Application

For a project with React frontend and .NET API:

```bash
# Method 1: Auto-detection
./scripts/deploy.sh development auto

# Method 2: Manual specification  
./scripts/deploy.sh development "nodejs:18.16.0,dotnet:8.0"

# Method 3: Environment variable
ENABLED_PLATFORMS="nodejs:18.16.0,dotnet:8.0" docker-compose --profile dynamic up -d
```

### Microservices Environment

For multiple services with different platforms:

```bash
# Development environment with all platforms
./scripts/deploy.sh development "java:17,nodejs:20.5,python:3.11,golang:1.21"

# Production with resource optimization
ENVIRONMENT_PROFILE=enterprise ./scripts/deploy.sh production "java:17,golang:1.21"
```

### Data Science Stack

For ML/AI projects:

```bash
# Python with Node.js for web interface
./scripts/deploy.sh development "python:3.11,nodejs:18.16.0"

# Add Rust for performance-critical components
./scripts/deploy.sh staging "python:3.11,nodejs:18.16.0,rust:1.75"
```

### Legacy Migration

Gradually migrate from legacy to new system:

```bash
# Current legacy deployment
./scripts/deploy.sh development legacy-nodejs

# Equivalent new deployment
./scripts/deploy.sh development "nodejs:18.16.0"

# Enhanced with additional platforms
./scripts/deploy.sh development "nodejs:18.16.0,python:3.11"
```

## Auto-Detection

### How It Works

1. **File Scanning**: Looks for platform-specific files in your project
2. **Version Parsing**: Extracts version requirements from config files
3. **Smart Defaults**: Uses sensible defaults when versions can't be determined
4. **Validation**: Checks for platform conflicts and compatibility

### Detection Examples

**Node.js Detection:**
```json
// package.json
{
  "engines": {
    "node": ">=18.16.0"
  }
}
```
→ Detects: `nodejs:18.16.0`

**.NET Detection:**
```json
// global.json
{
  "sdk": {
    "version": "8.0.100"
  }
}
```
→ Detects: `dotnet:8.0`

**Python Detection:**
```toml
# pyproject.toml
[project]
requires-python = ">=3.11"
```
→ Detects: `python:3.11`

### Manual Detection

You can run detection manually:

```bash
# Detect platforms in current directory
python3 scripts/platform-manager.py detect .

# Detect platforms in specific directory
python3 scripts/platform-manager.py detect /path/to/project

# Generate configuration file
python3 scripts/platform-manager.py generate . --output platforms.detected.yml
```

## Backward Compatibility

### Legacy Profiles

Existing profiles continue to work unchanged:

```bash
# These still work exactly as before
docker-compose --profile nodejs up -d
docker-compose --profile dotnet up -d

# Deploy script backwards compatibility
./scripts/deploy.sh development nodejs    # Maps to legacy-nodejs
./scripts/deploy.sh production dotnet     # Maps to legacy-dotnet
```

### Migration Path

1. **Keep Current Setup**: No changes required for existing deployments
2. **Try Auto-Detection**: `./scripts/deploy.sh development auto`
3. **Customize Platforms**: Add additional platforms as needed
4. **Full Migration**: Switch to dynamic profile once comfortable

### Profile Mapping

| Legacy Command | New Equivalent | Recommendation |
|----------------|----------------|----------------|
| `--profile nodejs` | `--profile dynamic` with `ENABLED_PLATFORMS=nodejs:18.16.0` | Migrate when ready |
| `--profile dotnet` | `--profile dynamic` with `ENABLED_PLATFORMS=dotnet:8.0,nodejs:10.13` | Keep if working well |
| Custom profiles | Define in `ENABLED_PLATFORMS` | More flexible |

## Configuration Reference

### Environment Variables

```bash
# Primary platform configuration
ENABLED_PLATFORMS=nodejs:18.16.0,dotnet:8.0        # Platform specifications
AUTO_DETECT_PLATFORMS=true                         # Enable auto-detection  
ENVIRONMENT_PROFILE=standard                       # Resource profile

# Advanced configuration
PLATFORMS_CONFIG=config/platforms.yml              # Platform registry
BASE_IMAGE=ubuntu:22.04                           # Base Docker image
WORKSPACE_PATH=/workspace                          # Project workspace path
```

### Environment Profiles

Controls resource allocation and capabilities:

- **minimal**: Single platform, 1GB memory, basic features
- **standard**: 2 platforms, 2GB memory, full features (default)
- **advanced**: 4 platforms, 4GB memory, enhanced monitoring
- **enterprise**: 8+ platforms, 8GB memory, full observability

### Configuration Files

**Platform Registry** (`config/platforms.yml`):
```yaml
platforms:
  nodejs:
    default_version: "18.16.0"
    supported_versions: ["10.13.0", "14.21.3", "16.20.1", "18.16.0", "20.5.0"]
    detection_patterns: ["package.json", "yarn.lock", ".nvmrc"]
    # ... more configuration
```

**Generated Config** (auto-created by detection):
```yaml
detected_at: "2025-06-25T10:30:00"
workspace_path: "/workspace"
detected_platforms:
  nodejs: "18.16.0"
  dotnet: "8.0"
recommended_platforms: "nodejs:18.16.0,dotnet:8.0"
docker_compose_command: "ENABLED_PLATFORMS='nodejs:18.16.0,dotnet:8.0' docker-compose --profile dynamic up -d"
```

## Troubleshooting

### Common Issues

**Platform Not Detected:**
```bash
# Check what was detected
python3 scripts/platform-manager.py detect .

# Force specific platforms
ENABLED_PLATFORMS="nodejs:18.16.0" docker-compose --profile dynamic up -d
```

**Version Conflicts:**
```bash
# Validate your platform combination
python3 scripts/platform-manager.py validate "nodejs:18.16.0,java:17,python:3.11"

# Check for known conflicts
./scripts/deploy.sh --validate-only --platforms="your,platforms,here"
```

**Build Failures:**
```bash
# Check Docker build logs
docker-compose --profile dynamic build --no-cache

# Use legacy profile as fallback
./scripts/deploy.sh development legacy-nodejs
```

**Health Check Failures:**
```bash
# Check platform health
docker exec claude-bot-dynamic /bot/scripts/health-check-platforms.sh

# Check individual platform availability
docker exec claude-bot-dynamic node --version
docker exec claude-bot-dynamic dotnet --version
```

### Debug Mode

Enable detailed logging:

```bash
# Enable debug output
DEBUG=true ./scripts/deploy.sh development auto

# Check platform detection details
DEBUG=true python3 scripts/platform-manager.py detect .
```

### Getting Help

1. **Validate Configuration**: Use `./scripts/deploy.sh --validate-only`
2. **Check Platform Registry**: Review `config/platforms.yml`
3. **Test Detection**: Run `scripts/platform-manager.py detect`
4. **Review Logs**: Check container logs for specific errors
5. **Use Legacy**: Fall back to legacy profiles if needed

### Performance Optimization

**Resource Limits:**
```yaml
# docker-compose.production.yml
services:
  claude-bot-dynamic:
    deploy:
      resources:
        limits:
          cpus: '4'      # Increase for more platforms
          memory: 8G     # Scale with platform count
```

**Build Optimization:**
```bash
# Use optimized Dockerfile generation
python3 scripts/build-dynamic-dockerfile.py --platforms "nodejs:18.16,dotnet:8.0" --output .devcontainer/Dockerfile.optimized

# Build with specific target
docker build -f .devcontainer/Dockerfile.optimized .
```

## Next Steps

1. **Try Auto-Detection**: Start with `./scripts/deploy.sh development auto`
2. **Explore Combinations**: Experiment with different platform combinations
3. **Optimize Resources**: Adjust environment profiles based on usage
4. **Monitor Performance**: Use built-in metrics to track resource usage
5. **Contribute**: Add support for additional platforms as needed

For more details, see the [main deployment guide](DEPLOYMENT.md) and [platform configuration](../config/platforms.yml).