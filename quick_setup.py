#!/usr/bin/env python3
"""
Nanobot Quick Setup & Test Script
Run this to: Install, configure, and test nanobot in minutes
"""

import os
import sys
import subprocess
from pathlib import Path
import json

class NanobotSetup:
    def __init__(self):
        self.home = Path.home()
        self.nanobot_dir = self.home / ".nanobot"
        self.config_file = self.nanobot_dir / "config.yaml"
        
    def print_header(self, text):
        print(f"\n{'='*60}")
        print(f"  {text}")
        print(f"{'='*60}\n")
    
    def print_step(self, num, text):
        print(f"\n✓ STEP {num}: {text}")
        print(f"  {'-'*55}")
    
    def print_success(self, text):
        print(f"  ✅ {text}")
    
    def print_error(self, text):
        print(f"  ❌ {text}")
    
    def print_info(self, text):
        print(f"  ℹ️  {text}")
    
    def check_python(self):
        """Verify Python version"""
        self.print_step(1, "Checking Python version")
        version = sys.version_info
        if version.major >= 3 and version.minor >= 9:
            self.print_success(f"Python {version.major}.{version.minor}.{version.micro} OK")
            return True
        else:
            self.print_error(f"Need Python 3.9+, got {version.major}.{version.minor}")
            return False
    
    def create_venv(self):
        """Create virtual environment"""
        self.print_step(2, "Setting up virtual environment")
        venv_path = Path.cwd() / "venv"
        
        if venv_path.exists():
            self.print_info(f"Virtual env already exists at {venv_path}")
            return True
        
        try:
            subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
            self.print_success(f"Created virtual environment at {venv_path}")
            self.print_info(f"Activate with: .\\venv\\Scripts\\activate (Windows) or source venv/bin/activate (Mac/Linux)")
            return True
        except Exception as e:
            self.print_error(f"Failed to create venv: {e}")
            return False
    
    def install_package(self):
        """Install nanobot package"""
        self.print_step(3, "Installing nanobot package")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], check=True)
            self.print_success("Nanobot installed successfully")
            return True
        except Exception as e:
            self.print_error(f"Installation failed: {e}")
            return False
    
    def create_config(self):
        """Create default configuration"""
        self.print_step(4, "Creating configuration")
        
        self.nanobot_dir.mkdir(parents=True, exist_ok=True)
        
        config_content = """# Nanobot Configuration
# Last generated: Auto-setup script

model:
  provider: "openai"
  api_key: "${OPENAI_API_KEY}"  # Set environment variable
  model_name: "gpt-4"
  temperature: 0.7
  max_tokens: 2000

gateway:
  host: "127.0.0.1"
  port: 8000
  debug: false

channels:
  # Add your channels here
  # telegram:
  #   enabled: false
  #   token: "${TELEGRAM_TOKEN}"
  # discord:
  #   enabled: false
  #   token: "${DISCORD_TOKEN}"

logging:
  level: "INFO"
  format: "[%(levelname)s] %(asctime)s %(message)s"

session:
  max_history: 100
  auto_persist: true
  persistence_file: "~/.nanobot/sessions.db"
"""
        
        with open(self.config_file, "w") as f:
            f.write(config_content)
        
        self.print_success(f"Config created at {self.config_file}")
        return True
    
    def setup_env_vars(self):
        """Guide user to set environment variables"""
        self.print_step(5, "Environment variables setup")
        
        self.print_info("You need to set API keys. Do this BEFORE running nanobot:")
        print("\n  📌 Windows PowerShell:")
        print("     $env:OPENAI_API_KEY = 'sk-xxx...'")
        print("     $env:TELEGRAM_TOKEN = 'xxx...' (optional)")
        print("     $env:DISCORD_TOKEN = 'xxx...' (optional)")
        
        print("\n  📌 Mac/Linux (bash):")
        print("     export OPENAI_API_KEY='sk-xxx...'")
        print("     export TELEGRAM_TOKEN='xxx...' (optional)")
        print("     export DISCORD_TOKEN='xxx...' (optional)")
        
        print("\n  📌 Get your keys from:")
        print("     • OpenAI: https://platform.openai.com/account/api-keys")
        print("     • Telegram: @BotFather on Telegram")
        print("     • Discord: https://discord.com/developers/applications")
        
        return True
    
    def test_import(self):
        """Test if nanobot can be imported"""
        self.print_step(6, "Testing nanobot import")
        try:
            import nanobot
            version = getattr(nanobot, '__version__', '0.1.5')
            self.print_success(f"Nanobot v{version} imported successfully")
            return True
        except ImportError as e:
            self.print_error(f"Could not import nanobot: {e}")
            return False
    
    def show_quick_start(self):
        """Show quick start commands"""
        self.print_header("🚀 QUICK START GUIDE")
        
        print("Your nanobot is ready! Here's what to do next:\n")
        
        print("1️⃣  Activate virtual environment:")
        print("    Windows: .\\venv\\Scripts\\activate")
        print("    Mac/Linux: source venv/bin/activate\n")
        
        print("2️⃣  Set API keys:")
        print("    $env:OPENAI_API_KEY = 'sk-xxx...'\n")
        
        print("3️⃣  Start the gateway:")
        print("    nanobot gateway --verbose\n")
        
        print("4️⃣  In another terminal, test:")
        print("    nanobot agent --message 'Hello!'")
        print("    nanobot agent --message '/status'\n")
        
        print("5️⃣  Try chat commands:")
        print("    /status     → Show session info")
        print("    /think high → Enable deep thinking")
        print("    /usage      → Show token usage")
        print("    /reset      → Clear history\n")
        
        print("📚 Full documentation:")
        print("    • Read: HOW_TO_USE.md")
        print("    • Setup channels: channels/TELEGRAM.md, channels/DISCORD.md, etc.")
        print("    • Integration guide: INTEGRATION_GUIDE_COMPLETE.md")
        
    def show_testing_guide(self):
        """Show testing commands"""
        self.print_header("🧪 TESTING COMMANDS")
        
        tests = [
            ("Basic functionality", "pytest tests/ -v -k 'test_basic'"),
            ("Full test suite", "pytest tests/ -v"),
            ("Channel tests", "pytest tests/ -k 'channel'"),
            ("Memory check", "nanobot test --memory"),
            ("Load testing", "pytest tests/performance/"),
        ]
        
        print("Run these commands to test your nanobot:\n")
        for desc, cmd in tests:
            print(f"  {desc}:")
            print(f"    {cmd}\n")
    
    def main(self):
        """Run complete setup"""
        self.print_header("🤖 NANOBOT QUICK SETUP")
        
        print("This script will:")
        print("  1. Check your Python version")
        print("  2. Create a virtual environment")
        print("  3. Install the nanobot package")
        print("  4. Create configuration files")
        print("  5. Test the installation")
        print("  6. Show you how to run it\n")
        
        input("Press ENTER to start...")
        
        # Run setup steps
        steps = [
            self.check_python,
            self.create_venv,
            self.install_package,
            self.create_config,
            self.setup_env_vars,
            self.test_import,
        ]
        
        for step in steps:
            try:
                if not step():
                    self.print_error(f"Setup interrupted during {step.__name__}")
                    return False
            except KeyboardInterrupt:
                self.print_info("Setup cancelled by user")
                return False
            except Exception as e:
                self.print_error(f"Unexpected error: {e}")
                return False
        
        self.show_quick_start()
        self.show_testing_guide()
        
        self.print_header("✅ SETUP COMPLETE!")
        print("Next step: Follow the Quick Start Guide above\n")
        print("Questions? Check the documentation files:\n")
        print("  • HOW_TO_USE.md - Complete reference")
        print("  • DEPLOYMENT_AND_TESTING.md - Deployment guide")
        print("  • INTEGRATION_GUIDE_COMPLETE.md - Technical deep dive")
        print("\n")
        
        return True

def main():
    setup = NanobotSetup()
    success = setup.main()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
