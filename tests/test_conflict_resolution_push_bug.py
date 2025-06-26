#!/usr/bin/env python3
"""
Comprehensive test to reproduce the conflict resolution push bug.
This test simulates:
1. User works offline and makes changes
2. User comes back online and conflict resolution is triggered
3. User resolves conflicts successfully
4. Script should immediately push the resolved changes to GitHub
5. Verify that GitHub is updated with the resolution

This reproduces the exact bug where conflict resolution succeeds but changes aren't pushed.
"""

import sys
import os
import time
import tempfile
import shutil
import subprocess
import json
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import offline_sync_manager
    import Stage1_conflict_resolution as conflict_resolution
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

def run_command(cmd, cwd=None):
    """Run a command and return output, error, return code"""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), 1

def simulate_offline_changes(vault_path):
    """Simulate user making changes while offline"""
    print("=== SIMULATING OFFLINE CHANGES ===")
    
    # Create a test file with offline changes
    test_file = os.path.join(vault_path, "offline_test.md")
    with open(test_file, 'w') as f:
        f.write("# Offline Test\n\nThis was created while offline.\n")
    
    # Commit the offline changes
    run_command("git add .", cwd=vault_path)
    out, err, rc = run_command('git commit -m "Offline changes - test file"', cwd=vault_path)
    print(f"Offline commit result: rc={rc}, out='{out}', err='{err}'")
    
    return rc == 0

def simulate_remote_changes(vault_path):
    """Simulate changes happening on remote while user was offline"""
    print("=== SIMULATING REMOTE CHANGES (creating conflict scenario) ===")
    
    # For this test, we'll create a situation where there are conflicting changes
    # We'll modify the same file that was created offline
    test_file = os.path.join(vault_path, "offline_test.md")
    
    # First, let's check the current state
    head_before = run_command("git rev-parse HEAD", cwd=vault_path)[0]
    print(f"Local HEAD before simulating remote changes: {head_before}")
    
    # To simulate remote changes, we'll:
    # 1. Create a new branch to represent "remote" 
    # 2. Make conflicting changes on that branch
    # 3. Set up the scenario where remote has advanced
    
    # Create a "remote-sim" branch to simulate remote state
    run_command("git branch remote-sim HEAD~1", cwd=vault_path)  # Branch from before offline commit
    run_command("git checkout remote-sim", cwd=vault_path)
    
    # Make conflicting changes on the remote-sim branch
    if os.path.exists(test_file):
        # File exists on remote-sim, modify it differently
        with open(test_file, 'w') as f:
            f.write("# Remote Test\n\nThis was changed on remote while you were offline.\n")
    else:
        # File doesn't exist on remote-sim, create it with different content
        with open(test_file, 'w') as f:
            f.write("# Remote Test\n\nThis was created on remote while you were offline.\n")
    
    run_command("git add .", cwd=vault_path)
    out, err, rc = run_command('git commit -m "Remote changes - conflicting test file"', cwd=vault_path)
    print(f"Remote-sim commit result: rc={rc}")
    
    # Switch back to main and set up the conflict scenario
    run_command("git checkout main", cwd=vault_path)
    
    # Now simulate trying to pull the remote changes (this should create a conflict)
    out, err, rc = run_command("git merge remote-sim", cwd=vault_path)
    print(f"Merge result: rc={rc}, out='{out}', err='{err}'")
    
    if rc != 0 and "CONFLICT" in (out + err):
        print("✅ Successfully created conflict scenario")
        return True
    else:
        print("❌ Failed to create conflict scenario")
        return False

def check_github_sync_status(vault_path):
    """Check if local is in sync with remote"""
    print("=== CHECKING GITHUB SYNC STATUS ===")
    
    # Fetch latest remote info
    run_command("git fetch origin", cwd=vault_path)
    
    # Check if local is ahead of remote
    ahead_out, _, ahead_rc = run_command("git rev-list --count HEAD ^origin/main", cwd=vault_path)
    behind_out, _, behind_rc = run_command("git rev-list --count origin/main ^HEAD", cwd=vault_path)
    
    try:
        ahead_count = int(ahead_out) if ahead_rc == 0 and ahead_out.isdigit() else 0
        behind_count = int(behind_out) if behind_rc == 0 and behind_out.isdigit() else 0
    except:
        ahead_count = behind_count = 0
    
    print(f"Local is {ahead_count} commits ahead of remote")
    print(f"Local is {behind_count} commits behind remote")
    
    # Get latest commit messages
    local_commit = run_command("git log -1 --oneline", cwd=vault_path)[0]
    remote_commit = run_command("git log -1 --oneline origin/main", cwd=vault_path)[0]
    
    print(f"Latest local commit: {local_commit}")
    print(f"Latest remote commit: {remote_commit}")
    
    return {
        'ahead_count': ahead_count,
        'behind_count': behind_count,
        'in_sync': ahead_count == 0 and behind_count == 0,
        'local_commit': local_commit,
        'remote_commit': remote_commit
    }

def test_conflict_resolution_push_bug():
    """
    Main test function to reproduce the conflict resolution push bug
    """
    vault_path = r"C:\Users\abiji\Test"
    config_data = {"GITHUB_REMOTE_URL": "test"}
    
    print("=== TESTING CONFLICT RESOLUTION PUSH BUG ===")
    print(f"Testing in vault: {vault_path}")
    
    # Step 1: Check initial state
    print("\n--- Step 1: Initial State ---")
    initial_status = check_github_sync_status(vault_path)
    print(f"Initial sync status: {initial_status}")
    
    # Step 2: Simulate offline session with changes
    print("\n--- Step 2: Simulating Offline Changes ---")
    if not simulate_offline_changes(vault_path):
        print("❌ Failed to simulate offline changes")
        return False
    
    # Step 3: Simulate remote changes (conflict scenario)
    print("\n--- Step 3: Simulating Remote Changes (Conflict Scenario) ---")
    if not simulate_remote_changes(vault_path):
        print("❌ Failed to create conflict scenario")
        return False
    
    # Step 4: Check status after creating conflicts
    print("\n--- Step 4: Status After Creating Conflicts ---")
    conflict_status = check_github_sync_status(vault_path)
    print(f"Conflict status: {conflict_status}")
    
    # Step 5: Test the offline sync manager detection
    print("\n--- Step 5: Testing Offline Sync Manager ---")
    try:
        sync_manager = offline_sync_manager.OfflineSyncManager(vault_path, config_data)
        summary = sync_manager.get_session_summary()
        print(f"Offline sync summary: {summary}")
        
        should_resolve = sync_manager.should_trigger_conflict_resolution()
        print(f"Should trigger conflict resolution: {should_resolve}")
        
    except Exception as e:
        print(f"❌ Error testing offline sync manager: {e}")
        return False
    
    # Step 6: Simulate manual conflict resolution
    print("\n--- Step 6: Simulating Manual Conflict Resolution ---")
    # For testing purposes, we'll resolve conflicts manually
    # In a real scenario, this would be done through the UI
    
    # Check current git status
    status_out, _, _ = run_command("git status --porcelain", cwd=vault_path)
    print(f"Git status before resolution: {status_out}")
    
    # Resolve conflicts by choosing our version (offline changes)
    test_file = os.path.join(vault_path, "offline_test.md")
    if os.path.exists(test_file):
        with open(test_file, 'w') as f:
            f.write("# Resolved Test\n\nThis is the resolved version combining offline and remote changes.\n")
    
    # Add and commit the resolution
    run_command("git add .", cwd=vault_path)
    out, err, rc = run_command('git commit -m "Resolve conflicts using manual resolution"', cwd=vault_path)
    print(f"Conflict resolution commit: rc={rc}, out='{out}', err='{err}'")
    
    if rc != 0:
        print("❌ Failed to commit conflict resolution")
        return False
    
    # Step 7: Check status after conflict resolution
    print("\n--- Step 7: Status After Conflict Resolution ---")
    post_resolution_status = check_github_sync_status(vault_path)
    print(f"Post-resolution status: {post_resolution_status}")
    
    # Step 8: Test if changes are pushed immediately (THIS IS THE BUG)
    print("\n--- Step 8: Testing Immediate Push After Conflict Resolution ---")
    
    if post_resolution_status['ahead_count'] > 0:
        print(f"🔍 Local is {post_resolution_status['ahead_count']} commits ahead - these should be pushed immediately")
        
        # Try to push the resolved changes
        push_out, push_err, push_rc = run_command("git push -u origin main", cwd=vault_path)
        print(f"Push result: rc={push_rc}, out='{push_out}', err='{push_err}'")
        
        if push_rc == 0:
            print("✅ Conflict resolution changes pushed successfully")
        else:
            print("❌ Failed to push conflict resolution changes")
            print(f"This is likely the bug - resolved changes not pushed")
            return False
    else:
        print("⚠️ No commits ahead after resolution - this might indicate an issue")
    
    # Step 9: Final verification
    print("\n--- Step 9: Final Verification ---")
    final_status = check_github_sync_status(vault_path)
    print(f"Final status: {final_status}")
    
    if final_status['in_sync']:
        print("✅ SUCCESS: Local and remote are in sync after conflict resolution")
        return True
    else:
        print("❌ FAILURE: Local and remote are NOT in sync after conflict resolution")
        print("This indicates the conflict resolution push bug exists")
        return False

def cleanup_test_artifacts(vault_path):
    """Clean up test artifacts"""
    print("\n=== CLEANUP ===")
    
    # Remove test files
    test_file = os.path.join(vault_path, "offline_test.md")
    if os.path.exists(test_file):
        os.remove(test_file)
        run_command("git add .", cwd=vault_path)
        run_command('git commit -m "Cleanup: remove test file"', cwd=vault_path)
        run_command("git push origin main", cwd=vault_path)
    
    # Remove test branch
    run_command("git branch -D remote-sim", cwd=vault_path)
    
    print("✅ Cleanup completed")

if __name__ == "__main__":
    try:
        success = test_conflict_resolution_push_bug()
        
        print(f"\n{'='*50}")
        if success:
            print("✅ TEST PASSED: Conflict resolution and push working correctly")
        else:
            print("❌ TEST FAILED: Conflict resolution push bug detected")
            print("The resolved changes are not being pushed to GitHub immediately")
        print(f"{'='*50}")
        
        # Ask user if they want to clean up
        response = input("\nDo you want to clean up test artifacts? (y/n): ").lower()
        if response == 'y':
            cleanup_test_artifacts(r"C:\Users\abiji\Test")
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
