#!/bin/bash
# Platform Health Check Script
# Verifies that all requested platforms are properly installed and functional

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PLATFORMS_CONFIG="${PLATFORMS_CONFIG:-/bot/config/platforms.yml}"
ENABLED_PLATFORMS="${ENABLED_PLATFORMS:-nodejs:18.16}"
DEBUG="${DEBUG:-false}"

log_debug() {
    if [ "$DEBUG" = "true" ]; then
        echo -e "${BLUE}[DEBUG]${NC} $1" >&2
    fi
}

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1" >&2
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Parse platform specification (e.g., "nodejs:18.16")
parse_platform() {
    local platform_spec="$1"
    if [[ "$platform_spec" == *":"* ]]; then
        echo "${platform_spec%:*}" "${platform_spec#*:}"
    else
        echo "$platform_spec" "latest"
    fi
}

# Check if a command exists and optionally verify version
check_command() {
    local cmd="$1"
    local expected_version="$2"
    local version_flag="${3:---version}"
    
    log_debug "Checking command: $cmd"
    
    if ! command -v "$cmd" >/dev/null 2>&1; then
        log_error "Command '$cmd' not found"
        return 1
    fi
    
    if [ -n "$expected_version" ] && [ "$expected_version" != "latest" ]; then
        local actual_version
        actual_version=$($cmd $version_flag 2>&1 | head -1)
        log_debug "Expected version: $expected_version, Actual: $actual_version"
        
        # Simple version matching (could be enhanced for more precise matching)
        if ! echo "$actual_version" | grep -q "$expected_version"; then
            log_warning "Version mismatch for $cmd: expected $expected_version, got $actual_version"
            # Don't fail on version mismatch, just warn
        fi
    fi
    
    log_debug "✅ Command '$cmd' is available"
    return 0
}

# Platform-specific health checks
check_nodejs() {
    local version="$1"
    local status=0
    
    log_debug "Checking Node.js $version"
    
    if ! check_command "node" "$version" "--version"; then
        status=1
    fi
    
    if ! check_command "npm" "" "--version"; then
        status=1
    fi
    
    # Test basic functionality
    if command -v node >/dev/null 2>&1; then
        if ! echo 'console.log("ok")' | node >/dev/null 2>&1; then
            log_error "Node.js runtime test failed"
            status=1
        fi
    fi
    
    return $status
}

check_dotnet() {
    local version="$1"
    local status=0
    
    log_debug "Checking .NET $version"
    
    if ! check_command "dotnet" "$version" "--version"; then
        status=1
    fi
    
    # Test basic functionality
    if command -v dotnet >/dev/null 2>&1; then
        if ! dotnet --info >/dev/null 2>&1; then
            log_error ".NET runtime test failed"
            status=1
        fi
    fi
    
    return $status
}

check_java() {
    local version="$1"
    local status=0
    
    log_debug "Checking Java $version"
    
    if ! check_command "java" "$version" "-version"; then
        status=1
    fi
    
    if ! check_command "javac" "$version" "-version"; then
        status=1
    fi
    
    # Test basic functionality
    if command -v java >/dev/null 2>&1; then
        if ! java -version >/dev/null 2>&1; then
            log_error "Java runtime test failed"
            status=1
        fi
    fi
    
    return $status
}

check_python() {
    local version="$1"
    local status=0
    
    log_debug "Checking Python $version"
    
    # Try version-specific command first
    local python_cmd="python$version"
    if ! command -v "$python_cmd" >/dev/null 2>&1; then
        python_cmd="python3"
    fi
    if ! command -v "$python_cmd" >/dev/null 2>&1; then
        python_cmd="python"
    fi
    
    if ! check_command "$python_cmd" "$version" "--version"; then
        status=1
    fi
    
    # Test basic functionality
    if command -v "$python_cmd" >/dev/null 2>&1; then
        if ! echo 'print("ok")' | $python_cmd >/dev/null 2>&1; then
            log_error "Python runtime test failed"
            status=1
        fi
    fi
    
    return $status
}

check_golang() {
    local version="$1"
    local status=0
    
    log_debug "Checking Go $version"
    
    if ! check_command "go" "$version" "version"; then
        status=1
    fi
    
    # Test basic functionality
    if command -v go >/dev/null 2>&1; then
        if ! go version >/dev/null 2>&1; then
            log_error "Go runtime test failed"
            status=1
        fi
    fi
    
    return $status
}

check_rust() {
    local version="$1"
    local status=0
    
    log_debug "Checking Rust $version"
    
    if ! check_command "rustc" "$version" "--version"; then
        status=1
    fi
    
    if ! check_command "cargo" "" "--version"; then
        status=1
    fi
    
    # Test basic functionality
    if command -v rustc >/dev/null 2>&1; then
        if ! rustc --version >/dev/null 2>&1; then
            log_error "Rust runtime test failed"
            status=1
        fi
    fi
    
    return $status
}

check_php() {
    local version="$1"
    local status=0
    
    log_debug "Checking PHP $version"
    
    if ! check_command "php" "$version" "--version"; then
        status=1
    fi
    
    if ! check_command "composer" "" "--version"; then
        status=1
    fi
    
    # Test basic functionality
    if command -v php >/dev/null 2>&1; then
        if ! echo '<?php echo "ok";' | php >/dev/null 2>&1; then
            log_error "PHP runtime test failed"
            status=1
        fi
    fi
    
    return $status
}

check_ruby() {
    local version="$1"
    local status=0
    
    log_debug "Checking Ruby $version"
    
    if ! check_command "ruby" "$version" "--version"; then
        status=1
    fi
    
    if ! check_command "gem" "" "--version"; then
        status=1
    fi
    
    if ! check_command "bundle" "" "--version"; then
        status=1
    fi
    
    # Test basic functionality
    if command -v ruby >/dev/null 2>&1; then
        if ! echo 'puts "ok"' | ruby >/dev/null 2>&1; then
            log_error "Ruby runtime test failed"
            status=1
        fi
    fi
    
    return $status
}

# Main health check function
check_platform() {
    local platform="$1"
    local version="$2"
    
    log_debug "Checking platform: $platform:$version"
    
    case "$platform" in
        nodejs)
            check_nodejs "$version"
            ;;
        dotnet)
            check_dotnet "$version"
            ;;
        java)
            check_java "$version"
            ;;
        python)
            check_python "$version"
            ;;
        golang)
            check_golang "$version"
            ;;
        rust)
            check_rust "$version"
            ;;
        php)
            check_php "$version"
            ;;
        ruby)
            check_ruby "$version"
            ;;
        *)
            log_error "Unknown platform: $platform"
            return 1
            ;;
    esac
}

# Check bot infrastructure
check_bot_infrastructure() {
    local status=0
    
    log_debug "Checking bot infrastructure"
    
    # Check required directories
    for dir in "/bot/data" "/bot/scripts" "/bot/logs" "/bot/config"; do
        if [ ! -d "$dir" ]; then
            log_error "Required directory missing: $dir"
            status=1
        fi
    done
    
    # Check Python for bot scripts
    if ! check_command "python3" "" "--version"; then
        log_error "Python3 required for bot scripts"
        status=1
    fi
    
    # Check GitHub CLI
    if ! check_command "gh" "" "--version"; then
        log_error "GitHub CLI required for bot operations"
        status=1
    fi
    
    return $status
}

# Main execution
main() {
    local overall_status=0
    local checked_platforms=0
    
    log_info "🔍 Starting platform health check"
    log_debug "Enabled platforms: $ENABLED_PLATFORMS"
    
    # Check bot infrastructure first
    if ! check_bot_infrastructure; then
        log_error "❌ Bot infrastructure check failed"
        overall_status=1
    else
        log_info "✅ Bot infrastructure is healthy"
    fi
    
    # Parse and check each platform
    IFS=',' read -ra PLATFORM_LIST <<< "$ENABLED_PLATFORMS"
    for platform_spec in "${PLATFORM_LIST[@]}"; do
        platform_spec=$(echo "$platform_spec" | xargs) # trim whitespace
        
        read -r platform version <<< "$(parse_platform "$platform_spec")"
        
        log_info "Checking $platform:$version..."
        
        if check_platform "$platform" "$version"; then
            log_info "✅ $platform:$version is healthy"
            ((checked_platforms++))
        else
            log_error "❌ $platform:$version failed health check"
            overall_status=1
        fi
    done
    
    # Summary
    if [ $overall_status -eq 0 ]; then
        log_info "🎉 All platforms healthy ($checked_platforms checked)"
        echo "healthy"
        exit 0
    else
        log_error "💥 Health check failed"
        echo "unhealthy"
        exit 1
    fi
}

# Handle different invocation modes
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    # Script is being run directly
    main "$@"
else
    # Script is being sourced (for testing)
    log_debug "Script sourced, functions available"
fi