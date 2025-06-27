# Migration Guide: New Folder Structure

The Claude Bot Infrastructure has been reorganized for better maintainability and clearer separation of concerns.

## 🎯 What Changed

### **Before** (Old Structure)
```
claude-bot-infrastructure/
├── 40+ files in root directory
├── scripts/ (30+ mixed files)
├── docs/ (scattered documentation)
├── 6 docker-compose files in root
└── Mixed configuration files
```

### **After** (New Structure)
```
claude-bot-infrastructure/
├── 📁 src/claude_bot/          # Core Python package
├── 📁 deployment/             # All deployment configs
├── 📁 config/                 # Organized configurations
├── 📁 docs/                   # Structured documentation
├── 📁 tests/                  # Consolidated testing
├── 📁 apps/                   # Standalone applications
└── 📁 data/                   # Runtime data
```

## 🚀 Migration Steps

### **If you have an existing installation:**

1. **Backup your configuration:**
   ```bash
   cp .env .env.backup
   cp -r data/ data_backup/
   ```

2. **Pull the new structure:**
   ```bash
   git pull origin main
   ```

3. **Update your environment file:**
   ```bash
   cp config/examples/.env.example .env
   # Copy your settings from .env.backup
   ```

4. **Update your docker commands:**
   ```bash
   # Old
   docker-compose up -d
   
   # New  
   docker-compose up -d  # Still works!
   
   # Or use specific configurations
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
   ```

5. **Update any custom scripts that reference old paths:**
   ```bash
   # Old paths
   scripts/bot_orchestrator.py
   
   # New paths
   python3 -m claude_bot.orchestrator.bot_orchestrator
   # OR
   python3 src/claude_bot/orchestrator/bot_orchestrator.py
   ```

## 📖 Path Changes Reference

| Old Path | New Path | Notes |
|----------|----------|-------|
| `scripts/bot_orchestrator.py` | `src/claude_bot/orchestrator/bot_orchestrator.py` | Core orchestration |
| `scripts/github_task_executor.py` | `src/claude_bot/executors/github_task_executor.py` | Task execution |
| `scripts/secrets_loader.py` | `src/claude_bot/security/secrets_loader.py` | Secret management |
| `docker-compose.*.yml` | `deployment/docker/docker-compose.*.yml` | Deployment configs |
| `setup-azure.sh` | `deployment/azure/setup-azure.sh` | Azure setup |
| `config/project-config.example.yml` | `config/examples/project-config.example.yml` | Config templates |
| `docs/*.md` | `docs/guides/*.md` or `docs/reference/*.md` | Organized docs |

## 🔧 Updated Commands

### **Python Module Execution**
```bash
# Old way (still works)
python3 scripts/bot_orchestrator.py

# New way (preferred)
python3 -m claude_bot.orchestrator.bot_orchestrator
```

### **Docker Compose**
```bash
# Development
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Production  
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Secure secrets
docker-compose -f docker-compose.yml -f deployment/docker/docker-compose.secure.yml up -d

# Azure integration
docker-compose -f docker-compose.yml -f deployment/docker/docker-compose.azure.yml up -d
```

### **Setup Scripts**
```bash
# Old
./setup-azure.sh

# New
./deployment/azure/setup-azure.sh

# Old
./setup-secure-secrets.sh

# New  
./deployment/scripts/setup-secure-secrets.sh
```

## ✅ Benefits of New Structure

1. **🧹 Clean Root Directory** - Only essential files at root level
2. **📦 Proper Python Package** - Installable as a package with proper imports
3. **🏗️ Logical Organization** - Related files grouped together
4. **📚 Better Documentation** - Structured by type and use case
5. **🚀 Environment-Specific Deployments** - Clear dev/staging/prod configurations
6. **🔧 Easier Maintenance** - Clear separation of concerns

## 🐛 Troubleshooting

### **Import Errors**
```bash
# If you get import errors, ensure PYTHONPATH is set
export PYTHONPATH=/bot/src:/bot

# Or run from the src directory
cd src && python3 -m claude_bot.orchestrator.bot_orchestrator
```

### **Docker Path Issues**
```bash
# Make sure you're using the updated docker-compose.yml
docker-compose down
docker-compose up -d
```

### **Configuration Not Found**
```bash
# Ensure your .env file is in the root directory
ls -la .env

# Copy from template if missing
cp config/examples/.env.example .env
```

## 📞 Need Help?

- Check the **[documentation](docs/README.md)** for detailed guides
- Look at **[examples](docs/examples/)** for reference implementations  
- Create an issue if you encounter problems

---

*This migration maintains backward compatibility while providing a cleaner, more maintainable structure.*