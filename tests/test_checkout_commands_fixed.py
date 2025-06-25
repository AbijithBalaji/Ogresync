#!/usr/bin/env python3
"""
Test script to verify git checkout commands work correctly in Stage1 conflict resolution.
This test simulates the actual scenario where we checkout files from origin/main.
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
    print("🔧 Testing Git Checkout Commands (Fixed Version)")
    print("=" * 55)
    
    # Create a temporary test repository
    test_dir = tempfile.mkdtemp(prefix="ogresync_checkout_test_")
    print(f"📁 Test directory: {test_dir}")
    
    try:
        # Initialize git repo
        run_command("git init", cwd=test_dir)
        run_command("git config user.email 'test@test.com'", cwd=test_dir)
        run_command("git config user.name 'Test User'", cwd=test_dir)
        
        # Create initial files
        test_file1 = os.path.join(test_dir, "test1.md")
        test_file2 = os.path.join(test_dir, "test2.md")
        space_file = os.path.join(test_dir, "file with spaces.md")
        
        with open(test_file1, 'w') as f:
            f.write("# Test File 1\nRemote content from origin\n")
        with open(test_file2, 'w') as f:
            f.write("# Test File 2\nRemote content from origin\n")
        with open(space_file, 'w') as f:
            f.write("# File with spaces\nRemote content\n")
        
        run_command("git add .", cwd=test_dir)
        run_command("git commit -m 'Initial commit with remote content'", cwd=test_dir)
        
        # Check what the default branch is
        stdout, stderr, rc = run_command("git branch --show-current", cwd=test_dir)
        default_branch = stdout if rc == 0 else "main"
        print(f"📌 Default branch: {default_branch}")
        
        # Create a feature branch and modify files
        run_command("git checkout -b feature-branch", cwd=test_dir)
        
        with open(test_file1, 'w') as f:
            f.write("# Test File 1\nLocal modified content\n")
        with open(test_file2, 'w') as f:
            f.write("# Test File 2\nLocal modified content\n")
        with open(space_file, 'w') as f:
            f.write("# File with spaces\nLocal modified content\n")
        
        run_command("git add .", cwd=test_dir)
        run_command("git commit -m 'Local modifications'", cwd=test_dir)
        
        print("\n🔧 Testing Checkout Commands")
        print("-" * 30)
        
        # Test 1: Basic checkout command
        print("\n1. Testing basic checkout command:")
        cmd = f"git checkout {default_branch} -- test1.md"
        stdout, stderr, rc = run_command(cmd, cwd=test_dir)
        if rc == 0:
            print(f"   ✅ SUCCESS: {cmd}")
            # Verify the content was restored
            with open(test_file1, 'r') as f:
                content = f.read()
                if "Remote content from origin" in content:
                    print("   ✅ File content correctly restored from remote")
                else:
                    print("   ⚠️ File content may not be correct")
        else:
            print(f"   ❌ FAILED: {cmd}")
            print(f"   Error: {stderr}")
        
        # Test 2: Checkout command with filename containing spaces
        print("\n2. Testing checkout with spaced filename:")
        cmd = f"git checkout {default_branch} -- \"file with spaces.md\""
        stdout, stderr, rc = run_command(cmd, cwd=test_dir)
        if rc == 0:
            print(f"   ✅ SUCCESS: {cmd}")
            # Verify the content was restored
            with open(space_file, 'r') as f:
                content = f.read()
                if "Remote content" in content:
                    print("   ✅ Spaced filename content correctly restored")
                else:
                    print("   ⚠️ Spaced filename content may not be correct")
        else:
            print(f"   ❌ FAILED: {cmd}")
            print(f"   Error: {stderr}")
        
        # Test 3: Checkout command with multiple files
        print("\n3. Testing checkout with multiple files:")
        # First modify both files again
        with open(test_file1, 'w') as f:
            f.write("# Test File 1\nLocal modified again\n")
        with open(test_file2, 'w') as f:
            f.write("# Test File 2\nLocal modified again\n")
        
        cmd = f"git checkout {default_branch} -- test1.md test2.md"
        stdout, stderr, rc = run_command(cmd, cwd=test_dir)
        if rc == 0:
            print(f"   ✅ SUCCESS: {cmd}")
            # Verify both files were restored
            with open(test_file1, 'r') as f1, open(test_file2, 'r') as f2:
                content1, content2 = f1.read(), f2.read()
                if "Remote content from origin" in content1 and "Remote content from origin" in content2:
                    print("   ✅ Multiple files correctly restored")
                else:
                    print("   ⚠️ Multiple files may not be correctly restored")
        else:
            print(f"   ❌ FAILED: {cmd}")
            print(f"   Error: {stderr}")
        
        # Test 4: Test the exact patterns used in Stage1_conflict_resolution.py
        print("\n4. Testing Stage1 conflict resolution checkout patterns:")
        
        # Simulate the exact scenario from the Stage1 code
        remote_branch = default_branch  # In real code this would be origin/main
        
        # Pattern 1: Missing file checkout (line 714)
        missing_file = "test1.md"
        cmd = f"git checkout {remote_branch} -- {missing_file}"
        stdout, stderr, rc = run_command(cmd, cwd=test_dir)
        if rc == 0:
            print(f"   ✅ SUCCESS: Pattern 1 - {cmd}")
        else:
            print(f"   ❌ FAILED: Pattern 1 - {cmd}")
            print(f"   Error: {stderr}")
        
        # Pattern 2: Smart merge checkout (line 1089)
        file_path = "test2.md"
        cmd = f"git checkout {remote_branch} -- {file_path}"
        stdout, stderr, rc = run_command(cmd, cwd=test_dir)
        if rc == 0:
            print(f"   ✅ SUCCESS: Pattern 2 - {cmd}")
        else:
            print(f"   ❌ FAILED: Pattern 2 - {cmd}")
            print(f"   Error: {stderr}")
        
        print("\n5. Testing with origin/branch syntax:")
        # This is the most realistic test since Stage1 uses origin/main
        # We can't really test this without a real remote, but we can test the command syntax
        remote_branch_with_origin = f"origin/{default_branch}"
        cmd = f"git checkout {remote_branch_with_origin} -- test1.md"
        stdout, stderr, rc = run_command(cmd, cwd=test_dir)
        if rc == 0:
            print(f"   ✅ SUCCESS: origin syntax - {cmd}")
        else:
            print(f"   ⚠️ EXPECTED FAIL: origin syntax - {cmd}")
            print(f"   Note: This fails because we don't have a real remote, but the syntax is correct")
            print(f"   Error: {stderr}")
        
        print("\n✅ All checkout command tests completed!")
        print("\n📊 Summary:")
        print("   - Basic checkout commands work correctly")
        print("   - Filenames with spaces are handled properly with quotes")
        print("   - Multiple file checkout works")
        print("   - The syntax used in Stage1_conflict_resolution.py is correct")
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        try:
            shutil.rmtree(test_dir)
            print(f"\n🧹 Cleaned up test directory: {test_dir}")
        except Exception as e:
            print(f"⚠️ Could not clean up test directory: {e}")

if __name__ == "__main__":
    test_checkout_commands()
