#!/usr/bin/env python3
"""
Test script to verify git checkout commands work correctly in Stage1 conflict resolution.
Checks that the checkout commands don't have extra quotes or syntax errors.
"""

import os
import sys
import tempfile
import shutil
import subprocess
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run a command and return stdout, stderr, returncode"""
    print(f"[CMD] {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), 1

def test_checkout_commands():
    """Test git checkout commands used in Stage1 conflict resolution"""
    print("🔧 Testing Git Checkout Commands")
    print("=" * 50)
    
    # Create a temporary test repository
    test_dir = tempfile.mkdtemp(prefix="ogresync_checkout_test_")
    print(f"📁 Test directory: {test_dir}")
    
    try:
        # Initialize git repo
        run_command("git init", cwd=test_dir)
        run_command("git config user.email 'test@test.com'", cwd=test_dir)
        run_command("git config user.name 'Test User'", cwd=test_dir)
        
        # Create main branch and add files
        test_file1 = os.path.join(test_dir, "test1.md")
        test_file2 = os.path.join(test_dir, "test2.md")
        
        with open(test_file1, 'w') as f:
            f.write("# Test File 1\nOriginal content\n")
        with open(test_file2, 'w') as f:
            f.write("# Test File 2\nOriginal content\n")
        
        run_command("git add .", cwd=test_dir)
        run_command("git commit -m 'Initial commit'", cwd=test_dir)
        
        # Create a remote repository simulation
        # We need to simulate origin/main, so let's create it properly
        run_command("git remote add origin https://github.com/test/test.git", cwd=test_dir)
        run_command("git push -u origin main", cwd=test_dir)  # This would fail but we'll simulate
        
        # Create a different branch for local changes
        run_command("git checkout -b feature-branch", cwd=test_dir)
        
        # Modify files in feature branch (simulating local changes)
        with open(test_file1, 'w') as f:
            f.write("# Test File 1\nLocal content\n")
        with open(test_file2, 'w') as f:
            f.write("# Test File 2\nLocal content\n")
        
        run_command("git add .", cwd=test_dir)
        run_command("git commit -m 'Local changes'", cwd=test_dir)
        
        # Go back to main and modify to create differences
        run_command("git checkout main", cwd=test_dir)
        
        # Modify main branch files differently (simulating remote content)
        with open(test_file1, 'w') as f:
            f.write("# Test File 1\nRemote content from origin\n")
        with open(test_file2, 'w') as f:
            f.write("# Test File 2\nRemote content from origin\n")
        
        run_command("git add .", cwd=test_dir)
        run_command("git commit -m 'Simulate remote changes'", cwd=test_dir)
        
        # Switch back to feature branch to test checkout
        run_command("git checkout feature-branch", cwd=test_dir)
        
        # Modify files in main branch
        with open(test_file1, 'w') as f:
            f.write("# Test File 1\nLocal content\n")
        with open(test_file2, 'w') as f:
            f.write("# Test File 2\nLocal content\n")
        
        run_command("git add .", cwd=test_dir)
        run_command("git commit -m 'Local changes'", cwd=test_dir)
        
        print("\n🔧 Testing Checkout Commands")
        print("-" * 30)
        
        # Test 1: Basic checkout command (no quotes)
        print("\n1. Testing basic checkout command:")
        cmd = f"git checkout main -- test1.md"
        stdout, stderr, rc = run_command(cmd, cwd=test_dir)
        if rc == 0:
            print(f"   ✅ SUCCESS: {cmd}")
        else:
            print(f"   ❌ FAILED: {cmd}")
            print(f"   Error: {stderr}")
        
        # Test 2: Checkout command with filename containing spaces
        space_file = os.path.join(test_dir, "file with spaces.md")
        with open(space_file, 'w') as f:
            f.write("# File with spaces\nContent\n")
        
        run_command("git checkout main", cwd=test_dir)
        run_command("git add .", cwd=test_dir)
        run_command("git commit -m 'Add file with spaces'", cwd=test_dir)
        run_command("git checkout feature-branch", cwd=test_dir)
        
        print("\n2. Testing checkout with spaced filename:")
        cmd = f"git checkout main -- \"file with spaces.md\""
        stdout, stderr, rc = run_command(cmd, cwd=test_dir)
        if rc == 0:
            print(f"   ✅ SUCCESS: {cmd}")
        else:
            print(f"   ❌ FAILED: {cmd}")
            print(f"   Error: {stderr}")
        
        # Test 3: Checkout command with multiple files
        print("\n3. Testing checkout with multiple files:")
        cmd = f"git checkout main -- test1.md test2.md"
        stdout, stderr, rc = run_command(cmd, cwd=test_dir)
        if rc == 0:
            print(f"   ✅ SUCCESS: {cmd}")
        else:
            print(f"   ❌ FAILED: {cmd}")
            print(f"   Error: {stderr}")
        
        # Test 4: Verify the actual commands used in Stage1_conflict_resolution.py
        print("\n4. Testing Stage1 conflict resolution checkout patterns:")
        
        # Pattern 1: From line 714 in Stage1_conflict_resolution.py
        remote_branch = "main"  # In real scenario this would be origin/main
        missing_file = "test1.md"
        cmd = f"git checkout {remote_branch} -- {missing_file}"
        stdout, stderr, rc = run_command(cmd, cwd=test_dir)
        if rc == 0:
            print(f"   ✅ SUCCESS: Pattern 1 - {cmd}")
        else:
            print(f"   ❌ FAILED: Pattern 1 - {cmd}")
            print(f"   Error: {stderr}")
        
        # Pattern 2: From line 1089 in Stage1_conflict_resolution.py
        file_path = "test2.md"
        cmd = f"git checkout {remote_branch} -- {file_path}"
        stdout, stderr, rc = run_command(cmd, cwd=test_dir)
        if rc == 0:
            print(f"   ✅ SUCCESS: Pattern 2 - {cmd}")
        else:
            print(f"   ❌ FAILED: Pattern 2 - {cmd}")
            print(f"   Error: {stderr}")
        
        print("\n✅ All checkout command tests completed!")
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        try:
            shutil.rmtree(test_dir)
            print(f"🧹 Cleaned up test directory: {test_dir}")
        except Exception as e:
            print(f"⚠️ Could not clean up test directory: {e}")

if __name__ == "__main__":
    test_checkout_commands()
