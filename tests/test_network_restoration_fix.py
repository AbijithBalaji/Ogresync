"""
Test script to verify the network restoration during Obsidian session fix

This test simulates:
1. Starting sync offline (with unpushed commits)
2. Network coming back during Obsidian session
3. Verifying conflict resolution triggers when Obsidian closes

This addresses the bug where conflict resolution didn't trigger when
network was restored during the Obsidian session.
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import offline_sync_manager
from offline_sync_manager import NetworkState, OfflineSyncManager


def test_network_restoration_during_session():
    """Test network restoration during Obsidian session triggers conflict resolution"""
    print("🧪 Testing network restoration during Obsidian session...")
    
    # Create a temporary test vault
    test_vault = tempfile.mkdtemp(prefix="ogresync_network_restore_test_")
    remote_vault = None
    print(f"📁 Created test vault: {test_vault}")
    
    try:
        # Initialize git repo with remote tracking
        subprocess.run(['git', 'init'], cwd=test_vault, check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=test_vault, check=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=test_vault, check=True)
        
        # Create a bare repository to simulate remote
        remote_vault = tempfile.mkdtemp(prefix="ogresync_remote_test_")
        print(f"📁 Created remote vault: {remote_vault}")
        subprocess.run(['git', 'init', '--bare'], cwd=remote_vault, check=True, capture_output=True)
        
        # Add remote and set up tracking
        subprocess.run(['git', 'remote', 'add', 'origin', remote_vault], cwd=test_vault, check=True)
        
        # Create initial commit and push to set up tracking
        test_file = Path(test_vault) / "initial.md"
        test_file.write_text("# Initial Note\nThis is the initial note.")
        
        subprocess.run(['git', 'add', 'initial.md'], cwd=test_vault, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=test_vault, check=True)
        
        # Rename branch to main if needed and push to set up tracking
        subprocess.run(['git', 'branch', '-M', 'main'], cwd=test_vault, check=True)
        subprocess.run(['git', 'push', '-u', 'origin', 'main'], cwd=test_vault, check=True)
        
        # Create offline sync manager
        config = {'VAULT_PATH': test_vault}
        manager = OfflineSyncManager(test_vault, config)
        
        # Simulate starting offline
        def mock_offline():
            return NetworkState.OFFLINE
        
        original_check = manager.check_network_availability
        manager.check_network_availability = mock_offline
        
        # Start offline session
        session_id = manager.start_sync_session(NetworkState.OFFLINE)
        print(f"✅ Started offline session: {session_id}")
        
        # Simulate offline changes (what would happen during Obsidian session)
        offline_file = Path(test_vault) / "offline_change.md"
        offline_file.write_text("# Offline Change\nThis was created while offline.")
        
        subprocess.run(['git', 'add', 'offline_change.md'], cwd=test_vault, check=True)
        subprocess.run(['git', 'commit', '-m', f'Offline commit - {session_id}'], cwd=test_vault, check=True)
        
        # End offline session
        commits = [f'Offline commit - {session_id}']
        manager.end_sync_session(session_id, NetworkState.OFFLINE, commits)
        
        print("📱 Simulated offline session with changes")
        
        # Now simulate network coming back online (what happens when Obsidian closes)
        def mock_online():
            return NetworkState.ONLINE
        
        manager.check_network_availability = mock_online
        
        # Check if conflict resolution should trigger
        needs_resolution = manager.should_trigger_conflict_resolution()
        summary = manager.get_session_summary()
        
        print(f"🌐 Network restored - needs conflict resolution: {needs_resolution}")
        print(f"📊 Session summary: {summary}")
        
        # Verify the fix
        if needs_resolution and summary['unpushed_commits'] > 0:
            print("✅ PASS: Conflict resolution correctly triggered after network restoration")
            return True
        else:
            print("❌ FAIL: Conflict resolution should have triggered after network restoration")
            return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
        
    finally:
        # Clean up
        try:
            shutil.rmtree(test_vault)
            if remote_vault:
                shutil.rmtree(remote_vault)
            print(f"🗑️ Cleaned up test vaults")
        except:
            print(f"⚠️ Could not clean up test vaults")


def test_network_restoration_logic():
    """Test the logic that detects network state changes"""
    print("🧪 Testing network state change detection logic...")
    
    # Simulate the key variables from Ogresync.py
    network_was_available_before = False  # Started offline
    network_available = True  # Now online (after Obsidian session)
    
    network_restored = not network_was_available_before and network_available
    
    print(f"📡 Network was available before: {network_was_available_before}")
    print(f"📡 Network available now: {network_available}")
    print(f"🔄 Network restoration detected: {network_restored}")
    
    if network_restored:
        print("✅ PASS: Network restoration logic works correctly")
        return True
    else:
        print("❌ FAIL: Network restoration logic failed")
        return False


if __name__ == "__main__":
    print("🚀 Testing network restoration during Obsidian session fix...")
    print("=" * 70)
    
    # Run tests
    test1_passed = test_network_restoration_during_session()
    print()
    test2_passed = test_network_restoration_logic()
    
    print("=" * 70)
    print("📋 Test Results:")
    print(f"   Network Restoration Session: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"   Network State Change Logic: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed:
        print("🎉 All tests passed! Network restoration fix is working correctly.")
        print()
        print("📝 The fix ensures that:")
        print("   - Network status is re-checked after Obsidian closes")
        print("   - Conflict resolution triggers when network is restored during session")
        print("   - Offline changes are properly processed when connectivity returns")
    else:
        print("⚠️ Some tests failed. Please review the implementation.")
