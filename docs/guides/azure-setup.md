# Azure Secrets Management for Claude Bot

## Overview

The Claude Bot infrastructure has comprehensive Azure integration for secure secret management using Azure Key Vault, Azure Container Instances, and Azure DevOps integration.

## Azure Services Integration

### 🔐 Azure Key Vault (Primary)
- **Centralized secret management**
- **Access policies and RBAC**
- **Audit logging and monitoring**
- **Automatic secret rotation**

### 🏗️ Azure Container Instances (Optional)
- **Serverless container execution**
- **Built-in Azure identity integration**
- **Cost-effective for periodic bot runs**

### 🚀 Azure DevOps (CI/CD)
- **Pipeline integration with Key Vault**
- **Service connections for authentication**
- **Scheduled bot execution**

## Setting Up Azure Key Vault

### 1. Create Azure Key Vault

```bash
# Create resource group
az group create --name claude-bot-rg --location eastus

# Create Key Vault
az keyvault create \
  --name claude-bot-keyvault \
  --resource-group claude-bot-rg \
  --location eastus \
  --sku standard

# Enable Key Vault for deployment
az keyvault update \
  --name claude-bot-keyvault \
  --resource-group claude-bot-rg \
  --enabled-for-deployment true \
  --enabled-for-template-deployment true
```

### 2. Add Secrets to Key Vault

```bash
# Add required secrets
az keyvault secret set \
  --vault-name claude-bot-keyvault \
  --name "github-token" \
  --value "your_github_token_here"

az keyvault secret set \
  --vault-name claude-bot-keyvault \
  --name "anthropic-api-key" \
  --value "your_anthropic_api_key_here"

az keyvault secret set \
  --vault-name claude-bot-keyvault \
  --name "git-author-name" \
  --value "Claude Bot"

az keyvault secret set \
  --vault-name claude-bot-keyvault \
  --name "git-author-email" \
  --value "bot@claude.ai"
```

### 3. Set Up Access Policies

```bash
# Get your user object ID
USER_OBJECT_ID=$(az ad signed-in-user show --query id --output tsv)

# Grant yourself access
az keyvault set-policy \
  --name claude-bot-keyvault \
  --object-id $USER_OBJECT_ID \
  --secret-permissions get list set delete

# Create service principal for the bot
az ad sp create-for-rbac \
  --name claude-bot-sp \
  --role "Key Vault Secrets User" \
  --scopes "/subscriptions/$(az account show --query id --output tsv)/resourceGroups/claude-bot-rg/providers/Microsoft.KeyVault/vaults/claude-bot-keyvault"
```

## Authentication Methods

### Method 1: Managed Identity (Recommended for Azure)

```bash
# Create user-assigned managed identity
az identity create \
  --name claude-bot-identity \
  --resource-group claude-bot-rg

# Get the identity details
IDENTITY_ID=$(az identity show \
  --name claude-bot-identity \
  --resource-group claude-bot-rg \
  --query id --output tsv)

IDENTITY_CLIENT_ID=$(az identity show \
  --name claude-bot-identity \
  --resource-group claude-bot-rg \
  --query clientId --output tsv)

# Grant Key Vault access to the managed identity
az keyvault set-policy \
  --name claude-bot-keyvault \
  --object-id $(az identity show --name claude-bot-identity --resource-group claude-bot-rg --query principalId --output tsv) \
  --secret-permissions get list
```

### Method 2: Service Principal

```bash
# Create service principal (if not done above)
SP_DETAILS=$(az ad sp create-for-rbac --name claude-bot-sp --output json)

# Extract credentials
export AZURE_CLIENT_ID=$(echo $SP_DETAILS | jq -r '.appId')
export AZURE_CLIENT_SECRET=$(echo $SP_DETAILS | jq -r '.password')
export AZURE_TENANT_ID=$(echo $SP_DETAILS | jq -r '.tenant')

# Grant Key Vault access
az keyvault set-policy \
  --name claude-bot-keyvault \
  --spn $AZURE_CLIENT_ID \
  --secret-permissions get list
```

## Configuration

### Environment Variables

```bash
# For Azure Key Vault
export AZURE_KEYVAULT_NAME=claude-bot-keyvault

# For Service Principal authentication
export AZURE_CLIENT_ID=your_client_id
export AZURE_CLIENT_SECRET=your_client_secret  
export AZURE_TENANT_ID=your_tenant_id

# For Managed Identity (in Azure services)
export AZURE_CLIENT_ID=managed_identity_client_id
```

### Docker Compose with Azure

```yaml
# docker-compose.azure.yml
version: '3.8'

services:
  claude-orchestrator:
    build:
      context: .
      dockerfile: .devcontainer/Dockerfile.dynamic
    environment:
      # Azure Key Vault configuration
      - AZURE_KEYVAULT_NAME=claude-bot-keyvault
      - AZURE_CLIENT_ID=${AZURE_CLIENT_ID}
      - AZURE_CLIENT_SECRET=${AZURE_CLIENT_SECRET}
      - AZURE_TENANT_ID=${AZURE_TENANT_ID}
      
      # Target repository
      - TARGET_REPO=${TARGET_REPO}
      
    volumes:
      - orchestrator-data:/bot/data
      - ${PROJECT_PATH}:/workspace
      - /var/run/docker.sock:/var/run/docker.sock
    restart: unless-stopped
    
volumes:
  orchestrator-data:
```

## Azure Container Instances Deployment

### 1. Create Container Group

```bash
# Create container instance with managed identity
az container create \
  --name claude-bot-aci \
  --resource-group claude-bot-rg \
  --image your-registry/claude-bot:latest \
  --assign-identity $IDENTITY_ID \
  --environment-variables \
    AZURE_KEYVAULT_NAME=claude-bot-keyvault \
    TARGET_REPO=owner/repo \
  --restart-policy OnFailure \
  --cpu 2 \
  --memory 4
```

### 2. Scheduled Execution with Azure Logic Apps

```json
{
  "definition": {
    "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
    "triggers": {
      "Recurrence": {
        "type": "Recurrence",
        "recurrence": {
          "frequency": "Hour",
          "interval": 6
        }
      }
    },
    "actions": {
      "Start_Container": {
        "type": "Http",
        "inputs": {
          "method": "POST",
          "uri": "https://management.azure.com/subscriptions/{subscription-id}/resourceGroups/claude-bot-rg/providers/Microsoft.ContainerInstance/containerGroups/claude-bot-aci/start",
          "authentication": {
            "type": "ManagedServiceIdentity"
          }
        }
      }
    }
  }
}
```

## Azure DevOps Integration

### 1. Azure Pipeline

```yaml
# azure-pipelines.yml
trigger: none

schedules:
- cron: "0 */6 * * *"
  displayName: Run Claude Bot every 6 hours
  branches:
    include:
    - main

variables:
- group: claude-bot-secrets  # Variable group linked to Key Vault

pool:
  vmImage: 'ubuntu-latest'

steps:
- task: Docker@2
  displayName: 'Build Claude Bot Image'
  inputs:
    command: 'build'
    Dockerfile: '.devcontainer/Dockerfile.dynamic'
    tags: 'claude-bot:$(Build.BuildNumber)'

- task: AzureKeyVault@2
  displayName: 'Get secrets from Key Vault'
  inputs:
    azureSubscription: 'Azure-Service-Connection'
    KeyVaultName: 'claude-bot-keyvault'
    SecretsFilter: '*'
    RunAsPreJob: false

- script: |
    docker run --rm \
      -e ANTHROPIC_API_KEY="$(anthropic-api-key)" \
      -e GITHUB_TOKEN="$(github-token)" \
      -e GIT_AUTHOR_NAME="$(git-author-name)" \
      -e GIT_AUTHOR_EMAIL="$(git-author-email)" \
      -e TARGET_REPO="$(TARGET_REPO)" \
      -v $(Agent.TempDirectory)/workspace:/workspace \
      claude-bot:$(Build.BuildNumber)
  displayName: 'Run Claude Bot'

- task: PublishTestResults@2
  condition: always()
  inputs:
    testResultsFiles: '**/test-results.xml'
    testRunTitle: 'Claude Bot Test Results'
```

### 2. Create Service Connection

```bash
# Create service principal for Azure DevOps
az ad sp create-for-rbac \
  --name claude-bot-devops-sp \
  --role contributor \
  --scopes "/subscriptions/$(az account show --query id --output tsv)"

# Add to Azure DevOps as service connection
# Project Settings > Service connections > New service connection > Azure Resource Manager
```

## Azure Functions Alternative

For lighter workloads, you can use Azure Functions:

```python
# Azure Function (function_app.py)
import azure.functions as func
import logging
import os
import subprocess
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

def main(mytimer: func.TimerRequest) -> None:
    logging.info('Claude Bot function triggered')
    
    # Get secrets from Key Vault
    keyvault_name = os.environ["AZURE_KEYVAULT_NAME"]
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=f"https://{keyvault_name}.vault.azure.net", credential=credential)
    
    # Retrieve secrets
    github_token = client.get_secret("github-token").value
    anthropic_key = client.get_secret("anthropic-api-key").value
    
    # Set environment variables
    os.environ["GITHUB_TOKEN"] = github_token
    os.environ["ANTHROPIC_API_KEY"] = anthropic_key
    
    # Run bot logic
    # (simplified - in practice you'd use the full bot infrastructure)
    logging.info('Claude Bot execution completed')
```

### Function Configuration

```json
{
  "version": "2.0",
  "functionApp": {
    "id": "/subscriptions/{subscription-id}/resourceGroups/claude-bot-rg/providers/Microsoft.Web/sites/claude-bot-function"
  },
  "functions": [
    {
      "name": "claude-bot-timer",
      "scriptFile": "function_app.py",
      "bindings": [
        {
          "name": "mytimer",
          "type": "timerTrigger",
          "direction": "in",
          "schedule": "0 0 */6 * * *"
        }
      ]
    }
  ],
  "extensions": {
    "azure-keyvault": {
      "keyvault_name": "claude-bot-keyvault"
    }
  }
}
```

## Monitoring and Logging

### 1. Azure Monitor Integration

```bash
# Create Log Analytics workspace
az monitor log-analytics workspace create \
  --resource-group claude-bot-rg \
  --workspace-name claude-bot-logs

# Create Application Insights
az monitor app-insights component create \
  --app claude-bot-insights \
  --location eastus \
  --resource-group claude-bot-rg \
  --workspace claude-bot-logs
```

### 2. Azure Alerts

```bash
# Create alert for failed bot runs
az monitor metrics alert create \
  --name "Claude Bot Failure Alert" \
  --resource-group claude-bot-rg \
  --scopes "/subscriptions/$(az account show --query id --output tsv)/resourceGroups/claude-bot-rg" \
  --condition "count 'ContainerInstanceEvent_CL' includes '*failed*'" \
  --description "Alert when Claude Bot container fails" \
  --evaluation-frequency 5m \
  --window-size 5m \
  --severity 2
```

## Cost Optimization

### 1. Azure Container Instances with Spot Instances

```bash
# Use spot pricing for cost savings
az container create \
  --name claude-bot-spot \
  --resource-group claude-bot-rg \
  --image your-registry/claude-bot:latest \
  --priority Spot \
  --restart-policy Never \
  --environment-variables AZURE_KEYVAULT_NAME=claude-bot-keyvault
```

### 2. Azure Batch for Scalable Processing

```bash
# Create Batch account for large-scale processing
az batch account create \
  --name claudebotbatch \
  --resource-group claude-bot-rg \
  --location eastus

# Create pool with auto-scaling
az batch pool create \
  --account-name claudebotbatch \
  --id claude-bot-pool \
  --vm-size Standard_D2s_v3 \
  --image "Canonical:0001-com-ubuntu-server-focal:20_04-lts-gen2" \
  --enable-auto-scale \
  --auto-scale-formula '$TargetDedicatedNodes=min(10,($PendingTasks.GetSample(1 * TimeInterval_Minute) + $ActiveTasks.GetSample(1 * TimeInterval_Minute)) / 1);'
```

## Terraform Infrastructure as Code

```hcl
# main.tf
resource "azurerm_resource_group" "claude_bot" {
  name     = "claude-bot-rg"
  location = "East US"
}

resource "azurerm_key_vault" "claude_bot" {
  name                = "claude-bot-keyvault"
  location            = azurerm_resource_group.claude_bot.location
  resource_group_name = azurerm_resource_group.claude_bot.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = azurerm_user_assigned_identity.claude_bot.principal_id

    secret_permissions = [
      "Get",
      "List",
    ]
  }
}

resource "azurerm_user_assigned_identity" "claude_bot" {
  location            = azurerm_resource_group.claude_bot.location
  name                = "claude-bot-identity"
  resource_group_name = azurerm_resource_group.claude_bot.name
}

resource "azurerm_key_vault_secret" "github_token" {
  name         = "github-token"
  value        = var.github_token
  key_vault_id = azurerm_key_vault.claude_bot.id
}

resource "azurerm_key_vault_secret" "anthropic_key" {
  name         = "anthropic-api-key"
  value        = var.anthropic_api_key
  key_vault_id = azurerm_key_vault.claude_bot.id
}

resource "azurerm_container_group" "claude_bot" {
  name                = "claude-bot-aci"
  location            = azurerm_resource_group.claude_bot.location
  resource_group_name = azurerm_resource_group.claude_bot.name
  os_type             = "Linux"
  restart_policy      = "OnFailure"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.claude_bot.id]
  }

  container {
    name   = "claude-bot"
    image  = "your-registry/claude-bot:latest"
    cpu    = "2"
    memory = "4"

    environment_variables = {
      AZURE_KEYVAULT_NAME = azurerm_key_vault.claude_bot.name
      TARGET_REPO         = var.target_repo
    }
  }
}
```

## Quick Start Commands

```bash
# 1. Set up Azure resources
az login
./scripts/setup-azure-infrastructure.sh

# 2. Configure local development
export AZURE_KEYVAULT_NAME=claude-bot-keyvault
export AZURE_CLIENT_ID=your_managed_identity_client_id

# 3. Test secret retrieval
python3 scripts/secrets_loader.py --validate-only

# 4. Deploy with Azure secrets
docker-compose -f docker-compose.yml -f docker-compose.azure.yml up -d

# 5. Monitor deployment
az container logs --name claude-bot-aci --resource-group claude-bot-rg
```

This comprehensive Azure integration provides enterprise-grade secret management with proper access controls, monitoring, and cost optimization! 🚀