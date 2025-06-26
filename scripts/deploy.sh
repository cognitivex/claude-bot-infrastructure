#!/bin/bash
# Enhanced Multi-Platform Deployment Script for Claude Bot Infrastructure

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOYMENT_TYPE="${1:-production}"
PLATFORM_SPEC="${2:-auto}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Help function
show_help() {
    cat << EOF
Claude Bot Infrastructure Multi-Platform Deployment Script

Usage: $0 [DEPLOYMENT_TYPE] [PLATFORM_SPEC] [OPTIONS]

DEPLOYMENT_TYPE:
  development    - Local development deployment
  staging        - Staging environment deployment  
  production     - Production deployment (default)

PLATFORM_SPEC:
  auto           - Auto-detect platforms from workspace (default)
  nodejs:18.16   - Single Node.js platform
  dotnet:8.0     - Single .NET platform
  "nodejs:18.16,dotnet:8.0,python:3.11" - Multiple platforms
  legacy-nodejs  - Use legacy Node.js profile
  legacy-dotnet  - Use legacy .NET profile

OPTIONS:
  --platforms=SPEC    Override platform specification
  --profile=PROFILE   Use specific docker-compose profile
  --validate-only     Only validate configuration without deploying
  --generate-config   Generate platform configuration file
  --build-only        Only build containers without starting
  --help, -h          Show this help

Examples:
  $0                                    # Production deployment with auto-detected platforms
  $0 development auto                   # Development with auto-detection
  $0 staging "nodejs:18.16,dotnet:8.0" # Staging with specific platforms
  $0 production --platforms="java:17,nodejs:20.5"
  $0 development legacy-nodejs          # Use legacy Node.js setup
  $0 --validate-only --platforms="rust:1.75,golang:1.21"

Legacy Compatibility:
  $0 development nodejs    # Maps to legacy-nodejs profile
  $0 production dotnet     # Maps to legacy-dotnet profile

EOF
}

# Parse command line arguments
parse_arguments() {
    VALIDATE_ONLY=false
    GENERATE_CONFIG=false
    BUILD_ONLY=false
    OVERRIDE_PLATFORMS=""
    OVERRIDE_PROFILE=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --platforms=*)
                OVERRIDE_PLATFORMS="${1#*=}"
                shift
                ;;
            --profile=*)
                OVERRIDE_PROFILE="${1#*=}"
                shift
                ;;
            --validate-only)
                VALIDATE_ONLY=true
                shift
                ;;
            --generate-config)
                GENERATE_CONFIG=true
                shift
                ;;
            --build-only)
                BUILD_ONLY=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            development|staging|production)
                DEPLOYMENT_TYPE="$1"
                shift
                ;;
            nodejs|dotnet)
                # Legacy compatibility: map to legacy profiles
                PLATFORM_SPEC="legacy-$1"
                shift
                ;;
            legacy-*)
                PLATFORM_SPEC="$1"
                shift
                ;;
            auto|*:*)
                PLATFORM_SPEC="$1"
                shift
                ;;
            *)
                log_error "Unknown argument: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Apply overrides
    if [ -n "$OVERRIDE_PLATFORMS" ]; then
        PLATFORM_SPEC="$OVERRIDE_PLATFORMS"
    fi
}

# Detect platforms if needed
detect_platforms() {
    local workspace_path="${PROJECT_PATH:-./workspace}"
    
    if [ "$PLATFORM_SPEC" = "auto" ]; then
        log_info "Auto-detecting platforms from workspace: $workspace_path"
        
        if [ -x "$PROJECT_ROOT/scripts/platform_manager.py" ]; then
            local detected_platforms
            detected_platforms=$(python3 "$PROJECT_ROOT/scripts/platform_manager.py" detect "$workspace_path" 2>/dev/null | grep "Detected platforms:" | cut -d: -f2- | xargs || echo "")
            
            if [ -n "$detected_platforms" ]; then
                PLATFORM_SPEC="$detected_platforms"
                log_success "Auto-detected platforms: $PLATFORM_SPEC"
            else
                log_warning "No platforms auto-detected, using Node.js default"
                PLATFORM_SPEC="nodejs:18.16.0"
            fi
        else
            log_warning "Platform manager not available, using Node.js default"
            PLATFORM_SPEC="nodejs:18.16.0"
        fi
    fi
}

# Validate platform specification
validate_platforms() {
    log_info "Validating platform specification: $PLATFORM_SPEC"
    
    # Handle legacy profiles
    if [[ "$PLATFORM_SPEC" == legacy-* ]]; then
        log_info "Using legacy profile: ${PLATFORM_SPEC#legacy-}"
        return 0
    fi
    
    # Validate using platform manager
    if [ -x "$PROJECT_ROOT/scripts/platform_manager.py" ]; then
        if python3 "$PROJECT_ROOT/scripts/platform_manager.py" validate "$PLATFORM_SPEC"; then
            log_success "Platform specification is valid"
            return 0
        else
            log_error "Platform specification validation failed"
            return 1
        fi
    else
        log_warning "Platform manager not available, skipping validation"
        return 0
    fi
}

# Generate platform configuration
generate_platform_config() {
    if [ "$GENERATE_CONFIG" = "true" ]; then
        log_info "Generating platform configuration..."
        
        local workspace_path="${PROJECT_PATH:-./workspace}"
        if [ -x "$PROJECT_ROOT/scripts/platform_manager.py" ]; then
            python3 "$PROJECT_ROOT/scripts/platform_manager.py" generate "$workspace_path" \
                --output "$PROJECT_ROOT/platforms.detected.yml"
            log_success "Platform configuration generated"
        else
            log_error "Platform manager not available"
            return 1
        fi
    fi
}

# Determine Docker Compose profile and environment
determine_deployment_strategy() {
    # Handle legacy profiles
    if [[ "$PLATFORM_SPEC" == legacy-* ]]; then
        local legacy_type="${PLATFORM_SPEC#legacy-}"
        DOCKER_PROFILE="$legacy_type"
        COMPOSE_FILES="-f docker-compose.yml"
        ENABLED_PLATFORMS=""
        log_info "Using legacy $legacy_type profile"
        return 0
    fi
    
    # Use dynamic multi-platform approach
    DOCKER_PROFILE="dynamic"
    COMPOSE_FILES="-f docker-compose.yml"
    ENABLED_PLATFORMS="$PLATFORM_SPEC"
    
    # Add production override if needed
    local override_file="docker-compose.${DEPLOYMENT_TYPE}.yml"
    if [ -f "$PROJECT_ROOT/$override_file" ]; then
        COMPOSE_FILES="$COMPOSE_FILES -f $override_file"
        log_info "Using deployment override: $override_file"
    fi
    
    log_info "Using dynamic multi-platform deployment"
    log_info "Platforms: $ENABLED_PLATFORMS"
}

# Pre-deployment checks
run_preflight_checks() {
    log_info "Running pre-deployment checks..."
    
    # Check if we're in the right directory
    if [[ ! -f "$PROJECT_ROOT/docker-compose.yml" ]]; then
        log_error "docker-compose.yml not found. Are you in the right directory?"
        exit 1
    fi
    
    # Check Docker is running
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running or not accessible"
        exit 1
    fi
    
    # Check Docker Compose is available
    if ! command -v docker-compose >/dev/null 2>&1; then
        log_error "Docker Compose not found"
        exit 1
    fi
    
    # Check .env file exists
    if [[ ! -f "$PROJECT_ROOT/.env" ]]; then
        log_warning ".env file not found. Using environment variables only."
    fi
    
    # Check required environment variables for dynamic deployments
    if [ "$DOCKER_PROFILE" = "dynamic" ]; then
        local required_vars=("ANTHROPIC_API_KEY" "GITHUB_TOKEN" "TARGET_REPO")
        for var in "${required_vars[@]}"; do
            if [[ -z "${!var:-}" ]]; then
                log_error "Required environment variable $var is not set"
                exit 1
            fi
        done
    fi
    
    # Check disk space (minimum 5GB)
    local available_space=$(df "$PROJECT_ROOT" | tail -1 | awk '{print $4}')
    if [[ $available_space -lt 5242880 ]]; then # 5GB in KB
        log_warning "Less than 5GB disk space available"
    fi
    
    log_success "Pre-deployment checks passed"
}

# Build containers
build_containers() {
    log_info "Building containers..."
    
    cd "$PROJECT_ROOT"
    
    # Set environment variables for build
    export ENABLED_PLATFORMS="${ENABLED_PLATFORMS:-nodejs:18.16.0}"
    export BASE_IMAGE="${BASE_IMAGE:-ubuntu:22.04}"
    
    # Build with appropriate profile
    if [ "$DOCKER_PROFILE" = "dynamic" ]; then
        log_info "Building dynamic multi-platform container..."
        log_info "Platforms: $ENABLED_PLATFORMS"
        
        # Generate optimized Dockerfile if builder is available
        if [ -x "$PROJECT_ROOT/scripts/build-dynamic-dockerfile.py" ]; then
            log_info "Generating optimized Dockerfile..."
            python3 "$PROJECT_ROOT/scripts/build-dynamic-dockerfile.py" \
                --platforms "$ENABLED_PLATFORMS" \
                --output ".devcontainer/Dockerfile.generated"
            
            # Update compose file to use generated Dockerfile
            export DOCKERFILE_PATH=".devcontainer/Dockerfile.generated"
        fi
        
        docker-compose $COMPOSE_FILES build --no-cache claude-bot-dynamic
    else
        # Legacy build
        docker-compose $COMPOSE_FILES build --no-cache
    fi
    
    log_success "Containers built successfully"
}

# Start services
start_services() {
    log_info "Starting services..."
    
    cd "$PROJECT_ROOT"
    
    # Set environment variables
    export ENABLED_PLATFORMS="${ENABLED_PLATFORMS:-nodejs:18.16.0}"
    export AUTO_DETECT_PLATFORMS="${AUTO_DETECT_PLATFORMS:-true}"
    export ENVIRONMENT_PROFILE="${ENVIRONMENT_PROFILE:-standard}"
    
    # Stop existing services
    docker-compose $COMPOSE_FILES down 2>/dev/null || true
    
    # Start new services
    if [ -n "$OVERRIDE_PROFILE" ]; then
        docker-compose $COMPOSE_FILES --profile "$OVERRIDE_PROFILE" up -d
    else
        docker-compose $COMPOSE_FILES --profile "$DOCKER_PROFILE" up -d
    fi
    
    log_success "Services started"
}

# Health checks
wait_for_health() {
    log_info "Waiting for services to become healthy..."
    
    local max_attempts=30
    local attempt=0
    
    while [[ $attempt -lt $max_attempts ]]; do
        if docker-compose $COMPOSE_FILES ps | grep -q "Up (healthy)"; then
            log_success "Services are healthy"
            return 0
        fi
        
        attempt=$((attempt + 1))
        log_info "Attempt $attempt/$max_attempts - waiting for health checks..."
        sleep 10
    done
    
    log_error "Services did not become healthy within expected time"
    log_info "Current status:"
    docker-compose $COMPOSE_FILES ps
    return 1
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."
    
    # Check container status
    log_info "Container status:"
    docker-compose $COMPOSE_FILES ps
    
    # Check logs for errors
    log_info "Checking for recent errors..."
    local container_name="claude-bot"
    if [ "$DOCKER_PROFILE" = "dynamic" ]; then
        container_name="claude-bot-dynamic"
    fi
    
    if docker-compose $COMPOSE_FILES logs --tail=50 "$container_name" | grep -i error; then
        log_warning "Errors found in logs (see above)"
    else
        log_success "No recent errors in logs"
    fi
    
    # Test API endpoints
    if command -v curl >/dev/null 2>&1; then
        log_info "Testing API endpoints..."
        
        # Test status endpoint
        if curl -sf http://localhost:8080/api/health >/dev/null; then
            log_success "Status API is responding"
        else
            log_warning "Status API is not responding"
        fi
        
        # Test metrics endpoint if available
        if curl -sf http://localhost:8000/metrics >/dev/null 2>&1; then
            log_success "Metrics endpoint is responding"
        else
            log_info "Metrics endpoint not available (expected for some configurations)"
        fi
    fi
    
    # Platform-specific verification
    if [ "$DOCKER_PROFILE" = "dynamic" ]; then
        log_info "Verifying platform health..."
        if docker-compose $COMPOSE_FILES exec -T claude-bot-dynamic /bot/scripts/health-check-platforms.sh; then
            log_success "All platforms are healthy"
        else
            log_error "Platform health check failed"
            return 1
        fi
    fi
}

# Backup existing data
backup_data() {
    if [[ "$DEPLOYMENT_TYPE" == "production" ]]; then
        log_info "Creating backup of existing data..."
        
        local backup_dir="$PROJECT_ROOT/backups"
        local timestamp=$(date +%Y%m%d_%H%M%S)
        
        mkdir -p "$backup_dir"
        
        # Backup volumes if they exist
        if docker volume ls | grep -q "claude-bot-infrastructure_bot-data"; then
            docker run --rm \
                -v claude-bot-infrastructure_bot-data:/data \
                -v "$backup_dir:/backup" \
                alpine:latest \
                tar czf "/backup/bot-data_${timestamp}.tar.gz" -C /data .
            
            log_success "Data backup created: bot-data_${timestamp}.tar.gz"
        fi
    fi
}

# Cleanup old resources
cleanup() {
    log_info "Cleaning up old resources..."
    
    # Remove old containers
    docker container prune -f
    
    # Remove old images (keep last 3 versions)
    docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}" | \
        grep claude-bot-infrastructure | \
        tail -n +4 | \
        awk '{print $3}' | \
        xargs -r docker rmi -f
    
    log_success "Cleanup completed"
}

# Main deployment function
main() {
    parse_arguments "$@"
    
    log_info "Starting multi-platform deployment"
    log_info "Deployment type: $DEPLOYMENT_TYPE"
    log_info "Platform specification: $PLATFORM_SPEC"
    
    # Early validation and config generation
    if [ "$VALIDATE_ONLY" = "true" ] || [ "$GENERATE_CONFIG" = "true" ]; then
        detect_platforms
        validate_platforms || exit 1
        generate_platform_config
        
        if [ "$VALIDATE_ONLY" = "true" ]; then
            log_success "Validation completed successfully"
            exit 0
        fi
        
        if [ "$GENERATE_CONFIG" = "true" ] && [ "$BUILD_ONLY" = "false" ]; then
            log_success "Configuration generation completed"
            exit 0
        fi
    fi
    
    # Full deployment process
    detect_platforms
    validate_platforms || exit 1
    determine_deployment_strategy
    run_preflight_checks
    
    if [ "$BUILD_ONLY" = "true" ]; then
        build_containers
        log_success "Build completed successfully"
        exit 0
    fi
    
    # Full deployment
    backup_data
    build_containers
    start_services
    wait_for_health
    verify_deployment
    
    if [[ "$DEPLOYMENT_TYPE" == "production" ]]; then
        cleanup
    fi
    
    log_success "Deployment completed successfully!"
    
    # Post-deployment information
    echo
    log_info "=== Deployment Summary ==="
    echo "Deployment Type: $DEPLOYMENT_TYPE"
    echo "Platform Specification: $PLATFORM_SPEC"
    echo "Docker Profile: $DOCKER_PROFILE"
    if [ -n "$ENABLED_PLATFORMS" ]; then
        echo "Enabled Platforms: $ENABLED_PLATFORMS"
    fi
    echo "Status Dashboard: http://localhost:8080"
    echo "Health Check: http://localhost:8080/api/health"
    echo
    local container_name="claude-bot"
    if [ "$DOCKER_PROFILE" = "dynamic" ]; then
        container_name="claude-bot-dynamic"
    fi
    log_info "To view logs: docker-compose logs -f $container_name"
    log_info "To check status: docker-compose ps"
    log_info "To check platform health: docker exec $container_name /bot/scripts/health-check-platforms.sh"
}

# Run main function
main "$@"