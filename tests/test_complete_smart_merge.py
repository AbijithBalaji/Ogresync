#!/usr/bin/env python3
"""
Test the complete smart merge scenario with proper file states
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

def test_complete_smart_merge_scenario():
    """Test complete scenario: Local repo with Test1-7, Remote with Test1-5"""
    print("🧪 Complete Smart Merge Scenario Test")
    print("="*50)
    
    # Create separate local and remote repos
    base_dir = tempfile.mkdtemp(prefix="complete_merge_test_")
    local_dir = os.path.join(base_dir, "local")
    remote_dir = os.path.join(base_dir, "remote.git")
    
    try:
        # Create bare remote repo
        os.makedirs(remote_dir)
        os.chdir(remote_dir)
        run_cmd("git init --bare")
        
        # Create local repo
        os.makedirs(local_dir)
        os.chdir(local_dir)
        run_cmd("git init")
        run_cmd("git config user.name 'Test User'")
        run_cmd("git config user.email 'test@example.com'")
        run_cmd(f"git remote add origin {remote_dir}")
        
        # Create Test1-5 and push to remote (establish baseline)
        for i in range(1, 6):
            with open(f"Test{i}.md", "w") as f:
                f.write(f"# Test {i}\nInitial content for test file {i}")
        
        run_cmd("git add .")
        run_cmd("git commit -m 'Initial commit: Test1-5'")
        run_cmd("git push -u origin main")
        
        # Add Test6-7 locally (local-only files)
        for i in range(6, 8):
            with open(f"Test{i}.md", "w") as f:
                f.write(f"# Test {i}\nLocal-only content for test file {i}")
        
        run_cmd("git add .")
        run_cmd("git commit -m 'Add local-only files Test6-7'")
        
        # Simulate remote changes using a temp clone
        temp_clone = os.path.join(base_dir, "temp_remote_work")
        run_cmd(f"git clone {remote_dir} {temp_clone}")
        os.chdir(temp_clone)
        run_cmd("git config user.name 'Remote User'")
        run_cmd("git config user.email 'remote@example.com'")
        
        # Modify Test1 to create a merge scenario
        with open("Test1.md", "a") as f:
            f.write("\n\nRemote modification added")
        
        run_cmd("git add .")
        run_cmd("git commit -m 'Remote changes to Test1'")
        run_cmd("git push origin main")
        
        # Go back to local repo and fetch
        os.chdir(local_dir)
        run_cmd("git fetch origin")
        
        print("📝 Setup complete:")
        local_files = sorted([f for f in os.listdir(".") if f.startswith("Test") and f.endswith(".md")])
        print(f"   Local files: {local_files}")
        
        # Simulate what our analysis would detect
        analysis_local_files = ['Test1.md', 'Test2.md', 'Test3.md', 'Test4.md', 'Test5.md', 'Test6.md', 'Test7.md']
        analysis_remote_files = ['Test1.md', 'Test2.md', 'Test3.md', 'Test4.md', 'Test5.md']
        local_only_files = list(set(analysis_local_files) - set(analysis_remote_files))
        
        print(f"   Analysis - Local: {analysis_local_files}")
        print(f"   Analysis - Remote: {analysis_remote_files}")
        print(f"   Analysis - Local-only: {local_only_files}")
        
        # IMPLEMENT OUR SMART MERGE FIX
        print("\n🔧 Applying Smart Merge with Local-only File Preservation...")
        
        # Step 1: Backup local-only files
        local_only_backup = {}
        for local_file in local_only_files:
            file_path = os.path.join(".", local_file)
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    local_only_backup[local_file] = f.read()
                print(f"[BACKUP] Saved {local_file} ({len(local_only_backup[local_file])} chars)")
        
        # Step 2: Perform git merge
        print(f"\n[MERGE] Executing git merge FETCH_HEAD...")
        success, stdout, stderr = run_cmd("git merge FETCH_HEAD --no-ff -m 'Smart merge - combining all files from local and remote'")
        
        if not success:
            print(f"❌ Merge failed: {stderr}")
            return False
        
        print("✅ Git merge completed")
        
        # Step 3: Check what files remain
        files_after_merge = sorted([f for f in os.listdir(".") if f.startswith("Test") and f.endswith(".md")])
        print(f"[CHECK] Files after merge: {files_after_merge}")
        
        # Step 4: Restore lost local-only files
        files_restored = []
        for local_file, content in local_only_backup.items():
            file_path = os.path.join(".", local_file)
            if not os.path.exists(file_path):
                print(f"[RESTORE] {local_file} was lost during merge, restoring...")
                with open(file_path, 'w') as f:
                    f.write(content)
                files_restored.append(local_file)
                print(f"✅ Restored {local_file}")
        
        if files_restored:
            run_cmd("git add .")
            success, stdout, stderr = run_cmd("git commit -m 'Restore local-only files after smart merge'")
            if success:
                print(f"✅ Committed {len(files_restored)} restored files")
            else:
                print(f"⚠️ Could not commit restored files: {stderr}")
        
        # Step 5: Final verification
        final_files = sorted([f for f in os.listdir(".") if f.startswith("Test") and f.endswith(".md")])
        print(f"\n📝 Final result: {final_files}")
        
        expected_files = ['Test1.md', 'Test2.md', 'Test3.md', 'Test4.md', 'Test5.md', 'Test6.md', 'Test7.md']
        success = set(final_files) == set(expected_files)
        
        print("\n" + "="*50)
        if success:
            print("🎉 SUCCESS! Smart merge with local-only file preservation works!")
            print("✅ All 7 files are present after smart merge")
            if files_restored:
                print(f"✅ {len(files_restored)} local-only files were automatically restored")
        else:
            print("❌ FAILED!")
            missing = set(expected_files) - set(final_files)
            extra = set(final_files) - set(expected_files)
            if missing:
                print(f"❌ Missing files: {sorted(missing)}")
            if extra:
                print(f"❌ Extra files: {sorted(extra)}")
        
        return success
        
    finally:
        os.chdir("/")
        shutil.rmtree(base_dir, ignore_errors=True)

if __name__ == "__main__":
    success = test_complete_smart_merge_scenario()
    print(f"\nOverall Result: {'PASS' if success else 'FAIL'}")
    sys.exit(0 if success else 1)
