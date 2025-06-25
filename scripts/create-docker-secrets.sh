#!/bin/bash
# Create Docker Secrets from .env file
# This script reads your .env file and creates Docker secrets safely

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENV_FILE="${1:-.env}"
FORCE_RECREATE="${2:-false}"

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

# Show usage
show_usage() {
    cat << EOF
Usage: $0 [ENV_FILE] [FORCE_RECREATE]

Create Docker secrets from environment file.

Arguments:
  ENV_FILE        Path to .env file (default: .env)
  FORCE_RECREATE  true/false - recreate existing secrets (default: false)

Examples:
  $0                    # Use .env file
  $0 .env.production    # Use specific env file
  $0 .env true          # Force recreate existing secrets

Required secrets:
  - GITHUB_TOKEN
  - ANTHROPIC_API_KEY

Optional secrets:
  - Any other KEY=value pairs in your .env file

EOF
}

# Check if Docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running or not accessible"
        log_info "Please start Docker and try again"
        exit 1
    fi
    
    # Check if we're in Swarm mode (required for secrets)
    if ! docker info 2>/dev/null | grep -q "Swarm: active"; then
        log_warning "Docker is not in Swarm mode. Initializing Swarm..."
        docker swarm init >/dev/null 2>&1 || {
            log_info "Swarm already initialized or initialization failed"
            log_info "If you're already in a swarm, this is normal"
        }
    fi
}

# Check if secret exists
secret_exists() {
    local secret_name="$1"
    docker secret ls --format "{{.Name}}" | grep -q "^${secret_name}$"
}

# Create or update a secret
create_secret() {
    local secret_name="$1"
    local secret_value="$2"
    
    # Convert to lowercase and replace underscores for Docker secret naming
    local docker_secret_name=$(echo "$secret_name" | tr '[:upper:]' '[:lower:]' | tr '_' '-')
    
    # Check if secret exists
    if secret_exists "$docker_secret_name"; then
        if [ "$FORCE_RECREATE" = "true" ]; then
            log_warning "Secret '$docker_secret_name' exists. Recreating..."
            docker secret rm "$docker_secret_name" >/dev/null
        else
            log_info "Secret '$docker_secret_name' already exists. Skipping (use 'true' as second argument to force recreate)"
            return 0
        fi
    fi
    
    # Create the secret
    echo -n "$secret_value" | docker secret create "$docker_secret_name" - >/dev/null
    
    if [ $? -eq 0 ]; then
        log_success "Created secret: $docker_secret_name"
        
        # Show masked value for verification
        local masked_value="${secret_value:0:10}...${secret_value: -4}"
        log_info "  Value: $masked_value"
    else
        log_error "Failed to create secret: $docker_secret_name"
        return 1
    fi
}

# Parse .env file and create secrets
process_env_file() {
    local env_file="$1"
    local created_count=0
    local failed_count=0
    local required_secrets_found=0
    
    # Required secrets
    local required_secrets=("GITHUB_TOKEN" "ANTHROPIC_API_KEY")
    local found_required=()
    
    log_info "Processing $env_file..."
    
    while IFS= read -r line || [ -n "$line" ]; do
        # Skip empty lines and comments
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
        
        # Parse KEY=value
        if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
            local key="${BASH_REMATCH[1]}"
            local value="${BASH_REMATCH[2]}"
            
            # Remove quotes if present
            value="${value%\"}"
            value="${value#\"}"
            value="${value%\'}"
            value="${value#\'}"
            
            # Skip if empty value
            if [ -z "$value" ]; then
                log_warning "Skipping $key - empty value"
                continue
            fi
            
            # Check if it's a required secret
            for req in "${required_secrets[@]}"; do
                if [ "$key" = "$req" ]; then
                    found_required+=("$key")
                    ((required_secrets_found++))
                fi
            done
            
            # Create the secret
            if create_secret "$key" "$value"; then
                ((created_count++))
            else
                ((failed_count++))
            fi
        fi
    done < "$env_file"
    
    # Check if all required secrets were found
    local missing_required=()
    for req in "${required_secrets[@]}"; do
        local found=false
        for found_req in "${found_required[@]}"; do
            if [ "$req" = "$found_req" ]; then
                found=true
                break
            fi
        done
        if [ "$found" = false ]; then
            missing_required+=("$req")
        fi
    done
    
    # Summary
    echo
    log_info "Summary:"
    log_info "  Created: $created_count secrets"
    if [ $failed_count -gt 0 ]; then
        log_warning "  Failed: $failed_count secrets"
    fi
    
    if [ ${#missing_required[@]} -gt 0 ]; then
        log_error "Missing required secrets: ${missing_required[*]}"
        log_info "Please add these to your $env_file file"
        return 1
    else
        log_success "All required secrets found and created!"
    fi
    
    return 0
}

# Main execution
main() {
    # Check arguments
    if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
        show_usage
        exit 0
    fi
    
    # Check if .env file exists
    if [ ! -f "$ENV_FILE" ]; then
        log_error "Environment file not found: $ENV_FILE"
        log_info "Please create a .env file with your secrets first"
        echo
        log_info "Example .env file:"
        cat << 'EOF'
# Required API Keys
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx

# Optional: Additional configuration
TARGET_REPO=myorg/myrepo
BOT_LABEL=claude-bot
EOF
        exit 1
    fi
    
    # Check file permissions
    if [ ! -r "$ENV_FILE" ]; then
        log_error "Cannot read $ENV_FILE - check permissions"
        exit 1
    fi
    
    # Warn if file has loose permissions
    if [ -f "$ENV_FILE" ]; then
        local perms=$(stat -c %a "$ENV_FILE" 2>/dev/null || stat -f %OLp "$ENV_FILE" 2>/dev/null || echo "unknown")
        if [ "$perms" != "600" ] && [ "$perms" != "unknown" ]; then
            log_warning "$ENV_FILE has permissions $perms (recommended: 600)"
            log_info "Fix with: chmod 600 $ENV_FILE"
        fi
    fi
    
    log_info "🔐 Docker Secrets Creator"
    log_info "Reading from: $ENV_FILE"
    
    # Check Docker
    check_docker
    
    # Process the env file
    process_env_file "$ENV_FILE"
    
    if [ $? -eq 0 ]; then
        echo
        log_success "✅ Docker secrets created successfully!"
        echo
        log_info "To use these secrets, deploy with:"
        echo
        echo "  docker-compose -f docker-compose.yml -f docker-compose.secrets.yml --profile dynamic up -d"
        echo
        log_info "To list all secrets:"
        echo "  docker secret ls"
        echo
        log_info "To remove a secret:"
        echo "  docker secret rm secret-name"
    else
        exit 1
    fi
}

# Run main
main "$@"