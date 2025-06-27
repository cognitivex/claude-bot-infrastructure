# Claude Bot Infrastructure Documentation

Welcome to the Claude Bot Infrastructure documentation! This system automates development tasks by integrating Claude Code with GitHub repositories.

## 📚 Documentation Structure

### 🚀 Getting Started
- **[Quick Start](getting-started/quick-start.md)** - Get up and running in 5 minutes
- **[CLAUDE.md](getting-started/CLAUDE.md)** - Complete project overview and setup
- **[Installation](getting-started/installation.md)** - Detailed installation guide

### 📖 Guides
- **[Secret Management](guides/secret-management.md)** - Secure credential handling (.env, Docker Secrets, Azure Key Vault)
- **[Azure Setup](guides/azure-setup.md)** - Enterprise Azure deployment with Key Vault
- **[Multi-Platform](guides/multi-platform.md)** - Supporting Node.js, .NET, Python projects
- **[Secure Setup](guides/secure-setup.md)** - Production security best practices
- **[New Repo Setup](guides/new-repo-setup.md)** - Setting up the bot for new repositories
- **[Orchestrator Setup](guides/orchestrator-setup.md)** - Advanced orchestrator configuration

### 🔧 Technical Reference
- **[Architecture](reference/architecture.md)** - System design and components
- **[API Reference](reference/api.md)** - Python API documentation
- **[Configuration](reference/configuration.md)** - Complete configuration options
- **[Testing](reference/testing.md)** - Testing framework and examples

### 🎯 Examples
- **[Node.js Bot](examples/nodejs-bot/)** - Example Node.js project setup
- **[.NET Bot](examples/dotnet-bot/)** - Example .NET project setup  
- **[Python Bot](examples/python-bot/)** - Example Python project setup

## 🔗 Quick Links

| What do you want to do? | Documentation |
|-------------------------|---------------|
| **Set up your first bot** | [Quick Start](getting-started/quick-start.md) |
| **Configure secrets securely** | [Secret Management](guides/secret-management.md) |
| **Deploy to production** | [Azure Setup](guides/azure-setup.md) |
| **Support multiple languages** | [Multi-Platform](guides/multi-platform.md) |
| **Understand the architecture** | [Architecture](reference/architecture.md) |
| **Troubleshoot issues** | [Testing](reference/testing.md) |

## 🏗️ Project Structure Overview

```
claude-bot-infrastructure/
├── src/claude_bot/          # Core application code
├── deployment/             # Docker and cloud deployments
├── config/                # Configuration templates
├── docs/                  # This documentation
├── tests/                # Testing framework
└── apps/                 # Standalone applications
```

## 🤝 Contributing to Documentation

1. Documentation is written in Markdown
2. Place new guides in the appropriate directory
3. Update this README.md with links to new content
4. Follow the existing structure and style
5. Include code examples and practical use cases

## 📞 Getting Help

- **Issues**: Create an issue in the GitHub repository
- **Discussions**: Use GitHub Discussions for questions
- **Documentation**: Check this docs directory first

---

*Last updated: $(date)*