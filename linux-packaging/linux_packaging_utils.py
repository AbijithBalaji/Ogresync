"""
Linux Packaging Utilities for Ogresync

This module provides Linux-specific utilities that complement the main packaging_utils.py
for handling Linux packaging requirements, particularly for AppImage creation.

Key features:
- Linux-specific path handling
- Desktop integration utilities
- Icon management for AppImages
- Cross-distribution compatibility helpers
- AppImage-specific resource resolution

Author: Ogresync Development Team
Date: June 2025
"""

import os
import sys
import platform
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any


def is_linux() -> bool:
    """Check if running on Linux"""
    return platform.system() == "Linux"


def get_linux_distro() -> Dict[str, str]:
    """Get Linux distribution information"""
    distro_info = {
        "name": "Unknown",
        "version": "Unknown",
        "id": "unknown"
    }
    
    try:
        # Try using os-release file (most modern distributions)
        if os.path.exists("/etc/os-release"):
            with open("/etc/os-release", "r") as f:
                for line in f:
                    if line.startswith("NAME="):
                        distro_info["name"] = line.split("=", 1)[1].strip().strip('"')
                    elif line.startswith("VERSION="):
                        distro_info["version"] = line.split("=", 1)[1].strip().strip('"')
                    elif line.startswith("ID="):
                        distro_info["id"] = line.split("=", 1)[1].strip().strip('"')
    except:
        pass
    
    return distro_info


def get_desktop_environment() -> str:
    """Detect the desktop environment"""
    # Check environment variables
    desktop_env = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    if desktop_env:
        return desktop_env
    
    # Fallback checks
    if os.environ.get("GNOME_DESKTOP_SESSION_ID"):
        return "gnome"
    elif os.environ.get("KDE_FULL_SESSION"):
        return "kde"
    elif os.environ.get("XFCE_SESSION"):
        return "xfce"
    
    return "unknown"


def get_appimage_mount_point() -> Optional[str]:
    """Get the mount point if running from an AppImage"""
    appimage_path = os.environ.get("APPIMAGE")
    if appimage_path:
        # When running from AppImage, files are mounted at /tmp/.mount_*
        appdir = os.environ.get("APPDIR")
        if appdir:
            return appdir
    
    return None


def get_linux_resource_path(relative_path: str) -> str:
    """
    Get resource path for Linux, handling both development and AppImage execution
    """
    # Check if running from AppImage
    appdir = get_appimage_mount_point()
    if appdir:
        # Running from AppImage
        resource_path = os.path.join(appdir, relative_path)
        if os.path.exists(resource_path):
            return resource_path
    
    # Check if running from PyInstaller bundle
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle
        bundle_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        resource_path = os.path.join(bundle_dir, relative_path)
        if os.path.exists(resource_path):
            return resource_path
    
    # Development mode - relative to script location
    if __name__ == "__main__":
        script_dir = os.path.dirname(os.path.abspath(__file__))
    else:
        module_file = sys.modules[__name__].__file__
        if module_file:
            script_dir = os.path.dirname(os.path.abspath(module_file))
        else:
            script_dir = os.getcwd()
    
    # Go up one level from linux-packaging directory
    project_root = os.path.dirname(script_dir)
    resource_path = os.path.join(project_root, relative_path)
    
    if os.path.exists(resource_path):
        return resource_path
    
    # Fallback to current directory
    return os.path.join(os.getcwd(), relative_path)


def get_linux_config_directory() -> str:
    """Get the Linux configuration directory following XDG Base Directory Specification"""
    # Use XDG_CONFIG_HOME if set, otherwise default to ~/.config
    config_home = os.environ.get("XDG_CONFIG_HOME")
    if config_home:
        config_dir = os.path.join(config_home, "ogresync")
    else:
        config_dir = os.path.expanduser("~/.config/ogresync")
    
    # Create directory if it doesn't exist
    Path(config_dir).mkdir(parents=True, exist_ok=True)
    
    return config_dir


def get_linux_data_directory() -> str:
    """Get the Linux data directory following XDG Base Directory Specification"""
    # Use XDG_DATA_HOME if set, otherwise default to ~/.local/share
    data_home = os.environ.get("XDG_DATA_HOME")
    if data_home:
        data_dir = os.path.join(data_home, "ogresync")
    else:
        data_dir = os.path.expanduser("~/.local/share/ogresync")
    
    # Create directory if it doesn't exist
    Path(data_dir).mkdir(parents=True, exist_ok=True)
    
    return data_dir


def create_desktop_file(app_name: str, exec_path: str, icon_path: Optional[str] = None, 
                       description: Optional[str] = None) -> str:
    """Create a .desktop file for Linux desktop integration"""
    
    desktop_content = f"""[Desktop Entry]
Type=Application
Name={app_name}
Comment={description or f"{app_name} application"}
Exec={exec_path}
Icon={icon_path or app_name.lower()}
Categories=Office;Utility;
Terminal=false
StartupWMClass={app_name}
StartupNotify=true
"""
    
    # Save to user's applications directory
    desktop_dir = os.path.expanduser("~/.local/share/applications")
    Path(desktop_dir).mkdir(parents=True, exist_ok=True)
    
    desktop_file = os.path.join(desktop_dir, f"{app_name.lower()}.desktop")
    
    with open(desktop_file, "w") as f:
        f.write(desktop_content)
    
    # Make executable
    os.chmod(desktop_file, 0o755)
    
    return desktop_file


def install_icon(icon_path: str, app_name: str) -> str:
    """Install application icon to the appropriate Linux location"""
    if not os.path.exists(icon_path):
        raise FileNotFoundError(f"Icon file not found: {icon_path}")
    
    # Determine icon size and format
    icon_name = f"{app_name.lower()}.png"
    
    # Install to user's icon directory
    icon_dir = os.path.expanduser("~/.local/share/icons/hicolor/256x256/apps")
    Path(icon_dir).mkdir(parents=True, exist_ok=True)
    
    import shutil
    dest_path = os.path.join(icon_dir, icon_name)
    shutil.copy2(icon_path, dest_path)
    
    return dest_path


def check_fuse_available() -> bool:
    """Check if FUSE is available for AppImage execution"""
    try:
        result = subprocess.run(
            ["which", "fusermount"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except:
        return False


def get_system_requirements() -> Dict[str, Any]:
    """Get system requirements and compatibility information"""
    requirements = {
        "os": platform.system(),
        "architecture": platform.machine(),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
        "distro": get_linux_distro(),
        "desktop_environment": get_desktop_environment(),
        "fuse_available": check_fuse_available(),
        "appimage_support": check_fuse_available(),  # FUSE is required for AppImages
    }
    
    return requirements


def run_subprocess_safe(*args, **kwargs):
    """
    Linux-safe subprocess execution
    
    Unlike Windows, Linux doesn't need special console window handling,
    but we still provide a consistent interface.
    """
    # Remove Windows-specific arguments if present
    kwargs.pop('startupinfo', None)
    kwargs.pop('creationflags', None)
    
    return subprocess.run(*args, **kwargs)


def safe_print(message: str, use_colors: bool = True):
    """
    Print message with optional color support for Linux terminals
    """
    if not use_colors or not sys.stdout.isatty():
        print(message)
        return
    
    # Simple color support for Linux terminals
    # This could be extended with more sophisticated color handling
    print(message)


def get_file_manager_command() -> Optional[str]:
    """Get the default file manager command for the current desktop environment"""
    desktop_env = get_desktop_environment()
    
    file_managers = {
        "gnome": "nautilus",
        "kde": "dolphin",
        "xfce": "thunar",
        "cinnamon": "nemo",
        "mate": "caja",
    }
    
    # Try desktop-specific file manager
    if desktop_env in file_managers:
        cmd = file_managers[desktop_env]
        try:
            subprocess.run(["which", cmd], capture_output=True, check=True)
            return cmd
        except:
            pass
    
    # Fallback to common file managers
    fallback_managers = ["nautilus", "dolphin", "thunar", "pcmanfm", "ranger"]
    
    for manager in fallback_managers:
        try:
            subprocess.run(["which", manager], capture_output=True, check=True)
            return manager
        except:
            continue
    
    return None


def open_file_manager(path: str):
    """Open file manager at the specified path"""
    file_manager = get_file_manager_command()
    
    if file_manager:
        try:
            subprocess.run([file_manager, path], check=False)
            return True
        except:
            pass
    
    # Fallback to xdg-open
    try:
        subprocess.run(["xdg-open", path], check=False)
        return True
    except:
        pass
    
    return False


def integrate_with_desktop():
    """Integrate the application with the Linux desktop environment"""
    try:
        # Get application paths
        if getattr(sys, 'frozen', False):
            # Running as executable
            app_path = sys.executable
        else:
            # Running as script
            app_path = os.path.abspath(__file__)
        
        # Find icon
        icon_path = get_linux_resource_path("assets/new_logo_1.png")
        
        # Install icon
        if os.path.exists(icon_path):
            installed_icon = install_icon(icon_path, "Ogresync")
            print(f"Icon installed: {installed_icon}")
        
        # Create desktop file
        desktop_file = create_desktop_file(
            "Ogresync",
            app_path,
            "ogresync",
            "Obsidian Sync Alternative - Git-based vault synchronization"
        )
        print(f"Desktop file created: {desktop_file}")
        
        return True
        
    except Exception as e:
        print(f"Desktop integration failed: {e}")
        return False


# Convenience functions for compatibility with main packaging_utils
def init_linux_packaging_compatibility():
    """Initialize Linux-specific packaging compatibility"""
    if not is_linux():
        return False
    
    # Set up any necessary environment variables or configurations
    requirements = get_system_requirements()
    
    print(f"Linux packaging initialized:")
    print(f"  Distribution: {requirements['distro']['name']}")
    print(f"  Desktop: {requirements['desktop_environment']}")
    print(f"  FUSE: {'Available' if requirements['fuse_available'] else 'Not available'}")
    
    return True


if __name__ == "__main__":
    # Test the Linux packaging utilities
    print("Testing Linux Packaging Utilities")
    print("=" * 40)
    
    print("\nSystem Information:")
    requirements = get_system_requirements()
    for key, value in requirements.items():
        print(f"  {key}: {value}")
    
    print(f"\nConfiguration directory: {get_linux_config_directory()}")
    print(f"Data directory: {get_linux_data_directory()}")
    print(f"File manager: {get_file_manager_command()}")
    
    print(f"\nResource path test: {get_linux_resource_path('assets/new_logo_1.png')}")
    
    if "--integrate" in sys.argv:
        print("\nAttempting desktop integration...")
        integrate_with_desktop()
