#!/usr/bin/env python3
"""
Simple test to reproduce the local-only files issue during smart merge
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path

def run_cmd(cmd, cwd=None):
    """Run command and return success"""
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, shell=True)
        return result.returncode == 0, result.stdout, result.stderr
    except:
        return False, "", "Exception occurred"

def test_simple_merge_scenario():
    """Test the exact scenario: Remote has Test1-5, Local has Test1-7"""
    print("🧪 Simple Test: Local-only files during git merge")
    
    # Create test directory
    test_dir = tempfile.mkdtemp(prefix="simple_merge_test_")
    
    try:
        # Initialize git repo
        os.chdir(test_dir)
        run_cmd("git init")
        run_cmd("git config user.name 'Test User'")
        run_cmd("git config user.email 'test@example.com'")
        
        # Create Test1-Test7 files
        for i in range(1, 8):
            with open(f"Test{i}.md", "w") as f:
                f.write(f"# Test {i}\nContent for test file {i}")
        
        # Add and commit all files
        run_cmd("git add .")
        run_cmd("git commit -m 'All files Test1-7'")
        
        # Create a branch to simulate remote state
        run_cmd("git checkout -b remote-sim")
        
        # Remove Test6 and Test7 to simulate remote state (only Test1-5)
        os.remove("Test6.md")
        os.remove("Test7.md")
        run_cmd("git add .")
        run_cmd("git commit -m 'Remote state: only Test1-5'")
        
        # Go back to main and add local changes
        run_cmd("git checkout main")
        
        # Modify Test1 to create a difference
        with open("Test1.md", "a") as f:
            f.write("\nLocal modification")
        run_cmd("git add .")
        run_cmd("git commit -m 'Local changes'")
        
        print("📝 Before merge:")
        files_before = [f for f in os.listdir(".") if f.startswith("Test") and f.endswith(".md")]
        print(f"   Local files: {sorted(files_before)}")
        
        # Simulate smart merge: merge remote-sim into main
        success, stdout, stderr = run_cmd("git merge remote-sim --no-ff -m 'Smart merge test'")
        
        print("📝 After merge:")
        files_after = [f for f in os.listdir(".") if f.startswith("Test") and f.endswith(".md")]
        print(f"   Local files: {sorted(files_after)}")
        
        if success:
            print("✅ Merge completed successfully")
            missing = set(['Test6.md', 'Test7.md']) - set(files_after)
            if missing:
                print(f"⚠️ Local-only files lost during merge: {missing}")
                return False
            else:
                print("✅ All local-only files preserved!")
                return True
        else:
            print(f"❌ Merge failed: {stderr}")
            return False
            
    finally:
        os.chdir("/")
        shutil.rmtree(test_dir, ignore_errors=True)

if __name__ == "__main__":
    success = test_simple_merge_scenario()
    print(f"\nResult: {'PASS' if success else 'FAIL'}")
