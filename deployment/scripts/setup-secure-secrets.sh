#!/bin/bash
# Setup Secure Secrets for Claude Bot
# Creates Docker secret files with proper permissions

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Create secrets directory
SECRETS_DIR="./data/secrets"
mkdir -p "$SECRETS_DIR"
chmod 700 "$SECRETS_DIR"

print_status "Setting up secure secrets directory: $SECRETS_DIR"

# Function to create secure secret file
create_secret_file() {
    local secret_name="$1"
    local secret_value="$2"
    local file_path="$SECRETS_DIR/$secret_name"
    
    if [ -z "$secret_value" ]; then
        print_warning "Skipping empty secret: $secret_name"
        return
    fi
    
    echo "$secret_value" > "$file_path"
    chmod 600 "$file_path"
    print_success "Created secure secret file: $secret_name"
}

# Check if we should use interactive mode
INTERACTIVE=true
if [ "$1" = "--non-interactive" ]; then
    INTERACTIVE=false
fi

# Get secrets interactively or from environment
if [ "$INTERACTIVE" = true ]; then
    echo
    echo "Please provide the following secrets:"
    echo "======================================"
    echo
    
    read -s -p "GitHub Personal Access Token: " GITHUB_TOKEN
    echo
    read -s -p "Anthropic API Key: " ANTHROPIC_API_KEY
    echo
    read -p "Git Author Name [Claude Bot]: " GIT_AUTHOR_NAME
    GIT_AUTHOR_NAME="${GIT_AUTHOR_NAME:-Claude Bot}"
    read -p "Git Author Email [bot@claude.ai]: " GIT_AUTHOR_EMAIL
    GIT_AUTHOR_EMAIL="${GIT_AUTHOR_EMAIL:-bot@claude.ai}"
    echo
else
    # Use environment variables
    GITHUB_TOKEN="${GITHUB_TOKEN:-}"
    ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"
    GIT_AUTHOR_NAME="${GIT_AUTHOR_NAME:-Claude Bot}"
    GIT_AUTHOR_EMAIL="${GIT_AUTHOR_EMAIL:-bot@claude.ai}"
fi

# Validate required secrets
if [ -z "$GITHUB_TOKEN" ] || [ -z "$ANTHROPIC_API_KEY" ]; then
    print_error "GitHub Token and Anthropic API Key are required"
    exit 1
fi

# Create secret files
print_status "Creating secure secret files..."

create_secret_file "github_token" "$GITHUB_TOKEN"
create_secret_file "anthropic_api_key" "$ANTHROPIC_API_KEY"
create_secret_file "git_author_name" "$GIT_AUTHOR_NAME"
create_secret_file "git_author_email" "$GIT_AUTHOR_EMAIL"

# Create .gitignore entry for secrets
if ! grep -q "data/secrets" .gitignore 2>/dev/null; then
    echo "# Secret files - DO NOT COMMIT" >> .gitignore
    echo "data/secrets/" >> .gitignore
    print_success "Added secrets directory to .gitignore"
fi

# Test secret loading
print_status "Testing secure secret loading..."
if python3 scripts/secrets_loader.py --validate-only; then
    print_success "Secret validation passed"
else
    print_warning "Secret validation failed - check your setup"
fi

echo
print_success "🔐 Secure secrets setup completed!"
echo
echo "📝 Next Steps:"
echo "=============="
echo "1. Start the bot with secure configuration:"
echo "   docker-compose -f docker-compose.yml -f docker-compose.secure.yml up -d"
echo
echo "2. Or use Azure Key Vault:"
echo "   docker-compose -f docker-compose.yml -f docker-compose.azure.yml up -d"
echo
echo "3. Monitor the bot:"
echo "   docker logs claude-orchestrator-secure -f"
echo
echo "🛡️  Security Notes:"
echo "=================="
echo "• Secret files have 600 permissions (owner read/write only)"
echo "• Secrets directory is added to .gitignore"
echo "• Workers load secrets securely at runtime"
echo "• No secrets are visible in environment variables"