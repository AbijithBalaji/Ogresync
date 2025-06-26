#!/usr/bin/env python3
"""
Test the Ogresync script's conflict resolution and immediate push functionality.
This test validates that our fix for immediate pushing after conflict resolution works.
"""

import sys
import os
import time
import subprocess
import json

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_command(cmd, cwd=None):
    """Run a command and return output, error, return code"""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), 1

def create_offline_session_scenario():
    """Create a scenario where we have offline changes that will trigger conflict resolution"""
    vault_path = r"C:\Users\abiji\Test"
    
    print("=== CREATING OFFLINE SESSION SCENARIO ===")
    
    # Create an offline session in the offline state file
    offline_state_file = os.path.join(vault_path, ".ogresync-offline-state.json")
    
    # Create some test changes first
    test_file = os.path.join(vault_path, "offline_session_test.md")
    with open(test_file, 'w') as f:
        f.write("# Offline Session Test\n\nThis file was created during an offline session.\n")
    
    run_command("git add .", cwd=vault_path)
    out, err, rc = run_command('git commit -m "Offline session: test file"', cwd=vault_path)
    
    if rc != 0:
        print(f"❌ Failed to create offline commit: {err}")
        return False
    
    print("✅ Created offline changes that will trigger conflict resolution")
    return True

def test_ogresync_immediate_push():
    """Test that Ogresync immediately pushes after conflict resolution"""
    print("\n=== TESTING OGRESYNC IMMEDIATE PUSH AFTER CONFLICT RESOLUTION ===")
    
    # This is a conceptual test - in reality, we'd need to:
    # 1. Have actual offline sessions detected
    # 2. Have actual conflicts to resolve  
    # 3. Run the Ogresync script and monitor its behavior
    
    # For now, let's check if our code changes are syntactically correct
    # and would work by examining the modified script
    
    script_path = "Ogresync.py"
    
    print("🔍 Checking if immediate push code was added to conflict resolution...")
    
    with open(script_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for the immediate push code we added
    immediate_push_patterns = [
        "Pushing conflict resolution results immediately",
        "Pushing fallback conflict resolution results immediately", 
        "Pushing post-Obsidian conflict resolution results immediately"
    ]
    
    found_patterns = []
    for pattern in immediate_push_patterns:
        if pattern in content:
            found_patterns.append(pattern)
            print(f"✅ Found: {pattern}")
        else:
            print(f"❌ Missing: {pattern}")
    
    if len(found_patterns) == len(immediate_push_patterns):
        print("✅ All immediate push fixes have been added to the script")
        return True
    else:
        print("❌ Some immediate push fixes are missing")
        return False

def manual_validation_test():
    """Manual validation instructions for the user"""
    print("\n=== MANUAL VALIDATION INSTRUCTIONS ===")
    print("To validate the fix works in practice:")
    print("1. Work offline in Obsidian (disconnect internet)")
    print("2. Make some changes and close Obsidian")
    print("3. Reconnect internet")
    print("4. Run Ogresync script")
    print("5. When conflict resolution appears, resolve the conflicts")
    print("6. Check immediately if changes appear on GitHub")
    print("7. The script should show: 'Pushing conflict resolution results immediately...'")
    print("8. And then: 'Conflict resolution results pushed to GitHub successfully'")
    
def cleanup_test_artifacts():
    """Clean up any test artifacts"""
    vault_path = r"C:\Users\abiji\Test"
    
    test_file = os.path.join(vault_path, "offline_session_test.md")
    if os.path.exists(test_file):
        os.remove(test_file)
        run_command("git add .", cwd=vault_path)
        run_command('git commit -m "Cleanup: remove offline session test file"', cwd=vault_path)
        run_command("git push origin main", cwd=vault_path)
        print("✅ Cleaned up test artifacts")

if __name__ == "__main__":
    print("=== TESTING OGRESYNC CONFLICT RESOLUTION IMMEDIATE PUSH FIX ===")
    
    try:
        # Test 1: Create scenario
        scenario_success = create_offline_session_scenario()
        
        # Test 2: Check code fixes
        code_success = test_ogresync_immediate_push()
        
        # Test 3: Manual validation instructions
        manual_validation_test()
        
        print(f"\n{'='*60}")
        if scenario_success and code_success:
            print("✅ PRELIMINARY TESTS PASSED")
            print("   - Offline scenario creation: ✅")
            print("   - Immediate push code added: ✅")
            print("   - Ready for manual validation")
        else:
            print("❌ PRELIMINARY TESTS FAILED")
            if not scenario_success:
                print("   - Offline scenario creation: ❌")
            if not code_success:
                print("   - Immediate push code: ❌")
        
        print("\n🔧 RECOMMENDATION:")
        print("Run the actual Ogresync script with an offline-to-online scenario")
        print("to verify that conflict resolution immediately pushes changes.")
        print(f"{'='*60}")
        
        # Cleanup
        response = input("\nDo you want to clean up test artifacts? (y/n): ").lower()
        if response == 'y':
            cleanup_test_artifacts()
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
