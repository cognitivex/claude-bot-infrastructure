#!/usr/bin/env python3
"""
Azure Integration for Claude Bot Infrastructure

Enhanced Azure support including Key Vault, Container Instances, and DevOps integration.
"""

import os
import sys
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AzureIntegration:
    """Enhanced Azure integration for Claude Bot."""
    
    def __init__(self, resource_group: str = "claude-bot-rg", 
                 keyvault_name: str = "claude-bot-keyvault"):
        self.resource_group = resource_group
        self.keyvault_name = keyvault_name
        self.subscription_id = self._get_subscription_id()
        
    def _get_subscription_id(self) -> Optional[str]:
        """Get current Azure subscription ID."""
        try:
            result = subprocess.run(
                ["az", "account", "show", "--query", "id", "--output", "tsv"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            logger.error(f"Failed to get subscription ID: {e}")
        return None
    
    def setup_azure_infrastructure(self) -> bool:
        """Set up complete Azure infrastructure for Claude Bot."""
        logger.info("🚀 Setting up Azure infrastructure...")
        
        try:
            # 1. Create resource group
            if not self._create_resource_group():
                return False
            
            # 2. Create Key Vault
            if not self._create_key_vault():
                return False
            
            # 3. Create managed identity
            identity_details = self._create_managed_identity()
            if not identity_details:
                return False
            
            # 4. Configure Key Vault access
            if not self._configure_keyvault_access(identity_details["principalId"]):
                return False
            
            # 5. Create Log Analytics workspace
            if not self._create_log_analytics():
                return False
            
            logger.info("✅ Azure infrastructure setup completed successfully!")
            
            # Print next steps
            self._print_setup_summary(identity_details)
            return True
            
        except Exception as e:
            logger.error(f"Failed to set up Azure infrastructure: {e}")
            return False
    
    def _create_resource_group(self) -> bool:
        """Create Azure resource group."""
        logger.info(f"Creating resource group: {self.resource_group}")
        
        try:
            result = subprocess.run([
                "az", "group", "create",
                "--name", self.resource_group,
                "--location", "eastus"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("✅ Resource group created successfully")
                return True
            else:
                logger.error(f"Failed to create resource group: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating resource group: {e}")
            return False
    
    def _create_key_vault(self) -> bool:
        """Create Azure Key Vault."""
        logger.info(f"Creating Key Vault: {self.keyvault_name}")
        
        try:
            result = subprocess.run([
                "az", "keyvault", "create",
                "--name", self.keyvault_name,
                "--resource-group", self.resource_group,
                "--location", "eastus",
                "--sku", "standard",
                "--enabled-for-deployment", "true",
                "--enabled-for-template-deployment", "true"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("✅ Key Vault created successfully")
                return True
            else:
                logger.error(f"Failed to create Key Vault: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating Key Vault: {e}")
            return False
    
    def _create_managed_identity(self) -> Optional[Dict[str, Any]]:
        """Create user-assigned managed identity."""
        identity_name = "claude-bot-identity"
        logger.info(f"Creating managed identity: {identity_name}")
        
        try:
            result = subprocess.run([
                "az", "identity", "create",
                "--name", identity_name,
                "--resource-group", self.resource_group
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                identity_details = json.loads(result.stdout)
                logger.info("✅ Managed identity created successfully")
                return identity_details
            else:
                logger.error(f"Failed to create managed identity: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating managed identity: {e}")
            return None
    
    def _configure_keyvault_access(self, principal_id: str) -> bool:
        """Configure Key Vault access for managed identity."""
        logger.info("Configuring Key Vault access policies")
        
        try:
            result = subprocess.run([
                "az", "keyvault", "set-policy",
                "--name", self.keyvault_name,
                "--object-id", principal_id,
                "--secret-permissions", "get", "list"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("✅ Key Vault access configured successfully")
                return True
            else:
                logger.error(f"Failed to configure Key Vault access: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error configuring Key Vault access: {e}")
            return False
    
    def _create_log_analytics(self) -> bool:
        """Create Log Analytics workspace."""
        workspace_name = "claude-bot-logs"
        logger.info(f"Creating Log Analytics workspace: {workspace_name}")
        
        try:
            result = subprocess.run([
                "az", "monitor", "log-analytics", "workspace", "create",
                "--resource-group", self.resource_group,
                "--workspace-name", workspace_name
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("✅ Log Analytics workspace created successfully")
                return True
            else:
                logger.error(f"Failed to create Log Analytics workspace: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating Log Analytics workspace: {e}")
            return False
    
    def add_secrets_to_keyvault(self, secrets: Dict[str, str]) -> bool:
        """Add secrets to Azure Key Vault."""
        logger.info(f"Adding {len(secrets)} secrets to Key Vault")
        
        success_count = 0
        for secret_name, secret_value in secrets.items():
            if not secret_value:
                logger.warning(f"Skipping empty secret: {secret_name}")
                continue
            
            try:
                # Convert environment variable name to Key Vault secret name
                kv_secret_name = secret_name.lower().replace('_', '-')
                
                result = subprocess.run([
                    "az", "keyvault", "secret", "set",
                    "--vault-name", self.keyvault_name,
                    "--name", kv_secret_name,
                    "--value", secret_value
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    logger.info(f"✅ Added secret: {kv_secret_name}")
                    success_count += 1
                else:
                    logger.error(f"Failed to add secret {kv_secret_name}: {result.stderr}")
                    
            except Exception as e:
                logger.error(f"Error adding secret {secret_name}: {e}")
        
        logger.info(f"Successfully added {success_count}/{len(secrets)} secrets")
        return success_count == len([v for v in secrets.values() if v])
    
    def create_container_instance(self, image: str, target_repo: str) -> bool:
        """Create Azure Container Instance for running the bot."""
        container_name = "claude-bot-aci"
        logger.info(f"Creating Container Instance: {container_name}")
        
        try:
            # Get managed identity ID
            identity_id = self._get_managed_identity_id()
            if not identity_id:
                logger.error("Failed to get managed identity ID")
                return False
            
            result = subprocess.run([
                "az", "container", "create",
                "--name", container_name,
                "--resource-group", self.resource_group,
                "--image", image,
                "--assign-identity", identity_id,
                "--environment-variables",
                f"AZURE_KEYVAULT_NAME={self.keyvault_name}",
                f"TARGET_REPO={target_repo}",
                "--restart-policy", "OnFailure",
                "--cpu", "2",
                "--memory", "4"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("✅ Container Instance created successfully")
                return True
            else:
                logger.error(f"Failed to create Container Instance: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating Container Instance: {e}")
            return False
    
    def _get_managed_identity_id(self) -> Optional[str]:
        """Get managed identity resource ID."""
        try:
            result = subprocess.run([
                "az", "identity", "show",
                "--name", "claude-bot-identity",
                "--resource-group", self.resource_group,
                "--query", "id",
                "--output", "tsv"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                return result.stdout.strip()
                
        except Exception as e:
            logger.error(f"Error getting managed identity ID: {e}")
        
        return None
    
    def create_devops_pipeline(self, repo_url: str) -> str:
        """Create Azure DevOps pipeline configuration."""
        pipeline_yaml = f"""
# Azure DevOps Pipeline for Claude Bot
trigger: none

schedules:
- cron: "0 */6 * * *"
  displayName: Run Claude Bot every 6 hours
  branches:
    include:
    - main

variables:
- group: claude-bot-secrets

pool:
  vmImage: 'ubuntu-latest'

steps:
- checkout: self

- task: AzureKeyVault@2
  displayName: 'Get secrets from Key Vault'
  inputs:
    azureSubscription: 'Azure-Service-Connection'
    KeyVaultName: '{self.keyvault_name}'
    SecretsFilter: '*'
    RunAsPreJob: false

- script: |
    # Clone target repository
    git clone https://$(github-token)@github.com/$(TARGET_REPO).git workspace
    cd workspace
    
    # Set up git configuration
    git config user.name "$(git-author-name)"
    git config user.email "$(git-author-email)"
  displayName: 'Prepare workspace'

- task: Docker@2
  displayName: 'Build Claude Bot Image'
  inputs:
    command: 'build'
    Dockerfile: '.devcontainer/Dockerfile.dynamic'
    tags: 'claude-bot:$(Build.BuildNumber)'

- script: |
    docker run --rm \\
      -e ANTHROPIC_API_KEY="$(anthropic-api-key)" \\
      -e GITHUB_TOKEN="$(github-token)" \\
      -e GIT_AUTHOR_NAME="$(git-author-name)" \\
      -e GIT_AUTHOR_EMAIL="$(git-author-email)" \\
      -e TARGET_REPO="$(TARGET_REPO)" \\
      -v $(Agent.TempDirectory)/workspace:/workspace \\
      claude-bot:$(Build.BuildNumber) \\
      python3 /bot/scripts/bot_orchestrator.py
  displayName: 'Run Claude Bot'
  timeoutInMinutes: 60

- task: PublishTestResults@2
  condition: always()
  inputs:
    testResultsFiles: '**/test-results.xml'
    testRunTitle: 'Claude Bot Test Results'

- task: PublishBuildArtifacts@1
  condition: always()
  inputs:
    pathToPublish: 'logs'
    artifactName: 'bot-logs'
"""
        
        # Save pipeline file
        pipeline_file = Path("azure-pipelines.yml")
        pipeline_file.write_text(pipeline_yaml.strip())
        
        logger.info(f"✅ Created Azure DevOps pipeline: {pipeline_file}")
        return str(pipeline_file)
    
    def create_terraform_config(self) -> str:
        """Create Terraform configuration for infrastructure."""
        terraform_config = f"""
# Terraform configuration for Claude Bot Azure infrastructure

terraform {{
  required_providers {{
    azurerm = {{
      source  = "hashicorp/azurerm"
      version = "~>3.0"
    }}
  }}
}}

provider "azurerm" {{
  features {{}}
}}

data "azurerm_client_config" "current" {{}}

resource "azurerm_resource_group" "claude_bot" {{
  name     = "{self.resource_group}"
  location = "East US"
}}

resource "azurerm_key_vault" "claude_bot" {{
  name                = "{self.keyvault_name}"
  location            = azurerm_resource_group.claude_bot.location
  resource_group_name = azurerm_resource_group.claude_bot.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  enabled_for_deployment          = true
  enabled_for_template_deployment = true
  purge_protection_enabled        = false
}}

resource "azurerm_user_assigned_identity" "claude_bot" {{
  location            = azurerm_resource_group.claude_bot.location
  name                = "claude-bot-identity"
  resource_group_name = azurerm_resource_group.claude_bot.name
}}

resource "azurerm_key_vault_access_policy" "claude_bot" {{
  key_vault_id = azurerm_key_vault.claude_bot.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azurerm_user_assigned_identity.claude_bot.principal_id

  secret_permissions = [
    "Get",
    "List",
  ]
}}

resource "azurerm_log_analytics_workspace" "claude_bot" {{
  name                = "claude-bot-logs"
  location            = azurerm_resource_group.claude_bot.location
  resource_group_name = azurerm_resource_group.claude_bot.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}}

resource "azurerm_application_insights" "claude_bot" {{
  name                = "claude-bot-insights"
  location            = azurerm_resource_group.claude_bot.location
  resource_group_name = azurerm_resource_group.claude_bot.name
  workspace_id        = azurerm_log_analytics_workspace.claude_bot.id
  application_type    = "other"
}}

# Variables for secrets (set via terraform.tfvars or environment)
variable "github_token" {{
  description = "GitHub personal access token"
  type        = string
  sensitive   = true
}}

variable "anthropic_api_key" {{
  description = "Anthropic API key"
  type        = string
  sensitive   = true
}}

variable "target_repo" {{
  description = "Target GitHub repository (owner/repo)"
  type        = string
}}

# Secrets
resource "azurerm_key_vault_secret" "github_token" {{
  name         = "github-token"
  value        = var.github_token
  key_vault_id = azurerm_key_vault.claude_bot.id
  depends_on   = [azurerm_key_vault_access_policy.claude_bot]
}}

resource "azurerm_key_vault_secret" "anthropic_key" {{
  name         = "anthropic-api-key"
  value        = var.anthropic_api_key
  key_vault_id = azurerm_key_vault.claude_bot.id
  depends_on   = [azurerm_key_vault_access_policy.claude_bot]
}}

# Container Instance (optional)
resource "azurerm_container_group" "claude_bot" {{
  name                = "claude-bot-aci"
  location            = azurerm_resource_group.claude_bot.location
  resource_group_name = azurerm_resource_group.claude_bot.name
  os_type             = "Linux"
  restart_policy      = "OnFailure"

  identity {{
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.claude_bot.id]
  }}

  container {{
    name   = "claude-bot"
    image  = "your-registry/claude-bot:latest"
    cpu    = "2"
    memory = "4"

    environment_variables = {{
      AZURE_KEYVAULT_NAME = azurerm_key_vault.claude_bot.name
      TARGET_REPO         = var.target_repo
    }}
  }}
}}

# Outputs
output "keyvault_name" {{
  value = azurerm_key_vault.claude_bot.name
}}

output "managed_identity_client_id" {{
  value = azurerm_user_assigned_identity.claude_bot.client_id
}}

output "resource_group_name" {{
  value = azurerm_resource_group.claude_bot.name
}}
"""
        
        # Save Terraform file
        terraform_file = Path("main.tf")
        terraform_file.write_text(terraform_config.strip())
        
        # Create terraform.tfvars.example
        tfvars_example = """
# terraform.tfvars.example
# Copy this to terraform.tfvars and fill in your values

github_token     = "your_github_token_here"
anthropic_api_key = "your_anthropic_api_key_here"
target_repo      = "owner/repository"
"""
        
        tfvars_file = Path("terraform.tfvars.example")
        tfvars_file.write_text(tfvars_example.strip())
        
        logger.info(f"✅ Created Terraform configuration: {terraform_file}")
        return str(terraform_file)
    
    def _print_setup_summary(self, identity_details: Dict[str, Any]):
        """Print setup summary and next steps."""
        print(f"""
🎉 Azure Infrastructure Setup Complete!

📋 Resources Created:
  • Resource Group: {self.resource_group}
  • Key Vault: {self.keyvault_name}
  • Managed Identity: claude-bot-identity
  • Log Analytics: claude-bot-logs

🔑 Managed Identity Details:
  • Client ID: {identity_details['clientId']}
  • Principal ID: {identity_details['principalId']}

📝 Next Steps:
  1. Add your secrets to Key Vault:
     az keyvault secret set --vault-name {self.keyvault_name} --name "github-token" --value "your_token"
     az keyvault secret set --vault-name {self.keyvault_name} --name "anthropic-api-key" --value "your_key"

  2. Configure your environment:
     export AZURE_KEYVAULT_NAME={self.keyvault_name}
     export AZURE_CLIENT_ID={identity_details['clientId']}

  3. Test the integration:
     python3 scripts/secrets_loader.py --validate-only

  4. Deploy the bot:
     docker-compose -f docker-compose.yml -f docker-compose.azure.yml up -d

🌐 Azure Portal Links:
  • Resource Group: https://portal.azure.com/#@/resource/subscriptions/{self.subscription_id}/resourceGroups/{self.resource_group}
  • Key Vault: https://portal.azure.com/#@/resource/subscriptions/{self.subscription_id}/resourceGroups/{self.resource_group}/providers/Microsoft.KeyVault/vaults/{self.keyvault_name}
""")

def main():
    """CLI interface for Azure integration."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Azure Integration for Claude Bot")
    parser.add_argument("--action", choices=[
        "setup", "add-secrets", "create-aci", "create-pipeline", "create-terraform"
    ], required=True, help="Action to perform")
    parser.add_argument("--resource-group", default="claude-bot-rg", help="Azure resource group")
    parser.add_argument("--keyvault-name", default="claude-bot-keyvault", help="Key Vault name")
    parser.add_argument("--image", help="Docker image for container instance")
    parser.add_argument("--target-repo", help="Target GitHub repository")
    
    args = parser.parse_args()
    
    azure = AzureIntegration(args.resource_group, args.keyvault_name)
    
    if args.action == "setup":
        success = azure.setup_azure_infrastructure()
        if success:
            print("✅ Azure infrastructure setup completed!")
        else:
            print("❌ Azure infrastructure setup failed!")
            sys.exit(1)
    
    elif args.action == "add-secrets":
        secrets = {
            "GITHUB_TOKEN": input("Enter GitHub token: ").strip(),
            "ANTHROPIC_API_KEY": input("Enter Anthropic API key: ").strip(),
            "GIT_AUTHOR_NAME": input("Enter Git author name (optional): ").strip() or "Claude Bot",
            "GIT_AUTHOR_EMAIL": input("Enter Git author email (optional): ").strip() or "bot@claude.ai"
        }
        
        success = azure.add_secrets_to_keyvault(secrets)
        if success:
            print("✅ Secrets added to Key Vault!")
        else:
            print("❌ Failed to add some secrets!")
    
    elif args.action == "create-aci":
        if not args.image or not args.target_repo:
            print("❌ --image and --target-repo are required for creating ACI")
            sys.exit(1)
        
        success = azure.create_container_instance(args.image, args.target_repo)
        if success:
            print("✅ Container Instance created!")
        else:
            print("❌ Failed to create Container Instance!")
    
    elif args.action == "create-pipeline":
        if not args.target_repo:
            args.target_repo = input("Enter target repository (owner/repo): ").strip()
        
        pipeline_file = azure.create_devops_pipeline(f"https://github.com/{args.target_repo}")
        print(f"✅ Azure DevOps pipeline created: {pipeline_file}")
    
    elif args.action == "create-terraform":
        terraform_file = azure.create_terraform_config()
        print(f"✅ Terraform configuration created: {terraform_file}")
        print("Next steps:")
        print("1. Copy terraform.tfvars.example to terraform.tfvars")
        print("2. Fill in your values in terraform.tfvars")
        print("3. Run: terraform init && terraform plan && terraform apply")

if __name__ == "__main__":
    main()