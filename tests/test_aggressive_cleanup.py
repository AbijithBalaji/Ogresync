#!/usr/bin/env python3
"""
Test the aggressive cleanup functionality directly
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import offline_sync_manager

# Test the offline sync manager with the actual vault path
vault_path = r"C:\Users\abiji\Test"
config_data = {"GITHUB_REMOTE_URL": "test"}

print("=== TESTING AGGRESSIVE CLEANUP ===")

try:
    manager = offline_sync_manager.OfflineSyncManager(vault_path, config_data)
    
    print("BEFORE cleanup:")
    summary = manager.get_session_summary()
    print(f"Summary: {summary}")
    print(f"Sessions count: {len(manager.offline_state.offline_sessions)}")
    
    for i, session in enumerate(manager.offline_state.offline_sessions):
        print(f"Session {i}: ID={session.session_id}, end_time={session.end_time}, requires_resolution={session.requires_conflict_resolution}")
    
    unpushed = manager.get_unpushed_commits()
    print(f"Unpushed commits: {len(unpushed)}")
    
    # Test aggressive cleanup
    print("\nRunning aggressive cleanup...")
    manager.cleanup_resolved_sessions(aggressive=True)
    
    print("\nAFTER cleanup:")
    summary = manager.get_session_summary()
    print(f"Summary: {summary}")
    print(f"Sessions count: {len(manager.offline_state.offline_sessions)}")
    
    for i, session in enumerate(manager.offline_state.offline_sessions):
        print(f"Session {i}: ID={session.session_id}, end_time={session.end_time}, requires_resolution={session.requires_conflict_resolution}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
