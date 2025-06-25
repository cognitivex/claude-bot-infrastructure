#!/usr/bin/env python3
"""
Dynamic Dockerfile Builder for Multi-Platform Support

This script generates a Dockerfile with only the platforms specified in the PLATFORMS environment variable.
It reads the platform registry from platforms.yml and creates optimized Docker stages.

Usage:
    python3 build-dynamic-dockerfile.py --platforms "nodejs:18.16,dotnet:8.0,python:3.11"
    python3 build-dynamic-dockerfile.py --config platforms.yml --output Dockerfile.generated
"""

import argparse
import os
import sys
import yaml
import re
from pathlib import Path

class DockerfileBuilder:
    def __init__(self, platforms_config_path):
        """Initialize the builder with platform configuration."""
        self.platforms_config_path = Path(platforms_config_path)
        self.config = self._load_config()
        self.base_dockerfile = Path(__file__).parent.parent / ".devcontainer" / "Dockerfile.dynamic"
        
    def _load_config(self):
        """Load platform configuration from YAML file."""
        try:
            with open(self.platforms_config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading platform config: {e}", file=sys.stderr)
            sys.exit(1)
            
    def parse_platforms(self, platforms_string):
        """
        Parse platform string into structured format.
        
        Args:
            platforms_string: "nodejs:18.16,dotnet:8.0,python:3.11" or "auto"
            
        Returns:
            List of dictionaries with platform info
        """
        if not platforms_string or platforms_string.lower() == "auto":
            return self._auto_detect_platforms()
            
        platforms = []
        for platform_spec in platforms_string.split(','):
            platform_spec = platform_spec.strip()
            if ':' in platform_spec:
                name, version = platform_spec.split(':', 1)
            else:
                name = platform_spec
                version = self.config['platforms'].get(name, {}).get('default_version', 'latest')
                
            if name not in self.config['platforms']:
                print(f"Warning: Unknown platform '{name}', skipping", file=sys.stderr)
                continue
                
            platform_config = self.config['platforms'][name]
            if version not in platform_config['supported_versions'] and version != 'latest':
                print(f"Warning: Version '{version}' not officially supported for {name}", file=sys.stderr)
                
            platforms.append({
                'name': name,
                'version': version,
                'config': platform_config
            })
            
        return platforms
        
    def _auto_detect_platforms(self):
        """Auto-detect platforms from current directory."""
        # This would scan current directory for platform indicators
        # For now, return default Node.js setup
        return [{
            'name': 'nodejs',
            'version': '18.16.0',
            'config': self.config['platforms']['nodejs']
        }]
        
    def generate_dockerfile(self, platforms, output_path=None):
        """
        Generate optimized Dockerfile for specified platforms.
        
        Args:
            platforms: List of platform dictionaries
            output_path: Where to write the generated Dockerfile
        """
        if not output_path:
            output_path = Path(__file__).parent.parent / ".devcontainer" / "Dockerfile.generated"
            
        dockerfile_content = self._build_dockerfile_content(platforms)
        
        with open(output_path, 'w') as f:
            f.write(dockerfile_content)
            
        print(f"Generated Dockerfile with {len(platforms)} platforms: {output_path}")
        return output_path
        
    def _build_dockerfile_content(self, platforms):
        """Build complete Dockerfile content."""
        lines = []
        
        # Header
        lines.extend([
            "# Generated Multi-Platform Dockerfile",
            f"# Platforms: {', '.join([f'{p[\"name\"]}:{p[\"version\"]}' for p in platforms])}",
            f"# Generated at: {os.popen('date').read().strip()}",
            "",
            "ARG BASE_IMAGE=ubuntu:22.04",
            "FROM ${BASE_IMAGE} as base",
            ""
        ])
        
        # Common dependencies
        lines.extend(self._get_common_dependencies())
        
        # User creation
        lines.extend(self._get_user_creation())
        
        # Platform-specific stages
        for platform in platforms:
            lines.extend(self._get_platform_stage(platform))
            
        # Final stage
        lines.extend(self._get_final_stage(platforms))
        
        return '\n'.join(lines)
        
    def _get_common_dependencies(self):
        """Get common system dependencies."""
        return [
            "# Install common system dependencies",
            "RUN apt-get update && apt-get install -y \\",
            "    curl \\",
            "    wget \\", 
            "    git \\",
            "    bash \\",
            "    jq \\",
            "    unzip \\",
            "    ca-certificates \\",
            "    gnupg \\",
            "    lsb-release \\",
            "    build-essential \\",
            "    python3 \\",
            "    python3-pip \\",
            "    python3-venv \\",
            "    && rm -rf /var/lib/apt/lists/*",
            "",
            "# Install GitHub CLI",
            "RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \\",
            "    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \\",
            "    && echo \"deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main\" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \\",
            "    && apt-get update \\",
            "    && apt-get install gh -y \\",
            "    && rm -rf /var/lib/apt/lists/*",
            ""
        ]
        
    def _get_user_creation(self):
        """Get user creation commands."""
        return [
            "# Create non-root user",
            "ARG USERNAME=bot",
            "ARG USER_UID=1000", 
            "ARG USER_GID=$USER_UID",
            "",
            "RUN groupadd --gid $USER_GID $USERNAME 2>/dev/null || \\",
            "    (getent group $USER_GID >/dev/null && groupadd $USERNAME) || \\",
            "    groupadd $USERNAME \\",
            "    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME 2>/dev/null || \\",
            "    (id $USER_UID >/dev/null 2>&1 && usermod -l $USERNAME -d /home/$USERNAME $(id -nu $USER_UID)) || \\",
            "    useradd --gid $USERNAME -m $USERNAME",
            "",
            "# Create bot directories",
            "RUN mkdir -p /bot/data /bot/scripts /bot/logs /bot/config /workspace \\",
            "    && chown -R $USERNAME:$USERNAME /bot /workspace",
            ""
        ]
        
    def _get_platform_stage(self, platform):
        """Generate Docker stage for a specific platform."""
        name = platform['name']
        version = platform['version']
        config = platform['config']
        stage_name = f"{name}-{version.replace('.', '-')}"
        
        lines = [
            f"# {config['name']} {version} installation stage",
            f"FROM base as {stage_name}",
        ]
        
        # Get install commands for this platform
        install_cmd = self._get_install_command(platform)
        if install_cmd:
            lines.append(f"RUN {install_cmd}")
            
        lines.extend(["", ""])
        return lines
        
    def _get_install_command(self, platform):
        """Get installation command for a platform."""
        name = platform['name']
        version = platform['version']
        config = platform['config']
        
        if name == 'nodejs':
            if version.startswith('10.'):
                return f"curl -fsSL https://nodejs.org/dist/v{version}/node-v{version}-linux-x64.tar.xz | tar -xJ -C /usr/local --strip-components=1"
            else:
                major = version.split('.')[0]
                return f"curl -fsSL https://deb.nodesource.com/setup_{major}.x | bash - && apt-get install -y nodejs && rm -rf /var/lib/apt/lists/*"
                
        elif name == 'dotnet':
            return f"wget https://packages.microsoft.com/config/ubuntu/22.04/packages-microsoft-prod.deb -O packages-microsoft-prod.deb && dpkg -i packages-microsoft-prod.deb && rm packages-microsoft-prod.deb && apt-get update && apt-get install -y dotnet-sdk-{version} && rm -rf /var/lib/apt/lists/*"
            
        elif name == 'java':
            return f"apt-get update && apt-get install -y openjdk-{version}-jdk && rm -rf /var/lib/apt/lists/*"
            
        elif name == 'python':
            return f"apt-get update && apt-get install -y python{version} python{version}-pip python{version}-venv && rm -rf /var/lib/apt/lists/*"
            
        elif name == 'golang':
            return f"wget https://golang.org/dl/go{version}.linux-amd64.tar.gz && tar -C /usr/local -xzf go{version}.linux-amd64.tar.gz && rm go{version}.linux-amd64.tar.gz"
            
        elif name == 'rust':
            return f"curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain {version}"
            
        elif name == 'php':
            return f"apt-get update && apt-get install -y php{version} php{version}-cli php{version}-common php{version}-curl php{version}-mbstring php{version}-xml && rm -rf /var/lib/apt/lists/* && curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer"
            
        elif name == 'ruby':
            return f"apt-get update && apt-get install -y ruby{version} ruby{version}-dev bundler && rm -rf /var/lib/apt/lists/*"
            
        return None
        
    def _get_final_stage(self, platforms):
        """Generate final stage that combines all platforms."""
        lines = [
            "# Final stage combining all requested platforms",
            "FROM base as final",
            ""
        ]
        
        # Copy platform binaries
        for platform in platforms:
            name = platform['name']
            version = platform['version']
            stage_name = f"{name}-{version.replace('.', '-')}"
            
            copy_commands = self._get_copy_commands(platform, stage_name)
            lines.extend(copy_commands)
            
        lines.extend([
            "",
            "# Install Claude Code CLI if Node.js is available",
            "RUN if command -v npm >/dev/null 2>&1; then npm install -g @anthropic-ai/claude-code; fi",
            "",
            "# Install Python packages for bot automation", 
            "RUN pip3 install --no-cache-dir --break-system-packages \\",
            "    requests \\",
            "    pyyaml \\",
            "    python-dotenv \\",
            "    schedule \\",
            "    prometheus_client",
            "",
            "# Switch to non-root user",
            "USER $USERNAME",
            "",
            "# Set up environment paths",
            "ENV PATH=\"/home/$USERNAME/.local/bin:/home/$USERNAME/.cargo/bin:/usr/local/go/bin:${PATH}\"",
            "ENV GOPATH=\"/home/$USERNAME/go\"",
            "ENV CARGO_HOME=\"/home/$USERNAME/.cargo\"", 
            "ENV RUSTUP_HOME=\"/home/$USERNAME/.rustup\"",
            "",
            "# Set working directory",
            "WORKDIR /workspace",
            "",
            "# Copy bot scripts and configuration",
            "COPY --chown=$USERNAME:$USERNAME scripts/ /bot/scripts/",
            "COPY --chown=$USERNAME:$USERNAME config/ /bot/config/",
            "",
            "# Add bot scripts to PATH", 
            "ENV PATH=\"/bot/scripts:${PATH}\"",
            "",
            "# Create initial bot data directories",
            "RUN mkdir -p /bot/data/tasks /bot/data/queue /bot/data/processed /bot/data/pr_feedback",
            "",
            "# Health check and entry point",
            "COPY --chown=$USERNAME:$USERNAME scripts/health-check-platforms.sh /bot/scripts/",
            "COPY --chown=$USERNAME:$USERNAME scripts/entrypoint-dynamic.sh /bot/scripts/",
            "RUN chmod +x /bot/scripts/health-check-platforms.sh /bot/scripts/entrypoint-dynamic.sh",
            "",
            "HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \\",
            "    CMD /bot/scripts/health-check-platforms.sh",
            "",
            "ENTRYPOINT [\"/bot/scripts/entrypoint-dynamic.sh\"]",
            "CMD [\"start-bot.sh\"]"
        ])
        
        return lines
        
    def _get_copy_commands(self, platform, stage_name):
        """Get COPY commands to extract platform binaries."""
        name = platform['name']
        
        if name == 'nodejs':
            return [
                f"COPY --from={stage_name} /usr/local/bin/node /usr/local/bin/node",
                f"COPY --from={stage_name} /usr/local/bin/npm /usr/local/bin/npm",
                f"COPY --from={stage_name} /usr/local/lib/node_modules /usr/local/lib/node_modules"
            ]
        elif name == 'dotnet':
            return [
                f"COPY --from={stage_name} /usr/share/dotnet /usr/share/dotnet",
                f"COPY --from={stage_name} /usr/bin/dotnet /usr/bin/dotnet"
            ]
        elif name == 'java':
            return [
                f"COPY --from={stage_name} /usr/lib/jvm /usr/lib/jvm",
                f"COPY --from={stage_name} /usr/bin/java /usr/bin/java",
                f"COPY --from={stage_name} /usr/bin/javac /usr/bin/javac"
            ]
        elif name == 'python':
            version = platform['version']
            return [
                f"COPY --from={stage_name} /usr/bin/python{version} /usr/bin/python{version}",
                f"COPY --from={stage_name} /usr/bin/pip{version.split('.')[0]} /usr/bin/pip{version.split('.')[0]}"
            ]
        elif name == 'golang':
            return [
                f"COPY --from={stage_name} /usr/local/go /usr/local/go"
            ]
        elif name == 'rust':
            return [
                f"COPY --from={stage_name} /home/bot/.cargo /home/bot/.cargo",
                f"COPY --from={stage_name} /home/bot/.rustup /home/bot/.rustup"
            ]
        elif name == 'php':
            version = platform['version']
            return [
                f"COPY --from={stage_name} /usr/bin/php{version} /usr/bin/php{version}",
                f"COPY --from={stage_name} /usr/local/bin/composer /usr/local/bin/composer"
            ]
        elif name == 'ruby':
            return [
                f"COPY --from={stage_name} /usr/bin/ruby /usr/bin/ruby",
                f"COPY --from={stage_name} /usr/bin/gem /usr/bin/gem",
                f"COPY --from={stage_name} /usr/bin/bundle /usr/bin/bundle"
            ]
            
        return []

def main():
    parser = argparse.ArgumentParser(description='Build dynamic Dockerfile for multi-platform support')
    parser.add_argument('--platforms', required=True, 
                       help='Comma-separated list of platforms (e.g., "nodejs:18.16,dotnet:8.0")')
    parser.add_argument('--config', default='config/platforms.yml',
                       help='Path to platforms configuration file')
    parser.add_argument('--output', 
                       help='Output path for generated Dockerfile')
    parser.add_argument('--validate', action='store_true',
                       help='Validate platform combinations without generating')
    
    args = parser.parse_args()
    
    try:
        builder = DockerfileBuilder(args.config)
        platforms = builder.parse_platforms(args.platforms)
        
        if not platforms:
            print("Error: No valid platforms specified", file=sys.stderr)
            sys.exit(1)
            
        if args.validate:
            print(f"✅ Platform combination is valid:")
            for p in platforms:
                print(f"  - {p['name']}:{p['version']}")
            return
            
        output_path = builder.generate_dockerfile(platforms, args.output)
        print(f"✅ Generated: {output_path}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()