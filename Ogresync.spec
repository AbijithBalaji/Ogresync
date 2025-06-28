# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Spec File for Ogresync Windows Packaging

This spec file addresses common packaging issues:
- Console window hiding for subprocess calls
- Asset bundling and path resolution
- Unicode character handling
- Dependency management
- Windows-specific optimizations

Author: Ogresync Development Team
Date: June 2025
"""

import os
import sys

# Get the directory containing this spec file
SPEC_DIR = os.path.dirname(os.path.abspath(__name__))

block_cipher = None

# Define all the data files and directories to include
datas = [
    # Include assets directory
    ('assets', 'assets'),
    # Include any config templates or default files if they exist
    # ('config_templates', 'config_templates'),
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
    pathex=[SPEC_DIR],
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
    console=False,  # Set to False to hide console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(SPEC_DIR, 'assets', 'new_logo_1.ico') if os.path.exists(os.path.join(SPEC_DIR, 'assets', 'new_logo_1.ico')) else None,
    version_file=os.path.join(SPEC_DIR, 'version_info.txt') if os.path.exists(os.path.join(SPEC_DIR, 'version_info.txt')) else None,
)

# Create additional files for distribution
# This section runs after the exe is built
import shutil

def create_distribution_files():
    """Create additional files for the distribution package"""
    dist_dir = os.path.join(SPEC_DIR, 'dist')
    
    if os.path.exists(dist_dir):
        # Copy README and LICENSE to dist folder
        for file in ['README.md', 'LICENSE', 'CONTRIBUTING.md']:
            src = os.path.join(SPEC_DIR, file)
            if os.path.exists(src):
                shutil.copy2(src, dist_dir)
        
        # Create a simple batch file for easy running
        batch_content = '''@echo off
echo Starting Ogresync...
echo.
echo If you see any errors, please check:
echo 1. Git is installed and available in PATH
echo 2. You have internet connection for GitHub access
echo 3. Your antivirus is not blocking the application
echo.
Ogresync.exe
pause
'''
        batch_path = os.path.join(dist_dir, 'run_ogresync.bat')
        with open(batch_path, 'w') as f:
            f.write(batch_content)
        
        print(f"Distribution files created in: {dist_dir}")

# Call the distribution function (this will run during build)
if __name__ == '__main__':
    create_distribution_files()
