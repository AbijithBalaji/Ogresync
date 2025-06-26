#!/usr/bin/env python3
"""
Test the backup and restore logic for local-o        
        # Step 3: Backup local-only files
        local_only_backup = {}
        for local_file in local_only_files:
            file_path = os.path.join(".", local_file)
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    local_only_backup[local_file] = f.read()
                print(f"[BACKUP] Saved content for {local_file}")
        
        print(f"Backed up {len(local_only_backup)} local-only files")s
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

def test_backup_restore_logic():
    """Test backup and restore logic that we added to smart merge"""
    print("🧪 Testing Backup and Restore Logic for Local-only Files")
    
    test_dir = tempfile.mkdtemp(prefix="backup_restore_test_")
    
    try:
        os.chdir(test_dir)
        run_cmd("git init")
        run_cmd("git config user.name 'Test User'")
        run_cmd("git config user.email 'test@example.com'")
        
        # Create Test1-Test7 files
        for i in range(1, 8):
            with open(f"Test{i}.md", "w") as f:
                f.write(f"# Test {i}\nContent for test file {i}")
        
        run_cmd("git add .")
        run_cmd("git commit -m 'All files Test1-7'")
        
        # Create remote simulation branch
        run_cmd("git checkout -b remote-sim")
        os.remove("Test6.md")
        os.remove("Test7.md")
        run_cmd("git add .")
        run_cmd("git commit -m 'Remote state: only Test1-5'")
        
        # Go back to main 
        run_cmd("git checkout main")
        
        # Modify Test1 to create merge scenario
        with open("Test1.md", "a") as f:
            f.write("\nLocal modification")
        run_cmd("git add .")
        run_cmd("git commit -m 'Local changes'")
        
        # Now implement our backup and restore logic
        print("📝 Implementing smart merge with backup/restore...")
        
        # Step 1: Get current files before checking remote
        current_files = [f for f in os.listdir(".") if f.startswith("Test") and f.endswith(".md")]
        print(f"Current files before merge: {sorted(current_files)}")
        
        # Step 2: Identify local-only files (simulate what Stage1 does)
        # In the real scenario, this comes from the analysis
        local_files = ['Test1.md', 'Test2.md', 'Test3.md', 'Test4.md', 'Test5.md', 'Test6.md', 'Test7.md']
        remote_files = ['Test1.md', 'Test2.md', 'Test3.md', 'Test4.md', 'Test5.md']  # What exists on remote
        local_only_files = list(set(local_files) - set(remote_files))
        
        print(f"Local files (from analysis): {sorted(local_files)}")
        print(f"Remote files (from analysis): {sorted(remote_files)}")  
        print(f"Local-only files (calculated): {sorted(local_only_files)}")
        
        # Step 2: Backup local-only files
        local_only_backup = {}
        for local_file in local_only_files:
            if os.path.exists(local_file):
                with open(local_file, 'r') as f:
                    local_only_backup[local_file] = f.read()
                print(f"[BACKUP] Saved content for {local_file}")
        
        # Step 3: Perform merge (this will lose local-only files)
        print(f"\n🔄 Performing git merge... (expecting to lose {len(local_only_backup)} files)")
        success, stdout, stderr = run_cmd("git merge remote-sim --no-ff -m 'Smart merge with backup/restore'")
        
        files_after_merge = [f for f in os.listdir(".") if f.startswith("Test") and f.endswith(".md")]
        print(f"Files after merge: {sorted(files_after_merge)}")
        
        # Step 4: Restore local-only files if they were lost
        files_restored = []
        for local_file, content in local_only_backup.items():
            if not os.path.exists(local_file):
                print(f"[RESTORE] {local_file} was lost during merge, restoring...")
                with open(local_file, 'w') as f:
                    f.write(content)
                files_restored.append(local_file)
                print(f"✅ Restored {local_file}")
        
        if files_restored:
            run_cmd("git add .")
            run_cmd("git commit -m 'Restore local-only files after smart merge'")
            print(f"✅ Committed {len(files_restored)} restored files")
        
        # Step 5: Final verification
        final_files = [f for f in os.listdir(".") if f.startswith("Test") and f.endswith(".md")]
        print(f"\n📝 Final files: {sorted(final_files)}")
        
        expected_files = ['Test1.md', 'Test2.md', 'Test3.md', 'Test4.md', 'Test5.md', 'Test6.md', 'Test7.md']
        success = set(final_files) == set(expected_files)
        
        if success:
            print("🎉 SUCCESS! Backup and restore logic works correctly")
            print("✅ All local-only files were preserved during smart merge")
        else:
            print("❌ FAILED! Some files are still missing")
            missing = set(expected_files) - set(final_files)
            print(f"Missing: {missing}")
        
        return success
        
    finally:
        os.chdir("/")
        shutil.rmtree(test_dir, ignore_errors=True)

if __name__ == "__main__":
    success = test_backup_restore_logic()
    print(f"\nResult: {'PASS' if success else 'FAIL'}")
