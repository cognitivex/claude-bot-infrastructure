#!/bin/bash
# Cleanup script for Claude Bot test environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}🧹 $1${NC}"
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

# Function to confirm action
confirm() {
    local message=$1
    local default=${2:-"n"}
    
    if [ "$default" = "y" ]; then
        prompt="[Y/n]"
    else
        prompt="[y/N]"
    fi
    
    read -p "$message $prompt: " response
    
    if [ -z "$response" ]; then
        response=$default
    fi
    
    case $response in
        [Yy]|[Yy][Ee][Ss]) return 0 ;;
        *) return 1 ;;
    esac
}

# Function to stop containers
stop_containers() {
    print_info "Stopping Claude Bot containers..."
    
    if docker ps | grep -q "claude-bot"; then
        docker-compose --profile nodejs --profile dotnet down
        print_success "Containers stopped"
    else
        print_info "No containers are running"
    fi
}

# Function to remove containers
remove_containers() {
    print_info "Removing Claude Bot containers..."
    
    local containers=$(docker ps -a --filter "name=claude-bot" --format "{{.Names}}")
    
    if [ -n "$containers" ]; then
        echo "$containers" | xargs docker rm -f
        print_success "Containers removed"
    else
        print_info "No containers to remove"
    fi
}

# Function to remove images
remove_images() {
    print_info "Removing Claude Bot Docker images..."
    
    local images=$(docker images --filter "reference=claude-bot*" --format "{{.Repository}}:{{.Tag}}")
    
    if [ -n "$images" ]; then
        echo "$images" | xargs docker rmi -f
        print_success "Images removed"
    else
        print_info "No images to remove"
    fi
}

# Function to remove volumes
remove_volumes() {
    print_info "Removing Claude Bot data volumes..."
    
    local volumes=$(docker volume ls --filter "name=bot-" --format "{{.Name}}")
    
    if [ -n "$volumes" ]; then
        echo "$volumes" | xargs docker volume rm
        print_success "Volumes removed"
    else
        print_info "No volumes to remove"
    fi
}

# Function to clean test files
clean_test_files() {
    print_info "Cleaning up test files..."
    
    # Remove test issue JSON files
    if ls test-issues-*.json 1> /dev/null 2>&1; then
        rm test-issues-*.json
        print_success "Test issue files removed"
    fi
    
    # Clean up node_modules in test projects
    if [ -d "test-projects/nodejs-test/node_modules" ]; then
        rm -rf test-projects/nodejs-test/node_modules
        print_success "Node.js test project node_modules removed"
    fi
    
    # Clean up bin/obj in .NET test project
    if [ -d "test-projects/dotnet-test/bin" ]; then
        rm -rf test-projects/dotnet-test/bin
        print_success ".NET test project bin directory removed"
    fi
    
    if [ -d "test-projects/dotnet-test/obj" ]; then
        rm -rf test-projects/dotnet-test/obj
        print_success ".NET test project obj directory removed"
    fi
    
    # Remove test environment files if they exist
    if [ -f ".env.test" ]; then
        print_warning "Found .env.test file - keeping for reference"
    fi
    
    if [ -f ".env.dotnet.test" ]; then
        print_warning "Found .env.dotnet.test file - keeping for reference"
    fi
}

# Function to close test GitHub issues
close_test_issues() {
    local repo=$1
    local label=${2:-"claude-bot-test"}
    
    if [ -z "$repo" ]; then
        print_warning "No repository specified - skipping GitHub issue cleanup"
        return
    fi
    
    print_info "Closing test issues in $repo with label '$label'..."
    
    # Check if gh CLI is available
    if ! command -v gh &> /dev/null; then
        print_warning "GitHub CLI not found - skipping issue cleanup"
        return
    fi
    
    # Check if authenticated
    if ! gh auth status &> /dev/null; then
        print_warning "Not authenticated with GitHub CLI - skipping issue cleanup"
        return
    fi
    
    # Get open issues with test label
    local issues=$(gh issue list --repo "$repo" --label "$label" --state open --json number --jq '.[].number')
    
    if [ -n "$issues" ]; then
        local count=$(echo "$issues" | wc -l)
        if confirm "Close $count test issues in $repo?"; then
            echo "$issues" | while read -r issue_num; do
                gh issue close "$issue_num" --repo "$repo" --comment "Closing test issue as part of cleanup"
                print_info "Closed issue #$issue_num"
            done
            print_success "Test issues closed"
        fi
    else
        print_info "No open test issues found"
    fi
}

# Function for complete cleanup
complete_cleanup() {
    print_header "Complete Claude Bot Test Environment Cleanup"
    
    if ! confirm "This will remove all containers, images, volumes, and test files. Continue?"; then
        print_info "Cleanup cancelled"
        exit 0
    fi
    
    stop_containers
    remove_containers
    remove_images
    remove_volumes
    clean_test_files
    
    # Docker system cleanup
    print_info "Running Docker system cleanup..."
    docker system prune -f
    print_success "Docker system cleanup completed"
    
    print_success "Complete cleanup finished"
}

# Function for selective cleanup
selective_cleanup() {
    print_header "Selective Claude Bot Test Environment Cleanup"
    
    if confirm "Stop containers?"; then
        stop_containers
    fi
    
    if confirm "Remove containers?"; then
        remove_containers
    fi
    
    if confirm "Remove Docker images?"; then
        remove_images
    fi
    
    if confirm "Remove data volumes? (WARNING: This will delete all bot data)"; then
        remove_volumes
    fi
    
    if confirm "Clean test files?"; then
        clean_test_files
    fi
    
    read -p "Repository to clean test issues from (or press Enter to skip): " repo
    if [ -n "$repo" ]; then
        close_test_issues "$repo"
    fi
    
    print_success "Selective cleanup completed"
}

# Main function
main() {
    local mode=${1:-"interactive"}
    
    case $mode in
        "complete")
            complete_cleanup
            ;;
        "containers")
            stop_containers
            remove_containers
            ;;
        "images")
            remove_images
            ;;
        "volumes")  
            remove_volumes
            ;;
        "files")
            clean_test_files
            ;;
        "issues")
            if [ -z "$2" ]; then
                print_error "Repository required for issue cleanup"
                echo "Usage: $0 issues <owner/repo> [label]"
                exit 1
            fi
            close_test_issues "$2" "$3"
            ;;
        "help")
            cat << EOF
Claude Bot Test Environment Cleanup Script

Usage: $0 [MODE] [OPTIONS]

Modes:
  interactive  Interactive cleanup (default)
  complete     Complete cleanup (all components)
  containers   Stop and remove containers only  
  images       Remove Docker images only
  volumes      Remove data volumes only
  files        Clean test files only
  issues       Close test GitHub issues
  help         Show this help

Examples:
  $0                           # Interactive cleanup
  $0 complete                  # Complete cleanup
  $0 containers                # Remove containers only
  $0 issues owner/repo         # Close test issues
  $0 issues owner/repo my-label # Close issues with custom label

EOF
            ;;
        *)
            selective_cleanup
            ;;
    esac
}

# Run main function with all arguments
main "$@"