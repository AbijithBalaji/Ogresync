"""
Simple Test for Offline Sync Components

Basic functionality test for offline sync manager components.
Run this to verify the offline system works before integration.
"""

import os
import sys
import tempfile
import shutil
import subprocess
from datetime import datetime

# Add current directory for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all components can be imported"""
    print("🧪 Testing imports...")
    
    try:
        from offline_sync_manager import (
            OfflineSyncManager, NetworkState, SyncMode, 
            create_offline_sync_manager, should_use_offline_mode
        )
        print("✅ Offline sync manager imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_basic_functionality():
    """Test basic offline sync manager functionality"""
    print("\n🧪 Testing basic functionality...")
    
    # Import here to avoid global import issues
    from offline_sync_manager import (
        OfflineSyncManager, NetworkState, SyncMode, 
        create_offline_sync_manager, should_use_offline_mode
    )
    
    # Create temporary test directory
    temp_dir = tempfile.mkdtemp(prefix="ogresync_basic_test_")
    print(f"📁 Test directory: {temp_dir}")
    
    try:
        # Initialize git repo
        subprocess.run(['git', 'init'], cwd=temp_dir, check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=temp_dir, check=True)
        subprocess.run(['git', 'config', 'user.email', 'test@test.com'], cwd=temp_dir, check=True)
        
        # Create test config
        config = {
            "VAULT_PATH": temp_dir,
            "OBSIDIAN_PATH": "test-obsidian",
            "GITHUB_REMOTE_URL": "git@github.com:test/repo.git"
        }
        
        # Test manager creation
        manager = create_offline_sync_manager(temp_dir, config)
        print("✅ Manager created successfully")
        
        # Test network state detection
        network_state = manager.check_network_availability()
        print(f"✅ Network state detected: {network_state.value}")
        
        # Test session management
        session_id = manager.start_sync_session(NetworkState.OFFLINE)
        print(f"✅ Session started: {session_id}")
        
        # Test session ending
        test_commits = ["test commit"]
        needs_resolution = manager.end_sync_session(session_id, NetworkState.ONLINE, test_commits)
        print(f"✅ Session ended, needs resolution: {needs_resolution}")
        
        # Test sync mode determination
        mode = manager.determine_sync_mode(NetworkState.OFFLINE, NetworkState.ONLINE)
        expected = SyncMode.OFFLINE_TO_ONLINE
        if mode == expected:
            print(f"✅ Sync mode correct: {mode.value}")
        else:
            print(f"❌ Sync mode wrong: expected {expected.value}, got {mode.value}")
            return False
        
        # Test should_use_offline_mode function
        use_offline, reason = should_use_offline_mode(manager)
        print(f"✅ Offline mode decision: {use_offline} - {reason}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        # Clean up
        shutil.rmtree(temp_dir)
        print("🗑️ Cleaned up test directory")

def test_workflow_scenarios():
    """Test the three main workflow scenarios"""
    print("\n🧪 Testing workflow scenarios...")
    
    from offline_sync_manager import (
        OfflineSyncManager, NetworkState, SyncMode, 
        create_offline_sync_manager
    )
    
    # Create temporary test directory
    temp_dir = tempfile.mkdtemp(prefix="ogresync_workflow_test_")
    
    try:
        # Initialize git repo
        subprocess.run(['git', 'init'], cwd=temp_dir, check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=temp_dir, check=True)
        subprocess.run(['git', 'config', 'user.email', 'test@test.com'], cwd=temp_dir, check=True)
        
        config = {"VAULT_PATH": temp_dir, "OBSIDIAN_PATH": "test", "GITHUB_REMOTE_URL": "test"}
        manager = create_offline_sync_manager(temp_dir, config)
        
        # Scenario 1: Offline → Offline (Pure offline)
        print("   📱 Testing Scenario 1: Pure Offline")
        session1 = manager.start_sync_session(NetworkState.OFFLINE)
        needs_resolution1 = manager.end_sync_session(session1, NetworkState.OFFLINE, ["commit1"])
        if not needs_resolution1:
            print("   ✅ Scenario 1: Correct - no conflict resolution needed")
        else:
            print("   ❌ Scenario 1: Wrong - should not need conflict resolution")
            return False
        
        # Scenario 2: Online → Offline (Hybrid)
        print("   🌐📱 Testing Scenario 2: Hybrid Mode")
        session2 = manager.start_sync_session(NetworkState.ONLINE)
        needs_resolution2 = manager.end_sync_session(session2, NetworkState.OFFLINE, ["commit2"])
        if not needs_resolution2:
            print("   ✅ Scenario 2: Correct - no conflict resolution needed")
        else:
            print("   ❌ Scenario 2: Wrong - should not need conflict resolution")
            return False
        
        # Scenario 3: Offline → Online (Delayed sync)
        print("   📱🌐 Testing Scenario 3: Delayed Sync")
        session3 = manager.start_sync_session(NetworkState.OFFLINE)
        needs_resolution3 = manager.end_sync_session(session3, NetworkState.ONLINE, ["commit3"])
        if needs_resolution3:
            print("   ✅ Scenario 3: Correct - conflict resolution needed")
        else:
            print("   ❌ Scenario 3: Wrong - should need conflict resolution")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Workflow test failed: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir)

def test_state_persistence():
    """Test that offline state persists across manager instances"""
    print("\n🧪 Testing state persistence...")
    
    from offline_sync_manager import create_offline_sync_manager, NetworkState
    
    temp_dir = tempfile.mkdtemp(prefix="ogresync_persistence_test_")
    
    try:
        # Initialize git repo
        subprocess.run(['git', 'init'], cwd=temp_dir, check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=temp_dir, check=True)
        subprocess.run(['git', 'config', 'user.email', 'test@test.com'], cwd=temp_dir, check=True)
        
        config = {"VAULT_PATH": temp_dir, "OBSIDIAN_PATH": "test", "GITHUB_REMOTE_URL": "test"}
        
        # Create first manager and session
        manager1 = create_offline_sync_manager(temp_dir, config)
        session_id = manager1.start_sync_session(NetworkState.OFFLINE)
        session_count1 = len(manager1.offline_state.offline_sessions)
        
        # Create second manager (simulates app restart)
        manager2 = create_offline_sync_manager(temp_dir, config)
        session_count2 = len(manager2.offline_state.offline_sessions)
        
        if session_count1 == session_count2:
            print("✅ State persistence works correctly")
            return True
        else:
            print(f"❌ State persistence failed: {session_count1} != {session_count2}")
            return False
            
    except Exception as e:
        print(f"❌ Persistence test failed: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir)

def run_all_tests():
    """Run all basic tests"""
    print("🚀 Offline Sync Manager - Basic Test Suite")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("Basic Functionality", test_basic_functionality),
        ("Workflow Scenarios", test_workflow_scenarios),
        ("State Persistence", test_state_persistence)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"\n{status}: {test_name}")
        except Exception as e:
            results.append((test_name, False))
            print(f"\n💥 ERROR: {test_name} - {e}")
    
    # Summary
    print("\n📊 TEST SUMMARY")
    print("=" * 50)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {test_name}")
    
    print(f"\nResult: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Components are ready.")
        return True
    else:
        print("⚠️ Some tests failed. Check issues before integration.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    
    if success:
        print("\n✅ READY FOR INTEGRATION")
        print("Next steps:")
        print("1. Add offline components to your main Ogresync.py")
        print("2. Test with real Obsidian workflow")
        print("3. Verify all three scenarios work in practice")
    else:
        print("\n❌ FIX ISSUES BEFORE INTEGRATION")
    
    sys.exit(0 if success else 1)
