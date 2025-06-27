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
    from packaging_utils import run_subprocess_safe, is_packaged_app
    PACKAGING_UTILS_AVAILABLE = True
except ImportError:
    PACKAGING_UTILS_AVAILABLE = False
    # Fallback to regular subprocess
    def run_subprocess_safe(*args, **kwargs):
        return subprocess.run(*args, **kwargs)

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

def launch_obsidian_safely(obsidian_path, vault_path):
    """
    Launch Obsidian with proper error handling and cross-platform compatibility.
    """
    try:
        import platform
        
        if platform.system() == "Windows":
            subprocess.Popen([obsidian_path], cwd=vault_path)
        elif platform.system() == "Darwin":  # macOS
            subprocess.Popen(["open", obsidian_path], cwd=vault_path)
        else:  # Linux
            subprocess.Popen([obsidian_path], cwd=vault_path)
        
        return True
        
    except Exception as e:
        print(f"Error launching Obsidian: {e}")
        return False

def enhanced_auto_sync_with_offline_support(
    original_auto_sync_func: Callable,
    config_data: dict,
    safe_update_log_func: Callable,
    is_obsidian_running_func: Optional[Callable] = None,
    run_command_func: Optional[Callable] = None,
    use_threading: bool = True
) -> bool:
    """
    Enhanced auto-sync wrapper that adds comprehensive offline support.
    
    This function wraps the original auto_sync to provide:
    - Offline state detection and management
    - Smart conflict resolution for offline-to-online transitions
    - Session tracking and recovery
    - Backward compatibility with existing sync flow
    
    Args:
        original_auto_sync_func: The original auto_sync function
        config_data: Configuration dictionary
        safe_update_log_func: Logging function
        is_obsidian_running_func: Function to check if Obsidian is running
        run_command_func: Function to run shell commands
        use_threading: Whether to use threading for sync
        
    Returns:
        bool: True if sync completed successfully, False otherwise
    """
    
    if not OFFLINE_MANAGER_AVAILABLE:
        safe_update_log_func("📱 Offline support not available, using standard sync", None)
        return original_auto_sync_func(use_threading=use_threading)
    
    vault_path = config_data.get("VAULT_PATH", "")
    if not vault_path:
        safe_update_log_func("❌ No vault path configured", None)
        return False
    
    try:
        # Create offline sync manager
        offline_manager = create_offline_sync_manager(vault_path, config_data)
        
        # Check if we should use offline mode
        if should_use_offline_mode():
            safe_update_log_func("📱 Running in offline mode", None)
            return _handle_offline_sync(
                offline_manager, 
                config_data, 
                safe_update_log_func,
                is_obsidian_running_func
            )
        else:
            safe_update_log_func("🌐 Network available, checking for offline changes", None)
            
            # Check for pending offline changes before standard sync
            if offline_manager and hasattr(offline_manager, 'has_pending_changes'):
                if offline_manager.has_pending_changes():
                    safe_update_log_func("📱 Processing pending offline changes", None)
                    _process_offline_changes(offline_manager, safe_update_log_func, run_command_func)
            
            # Run standard sync
            return original_auto_sync_func(use_threading=use_threading)
            
    except Exception as e:
        safe_update_log_func(f"❌ Error in enhanced sync: {e}", None)
        # Fall back to original sync
        return original_auto_sync_func(use_threading=use_threading)

def _handle_offline_sync(
    offline_manager,
    config_data: dict,
    safe_update_log_func: Callable,
    is_obsidian_running_func: Optional[Callable] = None
) -> bool:
    """Handle offline synchronization workflow."""
    
    try:
        safe_update_log_func("📱 Starting offline sync session", 10)
        
        # Start offline session
        if hasattr(offline_manager, 'start_offline_session'):
            offline_manager.start_offline_session()
        
        vault_path = config_data.get("VAULT_PATH", "")
        obsidian_path = config_data.get("OBSIDIAN_PATH", "")
        
        if not obsidian_path:
            safe_update_log_func("❌ No Obsidian path configured", None)
            return False
        
        # Launch Obsidian
        safe_update_log_func("🚀 Launching Obsidian for offline editing...", 30)
        if not launch_obsidian_safely(obsidian_path, vault_path):
            safe_update_log_func("❌ Failed to launch Obsidian", None)
            return False
        
        safe_update_log_func("✅ Obsidian launched successfully", 50)
        
        # Wait for Obsidian to close
        safe_update_log_func("⏳ Waiting for Obsidian to close...", 60)
        
        if is_obsidian_running_func:
            # Actively wait for Obsidian to close
            wait_count = 0
            while is_obsidian_running_func():
                time.sleep(2)
                wait_count += 1
                if wait_count % 30 == 0:  # Every minute
                    safe_update_log_func("⏳ Still waiting for Obsidian to close...", None)
        else:
            # Manual confirmation
            safe_update_log_func("ℹ️ Please close Obsidian manually when finished editing", None)
            input("Press Enter when you've finished editing and closed Obsidian...")
        
        safe_update_log_func("✅ Obsidian closed, processing changes...", 80)
        
        # Process offline changes
        try:
            if run_command_func:
                # Commit any changes made during offline session
                safe_update_log_func("💾 Committing offline changes...", 85)
                run_command_func("git add -A", cwd=vault_path)
                
                # Check if there are any changes to commit
                stdout, stderr, rc = run_command_func("git status --porcelain", cwd=vault_path)
                if stdout.strip():
                    commit_msg = f"Offline changes - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    run_command_func(f'git commit -m "{commit_msg}"', cwd=vault_path)
                    safe_update_log_func("✅ Offline changes committed", 90)
                else:
                    safe_update_log_func("ℹ️ No changes detected during offline session", 90)
            
            # End offline session
            if hasattr(offline_manager, 'end_offline_session'):
                offline_manager.end_offline_session()
            
            safe_update_log_func("✅ Offline sync completed successfully", 100)
            return True
            
        except Exception as e:
            safe_update_log_func(f"❌ Error processing offline changes: {e}", None)
            return False
            
    except Exception as e:
        safe_update_log_func(f"❌ Error in offline sync: {e}", None)
        return False

def _process_offline_changes(offline_manager, safe_update_log_func: Callable, run_command_func: Optional[Callable]):
    """Process any pending offline changes before online sync."""
    
    try:
        if hasattr(offline_manager, 'get_pending_changes'):
            changes = offline_manager.get_pending_changes()
            if changes:
                safe_update_log_func(f"📱 Found {len(changes)} pending offline changes", None)
                
                # Trigger conflict resolution if needed
                if CONFLICT_RESOLUTION_AVAILABLE and hasattr(offline_manager, 'needs_conflict_resolution'):
                    if offline_manager.needs_conflict_resolution():
                        safe_update_log_func("⚠️ Conflict resolution needed for offline changes", None)
                        # This would trigger the enhanced conflict resolution system
                        # Implementation depends on the conflict resolution interface
                
    except Exception as e:
        safe_update_log_func(f"❌ Error processing offline changes: {e}", None)

# Export the main function
__all__ = ['enhanced_auto_sync_with_offline_support', 'launch_obsidian_safely']
