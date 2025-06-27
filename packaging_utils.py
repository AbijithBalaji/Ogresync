"""
Packaging Utilities for Ogresync

This module provides utilities to handle common issues when packaging Python applications
with PyInstaller, particularly for Windows.

Key features:
- Safe Unicode character handling for packaged applications
- Resource path resolution for bundled assets
- Console window management
- Cross-platform compatibility helpers

Author: Ogresync Development Team
Date: June 2025
"""

import os
import sys
import platform
from typing import Optional


def is_packaged_app() -> bool:
    """
    Check if the application is running as a packaged executable.
    
    Returns:
        True if running as packaged app (PyInstaller), False otherwise
    """
    return getattr(sys, 'frozen', False)


def get_resource_path(relative_path: str) -> str:
    """
    Get the absolute path to a resource file, handling both development and packaged modes.
    
    Args:
        relative_path: Path relative to the application root
        
    Returns:
        Absolute path to the resource
    """
    if is_packaged_app():
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    else:
        # Development mode - use script directory
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, relative_path)


def safe_unicode_char(char: str, fallback: str = "?") -> str:
    """
    Safely handle Unicode characters that might cause issues in packaged applications.
    
    Args:
        char: Unicode character to display
        fallback: Fallback character if Unicode fails
        
    Returns:
        Safe character to display
    """
    if not is_packaged_app():
        return char
    
    try:
        # Test if the character can be encoded/decoded safely
        char.encode('utf-8').decode('utf-8')
        return char
    except (UnicodeEncodeError, UnicodeDecodeError):
        return fallback


class SafeUnicodeChars:
    """
    Safe Unicode characters for packaged applications with fallbacks.
    """
    # Checkmarks and status indicators
    CHECK_MARK = safe_unicode_char("✅", "[OK]")
    CROSS_MARK = safe_unicode_char("❌", "[FAIL]")
    WARNING = safe_unicode_char("⚠️", "[WARN]")
    INFO = safe_unicode_char("ℹ️", "[INFO]")
    
    # Progress indicators
    ARROW_RIGHT = safe_unicode_char("→", "->")
    ARROW_DOWN = safe_unicode_char("↓", "v")
    BULLET = safe_unicode_char("•", "*")
    
    # File and folder icons
    FOLDER = safe_unicode_char("📁", "[DIR]")
    FILE = safe_unicode_char("📄", "[FILE]")
    GEAR = safe_unicode_char("⚙️", "[GEAR]")
    KEY = safe_unicode_char("🔑", "[KEY]")
    
    # Network and sync
    SYNC = safe_unicode_char("🔄", "[SYNC]")
    UPLOAD = safe_unicode_char("⬆️", "[UP]")
    DOWNLOAD = safe_unicode_char("⬇️", "[DOWN]")
    CONNECTED = safe_unicode_char("🔗", "[CONN]")
    DISCONNECTED = safe_unicode_char("❗", "[DISC]")


def get_subprocess_startupinfo():
    """
    Get appropriate STARTUPINFO for subprocess calls to hide console windows in packaged apps.
    
    Returns:
        STARTUPINFO object for Windows or None for other platforms
    """
    if platform.system() == "Windows" and is_packaged_app():
        import subprocess
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        return startupinfo
    return None


def safe_print(message: str, use_unicode: bool = True):
    """
    Safely print messages, handling Unicode issues in packaged applications.
    
    Args:
        message: Message to print
        use_unicode: Whether to attempt Unicode characters
    """
    if not use_unicode or is_packaged_app():
        # Replace common Unicode characters with ASCII equivalents
        replacements = {
            "✅": "[OK]",
            "❌": "[FAIL]", 
            "⚠️": "[WARN]",
            "ℹ️": "[INFO]",
            "→": "->",
            "↓": "v",
            "•": "*",
            "📁": "[DIR]",
            "📄": "[FILE]",
            "⚙️": "[GEAR]",
            "🔑": "[KEY]",
            "🔄": "[SYNC]",
            "⬆️": "[UP]",
            "⬇️": "[DOWN]",
            "🔗": "[CONN]",
            "❗": "[DISC]"
        }
        
        for unicode_char, ascii_fallback in replacements.items():
            message = message.replace(unicode_char, ascii_fallback)
    
    try:
        print(message)
    except UnicodeEncodeError:
        # Last resort: encode to ASCII with error handling
        print(message.encode('ascii', 'replace').decode('ascii'))


def get_config_directory() -> str:
    """
    Get the OS-specific application data directory for Ogresync.
    Handles both development and packaged modes.
    
    Returns:
        Path to config directory
    """
    if platform.system() == "Windows":
        config_dir = os.path.join(os.environ.get("APPDATA", ""), "Ogresync")
    elif platform.system() == "Darwin":  # macOS
        config_dir = os.path.expanduser("~/Library/Application Support/Ogresync")
    else:  # Linux and others
        config_dir = os.path.expanduser("~/.config/ogresync")
    
    # Ensure the directory exists
    os.makedirs(config_dir, exist_ok=True)
    return config_dir


def handle_packaged_app_paths():
    """
    Handle path resolution issues in packaged applications.
    Call this early in the application startup.
    """
    if is_packaged_app():
        # Add the packaged app directory to Python path if needed
        if hasattr(sys, '_MEIPASS'):
            packaged_dir = getattr(sys, '_MEIPASS')
            if packaged_dir not in sys.path:
                sys.path.insert(0, packaged_dir)


# Convenience function for easy import
def init_packaging_compatibility():
    """
    Initialize packaging compatibility settings.
    Call this at the beginning of your main application.
    """
    handle_packaged_app_paths()
    
    # Set console encoding for Windows if needed
    if platform.system() == "Windows" and is_packaged_app():
        try:
            # Set console code page to UTF-8 for better Unicode support
            import locale
            locale.setlocale(locale.LC_ALL, 'C.UTF-8')
        except Exception:
            # If encoding setup fails, continue without it
            pass


if __name__ == "__main__":
    # Test the utilities
    print("Packaging Utilities Test")
    print(f"Is packaged: {is_packaged_app()}")
    print(f"Config directory: {get_config_directory()}")
    print("Unicode characters test:")
    chars = SafeUnicodeChars()
    print(f"Check: {chars.CHECK_MARK}")
    print(f"Cross: {chars.CROSS_MARK}")
    print(f"Arrow: {chars.ARROW_RIGHT}")
    print(f"Folder: {chars.FOLDER}")
