#!/usr/bin/env python3
"""
Test script to debug unpushed commit detection issue with real vault
"""

import subprocess
import os

def run_command(command, cwd=None):
    """Run a command and return stdout, stderr, return_code"""
    try:
        result = subprocess.run(
            command, shell=True, cwd=cwd, capture_output=True, 
            text=True, timeout=30
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired as e:
        return "", f"Command timed out: {e}", 1
    except Exception as e:
        return "", f"Command failed: {e}", 1

def test_unpushed_detection(vault_path):
    """Test unpushed commit detection logic"""
    print(f"Testing unpushed commit detection for: {vault_path}")
    print("=" * 60)
    
    # Check if directory exists and is a git repo
    if not os.path.exists(vault_path):
        print(f"❌ Vault path does not exist: {vault_path}")
        return
    
    git_status_out, git_status_err, git_status_rc = run_command("git status", cwd=vault_path)
    if git_status_rc != 0:
        print(f"❌ Not a git repository: {git_status_err}")
        return
    
    print("✅ Git repository found")
    
    # Step 1: Check current HEAD
    head_out, head_err, head_rc = run_command("git rev-parse HEAD", cwd=vault_path)
    if head_rc == 0:
        head_hash = head_out.strip()
        print(f"📍 Current HEAD: {head_hash}")
    else:
        print(f"❌ Could not get HEAD: {head_err}")
        return
    
    # Step 2: Check if origin/main exists
    origin_check_out, origin_check_err, origin_check_rc = run_command("git rev-parse origin/main", cwd=vault_path)
    if origin_check_rc == 0:
        origin_hash = origin_check_out.strip()
        print(f"📍 Remote origin/main: {origin_hash}")
        
        # Check if they're the same
        if head_hash == origin_hash:
            print("✅ HEAD and origin/main point to the same commit")
        else:
            print("⚠️ HEAD and origin/main point to different commits")
    else:
        print(f"❌ origin/main reference not found: {origin_check_err}")
        print("This explains the issue - git rev-list will count ALL commits when origin/main doesn't exist")
        return
    
    # Step 3: Test the problematic command
    print("\n" + "=" * 40)
    print("TESTING PROBLEMATIC COMMAND:")
    
    rev_list_out, rev_list_err, rev_list_rc = run_command("git rev-list --count HEAD ^origin/main", cwd=vault_path)
    print(f"Command: git rev-list --count HEAD ^origin/main")
    print(f"Return code: {rev_list_rc}")
    print(f"Output: '{rev_list_out.strip()}'")
    print(f"Error: '{rev_list_err.strip()}'")
    
    if rev_list_rc == 0 and rev_list_out.strip():
        try:
            count = int(rev_list_out.strip())
            print(f"Parsed count: {count}")
            
            if head_hash == origin_hash and count > 0:
                print("🐛 BUG CONFIRMED: Count is non-zero but hashes match!")
                print("This indicates the git rev-list command is malfunctioning or origin/main tracking is broken")
            elif head_hash == origin_hash and count == 0:
                print("✅ CORRECT: Count is zero and hashes match")
            elif head_hash != origin_hash:
                print(f"ℹ️ Count reflects actual difference between HEAD and origin/main")
        except ValueError:
            print(f"❌ Could not parse count as integer: {rev_list_out}")
    
    # Step 4: Test alternative methods
    print("\n" + "=" * 40)
    print("TESTING ALTERNATIVE METHODS:")
    
    # Method 1: Check tracking branch
    tracking_out, tracking_err, tracking_rc = run_command("git rev-parse --abbrev-ref HEAD@{upstream}", cwd=vault_path)
    print(f"Tracking branch: {tracking_out.strip() if tracking_rc == 0 else 'Not set'}")
    
    # Method 2: Check remote tracking
    remote_out, remote_err, remote_rc = run_command("git branch -vv", cwd=vault_path)
    print(f"Branch info: {remote_out.strip()}")
    
    # Method 3: Fresh fetch and retest
    print(f"\nFetching latest remote references...")
    fetch_out, fetch_err, fetch_rc = run_command("git fetch origin", cwd=vault_path)
    if fetch_rc == 0:
        print("✅ Fetch successful")
        
        # Retest after fetch
        rev_list_out2, rev_list_err2, rev_list_rc2 = run_command("git rev-list --count HEAD ^origin/main", cwd=vault_path)
        print(f"After fetch - Count: {rev_list_out2.strip()}")
        
        # Check hashes again
        head_out2, _, head_rc2 = run_command("git rev-parse HEAD", cwd=vault_path)
        origin_out2, _, origin_rc2 = run_command("git rev-parse origin/main", cwd=vault_path)
        
        if head_rc2 == 0 and origin_rc2 == 0:
            head_hash2 = head_out2.strip()
            origin_hash2 = origin_out2.strip()
            print(f"After fetch - HEAD: {head_hash2}")
            print(f"After fetch - origin/main: {origin_hash2}")
            
            if head_hash2 == origin_hash2:
                if rev_list_out2.strip() == "0":
                    print("✅ FIXED: After fetch, count is correctly 0")
                else:
                    print(f"🐛 STILL BROKEN: After fetch, count is {rev_list_out2.strip()} but hashes match")
    else:
        print(f"❌ Fetch failed: {fetch_err}")
    
    # Step 5: Test the fix logic
    print("\n" + "=" * 40)
    print("TESTING FIX LOGIC:")
    
    # Simulate the fixed logic
    origin_check_out, origin_check_err, origin_check_rc = run_command("git rev-parse origin/main", cwd=vault_path)
    
    if origin_check_rc != 0:
        print("✅ FIX: origin/main not found - would assume in sync")
    else:
        rev_list_out, rev_list_err, rev_list_rc = run_command("git rev-list --count HEAD ^origin/main", cwd=vault_path)
        
        if rev_list_rc != 0 or not rev_list_out.strip():
            print("✅ FIX: rev-list failed or empty - would assume in sync")
        else:
            try:
                ahead_count = int(rev_list_out.strip())
                
                # Hash comparison check
                head_hash_out, _, head_hash_rc = run_command("git rev-parse HEAD", cwd=vault_path)
                origin_hash_out, _, origin_hash_rc = run_command("git rev-parse origin/main", cwd=vault_path)
                
                if head_hash_rc == 0 and origin_hash_rc == 0:
                    head_hash = head_hash_out.strip()
                    origin_hash = origin_hash_out.strip()
                    
                    if head_hash == origin_hash:
                        print(f"✅ FIX: Hashes match - would override count from {ahead_count} to 0")
                        ahead_count = 0
                    else:
                        print(f"ℹ️ FIX: Hashes differ - would keep count {ahead_count}")
                
                print(f"Final ahead_count after fix: {ahead_count}")
                
            except ValueError:
                print("✅ FIX: Could not parse count - would assume in sync")

if __name__ == "__main__":
    vault_path = r"C:\Users\abiji\Test"
    test_unpushed_detection(vault_path)
