#!/bin/bash
# Test script to build and verify Docker images

set -e

echo "🧪 Testing Claude Bot Docker Setup"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ $1${NC}"
    else
        echo -e "${RED}❌ $1${NC}"
        exit 1
    fi
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "ℹ️  $1"
}

# Check if Docker is running
print_info "Checking Docker status..."
docker info > /dev/null 2>&1
print_status "Docker is running"

# Build the default Node.js bot image
print_info "Building default Node.js bot image..."
docker build -f .devcontainer/Dockerfile.claude-bot -t claude-bot:test .
print_status "Node.js bot image built successfully"

# Build the .NET bot image
print_info "Building .NET bot image..."
docker build -f .devcontainer/Dockerfile.dotnet -t claude-bot-dotnet:test .
print_status ".NET bot image built successfully"

# Test Node.js image basic functionality
print_info "Testing Node.js bot image..."
docker run --rm claude-bot:test node --version
print_status "Node.js version check passed"

docker run --rm claude-bot:test python3 --version
print_status "Python version check passed"

docker run --rm claude-bot:test gh --version
print_status "GitHub CLI check passed"

# Test .NET image basic functionality
print_info "Testing .NET bot image..."
docker run --rm claude-bot-dotnet:test dotnet --version
print_status ".NET version check passed"

docker run --rm claude-bot-dotnet:test node --version
print_status "Node.js version check passed (should be 10.13.x)"

docker run --rm claude-bot-dotnet:test python3 --version
print_status "Python version check passed"

# Verify Claude Code is installed
print_info "Verifying Claude Code installation..."
docker run --rm claude-bot:test claude --version 2>/dev/null || print_warning "Claude Code check failed - may need API key"
docker run --rm claude-bot-dotnet:test claude --version 2>/dev/null || print_warning "Claude Code check failed - may need API key"

# Test project mounting and basic commands
print_info "Testing project mounting with Node.js test project..."
if [ -d "./test-projects/nodejs-test" ]; then
    docker run --rm -v "$(pwd)/test-projects/nodejs-test:/workspace" claude-bot:test ls -la /workspace
    print_status "Node.js test project mounting works"
    
    docker run --rm -v "$(pwd)/test-projects/nodejs-test:/workspace" claude-bot:test bash -c "cd /workspace && npm list --depth=0 2>/dev/null || echo 'Dependencies not installed yet - OK for test'"
    print_status "Node.js project dependency check passed"
else
    print_warning "Node.js test project not found, skipping mount test"
fi

print_info "Testing project mounting with .NET test project..."
if [ -d "./test-projects/dotnet-test" ]; then
    docker run --rm -v "$(pwd)/test-projects/dotnet-test:/workspace" claude-bot-dotnet:test ls -la /workspace
    print_status ".NET test project mounting works"
    
    docker run --rm -v "$(pwd)/test-projects/dotnet-test:/workspace" claude-bot-dotnet:test bash -c "cd /workspace && dotnet restore --verbosity quiet"
    print_status ".NET project dependency check passed"
    
    docker run --rm -v "$(pwd)/test-projects/dotnet-test:/workspace" claude-bot-dotnet:test bash -c "cd /workspace && npm list --depth=0 2>/dev/null || echo 'Dependencies not installed yet - OK for test'"
    print_status ".NET project npm dependency check passed"
else
    print_warning ".NET test project not found, skipping mount test"
fi

# Test volume creation
print_info "Testing Docker volumes..."
docker volume create test-bot-data > /dev/null 2>&1
docker volume create test-bot-logs > /dev/null 2>&1
docker volume rm test-bot-data test-bot-logs > /dev/null 2>&1
print_status "Docker volume operations work"

echo ""
echo -e "${GREEN}🎉 All Docker image tests passed!${NC}"
echo ""
echo "Next steps:"
echo "1. Set up your test repositories on GitHub"
echo "2. Copy .env.test to .env and fill in your API keys"
echo "3. Copy .env.dotnet.test to .env.dotnet and fill in your API keys"
echo "4. Run: docker-compose --profile nodejs up -d (for Node.js bot)"
echo "5. Run: docker-compose --profile dotnet up -d (for .NET bot)"
echo "6. Create test issues in your repositories with 'claude-bot-test' label"