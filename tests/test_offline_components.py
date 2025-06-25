"""
Test Suite for Offline Sync Manager

This script tests all the offline sync components separately to ensure
they work correctly before integration with the main Ogresync system.

Test Coverage:
1. Network state detection and tracking
2. Session management and persistence
3. Sync mode determination
4. Conflict resolution triggering logic
5. All three offline workflow scenarios
6. Edge cases and error handling

Run this to verify offline components work correctly.
"""

import os
import sys
import tempfile
import shutil
import subprocess
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from offline_sync_manager import (
        OfflineSyncManager, NetworkState, SyncMode, OfflineSession, OfflineState,
        create_offline_sync_manager, should_use_offline_mode, get_offline_status_message
    )
    OFFLINE_MANAGER_AVAILABLE = True
    print("✅ Offline sync manager imported successfully")
except ImportError as e:
    print(f"❌ Failed to import offline sync manager: {e}")
    OFFLINE_MANAGER_AVAILABLE = False
    sys.exit(1)

class OfflineSyncTester:
    """Comprehensive tester for offline sync functionality"""
    
    def __init__(self):
        self.test_results = []
        self.temp_dir = None
        self.manager = None  # Will be set in setup_test_environment
        
    def setup_test_environment(self):
        """Create a temporary test environment"""
        print("\n🔧 Setting up test environment...")
        
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp(prefix="ogresync_test_")
        print(f"📁 Test directory: {self.temp_dir}")
        
        # Initialize git repository
        try:
            subprocess.run(['git', 'init'], cwd=self.temp_dir, check=True, capture_output=True)
            subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=self.temp_dir, check=True)
            subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=self.temp_dir, check=True)
            
            # Create initial file
            test_file = os.path.join(self.temp_dir, "test.md")
            with open(test_file, 'w') as f:
                f.write("# Test Vault\nInitial content")
            
            subprocess.run(['git', 'add', '.'], cwd=self.temp_dir, check=True)
            subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=self.temp_dir, check=True)
            
            print("✅ Git repository initialized")
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to initialize git repository: {e}")
            return False
        
        # Create test config
        test_config = {
            "VAULT_PATH": self.temp_dir,
            "OBSIDIAN_PATH": "test-obsidian",
            "GITHUB_REMOTE_URL": "git@github.com:test/repo.git",
            "SETUP_DONE": "1"
        }
        
        # Create offline sync manager
        self.manager = create_offline_sync_manager(self.temp_dir, test_config)
        print("✅ Offline sync manager created")
        
        return True
    
    def cleanup_test_environment(self):
        """Clean up test environment"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            print(f"🗑️ Cleaned up test directory: {self.temp_dir}")
    
    def run_test(self, test_name, test_func):
        """Run a single test and record results"""
        print(f"\n🧪 Running test: {test_name}")
        try:
            result = test_func()
            if result:
                print(f"✅ {test_name}: PASSED")
                self.test_results.append((test_name, "PASSED", None))
            else:
                print(f"❌ {test_name}: FAILED")
                self.test_results.append((test_name, "FAILED", "Test returned False"))
            return result
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
            self.test_results.append((test_name, "ERROR", str(e)))
            return False
    
    def test_network_detection(self):
        """Test network state detection"""
        print("   🌐 Testing network state detection...")
        
        if not self.manager:
            print("   ❌ Manager not initialized")
            return False
        
        # Test network check
        network_state = self.manager.check_network_availability()
        print(f"   📡 Current network state: {network_state.value}")
        
        # Verify state is recorded in history
        if len(self.manager.offline_state.network_state_history) > 0:
            latest_state = self.manager.offline_state.network_state_history[-1][1]
            if latest_state == network_state:
                print("   ✅ Network state history tracking works")
                return True
        
        print("   ❌ Network state history tracking failed")
        return False
    
    def test_session_management(self):
        """Test session creation, tracking, and persistence"""
        print("   📝 Testing session management...")
        
        # Start a session
        session_id = self.manager.start_sync_session(NetworkState.OFFLINE)
        print(f"   🆔 Started session: {session_id}")
        
        # Verify session exists
        session_found = any(s.session_id == session_id for s in self.manager.offline_state.offline_sessions)
        if not session_found:
            print("   ❌ Session not found in offline state")
            return False
        
        # End the session
        test_commits = ["test commit 1", "test commit 2"]
        needs_resolution = self.manager.end_sync_session(session_id, NetworkState.ONLINE, test_commits)
        
        # Verify session was updated
        session = next((s for s in self.manager.offline_state.offline_sessions if s.session_id == session_id), None)
        if not session:
            print("   ❌ Session disappeared after ending")
            return False
        
        if session.end_time is None:
            print("   ❌ Session end time not set")
            return False
        
        if session.local_commits != test_commits:
            print("   ❌ Local commits not saved correctly")
            return False
        
        if not needs_resolution:
            print("   ❌ Should require conflict resolution for OFFLINE_TO_ONLINE with commits")
            return False
        
        print("   ✅ Session management works correctly")
        return True
    
    def test_sync_mode_determination(self):
        """Test sync mode logic for all scenarios"""
        print("   🔄 Testing sync mode determination...")
        
        test_cases = [
            (NetworkState.ONLINE, NetworkState.ONLINE, SyncMode.ONLINE_TO_ONLINE),
            (NetworkState.ONLINE, NetworkState.OFFLINE, SyncMode.ONLINE_TO_OFFLINE),
            (NetworkState.OFFLINE, NetworkState.OFFLINE, SyncMode.OFFLINE_TO_OFFLINE),
            (NetworkState.OFFLINE, NetworkState.ONLINE, SyncMode.OFFLINE_TO_ONLINE),
        ]
        
        for start_state, end_state, expected_mode in test_cases:
            mode = self.manager.determine_sync_mode(start_state, end_state)
            if mode != expected_mode:
                print(f"   ❌ Wrong sync mode: {start_state.value}→{end_state.value} expected {expected_mode.value}, got {mode.value}")
                return False
            print(f"   ✅ {start_state.value}→{end_state.value} = {mode.value}")
        
        return True
    
    def test_conflict_resolution_logic(self):
        """Test conflict resolution trigger logic"""
        print("   ⚔️ Testing conflict resolution logic...")
        
        # Initially should not require conflict resolution
        if self.manager.should_trigger_conflict_resolution():
            print("   ❌ Should not require conflict resolution initially")
            return False
        
        # Create some unpushed commits
        try:
            test_file = os.path.join(self.temp_dir, "conflict_test.md")
            with open(test_file, 'w') as f:
                f.write("# Conflict Test\nTest content")
            
            subprocess.run(['git', 'add', '.'], cwd=self.temp_dir, check=True)
            subprocess.run(['git', 'commit', '-m', 'Test commit for conflict resolution'], cwd=self.temp_dir, check=True)
            
            # Now should require conflict resolution
            if not self.manager.should_trigger_conflict_resolution():
                print("   ❌ Should require conflict resolution with unpushed commits")
                return False
            
            print("   ✅ Conflict resolution logic works correctly")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Failed to create test commits: {e}")
            return False
    
    def test_offline_state_persistence(self):
        """Test that offline state persists across manager instances"""
        print("   💾 Testing offline state persistence...")
        
        # Create a session with the current manager
        session_id = self.manager.start_sync_session(NetworkState.OFFLINE)
        original_session_count = len(self.manager.offline_state.offline_sessions)
        
        # Create a new manager instance (simulates app restart)
        new_config = {
            "VAULT_PATH": self.temp_dir,
            "OBSIDIAN_PATH": "test-obsidian",
            "GITHUB_REMOTE_URL": "git@github.com:test/repo.git"
        }
        new_manager = create_offline_sync_manager(self.temp_dir, new_config)
        
        # Verify the session persisted
        new_session_count = len(new_manager.offline_state.offline_sessions)
        if new_session_count != original_session_count:
            print(f"   ❌ Session count mismatch: original={original_session_count}, new={new_session_count}")
            return False
        
        session_found = any(s.session_id == session_id for s in new_manager.offline_state.offline_sessions)
        if not session_found:
            print("   ❌ Session not found in new manager instance")
            return False
        
        print("   ✅ Offline state persistence works correctly")
        return True
    
    def test_workflow_scenario_1(self):
        """Test Scenario 1: No internet start + No internet end (Pure offline)"""
        print("   📱 Testing Workflow Scenario 1: Pure Offline Mode")
        
        # Simulate network being offline
        original_check = self.manager.check_network_availability
        self.manager.check_network_availability = lambda: NetworkState.OFFLINE
        
        try:
            # Check if offline mode is selected
            use_offline, reason = should_use_offline_mode(self.manager)
            if not use_offline:
                print(f"   ❌ Should use offline mode when network is offline. Reason: {reason}")
                return False
            
            # Start offline session
            session_id = self.manager.start_sync_session(NetworkState.OFFLINE)
            
            # Simulate some local changes
            test_commits = ["Offline edit 1", "Offline edit 2"]
            
            # End session (still offline)
            needs_resolution = self.manager.end_sync_session(session_id, NetworkState.OFFLINE, test_commits)
            
            # Should NOT require conflict resolution for pure offline
            if needs_resolution:
                print("   ❌ Pure offline mode should not require conflict resolution")
                return False
            
            print("   ✅ Scenario 1 (Pure Offline) works correctly")
            return True
            
        finally:
            # Restore original network check
            self.manager.check_network_availability = original_check
    
    def test_workflow_scenario_2(self):
        """Test Scenario 2: Internet start + No internet end (Hybrid mode)"""
        print("   🌐📱 Testing Workflow Scenario 2: Hybrid Mode (Online→Offline)")
        
        # Start with online
        session_id = self.manager.start_sync_session(NetworkState.ONLINE)
        
        # Simulate some local changes
        test_commits = ["Hybrid edit 1"]
        
        # End with offline
        needs_resolution = self.manager.end_sync_session(session_id, NetworkState.OFFLINE, test_commits)
        
        # Should NOT require conflict resolution for ONLINE_TO_OFFLINE
        if needs_resolution:
            print("   ❌ Hybrid mode (online→offline) should not require conflict resolution")
            return False
        
        # Verify sync mode
        session = next(s for s in self.manager.offline_state.offline_sessions if s.session_id == session_id)
        if session.sync_mode != SyncMode.ONLINE_TO_OFFLINE:
            print(f"   ❌ Wrong sync mode: expected {SyncMode.ONLINE_TO_OFFLINE.value}, got {session.sync_mode.value}")
            return False
        
        print("   ✅ Scenario 2 (Hybrid Mode) works correctly")
        return True
    
    def test_workflow_scenario_3(self):
        """Test Scenario 3: No internet start + Internet end (Delayed sync)"""
        print("   📱🌐 Testing Workflow Scenario 3: Delayed Sync (Offline→Online)")
        
        # Start with offline
        session_id = self.manager.start_sync_session(NetworkState.OFFLINE)
        
        # Simulate local changes
        test_commits = ["Delayed sync edit 1", "Delayed sync edit 2"]
        
        # End with online
        needs_resolution = self.manager.end_sync_session(session_id, NetworkState.ONLINE, test_commits)
        
        # SHOULD require conflict resolution for OFFLINE_TO_ONLINE with commits
        if not needs_resolution:
            print("   ❌ Delayed sync mode should require conflict resolution")
            return False
        
        # Verify sync mode
        session = next(s for s in self.manager.offline_state.offline_sessions if s.session_id == session_id)
        if session.sync_mode != SyncMode.OFFLINE_TO_ONLINE:
            print(f"   ❌ Wrong sync mode: expected {SyncMode.OFFLINE_TO_ONLINE.value}, got {session.sync_mode.value}")
            return False
        
        print("   ✅ Scenario 3 (Delayed Sync) works correctly")
        return True
    
    def test_session_summary(self):
        """Test session summary functionality"""
        print("   📊 Testing session summary...")
        
        summary = self.manager.get_session_summary()
        
        # Verify summary contains expected keys
        expected_keys = ['total_sessions', 'offline_sessions', 'unpushed_commits', 'last_sync', 'requires_resolution']
        for key in expected_keys:
            if key not in summary:
                print(f"   ❌ Missing key in summary: {key}")
                return False
        
        # Verify summary values are reasonable
        if summary['total_sessions'] < 0:
            print(f"   ❌ Invalid total_sessions: {summary['total_sessions']}")
            return False
        
        print(f"   📈 Summary: {summary}")
        print("   ✅ Session summary works correctly")
        return True
    
    def test_status_messages(self):
        """Test user-friendly status messages"""
        print("   💬 Testing status messages...")
        
        status_msg = get_offline_status_message(self.manager)
        if not isinstance(status_msg, str) or len(status_msg) == 0:
            print("   ❌ Invalid status message")
            return False
        
        print(f"   📝 Status message: {status_msg}")
        print("   ✅ Status messages work correctly")
        return True
    
    def run_all_tests(self):
        """Run all tests and report results"""
        print("🚀 Starting Offline Sync Manager Test Suite")
        print("=" * 60)
        
        if not self.setup_test_environment():
            print("❌ Failed to set up test environment")
            return False
        
        try:
            # Core functionality tests
            self.run_test("Network Detection", self.test_network_detection)
            self.run_test("Session Management", self.test_session_management)
            self.run_test("Sync Mode Determination", self.test_sync_mode_determination)
            self.run_test("Conflict Resolution Logic", self.test_conflict_resolution_logic)
            self.run_test("Offline State Persistence", self.test_offline_state_persistence)
            
            # Workflow scenario tests
            self.run_test("Workflow Scenario 1 (Pure Offline)", self.test_workflow_scenario_1)
            self.run_test("Workflow Scenario 2 (Hybrid Mode)", self.test_workflow_scenario_2)
            self.run_test("Workflow Scenario 3 (Delayed Sync)", self.test_workflow_scenario_3)
            
            # User interface tests
            self.run_test("Session Summary", self.test_session_summary)
            self.run_test("Status Messages", self.test_status_messages)
            
        finally:
            self.cleanup_test_environment()
        
        # Report results
        print("\n📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        passed = len([r for r in self.test_results if r[1] == "PASSED"])
        failed = len([r for r in self.test_results if r[1] == "FAILED"])
        errors = len([r for r in self.test_results if r[1] == "ERROR"])
        total = len(self.test_results)
        
        print(f"📈 Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"💥 Errors: {errors}")
        
        if failed > 0 or errors > 0:
            print("\n❌ FAILED TESTS:")
            for test_name, status, error in self.test_results:
                if status in ["FAILED", "ERROR"]:
                    print(f"   • {test_name}: {status}")
                    if error:
                        print(f"     Error: {error}")
        
        success_rate = (passed / total) * 100 if total > 0 else 0
        print(f"\n🎯 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 90:
            print("🎉 Excellent! Components are ready for integration.")
        elif success_rate >= 70:
            print("⚠️ Good, but some issues need attention before integration.")
        else:
            print("❌ Significant issues found. Fix before integration.")
        
        return success_rate >= 90


def main():
    """Main test execution"""
    if not OFFLINE_MANAGER_AVAILABLE:
        print("❌ Cannot run tests - offline sync manager not available")
        return False
    
    tester = OfflineSyncTester()
    return tester.run_all_tests()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
