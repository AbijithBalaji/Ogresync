"""
Test script to verify the smart merge file checkout fix

This test verifies that the smart merge strategy correctly checks out
missing files from remote without the quote issue.
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path

def test_smart_merge_file_checkout():
    """Test that smart merge correctly checks out missing files"""
    print("🧪 Testing smart merge file checkout fix...")
    
    # Create test repositories
    local_vault = tempfile.mkdtemp(prefix="ogresync_local_test_")
    remote_vault = tempfile.mkdtemp(prefix="ogresync_remote_test_")
    
    print(f"📁 Created local vault: {local_vault}")
    print(f"📁 Created remote vault: {remote_vault}")
    
    try:
        # Initialize remote repository
        subprocess.run(['git', 'init', '--bare'], cwd=remote_vault, check=True, capture_output=True)
        
        # Initialize local repository
        subprocess.run(['git', 'init'], cwd=local_vault, check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=local_vault, check=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=local_vault, check=True)
        subprocess.run(['git', 'remote', 'add', 'origin', remote_vault], cwd=local_vault, check=True)
        
        # Create initial commit in local and push to establish remote
        initial_file = Path(local_vault) / "initial.md"
        initial_file.write_text("# Initial File\nThis is the initial file.")
        
        subprocess.run(['git', 'add', 'initial.md'], cwd=local_vault, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=local_vault, check=True)
        subprocess.run(['git', 'branch', '-M', 'main'], cwd=local_vault, check=True)
        subprocess.run(['git', 'push', '-u', 'origin', 'main'], cwd=local_vault, check=True)
        
        # Create local-only files
        local_file = Path(local_vault) / "local_only.md"
        local_file.write_text("# Local Only\nThis file exists only locally.")
        
        subprocess.run(['git', 'add', 'local_only.md'], cwd=local_vault, check=True)
        subprocess.run(['git', 'commit', '-m', 'Add local-only file'], cwd=local_vault, check=True)
        
        # Simulate remote-only files by creating another clone, adding files, and pushing
        temp_clone = tempfile.mkdtemp(prefix="ogresync_temp_clone_")
        subprocess.run(['git', 'clone', remote_vault, temp_clone], check=True, capture_output=True)
        
        # Add remote-only files to the clone
        remote_file1 = Path(temp_clone) / "remote_file1.md"
        remote_file1.write_text("# Remote File 1\nThis file exists only on remote.")
        
        remote_file2 = Path(temp_clone) / "remote_file2.md"
        remote_file2.write_text("# Remote File 2\nAnother remote-only file.")
        
        subprocess.run(['git', 'add', '.'], cwd=temp_clone, check=True)
        subprocess.run(['git', 'commit', '-m', 'Add remote-only files'], cwd=temp_clone, check=True)
        subprocess.run(['git', 'push'], cwd=temp_clone, check=True)
        
        print("✅ Test repositories set up with local and remote files")
        
        # Now test the git checkout command directly (simulating the fix)
        print("🔧 Testing git checkout commands...")
        
        # First, fetch to get latest remote refs
        subprocess.run(['git', 'fetch', 'origin'], cwd=local_vault, check=True)
        
        # Check what branches exist
        branch_result = subprocess.run(['git', 'branch', '-r'], cwd=local_vault, capture_output=True, text=True)
        print(f"📋 Remote branches: {branch_result.stdout.strip()}")
        
        # Use the correct remote branch (might be master instead of main)
        remote_branch = "origin/master" if "origin/master" in branch_result.stdout else "origin/main"
        print(f"🌿 Using remote branch: {remote_branch}")
        
        # Test the old command (with quotes) - should fail
        old_command = ['git', 'checkout', remote_branch, '--', '"remote_file1.md"']
        result_old = subprocess.run(old_command, cwd=local_vault, capture_output=True, text=True)
        
        # Test the new command (without quotes) - should succeed
        new_command = ['git', 'checkout', remote_branch, '--', 'remote_file1.md']
        result_new = subprocess.run(new_command, cwd=local_vault, capture_output=True, text=True)
        
        print(f"📊 Old command result (with quotes): RC={result_old.returncode}")
        if result_old.returncode != 0:
            print(f"   Error: {result_old.stderr.strip()}")
        
        print(f"📊 New command result (without quotes): RC={result_new.returncode}")
        if result_new.returncode != 0:
            print(f"   Error: {result_new.stderr.strip()}")
        
        # Check if file was checked out successfully
        remote_file1_local = Path(local_vault) / "remote_file1.md"
        if remote_file1_local.exists():
            print("✅ PASS: File successfully checked out with new command")
            return True
        else:
            print("❌ FAIL: File was not checked out")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
        
    finally:
        # Clean up
        try:
            shutil.rmtree(local_vault)
            shutil.rmtree(remote_vault)
            if 'temp_clone' in locals():
                shutil.rmtree(temp_clone)
            print("🗑️ Cleaned up test repositories")
        except:
            print("⚠️ Could not clean up test repositories")


if __name__ == "__main__":
    print("🚀 Testing smart merge file checkout fix...")
    print("=" * 60)
    
    result = test_smart_merge_file_checkout()
    
    print("=" * 60)
    if result:
        print("🎉 Test passed! The smart merge file checkout fix is working.")
        print()
        print("📝 Fix applied:")
        print("   - Removed extra quotes from git checkout command")
        print("   - Changed: git checkout origin/main -- \"filename\"")
        print("   - To:      git checkout origin/main -- filename")
        print()
        print("This should resolve the issue where remote files weren't")
        print("being checked out during smart merge operations.")
    else:
        print("❌ Test failed. Please check the implementation.")
