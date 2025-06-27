#!/usr/bin/env python3
"""
Enhanced Ogresync Windows Executable Builder

This script builds a Windows executable from the Ogresync Python application
with comprehensive handling of packaging issues:

- Console window hiding for subprocess calls
- Unicode character compatibility
- Asset bundling and path resolution
- Dependency management
- Build verification and testing

Usage:
    python build_exe.py [--clean] [--test] [--verbose]

Author: Ogresync Development Team
Date: June 2025
"""

import os
import sys
import shutil
import subprocess
import argparse
import time
from pathlib import Path


def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


def print_step(step):
    """Print a formatted step"""
    print(f"\n➤ {step}")


def run_command(cmd, cwd=None, check=True):
    """Run a command and return the result"""
    print(f"  Running: {cmd}")
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check
        )
        if result.stdout:
            print("  Output:", result.stdout.strip())
        if result.stderr and result.returncode != 0:
            print("  Error:", result.stderr.strip())
        return result
    except subprocess.CalledProcessError as e:
        print(f"  Command failed with exit code {e.returncode}")
        if e.stderr:
            print(f"  Error: {e.stderr}")
        raise


def check_dependencies():
    """Check if all required dependencies are installed"""
    print_step("Checking dependencies...")
    
    required_packages = [
        ('PyInstaller', 'pyinstaller'),  # (import_name, package_name)
        ('psutil', 'psutil'),
        ('pyperclip', 'pyperclip'), 
        ('requests', 'requests')
    ]
    
    missing_packages = []
    for import_name, package_name in required_packages:
        try:
            __import__(import_name)
            print(f"  [OK] {package_name}")
        except ImportError:
            print(f"  [MISSING] {package_name}")
            missing_packages.append(package_name)
    
    if missing_packages:
        print(f"\nMissing packages: {', '.join(missing_packages)}")
        print("Install them with: pip install " + " ".join(missing_packages))
        return False
    
    return True


def clean_build_directories():
    """Clean build and dist directories"""
    print_step("Cleaning build directories...")
    
    dirs_to_clean = ['build', 'dist', '__pycache__']
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"  Removing {dir_name}/")
            shutil.rmtree(dir_name)
    
    # Also clean .pyc files
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.pyc'):
                pyc_path = os.path.join(root, file)
                os.remove(pyc_path)
                print(f"  Removed {pyc_path}")


def build_executable(verbose=False):
    """Build the executable using PyInstaller with spec file"""
    print_step("Building executable with PyInstaller...")
    
    # Use the spec file for better control
    spec_file = "Ogresync.spec"
    
    if not os.path.exists(spec_file):
        print(f"  Error: Spec file {spec_file} not found!")
        return False
    
    cmd = f"pyinstaller {spec_file}"
    if verbose:
        cmd += " --log-level DEBUG"
    else:
        cmd += " --log-level WARN"
    
    try:
        run_command(cmd)
        print("  [OK] Build completed successfully")
        return True
    except subprocess.CalledProcessError:
        print("  [FAIL] Build failed")
        return False


def verify_build():
    """Verify the build was successful"""
    print_step("Verifying build...")
    
    exe_path = "dist/Ogresync.exe"
    
    if not os.path.exists(exe_path):
        print(f"  [FAIL] Executable not found: {exe_path}")
        return False
    
    # Check file size
    file_size = os.path.getsize(exe_path) / (1024 * 1024)  # MB
    print(f"  [OK] Executable created: {exe_path}")
    print(f"  [OK] File size: {file_size:.1f} MB")
    
    if file_size < 10:
        print("  [WARN] File size seems small, build might be incomplete")
    elif file_size > 200:
        print("  [WARN] File size is large, consider optimizing dependencies")
    
    return True


def main():
    """Main build function"""
    parser = argparse.ArgumentParser(description='Build Ogresync Windows executable')
    parser.add_argument('--clean', action='store_true', help='Clean build directories first')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    
    args = parser.parse_args()
    
    print_section("Ogresync Windows Executable Builder")
    print(f"Build started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Step 1: Check dependencies
        if not check_dependencies():
            print("\n[FAIL] Build failed: Missing dependencies")
            return 1
        
        # Step 2: Clean if requested
        if args.clean:
            clean_build_directories()
        
        # Step 3: Build executable
        if not build_executable(args.verbose):
            print("\n[FAIL] Build failed during PyInstaller execution")
            return 1
        
        # Step 4: Verify build
        if not verify_build():
            print("\n[FAIL] Build verification failed")
            return 1
        
        print_section("Build Completed Successfully!")
        print("[SUCCESS] Your Ogresync executable is ready!")
        print("\nNext steps:")
        print("1. Test the executable: dist/Ogresync.exe")
        print("2. Distribute to users")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Build cancelled by user")
        return 1
    except Exception as e:
        print(f"\n[FAIL] Build failed with error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
