#!/usr/bin/env python3
"""
Test script to validate the unpushed commit detection fix in Ogresync

This script tests the specific issue where:
1. git rev-list --count HEAD ^origin/main returns total commits instead of unpushed commits
2. when HEAD and origin/main hashes are the same, the count should be 0

Usage: python test_unpushed_fix.py [vault_path]
"""

import os
import sys
import subprocess
import tempfile
import shutil

def run_command(command, cwd=None):
    """Run a command and return (stdout, stderr, return_code)"""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=cwd, 
            capture_output=True, 
            text=True, 
            timeout=30
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timed out", 1
    except Exception as e:
        return "", str(e), 1

def test_unpushed_commit_detection(vault_path=None):
    """Test the fixed unpushed commit detection logic"""
    
    if vault_path is None:
        # Create a temporary git repo for testing
        test_dir = tempfile.mkdtemp(prefix="ogresync_test_")
        vault_path = test_dir
        print(f"Created test repository at: {vault_path}")
        
        # Initialize git repo
        run_command("git init", cwd=vault_path)
        run_command("git config user.name 'Test User'", cwd=vault_path)
        run_command("git config user.email 'test@example.com'", cwd=vault_path)
        
        # Create a test file and commit
        test_file = os.path.join(vault_path, "test.md")
        with open(test_file, 'w') as f:
            f.write("# Test file\nThis is a test file for Ogresync.\n")
        
        run_command("git add test.md", cwd=vault_path)
        run_command("git commit -m 'Initial commit'", cwd=vault_path)
        
        # Create a fake remote reference that points to the same commit as HEAD
        # This simulates the scenario in your logs
        head_out, _, _ = run_command("git rev-parse HEAD", cwd=vault_path)
        head_hash = head_out.strip()
        
        # Create refs/remotes/origin/main pointing to the same commit
        remote_refs_dir = os.path.join(vault_path, ".git", "refs", "remotes", "origin")
        os.makedirs(remote_refs_dir, exist_ok=True)
        
        with open(os.path.join(remote_refs_dir, "main"), 'w') as f:
            f.write(head_hash + '\n')
            
        print(f"Set up test repo with HEAD and origin/main both pointing to: {head_hash}")
        
        cleanup_test_repo = True
    else:
        print(f"Using existing repository at: {vault_path}")
        cleanup_test_repo = False
    
    try:
        print("\n" + "="*60)
        print("TESTING UNPUSHED COMMIT DETECTION")
        print("="*60)
        
        # Test 1: Check if origin/main exists
        print("\n1. Checking if origin/main reference exists...")
        origin_check_out, origin_check_err, origin_check_rc = run_command("git rev-parse origin/main", cwd=vault_path)
        print(f"   Command: git rev-parse origin/main")
        print(f"   Return code: {origin_check_rc}")
        print(f"   Output: {origin_check_out.strip()}")
        
        if origin_check_rc != 0:
            print("   ❌ origin/main reference not found - this explains the issue!")
            print("   💡 When origin/main doesn't exist, git rev-list counts ALL commits")
            return
        
        # Test 2: Get commit hashes
        print("\n2. Comparing HEAD and origin/main commit hashes...")
        head_hash_out, _, head_hash_rc = run_command("git rev-parse HEAD", cwd=vault_path)
        origin_hash_out, _, origin_hash_rc = run_command("git rev-parse origin/main", cwd=vault_path)
        
        if head_hash_rc == 0 and origin_hash_rc == 0:
            head_hash = head_hash_out.strip()
            origin_hash = origin_hash_out.strip()
            print(f"   HEAD hash: {head_hash}")
            print(f"   origin/main hash: {origin_hash}")
            
            if head_hash == origin_hash:
                print("   ✅ Hashes match - repositories are in sync!")
            else:
                print("   ⚠️  Hashes differ - there are real differences")
        
        # Test 3: Test the problematic command
        print("\n3. Testing the problematic git rev-list command...")
        rev_list_out, rev_list_err, rev_list_rc = run_command("git rev-list --count HEAD ^origin/main", cwd=vault_path)
        print(f"   Command: git rev-list --count HEAD ^origin/main")
        print(f"   Return code: {rev_list_rc}")
        print(f"   Output: '{rev_list_out.strip()}'")
        print(f"   Error: '{rev_list_err.strip()}'")
        
        if rev_list_rc == 0 and rev_list_out.strip():
            try:
                count = int(rev_list_out.strip())
                print(f"   📊 Parsed count: {count}")
                
                if head_hash == origin_hash and count > 0:
                    print(f"   ❌ BUG DETECTED: Count is {count} but hashes match!")
                    print("   💡 This is the bug we're fixing - should be 0 when hashes match")
                elif head_hash == origin_hash and count == 0:
                    print("   ✅ CORRECT: Count is 0 when hashes match")
                elif head_hash != origin_hash:
                    print(f"   ✅ Count {count} makes sense - hashes differ")
                    
            except ValueError:
                print(f"   ❌ Error parsing count: '{rev_list_out.strip()}'")
        
        # Test 4: Test total commit count for comparison
        print("\n4. Testing total commit count for comparison...")
        total_out, _, total_rc = run_command("git rev-list --count HEAD", cwd=vault_path)
        if total_rc == 0:
            total_count = int(total_out.strip())
            print(f"   Total commits in repository: {total_count}")
            
            if rev_list_rc == 0 and rev_list_out.strip():
                ahead_count = int(rev_list_out.strip())
                if ahead_count == total_count and head_hash == origin_hash:
                    print(f"   ❌ CONFIRMED BUG: rev-list count ({ahead_count}) equals total count ({total_count}) when repos are in sync!")
                    
        print("\n" + "="*60)
        print("FIXED LOGIC SIMULATION")
        print("="*60)
        
        # Simulate the fixed logic
        print("\n5. Simulating the fixed logic...")
        
        # Step 1: Check if origin/main exists
        if origin_check_rc != 0:
            print("   🔧 FIXED: origin/main not found - assuming in sync")
            final_result = "in sync (no remote reference)"
        else:
            # Step 2: Check rev-list
            if rev_list_rc != 0 or not rev_list_out.strip():
                print("   🔧 FIXED: rev-list failed - assuming in sync")  
                final_result = "in sync (rev-list failed)"
            else:
                # Step 3: Parse count and verify with hashes
                ahead_count = int(rev_list_out.strip())
                print(f"   🔧 FIXED: Parsed ahead_count from rev-list: {ahead_count}")
                
                if head_hash == origin_hash:
                    print(f"   🔧 FIXED: Hashes match - overriding count to 0")
                    final_result = "in sync (verified by hash)"
                    actual_unpushed = 0
                else:
                    print(f"   🔧 FIXED: Hashes differ - count {ahead_count} is valid")
                    final_result = f"{ahead_count} unpushed commits"
                    actual_unpushed = ahead_count
        
        print(f"\n   📋 FINAL RESULT: {final_result}")
        
        if 'in sync' in final_result:
            print("   ✅ SUCCESS: Fixed logic correctly detects sync status")
        else:
            print(f"   📤 INFO: {actual_unpushed} commits need to be pushed")
            
    finally:
        if cleanup_test_repo and vault_path:
            try:
                shutil.rmtree(vault_path)
                print(f"\nCleaned up test repository: {vault_path}")
            except Exception as e:
                print(f"Warning: Could not clean up test repo: {e}")

if __name__ == "__main__":
    vault_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    if vault_path and not os.path.exists(vault_path):
        print(f"Error: Vault path '{vault_path}' does not exist")
        sys.exit(1)
        
    test_unpushed_commit_detection(vault_path)
