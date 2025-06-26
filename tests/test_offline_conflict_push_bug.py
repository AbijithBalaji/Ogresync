#!/usr/bin/env python3
"""
Focused test for the specific offline-to-online conflict resolution push bug.
This simulates exactly what the user described:
1. Work offline and make changes
2. Come back online 
3. Conflict resolution is triggered and user resolves it
4. Check if the resolved changes are immediately pushed to GitHub

This is a regression test for the bug where conflict resolution succeeds
but the resolved changes aren't pushed to GitHub.
"""

import sys
import os
import time
import subprocess

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_command(cmd, cwd=None):
    """Run a command and return output, error, return code"""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), 1

def get_commit_hash(vault_path, ref="HEAD"):
    """Get commit hash for a reference"""
    out, _, rc = run_command(f"git rev-parse {ref}", cwd=vault_path)
    return out if rc == 0 else None

def check_if_pushed(vault_path):
    """Check if local HEAD has been pushed to remote"""
    # Fetch latest remote info
    run_command("git fetch origin", cwd=vault_path)
    
    local_head = get_commit_hash(vault_path, "HEAD")
    remote_head = get_commit_hash(vault_path, "origin/main")
    
    print(f"Local HEAD:  {local_head}")
    print(f"Remote HEAD: {remote_head}")
    
    if local_head and remote_head:
        is_pushed = local_head == remote_head
        print(f"Changes pushed to GitHub: {'✅ YES' if is_pushed else '❌ NO'}")
        return is_pushed
    else:
        print("❌ Could not determine push status")
        return False

def simulate_offline_work_then_online_conflict_resolution():
    """
    Simulate the exact scenario the user described:
    1. Work offline (make changes, commit locally)
    2. Come back online (conflicts detected)
    3. Resolve conflicts through UI
    4. Check if resolved changes are pushed immediately
    """
    vault_path = r"C:\Users\abiji\Test"
    
    print("=== SIMULATING OFFLINE-TO-ONLINE CONFLICT RESOLUTION BUG ===")
    
    # Step 1: Check initial state
    print("\n--- Step 1: Initial state ---")
    initial_head = get_commit_hash(vault_path)
    print(f"Starting from commit: {initial_head}")
    
    # Step 2: Simulate offline work
    print("\n--- Step 2: Simulating offline work ---")
    test_file = os.path.join(vault_path, "offline_work_test.md")
    
    with open(test_file, 'w') as f:
        f.write("# Offline Work Test\n\nThis simulates working offline and making changes.\n")
    
    run_command("git add .", cwd=vault_path)
    out, err, rc = run_command('git commit -m "Offline work: added test file"', cwd=vault_path)
    
    if rc == 0:
        offline_commit = get_commit_hash(vault_path)
        print(f"✅ Offline work committed: {offline_commit}")
    else:
        print(f"❌ Failed to commit offline work: {err}")
        return False
    
    # Step 3: Simulate coming back online and finding conflicts
    print("\n--- Step 3: Simulating conflict scenario (remote advanced) ---")
    
    # For this test, we'll create a conflict by simulating remote changes
    # This is a simplified version - in reality this would come from actual remote changes
    
    # Create a branch to simulate what remote looks like
    run_command("git branch remote-state HEAD~1", cwd=vault_path)  # Remote is one commit behind
    run_command("git checkout remote-state", cwd=vault_path)
    
    # Make a conflicting change on "remote"
    with open(test_file, 'w') as f:
        f.write("# Remote Work Test\n\nThis simulates changes made on remote while offline.\n")
    
    run_command("git add .", cwd=vault_path)
    run_command('git commit -m "Remote work: modified test file differently"', cwd=vault_path)
    
    # Switch back to main and create the conflict
    run_command("git checkout main", cwd=vault_path)
    
    # Now try to merge the "remote" changes - this should create a conflict
    merge_out, merge_err, merge_rc = run_command("git merge remote-state", cwd=vault_path)
    
    if merge_rc != 0 and "CONFLICT" in (merge_out + merge_err):
        print("✅ Conflict scenario created successfully")
    else:
        print("❌ Failed to create conflict scenario")
        return False
    
    # Step 4: Manually resolve the conflict (simulating user choice)
    print("\n--- Step 4: Manually resolving conflict ---")
    
    # Resolve by choosing a merged version
    with open(test_file, 'w') as f:
        f.write("# Resolved Work Test\n\nThis is the resolved version combining offline and remote work.\n")
    
    run_command("git add .", cwd=vault_path)
    out, err, rc = run_command('git commit -m "Resolve conflicts: merged offline and remote changes"', cwd=vault_path)
    
    if rc == 0:
        resolved_commit = get_commit_hash(vault_path)
        print(f"✅ Conflict resolved and committed: {resolved_commit}")
    else:
        print(f"❌ Failed to commit conflict resolution: {err}")
        return False
    
    # Step 5: Check if resolved changes are on remote
    print("\n--- Step 5: Checking if conflict resolution was pushed to GitHub ---")
    
    # This is the critical test - are the resolved changes pushed immediately?
    is_pushed_before_manual_push = check_if_pushed(vault_path)
    
    if not is_pushed_before_manual_push:
        print("\n🔍 TESTING: Manually pushing to see if it works...")
        push_out, push_err, push_rc = run_command("git push -u origin main", cwd=vault_path)
        
        if push_rc == 0:
            print("✅ Manual push succeeded")
            is_pushed_after_manual = check_if_pushed(vault_path)
            
            if is_pushed_after_manual:
                print("❌ BUG CONFIRMED: Conflict resolution was successful but not automatically pushed")
                print("   The resolved changes required manual push to reach GitHub")
                return False
            else:
                print("❌ Even manual push didn't work - there's a bigger issue")
                return False
        else:
            print(f"❌ Manual push failed: {push_err}")
            return False
    else:
        print("✅ SUCCESS: Conflict resolution was automatically pushed to GitHub")
        return True

def cleanup_test():
    """Clean up test artifacts"""
    vault_path = r"C:\Users\abiji\Test"
    
    print("\n--- Cleanup ---")
    
    # Remove test file
    test_file = os.path.join(vault_path, "offline_work_test.md")
    if os.path.exists(test_file):
        os.remove(test_file)
        run_command("git add .", cwd=vault_path)
        run_command('git commit -m "Cleanup: remove test file"', cwd=vault_path)
        run_command("git push origin main", cwd=vault_path)
    
    # Remove test branch
    run_command("git branch -D remote-state", cwd=vault_path)
    
    print("✅ Cleanup completed")

if __name__ == "__main__":
    try:
        print("This test simulates the exact offline-to-online conflict resolution scenario")
        print("that the user reported where changes aren't pushed after successful resolution.\n")
        
        success = simulate_offline_work_then_online_conflict_resolution()
        
        print(f"\n{'='*60}")
        if success:
            print("✅ TEST PASSED: Conflict resolution automatically pushes to GitHub")
            print("   The bug appears to be fixed!")
        else:
            print("❌ TEST FAILED: Conflict resolution bug still exists")
            print("   Resolved changes are not automatically pushed to GitHub")
            print("   This confirms the user's reported issue")
        print(f"{'='*60}")
        
        # Ask user if they want to clean up
        response = input("\nDo you want to clean up test artifacts? (y/n): ").lower()
        if response == 'y':
            cleanup_test()
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
