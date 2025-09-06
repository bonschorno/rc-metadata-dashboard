#!/usr/bin/env python3
"""
Interactive setup script for ETH Research Collection API credentials.
Provides secure storage options for API keys.
"""

import os
import sys
import getpass
from pathlib import Path
from typing import Optional

try:
    from cryptography.fernet import Fernet
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False
    print("Warning: cryptography library not installed. Install with: pip install cryptography")
    print("Continuing with plain text storage in .env file.\n")


class CredentialManager:
    """Manage API credentials with multiple storage options."""
    
    def __init__(self):
        self.config_dir = Path.home() / '.eth_rc_config'
        self.config_dir.mkdir(exist_ok=True)
        self.key_file = self.config_dir / 'key.key'
        self.encrypted_file = self.config_dir / 'credentials.enc'
        self.env_file = Path('.env')
    
    def generate_encryption_key(self) -> bytes:
        """Generate or load encryption key."""
        if self.key_file.exists():
            with open(self.key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)
            os.chmod(self.key_file, 0o600)
            return key
    
    def encrypt_credentials(self, api_key: str, group_id: str) -> None:
        """Encrypt and store credentials."""
        if not ENCRYPTION_AVAILABLE:
            raise RuntimeError("Encryption not available")
        
        key = self.generate_encryption_key()
        f = Fernet(key)
        
        credentials = f"{api_key}|{group_id}"
        encrypted = f.encrypt(credentials.encode())
        
        with open(self.encrypted_file, 'wb') as file:
            file.write(encrypted)
        
        os.chmod(self.encrypted_file, 0o600)
        print(f"✓ Credentials encrypted and stored in {self.encrypted_file}")
    
    def decrypt_credentials(self) -> tuple[Optional[str], Optional[str]]:
        """Decrypt and return credentials."""
        if not ENCRYPTION_AVAILABLE or not self.encrypted_file.exists():
            return None, None
        
        key = self.generate_encryption_key()
        f = Fernet(key)
        
        with open(self.encrypted_file, 'rb') as file:
            encrypted = file.read()
        
        decrypted = f.decrypt(encrypted).decode()
        api_key, group_id = decrypted.split('|')
        
        return api_key, group_id
    
    def save_to_env(self, api_key: str, group_id: str) -> None:
        """Save credentials to .env file."""
        env_content = []
        
        if self.env_file.exists():
            with open(self.env_file, 'r') as f:
                for line in f:
                    if not line.strip().startswith(('ETH_RC_API_KEY', 'ETH_RC_GROUP_ID')):
                        env_content.append(line)
        
        env_content.append(f"ETH_RC_API_KEY={api_key}\n")
        env_content.append(f"ETH_RC_GROUP_ID={group_id}\n")
        
        with open(self.env_file, 'w') as f:
            f.writelines(env_content)
        
        os.chmod(self.env_file, 0o600)
        print(f"✓ Credentials saved to {self.env_file}")
    
    def setup_interactive(self) -> None:
        """Interactive setup for credentials."""
        print("ETH Research Collection API Credential Setup")
        print("=" * 50)
        
        api_key = getpass.getpass("Enter your API key: ").strip()
        if not api_key:
            print("Error: API key cannot be empty")
            sys.exit(1)
        
        group_id = input("Enter your group identifier (default: 09746): ").strip()
        if not group_id:
            group_id = "09746"
        
        print("\nStorage options:")
        print("1. Environment file (.env) - Good for development")
        print("2. System environment variables - Good for production")
        
        if ENCRYPTION_AVAILABLE:
            print("3. Encrypted local storage - Most secure for local development")
            max_option = 3
        else:
            max_option = 2
        
        while True:
            try:
                choice = int(input(f"\nSelect storage method (1-{max_option}): "))
                if 1 <= choice <= max_option:
                    break
            except ValueError:
                pass
            print(f"Please enter a number between 1 and {max_option}")
        
        if choice == 1:
            self.save_to_env(api_key, group_id)
            print("\n✓ Setup complete! Your credentials are stored in .env")
            print("  Remember to add .env to .gitignore")
            
        elif choice == 2:
            print("\n✓ To set environment variables, run these commands:")
            print(f"  export ETH_RC_API_KEY='{api_key}'")
            print(f"  export ETH_RC_GROUP_ID='{group_id}'")
            print("\nFor permanent storage, add these to your shell profile (~/.bashrc or ~/.zshrc)")
            
        elif choice == 3 and ENCRYPTION_AVAILABLE:
            self.encrypt_credentials(api_key, group_id)
            print("\n✓ Setup complete! Your credentials are encrypted")
            print(f"  Encryption key: {self.key_file}")
            print(f"  Encrypted credentials: {self.encrypted_file}")
            print("\nTo use encrypted credentials, update api_client.py to load from encrypted storage")
        
        if not self.env_file.exists() and choice != 1:
            print("\nCreating .env.example for reference...")
            self.create_env_example()
    
    def create_env_example(self) -> None:
        """Create example .env file."""
        example_content = """# ETH Research Collection API Configuration
# Copy this file to .env and fill in your values

# Your API key for ETH Research Collection
ETH_RC_API_KEY=your_api_key_here

# Your research group identifier (default: 09746)
ETH_RC_GROUP_ID=09746
"""
        with open('.env.example', 'w') as f:
            f.write(example_content)


def main():
    """Main entry point."""
    manager = CredentialManager()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--decrypt':
            api_key, group_id = manager.decrypt_credentials()
            if api_key:
                print(f"API Key: {api_key[:10]}...")
                print(f"Group ID: {group_id}")
            else:
                print("No encrypted credentials found")
        else:
            print("Usage: python setup_credentials.py [--decrypt]")
    else:
        manager.setup_interactive()


if __name__ == "__main__":
    main()