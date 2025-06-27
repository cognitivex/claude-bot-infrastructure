#!/bin/bash
# Azure Setup Script for Claude Bot Infrastructure

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
RESOURCE_GROUP="claude-bot-rg"
KEYVAULT_NAME="claude-bot-keyvault"
LOCATION="eastus"
SKIP_INFRASTRUCTURE=false
INTERACTIVE=true

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if Azure CLI is installed and logged in
check_azure_cli() {
    print_status "Checking Azure CLI..."
    
    if ! command -v az &> /dev/null; then
        print_error "Azure CLI is not installed. Please install it first:"
        echo "https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
        exit 1
    fi
    
    if ! az account show &> /dev/null; then
        print_error "Not logged into Azure CLI. Please run 'az login' first."
        exit 1
    fi
    
    print_success "Azure CLI is ready"
}

# Function to check if required Python packages are available
check_python_deps() {
    print_status "Checking Python dependencies..."
    
    if ! python3 -c "import azure.keyvault.secrets, azure.identity" &> /dev/null; then
        print_warning "Azure SDK for Python not found. Installing..."
        pip3 install azure-keyvault-secrets azure-identity
    fi
    
    print_success "Python dependencies are ready"
}

# Function to prompt for user input
prompt_input() {
    local prompt="$1"
    local default="$2"
    local secret="$3"
    
    if [ "$INTERACTIVE" = true ]; then
        if [ "$secret" = "true" ]; then
            read -s -p "$prompt [$default]: " input
            echo
        else
            read -p "$prompt [$default]: " input
        fi
        echo "${input:-$default}"
    else
        echo "$default"
    fi
}

# Function to setup Azure infrastructure
setup_infrastructure() {
    if [ "$SKIP_INFRASTRUCTURE" = true ]; then
        print_status "Skipping infrastructure setup"
        return 0
    fi
    
    print_status "Setting up Azure infrastructure..."
    
    # Run the Python Azure integration script
    python3 scripts/azure_integration.py \
        --action setup \
        --resource-group "$RESOURCE_GROUP" \
        --keyvault-name "$KEYVAULT_NAME"
    
    if [ $? -eq 0 ]; then
        print_success "Azure infrastructure setup completed"
    else
        print_error "Azure infrastructure setup failed"
        exit 1
    fi
}

# Function to collect and store secrets
setup_secrets() {
    print_status "Setting up secrets in Azure Key Vault..."
    
    if [ "$INTERACTIVE" = true ]; then
        echo
        echo "Please provide the following secrets:"
        echo "----------------------------------------"
        
        GITHUB_TOKEN=$(prompt_input "GitHub Personal Access Token" "" "true")
        ANTHROPIC_API_KEY=$(prompt_input "Anthropic API Key" "" "true")
        GIT_AUTHOR_NAME=$(prompt_input "Git Author Name" "Claude Bot" "false")
        GIT_AUTHOR_EMAIL=$(prompt_input "Git Author Email" "bot@claude.ai" "false")
        TARGET_REPO=$(prompt_input "Target Repository (owner/repo)" "" "false")
        
        echo
    else
        # Non-interactive mode - use environment variables
        GITHUB_TOKEN="${GITHUB_TOKEN:-}"
        ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"
        GIT_AUTHOR_NAME="${GIT_AUTHOR_NAME:-Claude Bot}"
        GIT_AUTHOR_EMAIL="${GIT_AUTHOR_EMAIL:-bot@claude.ai}"
        TARGET_REPO="${TARGET_REPO:-}"
    fi
    
    # Validate required secrets
    if [ -z "$GITHUB_TOKEN" ] || [ -z "$ANTHROPIC_API_KEY" ]; then
        print_error "GitHub Token and Anthropic API Key are required"
        exit 1
    fi
    
    # Add secrets to Key Vault
    print_status "Adding secrets to Key Vault..."
    
    az keyvault secret set --vault-name "$KEYVAULT_NAME" --name "github-token" --value "$GITHUB_TOKEN" > /dev/null
    az keyvault secret set --vault-name "$KEYVAULT_NAME" --name "anthropic-api-key" --value "$ANTHROPIC_API_KEY" > /dev/null
    az keyvault secret set --vault-name "$KEYVAULT_NAME" --name "git-author-name" --value "$GIT_AUTHOR_NAME" > /dev/null
    az keyvault secret set --vault-name "$KEYVAULT_NAME" --name "git-author-email" --value "$GIT_AUTHOR_EMAIL" > /dev/null
    
    if [ -n "$TARGET_REPO" ]; then
        az keyvault secret set --vault-name "$KEYVAULT_NAME" --name "target-repo" --value "$TARGET_REPO" > /dev/null
    fi
    
    print_success "Secrets added to Key Vault successfully"
}

# Function to create environment configuration
create_env_config() {
    print_status "Creating Azure environment configuration..."
    
    # Get managed identity client ID
    CLIENT_ID=$(az identity show \
        --name "claude-bot-identity" \
        --resource-group "$RESOURCE_GROUP" \
        --query clientId \
        --output tsv 2>/dev/null || echo "")
    
    # Create .env.azure file
    cat > .env.azure << EOF
# Azure Configuration for Claude Bot
# Generated by setup-azure.sh

# Azure Key Vault
AZURE_KEYVAULT_NAME=$KEYVAULT_NAME
AZURE_RESOURCE_GROUP=$RESOURCE_GROUP

# Managed Identity (for Azure deployments)
AZURE_CLIENT_ID=$CLIENT_ID
AZURE_USE_MANAGED_IDENTITY=true

# Target Repository
TARGET_REPO=$TARGET_REPO

# Logging
AZURE_LOG_LEVEL=INFO

# Data paths (adjust as needed)
AZURE_DATA_PATH=./data
AZURE_LOGS_PATH=./logs
EOF
    
    chmod 600 .env.azure
    
    print_success "Environment configuration created: .env.azure"
}

# Function to validate the setup
validate_setup() {
    print_status "Validating Azure setup..."
    
    # Test secret retrieval
    export AZURE_KEYVAULT_NAME="$KEYVAULT_NAME"
    export AZURE_CLIENT_ID="$CLIENT_ID"
    
    if python3 scripts/secrets_loader.py --validate-only; then
        print_success "Secret validation passed"
    else
        print_warning "Secret validation failed - this might be expected if not running in Azure"
    fi
    
    # Test Azure integration
    if python3 scripts/azure_integration.py --action setup --resource-group "$RESOURCE_GROUP" --keyvault-name "$KEYVAULT_NAME" 2>/dev/null; then
        print_success "Azure integration validation passed"
    else
        print_warning "Azure integration validation had issues"
    fi
}

# Function to create deployment files
create_deployment_files() {
    print_status "Creating deployment files..."
    
    # Create Azure DevOps pipeline
    python3 scripts/azure_integration.py \
        --action create-pipeline \
        --resource-group "$RESOURCE_GROUP" \
        --keyvault-name "$KEYVAULT_NAME" \
        --target-repo "$TARGET_REPO"
    
    # Create Terraform configuration
    python3 scripts/azure_integration.py \
        --action create-terraform \
        --resource-group "$RESOURCE_GROUP" \
        --keyvault-name "$KEYVAULT_NAME"
    
    print_success "Deployment files created"
}

# Function to show next steps
show_next_steps() {
    echo
    echo "🎉 Azure setup completed successfully!"
    echo
    echo "📝 Next Steps:"
    echo "=============="
    echo
    echo "1. Test the local setup:"
    echo "   source .env.azure"
    echo "   docker-compose -f docker-compose.yml -f docker-compose.azure.yml up -d"
    echo
    echo "2. For Azure Container Instances deployment:"
    echo "   python3 scripts/azure_integration.py --action create-aci --image your-registry/claude-bot:latest --target-repo $TARGET_REPO"
    echo
    echo "3. For Azure DevOps integration:"
    echo "   - Import the generated azure-pipelines.yml into your Azure DevOps project"
    echo "   - Create a service connection to your Azure subscription"
    echo "   - Create a variable group named 'claude-bot-secrets' linked to your Key Vault"
    echo
    echo "4. For Terraform deployment:"
    echo "   - Copy terraform.tfvars.example to terraform.tfvars"
    echo "   - Fill in your values"
    echo "   - Run: terraform init && terraform plan && terraform apply"
    echo
    echo "🔗 Useful Links:"
    echo "==============="
    echo "• Resource Group: https://portal.azure.com/#@/resource/subscriptions/$(az account show --query id --output tsv)/resourceGroups/$RESOURCE_GROUP"
    echo "• Key Vault: https://portal.azure.com/#@/resource/subscriptions/$(az account show --query id --output tsv)/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.KeyVault/vaults/$KEYVAULT_NAME"
    echo
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  -g, --resource-group NAME    Azure resource group name (default: claude-bot-rg)"
    echo "  -k, --keyvault-name NAME     Key Vault name (default: claude-bot-keyvault)" 
    echo "  -l, --location LOCATION      Azure location (default: eastus)"
    echo "  -s, --skip-infrastructure    Skip infrastructure setup"
    echo "  -n, --non-interactive        Non-interactive mode (use environment variables)"
    echo "  -h, --help                   Show this help message"
    echo
    echo "Environment variables (for non-interactive mode):"
    echo "  GITHUB_TOKEN                 GitHub personal access token"
    echo "  ANTHROPIC_API_KEY            Anthropic API key"
    echo "  GIT_AUTHOR_NAME             Git author name (optional)"
    echo "  GIT_AUTHOR_EMAIL            Git author email (optional)"
    echo "  TARGET_REPO                 Target repository (owner/repo)"
    echo
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -g|--resource-group)
            RESOURCE_GROUP="$2"
            shift 2
            ;;
        -k|--keyvault-name)
            KEYVAULT_NAME="$2"
            shift 2
            ;;
        -l|--location)
            LOCATION="$2"
            shift 2
            ;;
        -s|--skip-infrastructure)
            SKIP_INFRASTRUCTURE=true
            shift
            ;;
        -n|--non-interactive)
            INTERACTIVE=false
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    echo "🚀 Claude Bot Azure Setup"
    echo "========================="
    echo
    
    # Pre-flight checks
    check_azure_cli
    check_python_deps
    
    # Setup infrastructure
    setup_infrastructure
    
    # Setup secrets
    setup_secrets
    
    # Create configuration
    create_env_config
    
    # Validate setup
    validate_setup
    
    # Create deployment files
    create_deployment_files
    
    # Show next steps
    show_next_steps
}

# Run main function
main