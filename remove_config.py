#!/usr/bin/env python3
"""
Ogresync Config File Removal Utility

This script provides a reliable way to remove the config.txt file from the 
OS-specific application data directory, especially useful during development
when PowerShell fails to delete the file due to path issues.

This addresses the common Windows/PowerShell issue where certain paths
cannot be properly accessed or deleted through the shell.

WINDOWS USERS: If you encounter issues where the Ogresync application fails
to create a config folder in the specified AppData path when run directly,
use this Python script to remove any existing config file and reset the
application to setup mode. This allows you to run the app fresh and bypass
Windows-specific path/permission issues that can prevent proper initialization.

IMPORTANT: On Windows, when the Ogresync script is run directly (not as an executable),
sometimes no config folder is created in the specified AppData path due to permission
or path resolution errors. If this happens, run this Python script to remove any
existing config file and force the application to run in setup mode again.
"""

import os
import sys
from pathlib import Path

def get_config_directory():
    """
    Get the OS-specific application data directory for Ogresync.
    Same function as used in the main application.
    """
    if sys.platform == "win32":
        # Windows: Use APPDATA (Roaming)
        appdata = os.environ.get('APPDATA')
        if appdata:
            return os.path.join(appdata, 'Ogresync')
    elif sys.platform == "darwin":
        # macOS: Use ~/Library/Application Support
        home = Path.home()
        return str(home / "Library" / "Application Support" / "Ogresync")
    else:
        # Linux/Unix: Use ~/.config
        home = Path.home()
        return str(home / ".config" / "Ogresync")
    
    # Fallback to current directory (shouldn't happen in normal usage)
    return os.path.join(os.getcwd(), "config")

def get_config_file_path():
    """Get the full path to the config.txt file."""
    return os.path.join(get_config_directory(), "config.txt")

def remove_config_file():
    """
    Safely remove the config.txt file from the application data directory.
    Returns True if successful, False otherwise.
    """
    config_file_path = get_config_file_path()
    config_dir = get_config_directory()
    
    print(f"Ogresync Config Removal Utility")
    print(f"================================")
    print(f"Config directory: {config_dir}")
    print(f"Config file path: {config_file_path}")
    print()
    
    # Check if config file exists
    if not os.path.exists(config_file_path):
        print("✅ Config file does not exist - nothing to remove")
        return True
    
    try:
        # Remove the config file
        os.remove(config_file_path)
        print("✅ Successfully removed config.txt")
        
        # Check if directory is now empty and remove it if so
        if os.path.exists(config_dir):
            try:
                # List all files in the directory
                remaining_files = [f for f in os.listdir(config_dir) if not f.startswith('.')]
                if not remaining_files:
                    os.rmdir(config_dir)
                    print("✅ Removed empty config directory")
                else:
                    print(f"📁 Config directory kept (contains {len(remaining_files)} other files)")
            except OSError as e:
                print(f"⚠️  Could not remove config directory: {e}")
        
        return True
        
    except OSError as e:
        print(f"❌ Failed to remove config file: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def list_config_info():
    """Display information about the current config setup."""
    config_file_path = get_config_file_path()
    config_dir = get_config_directory()
    
    print(f"Ogresync Config Information")
    print(f"===========================")
    print(f"Operating System: {sys.platform}")
    print(f"Config directory: {config_dir}")
    print(f"Config file path: {config_file_path}")
    print()
    
    # Check directory existence
    if os.path.exists(config_dir):
        print(f"✅ Config directory exists")
        try:
            files = os.listdir(config_dir)
            if files:
                print(f"📁 Directory contents: {', '.join(files)}")
            else:
                print(f"📁 Directory is empty")
        except OSError as e:
            print(f"⚠️  Cannot list directory contents: {e}")
    else:
        print(f"❌ Config directory does not exist")
    
    # Check file existence
    if os.path.exists(config_file_path):
        print(f"✅ Config file exists")
        try:
            file_size = os.path.getsize(config_file_path)
            print(f"📄 File size: {file_size} bytes")
            
            # Try to read the file content (first few lines)
            with open(config_file_path, 'r', encoding='utf-8') as f:
                content = f.read(500)  # Read first 500 characters
                lines = content.splitlines()
                print(f"📄 Content preview (first {min(3, len(lines))} lines):")
                for i, line in enumerate(lines[:3]):
                    print(f"   {i+1}: {line}")
                if len(lines) > 3:
                    print(f"   ... ({len(lines)} total lines)")
        except Exception as e:
            print(f"⚠️  Cannot read file: {e}")
    else:
        print(f"❌ Config file does not exist")

def main():
    """Main function with command-line interface."""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command in ['remove', 'delete', 'rm']:
            success = remove_config_file()
            sys.exit(0 if success else 1)
        elif command in ['info', 'list', 'show']:
            list_config_info()
            sys.exit(0)
        elif command in ['help', '-h', '--help']:
            print(f"Ogresync Config Utility")
            print(f"Usage: python {sys.argv[0]} [command]")
            print(f"")
            print(f"Commands:")
            print(f"  remove, delete, rm  - Remove the config.txt file")
            print(f"  info, list, show    - Show config file information")
            print(f"  help                - Show this help message")
            print(f"")
            print(f"If no command is given, defaults to 'remove'")
            sys.exit(0)
        else:
            print(f"❌ Unknown command: {command}")
            print(f"Use 'python {sys.argv[0]} help' for usage information")
            sys.exit(1)
    else:
        # Default action: remove config file
        print("No command specified - defaulting to 'remove'")
        print("Use 'python remove_config.py help' for other options")
        print()
        success = remove_config_file()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
