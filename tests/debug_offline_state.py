#!/usr/bin/env python3
"""
Debug script to check the offline sync manager state
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import offline_sync_manager

# Test the offline sync manager with the actual vault path
vault_path = r"C:\Users\abiji\Test"
config_data = {"GITHUB_REMOTE_URL": "test"}

print("=== DEBUG: Offline Sync Manager State ===")

try:
    manager = offline_sync_manager.OfflineSyncManager(vault_path, config_data)
    summary = manager.get_session_summary()
    
    print(f"Summary: {summary}")
    print(f"Offline state file path: {manager.offline_state_file}")
    print(f"Offline state exists: {os.path.exists(manager.offline_state_file)}")
    print(f"Offline sessions count: {len(manager.offline_state.offline_sessions)}")
    print(f"Offline sessions: {manager.offline_state.offline_sessions}")
    
    # Print each session in detail
    for i, session in enumerate(manager.offline_state.offline_sessions):
        print(f"Session {i}: {session}")
        print(f"  Session ID: {session.session_id}")
        print(f"  Sync mode: {session.sync_mode}")
        print(f"  Start time: {session.start_time}")
        print(f"  End time: {session.end_time}")
        print(f"  Requires conflict resolution: {session.requires_conflict_resolution}")
    
    print(f"Has unpushed commits: {manager.offline_state.has_unpushed_commits}")
    
    unpushed = manager.get_unpushed_commits()
    print(f"Actual unpushed commits: {len(unpushed)}")
    for commit in unpushed:
        print(f"  Unpushed: {commit}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
