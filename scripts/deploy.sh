#!/bin/bash
# Production deployment script for Claude Bot Infrastructure

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOYMENT_TYPE="${1:-production}"
BOT_PROFILE="${2:-nodejs}"

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
Claude Bot Infrastructure Deployment Script

Usage: $0 [DEPLOYMENT_TYPE] [BOT_PROFILE]

DEPLOYMENT_TYPE:
  development    - Local development deployment
  staging        - Staging environment deployment
  production     - Production deployment (default)

BOT_PROFILE:
  nodejs         - Deploy Node.js bot (default)
  dotnet         - Deploy .NET bot

Examples:
  $0                              # Production nodejs deployment
  $0 staging nodejs               # Staging nodejs deployment
  $0 production dotnet            # Production dotnet deployment

EOF
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
    
    # Check required environment variables
    local required_vars=("ANTHROPIC_API_KEY" "GITHUB_TOKEN" "TARGET_REPO")
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_error "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    # Check disk space (minimum 5GB)
    local available_space=$(df / | tail -1 | awk '{print $4}')
    if [[ $available_space -lt 5242880 ]]; then # 5GB in KB
        log_warning "Less than 5GB disk space available"
    fi
    
    log_success "Pre-deployment checks passed"
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

# Build containers
build_containers() {
    log_info "Building containers..."
    
    cd "$PROJECT_ROOT"
    
    # Build with appropriate profile
    docker-compose build --no-cache
    
    log_success "Containers built successfully"
}

# Deploy configuration
deploy_config() {
    log_info "Deploying configuration..."
    
    # Create production override if it doesn't exist
    local override_file="$PROJECT_ROOT/docker-compose.${DEPLOYMENT_TYPE}.yml"
    
    if [[ ! -f "$override_file" ]] && [[ "$DEPLOYMENT_TYPE" == "production" ]]; then
        log_info "Creating production docker-compose override..."
        
        cat > "$override_file" << EOF
services:
  claude-bot:
    restart: always
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "5"
        compress: "true"
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp:noexec,nosuid,size=100m

  status-web:
    restart: always
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "5"
        compress: "true"
    security_opt:
      - no-new-privileges:true
EOF
        
        log_success "Production override created"
    fi
    
    # Generate configuration template if requested
    if [[ "${GENERATE_CONFIG_TEMPLATE:-false}" == "true" ]]; then
        python3 "$PROJECT_ROOT/scripts/config_manager.py" --save-template \
            "$PROJECT_ROOT/config/bot-config.${DEPLOYMENT_TYPE}.yml"
    fi
}

# Start services
start_services() {
    log_info "Starting services..."
    
    cd "$PROJECT_ROOT"
    
    local compose_files="-f docker-compose.yml"
    local override_file="docker-compose.${DEPLOYMENT_TYPE}.yml"
    
    if [[ -f "$override_file" ]]; then
        compose_files="$compose_files -f $override_file"
    fi
    
    # Stop existing services
    docker-compose $compose_files down
    
    # Start new services
    docker-compose $compose_files --profile "$BOT_PROFILE" up -d
    
    log_success "Services started"
}

# Health checks
wait_for_health() {
    log_info "Waiting for services to become healthy..."
    
    local max_attempts=30
    local attempt=0
    
    while [[ $attempt -lt $max_attempts ]]; do
        if docker-compose ps | grep -q "Up (healthy)"; then
            log_success "Services are healthy"
            return 0
        fi
        
        attempt=$((attempt + 1))
        log_info "Attempt $attempt/$max_attempts - waiting for health checks..."
        sleep 10
    done
    
    log_error "Services did not become healthy within expected time"
    log_info "Current status:"
    docker-compose ps
    return 1
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."
    
    # Check container status
    log_info "Container status:"
    docker-compose ps
    
    # Check logs for errors
    log_info "Checking for recent errors..."
    if docker-compose logs --tail=50 claude-bot | grep -i error; then
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
        
        # Test metrics endpoint
        if curl -sf http://localhost:8000/metrics >/dev/null; then
            log_success "Metrics endpoint is responding"
        else
            log_warning "Metrics endpoint is not responding"
        fi
    fi
    
    # Check configuration
    log_info "Validating configuration..."
    if docker-compose exec -T claude-bot python3 /bot/scripts/config_manager.py >/dev/null 2>&1; then
        log_success "Configuration is valid"
    else
        log_error "Configuration validation failed"
        return 1
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

# Rollback function
rollback() {
    log_error "Deployment failed. Initiating rollback..."
    
    # Stop current services
    docker-compose down
    
    # Restore from backup if available
    local backup_dir="$PROJECT_ROOT/backups"
    local latest_backup=$(ls -t "$backup_dir"/bot-data_*.tar.gz 2>/dev/null | head -1)
    
    if [[ -n "$latest_backup" ]]; then
        log_info "Restoring from backup: $(basename "$latest_backup")"
        
        docker run --rm \
            -v claude-bot-infrastructure_bot-data:/data \
            -v "$backup_dir:/backup" \
            alpine:latest \
            tar xzf "/backup/$(basename "$latest_backup")" -C /data
        
        log_success "Data restored from backup"
    fi
    
    # Start previous version
    # Note: In a real scenario, you'd want to keep track of the previous image version
    docker-compose --profile "$BOT_PROFILE" up -d
    
    log_info "Rollback completed"
}

# Main deployment function
main() {
    # Parse arguments
    case "${1:-}" in
        -h|--help)
            show_help
            exit 0
            ;;
        "")
            ;;
        development|staging|production)
            ;;
        *)
            log_error "Invalid deployment type: $1"
            show_help
            exit 1
            ;;
    esac
    
    log_info "Starting deployment: $DEPLOYMENT_TYPE with profile: $BOT_PROFILE"
    
    # Trap for cleanup on failure
    trap 'log_error "Deployment failed!"; rollback; exit 1' ERR
    
    # Deployment steps
    run_preflight_checks
    backup_data
    build_containers
    deploy_config
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
    echo "Bot Profile: $BOT_PROFILE"
    echo "Status Dashboard: http://localhost:8080"
    echo "Metrics: http://localhost:8000/metrics"
    echo "Health Check: http://localhost:8080/api/health"
    echo
    log_info "To view logs: docker-compose logs -f claude-bot"
    log_info "To check status: docker-compose ps"
}

# Run main function
main "$@"