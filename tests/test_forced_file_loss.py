#!/usr/bin/env python3
"""
Test scenario that definitely loses local-only files during merge
"""

import os
import sys
import subprocess
import tempfile
import shutil

def run_cmd(cmd, cwd=None):
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, shell=True)
        return result.returncode == 0, result.stdout, result.stderr
    except:
        return False, "", "Exception occurred"

def test_forced_file_loss_scenario():
    """Test scenario where local-only files are definitely lost during merge"""
    print("🧪 Forced File Loss Scenario Test")
    print("="*50)
    
    base_dir = tempfile.mkdtemp(prefix="forced_loss_test_")
    
    try:
        os.chdir(base_dir)
        
        # Initialize repo
        run_cmd("git init")
        run_cmd("git config user.name 'Test User'")
        run_cmd("git config user.email 'test@example.com'")
        
        # Create initial commit with Test1-5
        for i in range(1, 6):
            with open(f"Test{i}.md", "w") as f:
                f.write(f"# Test {i}\nInitial content")
        
        run_cmd("git add .")
        run_cmd("git commit -m 'Initial: Test1-5'")
        
        # Create branch that will become 'remote'
        run_cmd("git checkout -b remote-branch")
        
        # Modify Test1 in remote branch
        with open("Test1.md", "w") as f:
            f.write("# Test 1\nRemote version of Test1")
        
        run_cmd("git add .")
        run_cmd("git commit -m 'Remote: modified Test1'")
        
        # Go back to main and add local-only files
        run_cmd("git checkout main")
        
        # Add Test6-7 as local-only
        for i in range(6, 8):
            with open(f"Test{i}.md", "w") as f:
                f.write(f"# Test {i}\nLocal-only file {i}")
        
        # Modify Test1 differently in local
        with open("Test1.md", "w") as f:
            f.write("# Test 1\nLocal version of Test1")
        
        run_cmd("git add .")
        run_cmd("git commit -m 'Local: added Test6-7 and modified Test1'")
        
        print("📝 Setup complete:")
        local_files = sorted([f for f in os.listdir(".") if f.startswith("Test") and f.endswith(".md")])
        print(f"   Local files: {local_files}")
        
        # Simulate our analysis
        analysis_local_files = ['Test1.md', 'Test2.md', 'Test3.md', 'Test4.md', 'Test5.md', 'Test6.md', 'Test7.md']
        analysis_remote_files = ['Test1.md', 'Test2.md', 'Test3.md', 'Test4.md', 'Test5.md']
        local_only_files = ['Test6.md', 'Test7.md']
        
        print(f"   Local-only files to preserve: {local_only_files}")
        
        # APPLY OUR FIX
        print("\n🔧 Applying Smart Merge with Backup/Restore...")
        
        # Step 1: Backup local-only files
        local_only_backup = {}
        for local_file in local_only_files:
            if os.path.exists(local_file):
                with open(local_file, 'r') as f:
                    local_only_backup[local_file] = f.read()
                print(f"[BACKUP] Saved {local_file}")
        
        # Step 2: Force a merge that could lose files (using git reset + merge)
        print("\n[RESET] Reset to base state to force file loss...")
        run_cmd("git reset --hard HEAD~1")  # Go back before we added Test6-7
        
        files_after_reset = sorted([f for f in os.listdir(".") if f.startswith("Test") and f.endswith(".md")])
        print(f"[CHECK] Files after reset: {files_after_reset}")
        
        # Step 3: Merge remote branch
        print("\n[MERGE] Merging remote-branch...")
        success, stdout, stderr = run_cmd("git merge remote-branch --no-ff -m 'Merge remote changes'")
        
        if not success:
            print(f"Merge failed: {stderr}")
            # Handle merge conflict if needed
            run_cmd("git add .")
            run_cmd("git commit -m 'Resolve merge conflict'")
        
        files_after_merge = sorted([f for f in os.listdir(".") if f.startswith("Test") and f.endswith(".md")])
        print(f"[CHECK] Files after merge: {files_after_merge}")
        
        # Step 4: Restore local-only files
        files_restored = []
        for local_file, content in local_only_backup.items():
            if not os.path.exists(local_file):
                print(f"[RESTORE] {local_file} was lost, restoring...")
                with open(local_file, 'w') as f:
                    f.write(content)
                files_restored.append(local_file)
                print(f"✅ Restored {local_file}")
        
        if files_restored:
            run_cmd("git add .")
            run_cmd("git commit -m 'Restore local-only files after merge'")
            print(f"✅ Committed {len(files_restored)} restored files")
        
        # Final check
        final_files = sorted([f for f in os.listdir(".") if f.startswith("Test") and f.endswith(".md")])
        print(f"\n📝 Final result: {final_files}")
        
        expected_files = ['Test1.md', 'Test2.md', 'Test3.md', 'Test4.md', 'Test5.md', 'Test6.md', 'Test7.md']
        success = set(final_files) == set(expected_files)
        
        print("\n" + "="*50)
        if success:
            print("🎉 SUCCESS! Backup/restore logic preserved all files!")
            print(f"✅ {len(files_restored)} files were restored after being lost")
        else:
            print("❌ FAILED!")
            missing = set(expected_files) - set(final_files)
            if missing:
                print(f"❌ Still missing: {sorted(missing)}")
        
        return success
        
    finally:
        os.chdir("/")
        shutil.rmtree(base_dir, ignore_errors=True)

if __name__ == "__main__":
    success = test_forced_file_loss_scenario()
    print(f"\nResult: {'PASS' if success else 'FAIL'}")
    sys.exit(0 if success else 1)
