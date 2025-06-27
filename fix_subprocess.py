#!/usr/bin/env python3
"""
Subprocess Fixing Script for Ogresync Windows Packaging

This script fixes all subprocess.run calls to use the safe wrapper that hides
console windows in packaged applications.
"""

import os
import re
from pathlib import Path

def fix_subprocess_calls():
    """Fix subprocess calls in all Python files"""
    
    # Files to fix (excluding build scripts and tests)
    files_to_fix = [
        "setup_wizard.py",
        "enhanced_auto_sync.py", 
        "offline_sync_manager.py",
        "stage2_conflict_resolution.py"
    ]
    
    project_root = Path(__file__).parent
    
    for file_name in files_to_fix:
        file_path = project_root / file_name
        
        if not file_path.exists():
            print(f"Skipping {file_name} - file not found")
            continue
            
        print(f"Processing {file_name}...")
        
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if packaging_utils import already exists
        if 'from packaging_utils import' not in content:
            print(f"  Adding packaging_utils import to {file_name}")
            
            # Find where to insert the import (after other imports)
            import_pattern = r'(import subprocess\n)'
            replacement = r'\1\n# Import packaging utilities for safe subprocess calls\ntry:\n    from packaging_utils import run_subprocess_safe, is_packaged_app\n    PACKAGING_UTILS_AVAILABLE = True\nexcept ImportError:\n    PACKAGING_UTILS_AVAILABLE = False\n    # Fallback to regular subprocess\n    def run_subprocess_safe(*args, **kwargs):\n        return subprocess.run(*args, **kwargs)\n'
            
            content = re.sub(import_pattern, replacement, content)
        
        # Replace subprocess.run calls with run_subprocess_safe
        # Pattern: subprocess.run(
        pattern = r'subprocess\.run\('
        replacement = 'run_subprocess_safe('
        
        original_count = len(re.findall(pattern, content))
        content = re.sub(pattern, replacement, content)
        new_count = len(re.findall(pattern, content))
        
        replaced_count = original_count - new_count
        if replaced_count > 0:
            print(f"  Replaced {replaced_count} subprocess.run calls in {file_name}")
        
        # Write the file back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    print("\nSubprocess fixing completed!")

if __name__ == "__main__":
    fix_subprocess_calls()
