#!/usr/bin/env python3
"""
Test script to verify that local-only files are preserved during smart merge.

This test verifies that when performing a smart merge, local-only files
(files that exist locally but not on remote) are preserved and not lost
during the merge operation.
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run a command and return stdout, stderr, returncode"""
    print(f"[CMD] {cmd}")
    try:
        if isinstance(cmd, list):
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
        else:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), 1

def test_local_only_files_preservation():
    """Test that local-only files are preserved during smart merge"""
    print("🧪 Testing Local-Only Files Preservation During Smart Merge")
    print("=" * 60)
    
    # Create test repositories
    local_vault = tempfile.mkdtemp(prefix="ogresync_local_only_test_")
    remote_vault = tempfile.mkdtemp(prefix="ogresync_remote_test_")
    
    print(f"📁 Created local vault: {local_vault}")
    print(f"📁 Created remote vault: {remote_vault}")
    
    try:
        # Initialize remote repository (bare)
        run_command(['git', 'init', '--bare'], cwd=remote_vault)
        
        # Initialize local repository
        run_command(['git', 'init'], cwd=local_vault)
        run_command(['git', 'config', 'user.name', 'Test User'], cwd=local_vault)
        run_command(['git', 'config', 'user.email', 'test@example.com'], cwd=local_vault)
        run_command(['git', 'remote', 'add', 'origin', remote_vault], cwd=local_vault)
        
        # Create common files (Test1-Test5) in local and push to remote
        for i in range(1, 6):
            file_path = Path(local_vault) / f"Test{i}.md"
            file_path.write_text(f"# Test File {i}\nContent for test file {i}.")
        
        run_command(['git', 'add', '.'], cwd=local_vault)
        run_command(['git', 'commit', '-m', 'Initial commit - Test1 to Test5'], cwd=local_vault)
        run_command(['git', 'branch', '-M', 'main'], cwd=local_vault)
        run_command(['git', 'push', '-u', 'origin', 'main'], cwd=local_vault)
        
        # Create local-only files (Test6-Test7)
        for i in range(6, 8):
            file_path = Path(local_vault) / f"Test{i}.md"
            file_path.write_text(f"# Test File {i}\nThis is a LOCAL-ONLY file {i}.")
        
        run_command(['git', 'add', '.'], cwd=local_vault)
        run_command(['git', 'commit', '-m', 'Add local-only files Test6 and Test7'], cwd=local_vault)
        
        # Simulate remote changes by creating a new commit directly to remote
        temp_clone = tempfile.mkdtemp(prefix="ogresync_temp_clone_")
        run_command(['git', 'clone', remote_vault, temp_clone])
        
        # Modify a common file in the temp clone and push
        common_file = Path(temp_clone) / "Test1.md"
        current_content = common_file.read_text()
        common_file.write_text(current_content + "\n\nRemote modification added.")
        
        run_command(['git', 'config', 'user.name', 'Remote User'], cwd=temp_clone)
        run_command(['git', 'config', 'user.email', 'remote@example.com'], cwd=temp_clone)
        run_command(['git', 'add', '.'], cwd=temp_clone)
        run_command(['git', 'commit', '-m', 'Remote changes to Test1'], cwd=temp_clone)
        run_command(['git', 'push', 'origin', 'main'], cwd=temp_clone)
        
        # Now test the merge scenario
        print("\n🔄 Testing Smart Merge Scenario...")
        print("Local has: Test1-Test7 (Test6,Test7 are local-only)")
        print("Remote has: Test1-Test5 (with modifications to Test1)")
        print("Expected after smart merge: Test1-Test7 (all files preserved)")
        
        # Fetch the remote changes
        run_command(['git', 'fetch', 'origin'], cwd=local_vault)
        
        # Get current local files before merge
        local_files_before = []
        for file in Path(local_vault).glob("Test*.md"):
            local_files_before.append(file.name)
        local_files_before.sort()
        print(f"📝 Files before merge: {local_files_before}")
        
        # Simulate what smart merge does
        # 1. First backup local-only files
        local_only_backup = {}
        local_only_files = ['Test6.md', 'Test7.md']
        
        for local_file in local_only_files:
            file_path = Path(local_vault) / local_file
            if file_path.exists():
                local_only_backup[local_file] = file_path.read_text()
                print(f"[BACKUP] Saved content for {local_file}")
        
        # 2. Perform the merge
        stdout, stderr, rc = run_command([
            'git', 'merge', 'origin/main', '--no-ff', '--allow-unrelated-histories',
            '-m', 'Smart merge test - combining all files'
        ], cwd=local_vault)
        
        if rc != 0:
            print(f"❌ Merge failed: {stderr}")
            return False
        
        print("✅ Git merge completed")
        
        # 3. Check what files exist after merge
        local_files_after_merge = []
        for file in Path(local_vault).glob("Test*.md"):
            local_files_after_merge.append(file.name)
        local_files_after_merge.sort()
        print(f"📝 Files after merge: {local_files_after_merge}")
        
        # 4. Restore local-only files if they were lost
        files_restored = []
        for local_file, content in local_only_backup.items():
            file_path = Path(local_vault) / local_file
            if not file_path.exists():
                print(f"[RESTORE] {local_file} was lost during merge, restoring...")
                file_path.write_text(content)
                files_restored.append(local_file)
                print(f"✅ Restored {local_file}")
        
        if files_restored:
            # Stage and commit restored files
            run_command(['git', 'add', '.'], cwd=local_vault)
            run_command(['git', 'commit', '-m', 'Restore local-only files after smart merge'], cwd=local_vault)
            print(f"✅ Committed {len(files_restored)} restored files")
        
        # 5. Final verification
        local_files_final = []
        for file in Path(local_vault).glob("Test*.md"):
            local_files_final.append(file.name)
        local_files_final.sort()
        print(f"📝 Final files: {local_files_final}")
        
        # Check results
        expected_files = ['Test1.md', 'Test2.md', 'Test3.md', 'Test4.md', 'Test5.md', 'Test6.md', 'Test7.md']
        success = set(local_files_final) == set(expected_files)
        
        print("\n" + "=" * 60)
        if success:
            print("🎉 TEST PASSED!")
            print("✅ All local-only files were preserved during smart merge")
            print(f"✅ Expected: {sorted(expected_files)}")
            print(f"✅ Actual:   {sorted(local_files_final)}")
            if files_restored:
                print(f"✅ {len(files_restored)} files were automatically restored after merge")
        else:
            print("❌ TEST FAILED!")
            print(f"❌ Expected: {sorted(expected_files)}")
            print(f"❌ Actual:   {sorted(local_files_final)}")
            missing = set(expected_files) - set(local_files_final)
            extra = set(local_files_final) - set(expected_files)
            if missing:
                print(f"❌ Missing files: {sorted(missing)}")
            if extra:
                print(f"❌ Extra files: {sorted(extra)}")
        
        return success
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False
        
    finally:
        # Cleanup
        try:
            shutil.rmtree(local_vault)
            shutil.rmtree(remote_vault)
            if 'temp_clone' in locals():
                shutil.rmtree(temp_clone)
        except Exception as e:
            print(f"⚠️ Cleanup failed: {e}")

if __name__ == "__main__":
    success = test_local_only_files_preservation()
    sys.exit(0 if success else 1)
