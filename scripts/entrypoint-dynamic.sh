#!/bin/bash
# Dynamic Platform Entrypoint Script
# Initializes the container with the requested platforms and starts the bot

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    if [ "${DEBUG:-false}" = "true" ]; then
        echo -e "${BLUE}[DEBUG]${NC} $1"
    fi
}

# Configuration
PLATFORMS_CONFIG="${PLATFORMS_CONFIG:-/bot/config/platforms.yml}"
ENABLED_PLATFORMS="${ENABLED_PLATFORMS:-nodejs:18.16}"
AUTO_DETECT_PLATFORMS="${AUTO_DETECT_PLATFORMS:-true}"
WORKSPACE_PATH="${WORKSPACE_PATH:-/workspace}"

log_info "🚀 Claude Bot Multi-Platform Entrypoint"
log_info "Enabled platforms: $ENABLED_PLATFORMS"

# Auto-detect platforms if requested
auto_detect_platforms() {
    local detected_platforms=""
    local workspace="$1"
    
    log_info "🔍 Auto-detecting platforms in $workspace"
    
    if [ ! -d "$workspace" ] || [ -z "$(ls -A "$workspace" 2>/dev/null)" ]; then
        log_warning "Workspace is empty, using default platforms"
        return 0
    fi
    
    cd "$workspace"
    
    # Node.js detection
    if [ -f "package.json" ] || [ -f "yarn.lock" ] || [ -f "pnpm-lock.yaml" ]; then
        local node_version="18.16.0"
        
        # Try to detect version from package.json
        if [ -f "package.json" ] && command -v python3 >/dev/null 2>&1; then
            node_version=$(python3 -c "
import json
try:
    with open('package.json') as f:
        data = json.load(f)
    engines = data.get('engines', {})
    node = engines.get('node', '18.16.0')
    # Extract version number
    import re
    match = re.search(r'(\d+\.\d+\.\d+)', node)
    print(match.group(1) if match else '18.16.0')
except:
    print('18.16.0')
" 2>/dev/null || echo "18.16.0")
        fi
        
        detected_platforms="${detected_platforms:+$detected_platforms,}nodejs:$node_version"
        log_info "  📦 Detected Node.js project (version: $node_version)"
    fi
    
    # .NET detection
    if find . -name "*.csproj" -o -name "*.sln" -o -name "*.fsproj" | head -1 | grep -q .; then
        local dotnet_version="8.0"
        
        # Try to detect version from project files
        if [ -f "global.json" ] && command -v python3 >/dev/null 2>&1; then
            dotnet_version=$(python3 -c "
import json
try:
    with open('global.json') as f:
        data = json.load(f)
    sdk = data.get('sdk', {})
    version = sdk.get('version', '8.0')
    # Extract major.minor
    parts = version.split('.')
    print(f'{parts[0]}.{parts[1]}' if len(parts) >= 2 else '8.0')
except:
    print('8.0')
" 2>/dev/null || echo "8.0")
        fi
        
        detected_platforms="${detected_platforms:+$detected_platforms,}dotnet:$dotnet_version"
        log_info "  🔷 Detected .NET project (version: $dotnet_version)"
    fi
    
    # Java detection
    if [ -f "pom.xml" ] || [ -f "build.gradle" ] || [ -f "build.gradle.kts" ]; then
        local java_version="17"
        
        # Try to detect version from Maven
        if [ -f "pom.xml" ] && command -v python3 >/dev/null 2>&1; then
            java_version=$(python3 -c "
import xml.etree.ElementTree as ET
try:
    tree = ET.parse('pom.xml')
    root = tree.getroot()
    ns = {'maven': 'http://maven.apache.org/POM/4.0.0'}
    
    # Check properties
    props = root.find('.//maven:properties', ns)
    if props is not None:
        for prop in ['maven.compiler.source', 'java.version', 'maven.compiler.target']:
            elem = props.find(f'maven:{prop}', ns)
            if elem is not None:
                print(elem.text)
                break
    else:
        print('17')
except:
    print('17')
" 2>/dev/null || echo "17")
        fi
        
        detected_platforms="${detected_platforms:+$detected_platforms,}java:$java_version"
        log_info "  ☕ Detected Java project (version: $java_version)"
    fi
    
    # Python detection
    if [ -f "requirements.txt" ] || [ -f "pyproject.toml" ] || [ -f "setup.py" ] || [ -f "Pipfile" ]; then
        local python_version="3.11"
        
        # Try to detect version from pyproject.toml or runtime.txt
        if [ -f "pyproject.toml" ] && command -v python3 >/dev/null 2>&1; then
            python_version=$(python3 -c "
import re
try:
    with open('pyproject.toml') as f:
        content = f.read()
    
    # Look for requires-python
    match = re.search(r'requires-python\s*=\s*[\"\\']([^\"\\'']+)[\"\\']', content)
    if match:
        version_spec = match.group(1)
        # Extract version number
        version_match = re.search(r'(\d+\.\d+)', version_spec)
        if version_match:
            print(version_match.group(1))
        else:
            print('3.11')
    else:
        print('3.11')
except:
    print('3.11')
" 2>/dev/null || echo "3.11")
        elif [ -f "runtime.txt" ]; then
            python_version=$(grep -o 'python-[0-9.]*' runtime.txt | head -1 | cut -d'-' -f2 || echo "3.11")
        fi
        
        detected_platforms="${detected_platforms:+$detected_platforms,}python:$python_version"
        log_info "  🐍 Detected Python project (version: $python_version)"
    fi
    
    # Go detection
    if [ -f "go.mod" ] || [ -f "go.sum" ]; then
        local go_version="1.21"
        
        if [ -f "go.mod" ]; then
            go_version=$(grep -o 'go [0-9.]*' go.mod | head -1 | cut -d' ' -f2 || echo "1.21")
        fi
        
        detected_platforms="${detected_platforms:+$detected_platforms,}golang:$go_version"
        log_info "  🔵 Detected Go project (version: $go_version)"
    fi
    
    # Rust detection
    if [ -f "Cargo.toml" ] || [ -f "Cargo.lock" ]; then
        local rust_version="1.75"
        
        # Try to detect version from rust-toolchain.toml or Cargo.toml
        if [ -f "rust-toolchain.toml" ] && command -v python3 >/dev/null 2>&1; then
            rust_version=$(python3 -c "
import re
try:
    with open('rust-toolchain.toml') as f:
        content = f.read()
    
    match = re.search(r'channel\s*=\s*[\"\\']([^\"\\'']+)[\"\\']', content)
    if match:
        channel = match.group(1)
        version_match = re.search(r'(\d+\.\d+)', channel)
        print(version_match.group(1) if version_match else '1.75')
    else:
        print('1.75')
except:
    print('1.75')
" 2>/dev/null || echo "1.75")
        fi
        
        detected_platforms="${detected_platforms:+$detected_platforms,}rust:$rust_version"
        log_info "  🦀 Detected Rust project (version: $rust_version)"
    fi
    
    # PHP detection
    if [ -f "composer.json" ] || [ -f "composer.lock" ]; then
        local php_version="8.2"
        
        if [ -f "composer.json" ] && command -v python3 >/dev/null 2>&1; then
            php_version=$(python3 -c "
import json, re
try:
    with open('composer.json') as f:
        data = json.load(f)
    
    require = data.get('require', {})
    php_req = require.get('php', '8.2')
    
    # Extract version number
    match = re.search(r'(\d+\.\d+)', php_req)
    print(match.group(1) if match else '8.2')
except:
    print('8.2')
" 2>/dev/null || echo "8.2")
        fi
        
        detected_platforms="${detected_platforms:+$detected_platforms,}php:$php_version"
        log_info "  🐘 Detected PHP project (version: $php_version)"
    fi
    
    # Ruby detection
    if [ -f "Gemfile" ] || [ -f "Gemfile.lock" ] || [ -f ".ruby-version" ]; then
        local ruby_version="3.2"
        
        if [ -f ".ruby-version" ]; then
            ruby_version=$(cat .ruby-version | tr -d '\n\r' || echo "3.2")
        elif [ -f "Gemfile" ]; then
            ruby_version=$(grep -o "ruby ['\"][0-9.]*['\"]" Gemfile | head -1 | grep -o '[0-9.]*' || echo "3.2")
        fi
        
        detected_platforms="${detected_platforms:+$detected_platforms,}ruby:$ruby_version"
        log_info "  💎 Detected Ruby project (version: $ruby_version)"
    fi
    
    if [ -n "$detected_platforms" ]; then
        log_info "🎯 Auto-detected platforms: $detected_platforms"
        # Update ENABLED_PLATFORMS if auto-detection found something
        if [ "$AUTO_DETECT_PLATFORMS" = "true" ]; then
            ENABLED_PLATFORMS="$detected_platforms"
            export ENABLED_PLATFORMS
        fi
    else
        log_info "No platforms auto-detected, using configured platforms"
    fi
}

# Initialize platform environments
initialize_platforms() {
    log_info "🔧 Initializing platform environments"
    
    # Parse enabled platforms and set up environment
    IFS=',' read -ra PLATFORM_LIST <<< "$ENABLED_PLATFORMS"
    for platform_spec in "${PLATFORM_LIST[@]}"; do
        platform_spec=$(echo "$platform_spec" | xargs) # trim whitespace
        
        # Parse platform:version
        if [[ "$platform_spec" == *":"* ]]; then
            platform="${platform_spec%:*}"
            version="${platform_spec#*:}"
        else
            platform="$platform_spec"
            version="latest"
        fi
        
        log_info "  ⚡ Initializing $platform:$version"
        initialize_platform "$platform" "$version"
    done
}

# Initialize a specific platform
initialize_platform() {
    local platform="$1"
    local version="$2"
    
    case "$platform" in
        nodejs)
            # Set up Node.js environment
            if command -v node >/dev/null 2>&1; then
                export NODE_VERSION="$version"
                export NODE_ENV="${NODE_ENV:-development}"
                log_debug "Node.js environment configured"
            fi
            ;;
        dotnet)
            # Set up .NET environment
            if command -v dotnet >/dev/null 2>&1; then
                export DOTNET_VERSION="$version"
                export DOTNET_ENVIRONMENT="${DOTNET_ENVIRONMENT:-Development}"
                export ASPNETCORE_ENVIRONMENT="${ASPNETCORE_ENVIRONMENT:-Development}"
                log_debug ".NET environment configured"
            fi
            ;;
        java)
            # Set up Java environment
            if command -v java >/dev/null 2>&1; then
                export JAVA_VERSION="$version"
                # Set JAVA_HOME if not already set
                if [ -z "$JAVA_HOME" ]; then
                    export JAVA_HOME="/usr/lib/jvm/java-$version-openjdk-amd64"
                fi
                log_debug "Java environment configured"
            fi
            ;;
        python)
            # Set up Python environment
            if command -v python3 >/dev/null 2>&1; then
                export PYTHON_VERSION="$version"
                export PYTHONUNBUFFERED=1
                export PYTHONDONTWRITEBYTECODE=1
                log_debug "Python environment configured"
            fi
            ;;
        golang)
            # Set up Go environment
            if command -v go >/dev/null 2>&1; then
                export GO_VERSION="$version"
                export GOPATH="${GOPATH:-/home/bot/go}"
                export GOPROXY="${GOPROXY:-https://proxy.golang.org,direct}"
                mkdir -p "$GOPATH"
                log_debug "Go environment configured"
            fi
            ;;
        rust)
            # Set up Rust environment
            if command -v rustc >/dev/null 2>&1; then
                export RUST_VERSION="$version"
                export CARGO_HOME="${CARGO_HOME:-/home/bot/.cargo}"
                export RUSTUP_HOME="${RUSTUP_HOME:-/home/bot/.rustup}"
                # Source cargo environment
                [ -f "$CARGO_HOME/env" ] && source "$CARGO_HOME/env"
                log_debug "Rust environment configured"
            fi
            ;;
        php)
            # Set up PHP environment
            if command -v php >/dev/null 2>&1; then
                export PHP_VERSION="$version"
                export COMPOSER_HOME="${COMPOSER_HOME:-/home/bot/.composer}"
                log_debug "PHP environment configured"
            fi
            ;;
        ruby)
            # Set up Ruby environment
            if command -v ruby >/dev/null 2>&1; then
                export RUBY_VERSION="$version"
                export BUNDLE_PATH="${BUNDLE_PATH:-/home/bot/.bundle}"
                log_debug "Ruby environment configured"
            fi
            ;;
        *)
            log_warning "Unknown platform: $platform"
            ;;
    esac
}

# Validate platform health
validate_platforms() {
    log_info "🏥 Validating platform health"
    
    if [ -x "/bot/scripts/health-check-platforms.sh" ]; then
        if /bot/scripts/health-check-platforms.sh; then
            log_info "✅ All platforms are healthy"
        else
            log_error "❌ Platform health check failed"
            exit 1
        fi
    else
        log_warning "Health check script not found, skipping validation"
    fi
}

# Setup workspace permissions
setup_workspace() {
    log_info "📁 Setting up workspace permissions"
    
    # Ensure workspace directory exists and has correct permissions
    mkdir -p "$WORKSPACE_PATH"
    
    # Only try to change ownership if we have permission
    if [ "$(id -u)" = "0" ]; then
        chown -R bot:bot "$WORKSPACE_PATH" 2>/dev/null || true
        chown -R bot:bot /bot 2>/dev/null || true
    fi
    
    # Ensure directories are writable
    chmod -R 755 /bot/data /bot/logs 2>/dev/null || true
}

# Main entrypoint logic
main() {
    log_info "Starting Claude Bot with multi-platform support"
    
    # Setup workspace and permissions
    setup_workspace
    
    # Auto-detect platforms if enabled and workspace is available
    if [ "$AUTO_DETECT_PLATFORMS" = "true" ] && [ -d "$WORKSPACE_PATH" ]; then
        auto_detect_platforms "$WORKSPACE_PATH"
    fi
    
    # Initialize platform environments
    initialize_platforms
    
    # Validate that all platforms are working
    validate_platforms
    
    # Display final configuration
    log_info "🎉 Platform initialization complete"
    log_info "Active platforms: $ENABLED_PLATFORMS"
    log_info "Workspace: $WORKSPACE_PATH"
    
    # Execute the command passed to the container
    if [ $# -gt 0 ]; then
        log_info "🚀 Executing: $*"
        exec "$@"
    else
        log_info "🚀 Starting default bot command"
        exec start-bot.sh
    fi
}

# Run main function with all arguments
main "$@"