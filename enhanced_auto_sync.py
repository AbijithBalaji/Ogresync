"""
Enhanced Auto-Sync with Offline Support for Ogresync

This module enhances the existing auto_sync function with comprehensive
offline capabilities while preserving all existing online functionality.

Key Features:
- Seamless offline/online mode detection and switching
- Smart conflict resolution triggering for offline-to-online transitions
- Session tracking and state management
- Complete backward compatibility with existing workflow

Integration approach:
- Wraps existing auto_sync function without modifying core logic
- Adds offline state detection and management
- Triggers conflict resolution only when needed
- Maintains all existing edge case handling

Author: Ogresync Development Team
Date: June 2025
"""

import subprocess
import threading
import time
from datetime import datetime
from typing import Optional, Callable, Any

# Import packaging utilities for safe subprocess calls
try:
    import packaging_utils
    PACKAGING_UTILS_AVAILABLE = True
except ImportError:
    PACKAGING_UTILS_AVAILABLE = False

# Import our new offline manager
try:
    from offline_sync_manager import (
        OfflineSyncManager, 
        NetworkState, 
        SyncMode,
        create_offline_sync_manager,
        should_use_offline_mode,
        get_offline_status_message
    )
    OFFLINE_MANAGER_AVAILABLE = True
except ImportError:
    OfflineSyncManager = None
    NetworkState = None
    SyncMode = None
    OFFLINE_MANAGER_AVAILABLE = False

# Import existing conflict resolution
try:
    import Stage1_conflict_resolution as conflict_resolution
    CONFLICT_RESOLUTION_AVAILABLE = True
except ImportError:
    conflict_resolution = None
    CONFLICT_RESOLUTION_AVAILABLE = False


def create_enhanced_auto_sync(original_auto_sync_func: Callable, 
                            vault_path: str, 
                            config_data: dict,
                            safe_update_log_func: Callable,
                            root_window: Optional[Any] = None,
                            is_obsidian_running_func: Optional[Callable] = None,
                            run_command_func: Optional[Callable] = None) -> Callable:
    """
    Create an enhanced auto_sync function that adds offline support
    
    Args:
        original_auto_sync_func: The existing auto_sync function
        vault_path: Path to the Obsidian vault
        config_data: Configuration dictionary
        safe_update_log_func: Logging function
        root_window: Tkinter root window for UI integration
        is_obsidian_running_func: Function to check if Obsidian is running
        run_command_func: Function to run shell commands
        
    Returns:
        Enhanced auto_sync function with offline support
    """
    
    def enhanced_auto_sync(use_threading=True):
        """Enhanced auto_sync with offline capabilities"""
        
        if not OFFLINE_MANAGER_AVAILABLE:
            # Fallback to original function if offline manager not available
            safe_update_log_func("⚠️ Offline manager not available, using standard sync mode")
            return original_auto_sync_func(use_threading)
        
        # Create offline sync manager
        manager = create_offline_sync_manager(vault_path, config_data)
        
        # Check network and offline state
        network_state = manager.check_network_availability()
        use_offline, reason = should_use_offline_mode(manager)
        
        safe_update_log_func(f"🌐 Network Status: {network_state.value}")
        safe_update_log_func(f"📊 Sync Mode: {'Offline' if use_offline else 'Online'} - {reason}")
        
        # Display offline session summary if relevant
        session_summary = manager.get_session_summary()
        if session_summary['offline_sessions'] > 0 or session_summary['unpushed_commits'] > 0:
            status_msg = get_offline_status_message(manager)
            safe_update_log_func(f"📋 {status_msg}")
        
        # Check if conflict resolution is needed BEFORE proceeding
        if manager.should_trigger_conflict_resolution() and NetworkState and network_state == NetworkState.ONLINE:
            safe_update_log_func("🔧 Previous offline changes detected - activating conflict resolution...")
            
            if CONFLICT_RESOLUTION_AVAILABLE and conflict_resolution:
                try:
                    # Create backup before conflict resolution
                    session_backup_id = None
                    if manager.backup_manager:
                        try:
                            from backup_manager import BackupReason
                            session_backup_id = manager.backup_manager.create_backup(
                                BackupReason.CONFLICT_RESOLUTION,
                                "Pre-conflict resolution backup for offline changes"
                            )
                            if session_backup_id:
                                safe_update_log_func(f"✅ Safety backup created: {session_backup_id}")
                        except ImportError:
                            safe_update_log_func("⚠️ Backup system not available")
                    
                    # Use existing conflict resolution system
                    resolver = conflict_resolution.ConflictResolver(vault_path, root_window)
                    remote_url = config_data.get("GITHUB_REMOTE_URL", "")
                    
                    safe_update_log_func("📋 Starting conflict resolution for offline changes...")
                    resolution_result = resolver.resolve_initial_setup_conflicts(remote_url)
                    
                    if resolution_result.success:
                        safe_update_log_func("✅ Offline changes resolved successfully!")
                        
                        # Mark all sessions as resolved
                        for session in manager.offline_state.offline_sessions:
                            if session.requires_conflict_resolution:
                                manager.mark_session_resolved(session.session_id)
                        
                        # Update state
                        manager.offline_state.last_successful_sync = datetime.now()
                        manager.offline_state.has_unpushed_commits = False
                        manager._save_offline_state()
                        
                        safe_update_log_func("🎉 All offline sessions synchronized successfully!")
                        
                        # Proceed with normal online sync
                        return original_auto_sync_func(use_threading)
                        
                    else:
                        if "cancelled by user" in resolution_result.message.lower():
                            safe_update_log_func("❌ Conflict resolution cancelled by user")
                            safe_update_log_func("📝 Your offline changes remain safe and can be resolved later")
                        else:
                            safe_update_log_func(f"❌ Conflict resolution failed: {resolution_result.message}")
                            if session_backup_id:
                                safe_update_log_func(f"📝 Your changes are safe in backup: {session_backup_id}")
                        
                        # Don't proceed with sync if conflicts weren't resolved
                        return
                        
                except Exception as e:
                    safe_update_log_func(f"❌ Error in conflict resolution: {e}")
                    safe_update_log_func("📝 Your offline changes remain safe and can be resolved manually")
                    return
            else:
                safe_update_log_func("❌ Conflict resolution system not available")
                safe_update_log_func("📝 Please resolve conflicts manually before proceeding")
                return
        
        # Proceed based on determined mode
        if use_offline:
            # Start offline session and run offline sync
            session_id = manager.start_sync_session(network_state)
            safe_update_log_func(f"🔄 Starting offline session: {session_id}")
            
            return run_enhanced_offline_sync(
                vault_path, config_data, manager, session_id, 
                safe_update_log_func, is_obsidian_running_func, run_command_func
            )
        else:
            # Run original online sync with session tracking
            session_id = manager.start_sync_session(network_state)
            safe_update_log_func(f"🔄 Starting online session: {session_id}")
            
            try:
                # Run original auto_sync
                result = original_auto_sync_func(use_threading)
                
                # End session successfully
                if NetworkState:
                    manager.end_sync_session(session_id, NetworkState.ONLINE, [])
                manager.offline_state.last_successful_sync = datetime.now()
                manager._save_offline_state()
                
                return result
                
            except Exception as e:
                # End session with error
                if NetworkState:
                    manager.end_sync_session(session_id, NetworkState.ONLINE, [])
                safe_update_log_func(f"❌ Online sync session failed: {e}")
                raise
    
    return enhanced_auto_sync


def run_enhanced_offline_sync(vault_path: str, 
                            config_data: dict,
                            manager,  # OfflineSyncManager type
                            session_id: str,
                            safe_update_log_func: Callable,
                            is_obsidian_running_func: Optional[Callable] = None,
                            run_command_func: Optional[Callable] = None):
    """
    Enhanced offline sync that integrates with existing Ogresync functions
    
    This function provides a streamlined offline experience while maintaining
    integration with existing utility functions.
    """
    from datetime import datetime
    
    safe_update_log_func("📱 Running in offline mode - no remote synchronization")
    safe_update_log_func("💡 All changes will be saved locally and synced when online")
    
    obsidian_path = config_data.get("OBSIDIAN_PATH", "")
    if not obsidian_path:
        safe_update_log_func("❌ Obsidian path not configured")
        return
    
    # Step 1: Open Obsidian for editing
    safe_update_log_func("🚀 Launching Obsidian in offline mode...")
    
    try:
        # Use existing open_obsidian function if available, or implement simple launch
        import platform
        
        if platform.system() == "Windows":
            if PACKAGING_UTILS_AVAILABLE:
                # For Popen, we need to use subprocess directly but with safe handling
                import subprocess
                subprocess.Popen([obsidian_path], cwd=vault_path)
            else:
                import subprocess
                subprocess.Popen([obsidian_path], cwd=vault_path)
        elif platform.system() == "Darwin":  # macOS
            if PACKAGING_UTILS_AVAILABLE:
                import subprocess
                subprocess.Popen(["open", obsidian_path], cwd=vault_path)
            else:
                import subprocess
                subprocess.Popen(["open", obsidian_path], cwd=vault_path)
        else:  # Linux
            if PACKAGING_UTILS_AVAILABLE:
                import subprocess
                subprocess.Popen([obsidian_path], cwd=vault_path)
            else:
                import subprocess
                subprocess.Popen([obsidian_path], cwd=vault_path)
        
        safe_update_log_func("✅ Obsidian launched successfully")
        safe_update_log_func("📝 Make your edits and close Obsidian when finished")
        
        # Give Obsidian time to start
        time.sleep(2.0)
        
    except Exception as e:
        safe_update_log_func(f"❌ Error launching Obsidian: {e}")
        return
    
    # Step 2: Wait for Obsidian to close
    safe_update_log_func("⏳ Waiting for Obsidian to close...")
    
    if is_obsidian_running_func:
        # Use existing function if available
        check_count = 0
        while is_obsidian_running_func():
            time.sleep(0.5)
            check_count += 1
            # Update every 10 seconds
            if check_count % 20 == 0:
                safe_update_log_func("⏳ Still waiting for Obsidian to close...")
    else:
        # Simple wait with user notification
        safe_update_log_func("ℹ️ Please close Obsidian manually when finished editing")
        input("Press Enter after closing Obsidian to continue...")
    
    safe_update_log_func("✅ Obsidian closed, processing changes...")
    
    # Step 3: Commit changes locally
    try:
        local_commits = []
        
        if run_command_func:
            # Use existing run_command function
            add_out, add_err, add_rc = run_command_func("git add -A", cwd=vault_path)
            
            if add_rc == 0:
                commit_msg = f"Offline sync commit - {session_id} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                commit_out, commit_err, commit_rc = run_command_func(f'git commit -m "{commit_msg}"', cwd=vault_path)
                
                if commit_rc == 0:
                    safe_update_log_func("✅ Local changes committed successfully")
                    local_commits = [commit_msg]
                elif "nothing to commit" in (commit_out + commit_err).lower():
                    safe_update_log_func("ℹ️ No changes detected during this session")
                else:
                    safe_update_log_func(f"⚠️ Commit issue: {commit_err}")
            else:
                safe_update_log_func(f"⚠️ Error staging files: {add_err}")
        else:
            # Fallback to subprocess with safe handling
            if PACKAGING_UTILS_AVAILABLE:
                # Add all changes
                packaging_utils.run_subprocess_safe(['git', 'add', '-A'], cwd=vault_path, check=True)
                
                # Commit with offline indicator
                commit_msg = f"Offline sync commit - {session_id} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                result = packaging_utils.run_subprocess_safe(['git', 'commit', '-m', commit_msg], 
                                      cwd=vault_path, capture_output=True, text=True)
            else:
                import subprocess
                
                # Add all changes
                subprocess.run(['git', 'add', '-A'], cwd=vault_path, check=True)
                
                # Commit with offline indicator
                commit_msg = f"Offline sync commit - {session_id} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                result = subprocess.run(['git', 'commit', '-m', commit_msg], 
                                      cwd=vault_path, capture_output=True, text=True)
            
            if result.returncode == 0:
                safe_update_log_func("✅ Local changes committed successfully")
                local_commits = [commit_msg]
            elif "nothing to commit" in result.stdout:
                safe_update_log_func("ℹ️ No changes detected during this session")
            else:
                safe_update_log_func(f"⚠️ Commit warning: {result.stderr}")
        
        # Step 4: End session and check for conflict resolution needs
        network_end = manager.check_network_availability()
        needs_resolution = manager.end_sync_session(session_id, network_end, local_commits)
        
        if NetworkState and network_end == NetworkState.ONLINE and needs_resolution:
            safe_update_log_func("🌐 Network connection detected!")
            safe_update_log_func("🔧 Conflict resolution will be available on next sync")
        elif needs_resolution:
            safe_update_log_func("📋 Session completed - changes saved locally")
            safe_update_log_func("🔄 Sync with remote when network is available")
        else:
            safe_update_log_func("✅ Offline session completed successfully")
        
        # Step 5: Provide user feedback about offline session
        session_summary = manager.get_session_summary()
        if session_summary['unpushed_commits'] > 0:
            safe_update_log_func(f"📊 Total unpushed commits: {session_summary['unpushed_commits']}")
            
    except Exception as e:
        safe_update_log_func(f"❌ Error processing offline changes: {e}")
        # Still end the session to maintain state consistency
        network_end = manager.check_network_availability()
        manager.end_sync_session(session_id, network_end, [])


# =============================================================================
# INTEGRATION HELPER FUNCTIONS
# =============================================================================

def enhance_existing_auto_sync(original_module, vault_path: str, config_data: dict, 
                              safe_update_log_func: Callable, root_window: Optional[Any] = None) -> Callable:
    """
    Helper function to enhance an existing auto_sync function with offline support
    
    Args:
        original_module: Module containing the original auto_sync function
        vault_path: Path to vault
        config_data: Configuration dictionary
        safe_update_log_func: Logging function
        root_window: UI root window
        
    Returns:
        Enhanced auto_sync function
    """
    # Get references to existing functions
    original_auto_sync = getattr(original_module, 'auto_sync', None)
    is_obsidian_running = getattr(original_module, 'is_obsidian_running', None)
    run_command = getattr(original_module, 'run_command', None)
    
    if not original_auto_sync:
        raise ValueError("Original auto_sync function not found in module")
    
    # Create enhanced version
    enhanced_func = create_enhanced_auto_sync(
        original_auto_sync,
        vault_path,
        config_data,
        safe_update_log_func,
        root_window,
        is_obsidian_running,
        run_command
    )
    
    return enhanced_func


def get_offline_integration_status() -> dict:
    """Get status of offline integration components"""
    return {
        'offline_manager_available': OFFLINE_MANAGER_AVAILABLE,
        'conflict_resolution_available': CONFLICT_RESOLUTION_AVAILABLE,
        'integration_ready': OFFLINE_MANAGER_AVAILABLE and CONFLICT_RESOLUTION_AVAILABLE
    }


if __name__ == "__main__":
    print("Testing Enhanced Auto-Sync Integration...")
    
    status = get_offline_integration_status()
    print(f"Integration Status: {status}")
    
    if status['integration_ready']:
        print("✅ All components available for offline integration")
    else:
        print("⚠️ Some components missing - check imports")
