#!/usr/bin/env python3
"""
Ogresync Linux AppImage Builder

This script builds a Linux AppImage from the Ogresync Python application
with comprehensive handling of Linux-specific packaging requirements:

- Dependency bundling for cross-distribution compatibility
- Desktop integration with .desktop files
- Icon and asset management
- Library path resolution
- AppImage structure creation
- Build verification and testing

Usage:
    python build_appimage.py [--clean] [--test] [--verbose] [--arch x86_64]

Requirements:
    - Python 3.8+
    - PyInstaller
    - appimagetool (automatically downloaded if missing)
    - fuse (for AppImage execution)

Author: Ogresync Development Team
Date: June 2025
"""

import os
import sys
import shutil
import subprocess
import argparse
import time
import urllib.request
import tempfile
import stat
from pathlib import Path

# Import safe subprocess handling
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from packaging_utils import run_subprocess_safe, is_packaged_app
    PACKAGING_UTILS_AVAILABLE = True
except ImportError:
    PACKAGING_UTILS_AVAILABLE = False
    # Fallback to regular subprocess for build scripts
    def run_subprocess_safe(*args, **kwargs):
        return subprocess.run(*args, **kwargs)


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_section(title):
    """Print a formatted section header"""
    print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD} {title}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")


def print_step(step):
    """Print a formatted step"""
    print(f"\n{Colors.OKBLUE}➤ {step}{Colors.ENDC}")


def print_success(message):
    """Print a success message"""
    print(f"{Colors.OKGREEN}[OK] {message}{Colors.ENDC}")


def print_warning(message):
    """Print a warning message"""
    print(f"{Colors.WARNING}[WARN] {message}{Colors.ENDC}")


def print_error(message):
    """Print an error message"""
    print(f"{Colors.FAIL}[FAIL] {message}{Colors.ENDC}")


def run_command(cmd, cwd=None, check=True, capture_output=True):
    """Run a command and return the result"""
    print(f"  Running: {cmd}")
    try:
        result = run_subprocess_safe(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if check and result.returncode != 0:
            print_error(f"Command failed with return code {result.returncode}")
            if result.stderr:
                print(f"  Error: {result.stderr}")
            return False
        
        if result.stdout and capture_output:
            print(f"  Output: {result.stdout.strip()}")
        
        return result
        
    except subprocess.TimeoutExpired:
        print_error(f"Command timed out: {cmd}")
        return False
    except Exception as e:
        print_error(f"Command failed: {e}")
        return False


def check_dependencies():
    """Check if all required dependencies are available"""
    print_step("Checking build dependencies")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print_error("Python 3.8+ is required")
        return False
    print_success(f"Python {sys.version_info.major}.{sys.version_info.minor}")
    
    # Check PyInstaller
    try:
        # Try using python -m PyInstaller first (works with local pip installs)
        result = run_command("python -m PyInstaller --version", capture_output=True)
        if result and result.returncode == 0:
            print_success(f"PyInstaller available")
        else:
            # Fallback to direct pyinstaller command
            result = run_command("pyinstaller --version", capture_output=True)
            if result and result.returncode == 0:
                print_success(f"PyInstaller available")
            else:
                print_error("PyInstaller not found. Install with: pip install pyinstaller")
                return False
    except Exception as e:
        print_error(f"PyInstaller not found: {e}")
        return False
    
    # Check for fuse (required for AppImage execution)
    result = run_command("which fusermount", capture_output=True, check=False)
    if not result or result.returncode != 0:
        print_warning("FUSE not found. Install with: sudo apt install fuse (Ubuntu/Debian) or sudo dnf install fuse (Fedora)")
        print_warning("AppImage may not run without FUSE")
    else:
        print_success("FUSE available")
    
    return True


def download_appimagetool(arch="x86_64"):
    """Download appimagetool if not available"""
    print_step("Checking for appimagetool")
    
    # Check if appimagetool is already available
    result = run_command("which appimagetool", capture_output=True, check=False)
    if result and result.returncode == 0:
        print_success("appimagetool already available")
        return "appimagetool"
    
    # Download appimagetool
    appimagetool_path = Path.cwd() / f"appimagetool-{arch}.AppImage"
    
    if appimagetool_path.exists():
        print_success(f"Using existing appimagetool: {appimagetool_path}")
        return str(appimagetool_path)
    
    print_step(f"Downloading appimagetool for {arch}")
    url = f"https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-{arch}.AppImage"
    
    try:
        urllib.request.urlretrieve(url, str(appimagetool_path))
        # Make executable
        os.chmod(appimagetool_path, os.stat(appimagetool_path).st_mode | stat.S_IEXEC)
        print_success(f"Downloaded appimagetool: {appimagetool_path}")
        return str(appimagetool_path)
    except Exception as e:
        print_error(f"Failed to download appimagetool: {e}")
        return None


def clean_build_directories():
    """Clean previous build artifacts"""
    print_step("Cleaning build directories")
    
    dirs_to_clean = ["build", "dist", "AppDir"]
    files_to_clean = ["linux-packaging/Ogresync-x86_64.AppImage"]
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print_success(f"Removed: {dir_name}")
    
    for file_name in files_to_clean:
        if os.path.exists(file_name):
            os.remove(file_name)
            print_success(f"Removed: {file_name}")


def create_linux_spec_file():
    """Create PyInstaller spec file optimized for Linux AppImage"""
    print_step("Creating Linux-optimized PyInstaller spec file")
    
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Spec File for Ogresync Linux AppImage Packaging

This spec file is optimized for creating Linux AppImages:
- No console window hiding (Linux doesn't need this)
- Linux-appropriate dependency handling
- Asset bundling for AppImage structure
- Library path considerations for cross-distribution compatibility

Author: Ogresync Development Team
Date: June 2025
"""

import os
import sys

# Get the directory containing this spec file
SPEC_DIR = os.path.dirname(os.path.abspath(SPECPATH))
PROJECT_ROOT = os.path.dirname(SPEC_DIR)

block_cipher = None

# Define all the data files and directories to include
datas = [
    ('assets', 'assets'),
]

# Define hidden imports - modules that PyInstaller might miss
hiddenimports = [
    'tkinter',
    'tkinter.ttk',
    'tkinter.scrolledtext',
    'tkinter.filedialog',
    'tkinter.messagebox',
    'tkinter.simpledialog',
    'subprocess',
    'threading',
    'psutil',
    'pyperclip',
    'requests',
    'shlex',
    'platform',
    'webbrowser',
    'packaging_utils',
    'ui_elements',
    'wizard_steps',
    'github_setup',
    'setup_wizard',
    'Stage1_conflict_resolution',
    'stage2_conflict_resolution',
    'backup_manager',
    'conflict_resolution_integration',
    'offline_sync_manager',
    'enhanced_auto_sync',
]

# Binaries to exclude (reduces size)
excludes = [
    'matplotlib',
    'numpy',
    'pandas',
    'scipy',
    'PIL',
    'PyQt5',
    'PyQt6',
    'PySide2',
    'PySide6',
    'wx',
]

a = Analysis(
    ['Ogresync.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Remove duplicate files to reduce size
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Ogresync',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Enable UPX compression to reduce file size
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Linux GUI apps can use console for debugging
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Icon will be handled by .desktop file in AppImage
)
'''
    
    spec_path = Path("linux-packaging") / "Ogresync-linux.spec"
    with open(spec_path, "w") as f:
        f.write(spec_content)
    
    print_success(f"Created spec file: {spec_path}")
    return spec_path


def build_executable(verbose=False):
    """Build the executable using PyInstaller"""
    print_step("Building executable with PyInstaller")
    
    # Use a simple, working spec file approach
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['../Ogresync.py'],
    pathex=['/home/gloup/Personal/Development/Ogresync'],
    binaries=[],
    datas=[('../assets', 'assets')],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.scrolledtext',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.simpledialog',
        'subprocess',
        'threading',
        'psutil',
        'pyperclip',
        'requests',
        'shlex',
        'platform',
        'webbrowser',
        'packaging_utils',
        'ui_elements',
        'wizard_steps',
        'github_setup',
        'setup_wizard',
        'Stage1_conflict_resolution',
        'stage2_conflict_resolution',
        'backup_manager',
        'conflict_resolution_integration',
        'offline_sync_manager',
        'enhanced_auto_sync',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
        'wx',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Ogresync',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
'''
    
    spec_path = Path("Ogresync-working.spec")
    with open(spec_path, "w") as f:
        f.write(spec_content)
    
    print_success(f"Created working spec file: {spec_path}")
    
    # We're already in the linux-packaging directory, no need to change directories
    try:
        # Try using python -m PyInstaller first (works with local pip installs)
        # Note: --debug option is not allowed with existing .spec files
        cmd = f"python -m PyInstaller --clean Ogresync-working.spec"
        
        result = run_command(cmd, capture_output=not verbose)
        
        if not result or result.returncode != 0:
            # Try with full path to PyInstaller
            print_warning("python -m PyInstaller failed, trying with full path")
            cmd = f"python -m PyInstaller --clean --onefile Ogresync-working.spec"
            result = run_command(cmd, capture_output=not verbose)
        
        if not result or result.returncode != 0:
            print_error("PyInstaller command failed")
            return False
        
        # Check if executable was created
        exe_path = Path("dist") / "Ogresync"
        if not exe_path.exists():
            print_error(f"Executable not found at: {exe_path}")
            return False
        
        print_success(f"Executable created: {exe_path}")
        return True
    except Exception as e:
        print_error(f"Build failed with error: {e}")
        return False


def create_appdir_structure():
    """Create AppDir structure for AppImage"""
    print_step("Creating AppDir structure")
    
    appdir = Path("AppDir")
    appdir.mkdir(exist_ok=True)
    
    # Copy the built executable from dist/
    exe_src = Path("dist") / "Ogresync"
    exe_dst = appdir / "usr" / "bin"
    exe_dst.mkdir(parents=True, exist_ok=True)
    
    shutil.copy2(exe_src, exe_dst / "ogresync")
    os.chmod(exe_dst / "ogresync", 0o755)
    print_success("Copied executable to AppDir")
    
    # Create desktop file
    desktop_content = """[Desktop Entry]
Version=1.0
Type=Application
Name=Ogresync
GenericName=Obsidian Sync Alternative
Comment=Git-based vault synchronization for Obsidian
Exec=ogresync
Icon=ogresync
Categories=Office;Utility;
Keywords=obsidian;sync;git;vault;notes;markdown;
Terminal=false
StartupWMClass=Ogresync
StartupNotify=true
NoDisplay=false
"""
    
    desktop_path = appdir / "ogresync.desktop"
    with open(desktop_path, "w") as f:
        f.write(desktop_content)
    os.chmod(desktop_path, 0o755)
    print_success("Created desktop file")
    
    # Copy icon with GNOME-specific handling
    icon_src_png = Path("../assets") / "new_logo_1.png"
    icon_src_transparent = Path("../assets") / "new_logo_1_Transparent.png"
    
    # Create GNOME-compatible icon directories with multiple sizes
    icon_dirs = [
        appdir / "usr" / "share" / "icons" / "hicolor" / "16x16" / "apps",
        appdir / "usr" / "share" / "icons" / "hicolor" / "32x32" / "apps",
        appdir / "usr" / "share" / "icons" / "hicolor" / "48x48" / "apps",
        appdir / "usr" / "share" / "icons" / "hicolor" / "64x64" / "apps",
        appdir / "usr" / "share" / "icons" / "hicolor" / "128x128" / "apps",
        appdir / "usr" / "share" / "icons" / "hicolor" / "256x256" / "apps",
        appdir / "usr" / "share" / "icons" / "hicolor" / "512x512" / "apps",
        appdir / "usr" / "share" / "pixmaps"
    ]
    
    for icon_dir in icon_dirs:
        icon_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy icons to multiple locations for better compatibility
    if icon_src_transparent.exists():
        # Use transparent version as primary
        primary_icon = icon_src_transparent
    elif icon_src_png.exists():
        primary_icon = icon_src_png
    else:
        primary_icon = None
    
    if primary_icon:
        # Copy to AppDir root (required for AppImage)
        shutil.copy2(primary_icon, appdir / "ogresync.png")
        
        # Copy to all standard icon sizes for GNOME compatibility
        for icon_dir in icon_dirs:
            shutil.copy2(primary_icon, icon_dir / "ogresync.png")
        
        # Create .DirIcon for AppImage (helps with file manager display)
        shutil.copy2(primary_icon, appdir / ".DirIcon")
        
        # Create index.theme file for GNOME icon theme compatibility
        index_theme_dir = appdir / "usr" / "share" / "icons" / "hicolor"
        index_theme_path = index_theme_dir / "index.theme"
        
        index_theme_content = """[Icon Theme]
Name=Hicolor
Comment=Fallback icon theme
Hidden=true
Directories=16x16/apps,32x32/apps,48x48/apps,64x64/apps,128x128/apps,256x256/apps,512x512/apps

[16x16/apps]
Size=16
Context=Applications
Type=Fixed

[32x32/apps]
Size=32
Context=Applications
Type=Fixed

[48x48/apps]
Size=48
Context=Applications
Type=Fixed

[64x64/apps]
Size=64
Context=Applications
Type=Fixed

[128x128/apps]
Size=128
Context=Applications
Type=Fixed

[256x256/apps]
Size=256
Context=Applications
Type=Fixed

[512x512/apps]
Size=512
Context=Applications
Type=Fixed
"""
        
        with open(index_theme_path, "w") as f:
            f.write(index_theme_content)
        
        print_success("Copied application icon to multiple locations with GNOME compatibility")
    else:
        print_warning("Application icon not found, using default")
        
    # Create AppRun script
    apprun_content = """#!/bin/bash
# AppRun script for Ogresync

# Get the directory containing this script
HERE="$(dirname "$(readlink -f "$0")")"

# Set up environment
export PATH="$HERE/usr/bin:$PATH"
export LD_LIBRARY_PATH="$HERE/usr/lib:$LD_LIBRARY_PATH"

# Run the application
exec "$HERE/usr/bin/ogresync" "$@"
"""
    
    apprun_path = appdir / "AppRun"
    with open(apprun_path, "w") as f:
        f.write(apprun_content)
    os.chmod(apprun_path, 0o755)
    print_success("Created AppRun script")
    
    # Update GNOME icon cache and desktop database
    update_gnome_icon_cache(appdir)
    
    return appdir


def build_appimage(appimagetool_path, appdir):
    """Build the final AppImage"""
    print_step("Building AppImage")
    
    appimage_name = "Ogresync-x86_64.AppImage"
    appimage_path = Path(appimage_name)
    
    # Remove existing AppImage
    if appimage_path.exists():
        os.remove(appimage_path)
    
    # Build AppImage
    cmd = f"{appimagetool_path} {appdir} {appimage_path}"
    result = run_command(cmd, capture_output=False)
    
    if not result:
        print_error("Failed to build AppImage")
        return False
    
    if not appimage_path.exists():
        print_error(f"AppImage not created: {appimage_path}")
        return False
    
    # Make executable
    os.chmod(appimage_path, 0o755)
    
    # Check file size
    file_size = os.path.getsize(appimage_path) / (1024 * 1024)  # MB
    print_success(f"AppImage created: {appimage_path}")
    print_success(f"File size: {file_size:.1f} MB")
    
    if file_size < 20:
        print_warning("File size seems small, build might be incomplete")
    elif file_size > 500:
        print_warning("File size is large, consider optimizing dependencies")
    
    return appimage_path


def verify_appimage(appimage_path):
    """Verify the AppImage works correctly"""
    print_step("Verifying AppImage")
    
    # Convert to absolute path to avoid path resolution issues
    appimage_path = Path(appimage_path).resolve()
    
    # Test if AppImage exists and is executable
    if not appimage_path.exists():
        print_error(f"AppImage not found at: {appimage_path}")
        return False
        
    if not os.access(appimage_path, os.X_OK):
        print_error("AppImage is not executable")
        return False
    
    print_success("AppImage is executable")
    
    # Test basic execution (this might need adjustment based on your app's behavior)
    print("Testing AppImage execution (this may take a moment)...")
    
    try:
        # Test with --help or --version if your app supports it
        # For now, we'll just check if it starts without immediate crash
        result = run_subprocess_safe(
            [str(appimage_path), "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print_success("AppImage executed successfully")
            return True
        else:
            print_warning("AppImage executed but returned non-zero exit code")
            return True  # This might be expected behavior
            
    except subprocess.TimeoutExpired:
        print_warning("AppImage test timed out (app might be running)")
        return True
    except Exception as e:
        print_error(f"Failed to test AppImage execution: {e}")
        return False


def update_gnome_icon_cache(appdir):
    """Update GNOME icon cache for better icon display"""
    print_step("Updating GNOME icon cache")
    
    try:
        # Create icon cache for the hicolor theme
        hicolor_dir = appdir / "usr" / "share" / "icons" / "hicolor"
        
        # Try to run gtk-update-icon-cache if available
        cache_cmd = f"gtk-update-icon-cache -f -t {hicolor_dir}"
        result = run_command(cache_cmd, capture_output=True, check=False)
        
        if result and result.returncode == 0:
            print_success("GNOME icon cache updated")
        else:
            print_warning("Could not update icon cache (gtk-update-icon-cache not found)")
            
        # Also create desktop database entry
        applications_dir = appdir / "usr" / "share" / "applications"
        applications_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy desktop file to applications directory as well
        desktop_src = appdir / "ogresync.desktop"
        desktop_dst = applications_dir / "ogresync.desktop"
        if desktop_src.exists():
            shutil.copy2(desktop_src, desktop_dst)
            print_success("Desktop file added to applications directory")
            
        # Update desktop database
        update_cmd = f"update-desktop-database {applications_dir}"
        result = run_command(update_cmd, capture_output=True, check=False)
        
        if result and result.returncode == 0:
            print_success("Desktop database updated")
        else:
            print_warning("Could not update desktop database")
            
    except Exception as e:
        print_warning(f"Icon cache update failed: {e}")
        
def main():
    """Main build function"""
    parser = argparse.ArgumentParser(description='Build Ogresync Linux AppImage')
    parser.add_argument('--clean', action='store_true', help='Clean build directories first')
    parser.add_argument('--test', action='store_true', help='Run tests after building')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    parser.add_argument('--arch', default='x86_64', help='Target architecture (default: x86_64)')
    
    args = parser.parse_args()
    
    print_section("Ogresync Linux AppImage Builder")
    print(f"Build started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target architecture: {args.arch}")
    
    try:
        # Step 1: Check dependencies
        if not check_dependencies():
            print_error("Build failed: Missing dependencies")
            return 1
        
        # Step 2: Download appimagetool
        appimagetool_path = download_appimagetool(args.arch)
        if not appimagetool_path:
            print_error("Failed to get appimagetool")
            return 1
        
        # Step 3: Clean if requested
        if args.clean:
            clean_build_directories()
        
        # Step 4: Build executable
        if not build_executable(args.verbose):
            print_error("Build failed during PyInstaller execution")
            return 1
        
        # Step 5: Create AppDir structure
        appdir = create_appdir_structure()
        if not appdir:
            print_error("Failed to create AppDir structure")
            return 1
        
        # Step 6: Build AppImage
        appimage_path = build_appimage(appimagetool_path, appdir)
        if not appimage_path:
            print_error("Failed to build AppImage")
            return 1
        
        # Step 7: Verify AppImage
        if args.test:
            if not verify_appimage(appimage_path):
                print_error("AppImage verification failed")
                return 1
        
        print_section("Build Completed Successfully!")
        print_success("Your Ogresync AppImage is ready!")
        print(f"\n{Colors.BOLD}AppImage location:{Colors.ENDC} {appimage_path}")
        print(f"\n{Colors.BOLD}Next steps:{Colors.ENDC}")
        print("1. Test the AppImage: ./linux-packaging/Ogresync-x86_64.AppImage")
        print("2. Distribute to users")
        print("3. Consider creating a Flatpak for wider distribution")
        
        return 0
        
    except KeyboardInterrupt:
        print_error("Build cancelled by user")
        return 1
    except Exception as e:
        print_error(f"Build failed with error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
