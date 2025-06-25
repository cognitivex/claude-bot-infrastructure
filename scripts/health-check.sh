#!/bin/bash
# Health check script for Claude Bot instances

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}🔍 $1${NC}"
    echo "$(printf '=%.0s' {1..50})"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "ℹ️  $1"
}

# Function to check container status
check_container() {
    local container_name=$1
    local service_name=$2
    
    if docker ps --format "table {{.Names}}" | grep -q "^${container_name}$"; then
        print_success "${service_name} container is running"
        
        # Check container health
        local status=$(docker inspect --format='{{.State.Status}}' $container_name 2>/dev/null || echo "unknown")
        if [ "$status" = "running" ]; then
            print_success "${service_name} status: healthy"
        else
            print_warning "${service_name} status: $status"
        fi
        
        # Check resource usage
        local stats=$(docker stats --no-stream --format "table {{.CPUPerc}}\t{{.MemUsage}}" $container_name | tail -n 1)
        print_info "${service_name} resources: $stats"
        
        return 0
    else
        print_error "${service_name} container is not running"
        return 1
    fi
}

# Function to check logs for errors
check_logs() {
    local container_name=$1
    local service_name=$2
    
    print_info "Checking ${service_name} logs for recent errors..."
    local error_count=$(docker logs --since=10m $container_name 2>&1 | grep -i "error\|exception\|failed" | wc -l)
    
    if [ $error_count -eq 0 ]; then
        print_success "${service_name} logs: no recent errors"
    else
        print_warning "${service_name} logs: $error_count recent errors/warnings"
        echo "Recent errors:"
        docker logs --since=10m $container_name 2>&1 | grep -i "error\|exception\|failed" | tail -5
    fi
}

# Function to check environment variables
check_environment() {
    local container_name=$1
    local service_name=$2
    
    print_info "Checking ${service_name} environment..."
    
    # Check required environment variables
    local env_check=$(docker exec $container_name env | grep -E "ANTHROPIC_API_KEY|GITHUB_TOKEN|TARGET_REPO" | wc -l)
    
    if [ $env_check -ge 3 ]; then
        print_success "${service_name} environment: required variables set"
    else
        print_warning "${service_name} environment: some required variables may be missing"
    fi
}

# Function to test GitHub connectivity
test_github_connectivity() {
    local container_name=$1
    local service_name=$2
    
    print_info "Testing ${service_name} GitHub connectivity..."
    
    if docker exec $container_name gh auth status >/dev/null 2>&1; then
        print_success "${service_name} GitHub auth: authenticated"
    else
        print_warning "${service_name} GitHub auth: not authenticated or token expired"
    fi
}

# Function to check data volumes
check_data_volumes() {
    local volume_name=$1
    local service_name=$2
    
    print_info "Checking ${service_name} data volumes..."
    
    # Check for data volume (with or without project prefix)
    if docker volume ls --format "{{.Name}}" | grep -E "(^|_)${volume_name}data($|_)"; then
        local full_volume_name=$(docker volume ls --format "{{.Name}}" | grep -E "(^|_)${volume_name}data($|_)" | head -1)
        local size=$(docker run --rm -v "${full_volume_name}:/data" alpine du -sh /data 2>/dev/null | cut -f1 || echo "N/A")
        print_success "${service_name} data volume exists (size: $size)"
    else
        print_warning "${service_name} data volume not found"
    fi
    
    # Check for logs volume (with or without project prefix)
    if docker volume ls --format "{{.Name}}" | grep -E "(^|_)${volume_name}logs($|_)"; then
        local full_volume_name=$(docker volume ls --format "{{.Name}}" | grep -E "(^|_)${volume_name}logs($|_)" | head -1)
        local size=$(docker run --rm -v "${full_volume_name}:/logs" alpine du -sh /logs 2>/dev/null | cut -f1 || echo "N/A")
        print_success "${service_name} logs volume exists (size: $size)"
    else
        print_warning "${service_name} logs volume not found"
    fi
}

# Main health check
main() {
    print_header "Claude Bot Health Check"
    
    # Check Docker daemon
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker daemon is not running"
        exit 1
    fi
    print_success "Docker daemon is running"
    
    echo ""
    print_header "Node.js Bot Health Check"
    
    if check_container "claude-bot" "Node.js Bot"; then
        check_logs "claude-bot" "Node.js Bot"
        check_environment "claude-bot" "Node.js Bot"
        test_github_connectivity "claude-bot" "Node.js Bot"
        check_data_volumes "bot-" "Node.js Bot"
    fi
    
    echo ""
    print_header ".NET Bot Health Check"
    
    if check_container "claude-bot-dotnet" ".NET Bot"; then
        check_logs "claude-bot-dotnet" ".NET Bot"
        check_environment "claude-bot-dotnet" ".NET Bot"
        test_github_connectivity "claude-bot-dotnet" ".NET Bot"
        check_data_volumes "bot-.*dotnet" ".NET Bot"
        
        # Additional .NET specific checks
        print_info "Checking .NET Bot specific functionality..."
        if docker exec claude-bot-dotnet dotnet --version >/dev/null 2>&1; then
            print_success ".NET Bot: .NET SDK available"
        else
            print_error ".NET Bot: .NET SDK not available"
        fi
        
        if docker exec claude-bot-dotnet node --version >/dev/null 2>&1; then
            local node_version=$(docker exec claude-bot-dotnet node --version)
            print_success ".NET Bot: Node.js available ($node_version)"
        else
            print_error ".NET Bot: Node.js not available"
        fi
    fi
    
    echo ""
    print_header "System Resources"
    
    # Check overall Docker resource usage
    print_info "Docker system resource usage:"
    docker system df
    
    echo ""
    print_header "Network Connectivity"
    
    # Test internet connectivity from containers
    if docker run --rm alpine ping -c 1 github.com >/dev/null 2>&1; then
        print_success "Internet connectivity: available"
    else
        print_warning "Internet connectivity: limited or unavailable"
    fi
    
    echo ""
    print_header "Summary"
    
    local running_containers=$(docker ps --filter "name=claude-bot" --format "{{.Names}}" | wc -l)
    print_info "Active Claude Bot containers: $running_containers"
    
    if [ $running_containers -eq 0 ]; then
        print_warning "No Claude Bot containers are currently running"
        echo ""
        echo "To start the bots:"
        echo "  Node.js Bot: docker-compose --profile nodejs up -d"
        echo "  .NET Bot:    docker-compose --profile dotnet up -d"
        echo "  Both:        docker-compose --profile nodejs --profile dotnet up -d"
    else
        print_success "Claude Bot infrastructure is operational"
    fi
}

# Run main function
main "$@"