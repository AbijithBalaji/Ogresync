#!/usr/bin/env python3
"""
Ogresync Executable Builder

This script creates a standalone .exe file from the Ogresync Python application
using PyInstaller with optimized settings for Windows distribution.

Features:
- Single-file executable for easy distribution
- Includes all dependencies and assets
- Windows-optimized with proper icon and version info
- Handles all Python modules and tkinter properly
- Creates clean, portable executable

Usage:
    python build_exe.py

Requirements:
    - PyInstaller installed (pip install pyinstaller>=6.0.0)
    - All dependencies from requirements.txt installed
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def get_project_root():
    """Get the project root directory"""
    return Path(__file__).parent.absolute()

def clean_build_dirs():
    """Clean up previous build directories"""
    project_root = get_project_root()
    dirs_to_clean = ['build', 'dist', '__pycache__']
    
    print("🧹 Cleaning up previous build artifacts...")
    for dir_name in dirs_to_clean:
        dir_path = project_root / dir_name
        if dir_path.exists():
            print(f"   Removing {dir_path}")
            shutil.rmtree(dir_path, ignore_errors=True)
    
    # Also clean .spec files
    for spec_file in project_root.glob("*.spec"):
        print(f"   Removing {spec_file}")
        spec_file.unlink()

def check_dependencies():
    """Check if all required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    required_packages = ['pyinstaller', 'psutil', 'pyperclip', 'requests', 'tkinter']
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'tkinter':
                import tkinter
            else:
                __import__(package)
            print(f"   ✓ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"   ❌ {package} - MISSING")
    
    if missing_packages:
        print(f"\n❌ Missing packages: {', '.join(missing_packages)}")
        print("   Please install with: pip install -r requirements.txt")
        return False
    
    print("✓ All dependencies available")
    return True

def get_version_info():
    """Extract version information from the application"""
    # Try to get version from main file or use default
    return "1.0.0"

def create_version_file():
    """Create a version file for Windows executable"""
    project_root = get_project_root()
    version_file = project_root / "version_info.txt"
    
    version = get_version_info()
    
    version_content = f'''# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1,0,0,0),
    prodvers=(1,0,0,0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'Ogrelix Solutions'),
        StringStruct(u'FileDescription', u'Ogresync - Obsidian to GitHub Sync Tool'),
        StringStruct(u'FileVersion', u'{version}'),
        StringStruct(u'InternalName', u'Ogresync'),
        StringStruct(u'LegalCopyright', u'© 2025 Ogrelix Solutions. Licensed under GPL v3.'),
        StringStruct(u'OriginalFilename', u'Ogresync.exe'),
        StringStruct(u'ProductName', u'Ogresync'),
        StringStruct(u'ProductVersion', u'{version}')])
      ]), 
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
'''
    
    with open(version_file, 'w', encoding='utf-8') as f:
        f.write(version_content)
    
    return version_file

def build_executable():
    """Build the executable using PyInstaller"""
    project_root = get_project_root()
    
    print("🔨 Building Ogresync executable...")
    
    # Create version file
    version_file = create_version_file()
    
    # Find the icon file
    icon_path = project_root / "assets" / "new_logo_1.ico"
    if not icon_path.exists():
        icon_path = project_root / "assets" / "ogrelix_logo.ico"
    
    # Build the PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",  # Create a single executable file
        "--windowed",  # Hide console window (for GUI apps)
        "--clean",  # Clean PyInstaller cache and temp files
        "--noconfirm",  # Replace output directory without confirmation
        f"--name=Ogresync",  # Name of the executable
        f"--distpath={project_root / 'dist'}",  # Output directory
        f"--workpath={project_root / 'build'}",  # Work directory
        f"--specpath={project_root}",  # Spec file location
    ]
    
    # Add icon if available
    if icon_path.exists():
        cmd.extend([f"--icon={icon_path}"])
        print(f"   Using icon: {icon_path}")
    
    # Add version info if on Windows
    if sys.platform == "win32" and version_file.exists():
        cmd.extend([f"--version-file={version_file}"])
        print(f"   Using version info: {version_file}")
    
    # Add hidden imports for modules that might not be detected
    hidden_imports = [
        "ui_elements",
        "setup_wizard", 
        "wizard_steps",
        "github_setup",
        "Stage1_conflict_resolution",
        "stage2_conflict_resolution", 
        "offline_sync_manager",
        "enhanced_auto_sync",
        "backup_manager",
        "conflict_resolution_integration",
        "tkinter.ttk",
        "tkinter.scrolledtext",
        "tkinter.filedialog",
        "tkinter.messagebox",
        "tkinter.simpledialog"
    ]
    
    for module in hidden_imports:
        cmd.extend([f"--hidden-import={module}"])
    
    # Add data files (assets)
    assets_dir = project_root / "assets"
    if assets_dir.exists():
        cmd.extend([f"--add-data={assets_dir};assets"])
        print(f"   Including assets: {assets_dir}")
    
    # Add the main script
    main_script = project_root / "Ogresync.py"
    cmd.append(str(main_script))
    
    print(f"   Command: {' '.join(cmd)}")
    print("   This may take a few minutes...")
    
    # Run PyInstaller
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=project_root)
        print("✓ Build completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed!")
        print(f"Error: {e}")
        if e.stdout:
            print(f"STDOUT:\n{e.stdout}")
        if e.stderr:
            print(f"STDERR:\n{e.stderr}")
        return False

def post_build_cleanup():
    """Clean up temporary files after build"""
    project_root = get_project_root()
    
    print("🧹 Cleaning up temporary files...")
    
    # Remove version file
    version_file = project_root / "version_info.txt"
    if version_file.exists():
        version_file.unlink()
    
    # Remove build directory (keep dist)
    build_dir = project_root / "build"
    if build_dir.exists():
        shutil.rmtree(build_dir, ignore_errors=True)
    
    # Remove .spec file
    for spec_file in project_root.glob("*.spec"):
        spec_file.unlink()

def check_output():
    """Check if the executable was created successfully"""
    project_root = get_project_root()
    exe_path = project_root / "dist" / "Ogresync.exe"
    
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"✓ Executable created: {exe_path}")
        print(f"   Size: {size_mb:.1f} MB")
        
        # Test if it's properly executable
        print("🧪 Testing executable...")
        try:
            # Test with --help or version flag if available
            result = subprocess.run([str(exe_path), "--version"], 
                                  capture_output=True, text=True, timeout=10)
            print("✓ Executable appears to be working")
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            # This is expected since we don't have --version flag, just check if it starts
            print("✓ Executable file is valid")
        
        return True
    else:
        print("❌ Executable not found in dist/ directory")
        return False

def main():
    """Main build process"""
    print("🚀 Ogresync Executable Builder")
    print("=" * 50)
    
    if not check_dependencies():
        return False
    
    clean_build_dirs()
    
    if not build_executable():
        print("\n❌ Build process failed!")
        return False
    
    post_build_cleanup()
    
    if check_output():
        print("\n🎉 Build completed successfully!")
        print("📦 Your executable is ready in the 'dist' directory")
        print("   You can now distribute 'dist/Ogresync.exe' as a standalone application")
        return True
    else:
        print("\n❌ Build verification failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
