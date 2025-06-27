"""
Offline Sync Management System for Ogresync

This module provides comprehensive offline-friendly synchronization capabilities
that enhance the existing online workflow without disrupting it.

Key Features:
- Smart network state detection and tracking
- Offline session management with safe local commits
- Intelligent conflict resolution trigger logic
- Enhanced user control and transparency
- Seamless transition between offline/online modes

Author: Ogresync Development Team  
Date: June 2025
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum

# Import packaging utilities for safe subprocess calls
try:
    import packaging_utils
    PACKAGING_UTILS_AVAILABLE = True
    run_subprocess_safe = packaging_utils.run_subprocess_safe
except ImportError:
    PACKAGING_UTILS_AVAILABLE = False
    # Fallback to regular subprocess with safe handling for packaged apps
    def run_subprocess_safe(*args, **kwargs):
        import subprocess
        import sys
        
        # Check if we're running as a packaged executable
        is_packaged = getattr(sys, 'frozen', False)
        
        # On Windows, hide console windows when packaged
        if sys.platform == "win32" and is_packaged:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            kwargs['startupinfo'] = startupinfo
        
        return subprocess.run(*args, **kwargs)

# Import existing modules
try:
    from backup_manager import OgresyncBackupManager, BackupReason
    BACKUP_MANAGER_AVAILABLE = True
except ImportError:
    OgresyncBackupManager = None
    BackupReason = None
    BACKUP_MANAGER_AVAILABLE = False

try:
    import Stage1_conflict_resolution as conflict_resolution
    CONFLICT_RESOLUTION_AVAILABLE = True
except ImportError:
    conflict_resolution = None
    CONFLICT_RESOLUTION_AVAILABLE = False


# =============================================================================
# OFFLINE SYNC DATA STRUCTURES
# =============================================================================

class NetworkState(Enum):
    """Network connectivity states"""
    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"

class SyncMode(Enum):
    """Synchronization modes"""
    ONLINE_TO_ONLINE = "online_to_online"       # Current default behavior
    OFFLINE_TO_OFFLINE = "offline_to_offline"   # Pure offline mode
    OFFLINE_TO_ONLINE = "offline_to_online"     # Delayed sync mode
    ONLINE_TO_OFFLINE = "online_to_offline"     # Hybrid mode

@dataclass
class OfflineSession:
    """Information about an offline editing session"""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime]
    network_start: NetworkState
    network_end: Optional[NetworkState]
    local_commits: List[str]
    sync_mode: SyncMode
    requires_conflict_resolution: bool = False
    backup_id: Optional[str] = None

@dataclass
class OfflineState:
    """Current offline synchronization state"""
    has_unpushed_commits: bool
    offline_sessions: List[OfflineSession]
    last_successful_sync: Optional[datetime]
    pending_sync_operations: List[str]
    network_state_history: List[Tuple[datetime, NetworkState]]


# =============================================================================
# CORE OFFLINE SYNC MANAGER
# =============================================================================

class OfflineSyncManager:
    """Manages offline-aware synchronization for Ogresync"""
    
    def __init__(self, vault_path: str, config_data: Dict[str, str]):
        self.vault_path = vault_path
        self.config_data = config_data
        self.offline_state_file = os.path.join(vault_path, ".ogresync-offline-state.json")
        self.network_check_timeout = 5  # seconds
        
        # Load or initialize offline state
        self.offline_state = self._load_offline_state()
        
        # Set up backup manager if available
        self.backup_manager = None
        if BACKUP_MANAGER_AVAILABLE and OgresyncBackupManager:
            self.backup_manager = OgresyncBackupManager(vault_path)
    
    def _load_offline_state(self) -> OfflineState:
        """Load offline state from disk or create new"""
        if os.path.exists(self.offline_state_file):
            try:
                with open(self.offline_state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Convert datetime strings back to datetime objects
                sessions = []
                for session_data in data.get('offline_sessions', []):
                    session = OfflineSession(
                        session_id=session_data['session_id'],
                        start_time=datetime.fromisoformat(session_data['start_time']),
                        end_time=datetime.fromisoformat(session_data['end_time']) if session_data.get('end_time') else None,
                        network_start=NetworkState(session_data['network_start']),
                        network_end=NetworkState(session_data['network_end']) if session_data.get('network_end') else None,
                        local_commits=session_data.get('local_commits', []),
                        sync_mode=SyncMode(session_data['sync_mode']),
                        requires_conflict_resolution=session_data.get('requires_conflict_resolution', False),
                        backup_id=session_data.get('backup_id')
                    )
                    sessions.append(session)
                
                network_history = []
                for hist_data in data.get('network_state_history', []):
                    network_history.append((
                        datetime.fromisoformat(hist_data[0]),
                        NetworkState(hist_data[1])
                    ))
                
                return OfflineState(
                    has_unpushed_commits=data.get('has_unpushed_commits', False),
                    offline_sessions=sessions,
                    last_successful_sync=datetime.fromisoformat(data['last_successful_sync']) if data.get('last_successful_sync') else None,
                    pending_sync_operations=data.get('pending_sync_operations', []),
                    network_state_history=network_history
                )
            except Exception as e:
                print(f"Warning: Could not load offline state: {e}")
        
        # Return default state
        return OfflineState(
            has_unpushed_commits=False,
            offline_sessions=[],
            last_successful_sync=None,
            pending_sync_operations=[],
            network_state_history=[]
        )
    
    def _save_offline_state(self):
        """Save offline state to disk"""
        try:
            # Convert to serializable format
            data = {
                'has_unpushed_commits': self.offline_state.has_unpushed_commits,
                'offline_sessions': [],
                'last_successful_sync': self.offline_state.last_successful_sync.isoformat() if self.offline_state.last_successful_sync else None,
                'pending_sync_operations': self.offline_state.pending_sync_operations,
                'network_state_history': [(dt.isoformat(), state.value) for dt, state in self.offline_state.network_state_history]
            }
            
            # Convert sessions
            for session in self.offline_state.offline_sessions:
                session_data = {
                    'session_id': session.session_id,
                    'start_time': session.start_time.isoformat(),
                    'end_time': session.end_time.isoformat() if session.end_time else None,
                    'network_start': session.network_start.value,
                    'network_end': session.network_end.value if session.network_end else None,
                    'local_commits': session.local_commits,
                    'sync_mode': session.sync_mode.value,
                    'requires_conflict_resolution': session.requires_conflict_resolution,
                    'backup_id': session.backup_id
                }
                data['offline_sessions'].append(session_data)
            
            with open(self.offline_state_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save offline state: {e}")
    
    def check_network_availability(self) -> NetworkState:
        """Enhanced network detection with history tracking"""
        try:
            import socket
            socket.create_connection(("github.com", 443), timeout=self.network_check_timeout)
            
            current_state = NetworkState.ONLINE
            
            # Record network state change
            self.offline_state.network_state_history.append((datetime.now(), current_state))
            
            # Keep only last 50 network state changes
            if len(self.offline_state.network_state_history) > 50:
                self.offline_state.network_state_history = self.offline_state.network_state_history[-50:]
            
            self._save_offline_state()
            return current_state
            
        except Exception:
            current_state = NetworkState.OFFLINE
            
            # Record network state change
            self.offline_state.network_state_history.append((datetime.now(), current_state))
            
            # Keep only last 50 network state changes  
            if len(self.offline_state.network_state_history) > 50:
                self.offline_state.network_state_history = self.offline_state.network_state_history[-50:]
            
            self._save_offline_state()
            return current_state
    
    def get_unpushed_commits(self) -> List[str]:
        """Get list of unpushed commits"""
        try:
            if PACKAGING_UTILS_AVAILABLE:
                result = packaging_utils.run_subprocess_safe(['git', 'log', 'origin/main..HEAD', '--oneline'], 
                                      cwd=self.vault_path, capture_output=True, text=True, timeout=10)
            else:
                import subprocess
                result = run_subprocess_safe(['git', 'log', 'origin/main..HEAD', '--oneline'], 
                                      cwd=self.vault_path, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                commits = [line.strip() for line in result.stdout.splitlines() if line.strip()]
                return commits
            else:
                return []
        except Exception:
            return []
    
    def determine_sync_mode(self, network_start: NetworkState, network_end: Optional[NetworkState] = None) -> SyncMode:
        """Determine appropriate sync mode based on network states"""
        if network_start == NetworkState.ONLINE:
            if network_end is None:
                return SyncMode.ONLINE_TO_ONLINE  # Default assumption
            elif network_end == NetworkState.ONLINE:
                return SyncMode.ONLINE_TO_ONLINE
            else:
                return SyncMode.ONLINE_TO_OFFLINE
        else:  # network_start == NetworkState.OFFLINE
            if network_end is None:
                return SyncMode.OFFLINE_TO_OFFLINE  # Default assumption
            elif network_end == NetworkState.ONLINE:
                return SyncMode.OFFLINE_TO_ONLINE
            else:
                return SyncMode.OFFLINE_TO_OFFLINE
    
    def should_trigger_conflict_resolution(self) -> bool:
        """
        Determine if conflict resolution should be triggered based on:
        1. Unpushed local commits exist
        2. Previous offline sessions
        3. Network state transitions
        """
        # Check for unpushed commits
        unpushed_commits = self.get_unpushed_commits()
        if unpushed_commits:
            print(f"[OFFLINE] Found {len(unpushed_commits)} unpushed commits - conflict resolution needed")
            return True
        
        # Check for unresolved offline sessions
        unresolved_sessions = [s for s in self.offline_state.offline_sessions 
                             if s.requires_conflict_resolution and s.end_time is None]
        if unresolved_sessions:
            print(f"[OFFLINE] Found {len(unresolved_sessions)} unresolved offline sessions")
            return True
        
        return False
    
    def start_sync_session(self, network_state: NetworkState) -> str:
        """Start a new sync session and return session ID"""
        session_id = f"session_{int(time.time())}_{len(self.offline_state.offline_sessions)}"
        
        # Determine sync mode
        sync_mode = self.determine_sync_mode(network_state)
        
        # Create new session
        session = OfflineSession(
            session_id=session_id,
            start_time=datetime.now(),
            end_time=None,
            network_start=network_state,
            network_end=None,
            local_commits=[],
            sync_mode=sync_mode,
            requires_conflict_resolution=False
        )
        
        # Create backup for offline sessions
        if network_state == NetworkState.OFFLINE and self.backup_manager and BackupReason:
            backup_id = self.backup_manager.create_backup(
                BackupReason.SYNC_OPERATION,
                f"Pre-offline session backup - {session_id}"
            )
            session.backup_id = backup_id
        
        self.offline_state.offline_sessions.append(session)
        self._save_offline_state()
        
        print(f"[OFFLINE] Started sync session: {session_id} (mode: {sync_mode.value})")
        return session_id
    
    def end_sync_session(self, session_id: str, network_state: NetworkState, 
                        local_commits: List[str]) -> bool:
        """End a sync session and determine if conflict resolution is needed"""
        # Find the session
        session = None
        for s in self.offline_state.offline_sessions:
            if s.session_id == session_id:
                session = s
                break
        
        if not session:
            print(f"[OFFLINE] Warning: Session {session_id} not found")
            return False
        
        # Update session
        session.end_time = datetime.now()
        session.network_end = network_state
        session.local_commits = local_commits
        session.sync_mode = self.determine_sync_mode(session.network_start, network_state)
        
        # Determine if conflict resolution is needed
        if session.sync_mode == SyncMode.OFFLINE_TO_ONLINE and local_commits:
            session.requires_conflict_resolution = True
            print(f"[OFFLINE] Session {session_id} requires conflict resolution")
        
        # Update global state
        if local_commits:
            self.offline_state.has_unpushed_commits = True
        
        self._save_offline_state()
        
        print(f"[OFFLINE] Ended sync session: {session_id} (final mode: {session.sync_mode.value})")
        return session.requires_conflict_resolution
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of offline sessions for user display"""
        total_sessions = len(self.offline_state.offline_sessions)
        offline_sessions = len([s for s in self.offline_state.offline_sessions 
                               if s.sync_mode in [SyncMode.OFFLINE_TO_OFFLINE, SyncMode.OFFLINE_TO_ONLINE]])
        
        total_unpushed = len(self.get_unpushed_commits())
        
        return {
            'total_sessions': total_sessions,
            'offline_sessions': offline_sessions,
            'unpushed_commits': total_unpushed,
            'last_sync': self.offline_state.last_successful_sync,
            'requires_resolution': self.should_trigger_conflict_resolution()
        }
    
    def cleanup_resolved_sessions(self, aggressive: bool = False):
        """Clean up resolved sessions to prevent clutter"""
        resolved_sessions = [s for s in self.offline_state.offline_sessions 
                           if not s.requires_conflict_resolution and s.end_time is not None]
        
        if aggressive:
            # Aggressive cleanup: remove all fully resolved sessions older than 1 hour
            # or if there are no unpushed commits, remove all resolved sessions
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(hours=1)
            unpushed = self.get_unpushed_commits()
            
            if len(unpushed) == 0:
                # No unpushed commits - safe to clean up all resolved sessions
                sessions_to_remove = resolved_sessions
                remaining_sessions = [s for s in self.offline_state.offline_sessions 
                                    if s.requires_conflict_resolution or s.end_time is None]
                
                if sessions_to_remove:
                    self.offline_state.offline_sessions = remaining_sessions
                    self._save_offline_state()
                    print(f"[OFFLINE] Aggressively cleaned up {len(sessions_to_remove)} resolved sessions (no unpushed commits)")
                    return
            
            # Otherwise, clean up sessions older than 1 hour
            old_sessions = [s for s in resolved_sessions if s.end_time and s.end_time < cutoff_time]
            if old_sessions:
                sessions_to_keep = [s for s in self.offline_state.offline_sessions if s not in old_sessions]
                self.offline_state.offline_sessions = sessions_to_keep
                self._save_offline_state()
                print(f"[OFFLINE] Cleaned up {len(old_sessions)} old resolved sessions")
                return
        
        # Regular cleanup: Keep only last 10 resolved sessions
        if len(resolved_sessions) > 10:
            sessions_to_keep = resolved_sessions[-10:]
            unresolved_sessions = [s for s in self.offline_state.offline_sessions 
                                 if s.requires_conflict_resolution or s.end_time is None]
            
            self.offline_state.offline_sessions = unresolved_sessions + sessions_to_keep
            self._save_offline_state()
            print(f"[OFFLINE] Cleaned up old resolved sessions")
    
    def mark_session_resolved(self, session_id: str):
        """Mark a session as resolved after conflict resolution"""
        for session in self.offline_state.offline_sessions:
            if session.session_id == session_id:
                session.requires_conflict_resolution = False
                break
        
        # Update global state if no more unresolved sessions
        if not any(s.requires_conflict_resolution for s in self.offline_state.offline_sessions):
            unpushed = self.get_unpushed_commits()
            self.offline_state.has_unpushed_commits = len(unpushed) > 0
        
        self._save_offline_state()
    
    def complete_successful_sync(self):
        """
        Mark all sessions as completed after a successful sync.
        This should be called when all changes have been successfully pushed to remote.
        """
        current_time = datetime.now()
        changes_made = False
        
        for session in self.offline_state.offline_sessions:
            if session.end_time is None:
                session.end_time = current_time
                changes_made = True
                print(f"[OFFLINE] Completed session: {session.session_id}")
        
        # Update unpushed commits status
        unpushed = self.get_unpushed_commits()
        if len(unpushed) == 0:
            self.offline_state.has_unpushed_commits = False
            changes_made = True
        
        if changes_made:
            self._save_offline_state()
            print(f"[OFFLINE] All sessions marked as completed - ready for cleanup")


# =============================================================================
# INTEGRATION FUNCTIONS
# =============================================================================

def create_offline_sync_manager(vault_path: str, config_data: Dict[str, str]) -> OfflineSyncManager:
    """Create and return an OfflineSyncManager instance"""
    return OfflineSyncManager(vault_path, config_data)

def should_use_offline_mode(manager: OfflineSyncManager) -> Tuple[bool, str]:
    """
    Determine if offline mode should be used based on current state
    Returns: (use_offline_mode, reason)
    """
    network_state = manager.check_network_availability()
    
    if network_state == NetworkState.OFFLINE:
        return True, "No network connectivity detected"
    
    # Check if we have unresolved offline sessions that need user attention
    if manager.should_trigger_conflict_resolution():
        return False, "Conflict resolution required - switching to online mode"
    
    return False, "Network available - using standard online mode"

def get_offline_status_message(manager: OfflineSyncManager) -> str:
    """Get user-friendly status message about offline state"""
    summary = manager.get_session_summary()
    
    if summary['requires_resolution']:
        return f"⚠️ {summary['unpushed_commits']} unpushed commits require conflict resolution"
    elif summary['unpushed_commits'] > 0:
        return f"📝 {summary['unpushed_commits']} local commits ready to sync"
    elif summary['offline_sessions'] > 0:
        return f"✅ {summary['offline_sessions']} offline sessions completed"
    else:
        return "✅ All changes synchronized"


# =============================================================================
# MAIN ENTRY POINTS
# =============================================================================

def enhance_auto_sync_with_offline_support(vault_path: str, config_data: Dict[str, str], 
                                          original_auto_sync_func, safe_update_log_func):
    """
    Enhanced auto_sync wrapper that adds offline support to existing workflow
    
    This function wraps the original auto_sync to add offline capabilities
    without disrupting the existing online workflow.
    """
    manager = create_offline_sync_manager(vault_path, config_data)
    
    # Check network and determine mode
    network_state = manager.check_network_availability()
    use_offline, reason = should_use_offline_mode(manager)
    
    safe_update_log_func(f"🌐 Network status: {network_state.value} - {reason}")
    
    if use_offline:
        # Start offline session
        session_id = manager.start_sync_session(network_state)
        safe_update_log_func(f"🔄 Starting offline session: {session_id}")
        
        # Run modified offline sync (simplified version of auto_sync)
        return run_offline_sync(vault_path, config_data, manager, session_id, safe_update_log_func)
    else:
        # Check if conflict resolution is needed before running online sync
        if manager.should_trigger_conflict_resolution():
            safe_update_log_func("🔧 Triggering conflict resolution for previous offline changes...")
            
            # TODO: Integrate with existing conflict resolution system
            # This would call the existing Stage1_conflict_resolution system
            
        # Run original online sync
        return original_auto_sync_func()

def run_offline_sync(vault_path: str, config_data: Dict[str, str], 
                    manager: OfflineSyncManager, session_id: str, safe_update_log_func):
    """
    Simplified offline-only sync process
    
    This is a streamlined version that:
    1. Skips all remote operations
    2. Opens Obsidian for editing
    3. Commits changes locally
    4. Tracks session for future conflict resolution
    """
    safe_update_log_func("📱 Running in offline mode - no remote synchronization")
    
    obsidian_path = config_data.get("OBSIDIAN_PATH", "")
    if not obsidian_path:
        safe_update_log_func("❌ Obsidian path not configured")
        return
    
    # Open Obsidian for editing
    safe_update_log_func("🚀 Launching Obsidian in offline mode...")
    
    try:
        # Use the existing open_obsidian function
        # This would need to be imported or passed as a parameter
        
        # Simple Obsidian launch - adjust based on platform
        if os.name == 'nt':  # Windows
            if PACKAGING_UTILS_AVAILABLE:
                import subprocess
                subprocess.Popen([obsidian_path], cwd=vault_path)
            else:
                import subprocess
                subprocess.Popen([obsidian_path], cwd=vault_path)
        else:  # Linux/Mac
            if PACKAGING_UTILS_AVAILABLE:
                import subprocess
                subprocess.Popen([obsidian_path], cwd=vault_path)
            else:
                import subprocess
                subprocess.Popen([obsidian_path], cwd=vault_path)
        
        safe_update_log_func("✅ Obsidian launched. Make your edits and close when finished.")
        
        # Wait for Obsidian to close (simplified version)
        # This would need to use the existing is_obsidian_running function
        
        # For now, just inform user
        safe_update_log_func("ℹ️ Close Obsidian when finished to commit your changes locally")
        
    except Exception as e:
        safe_update_log_func(f"❌ Error launching Obsidian: {e}")
        return
    
    # After Obsidian closes, commit changes locally
    safe_update_log_func("💾 Committing local changes...")
    
    try:
        if PACKAGING_UTILS_AVAILABLE:
            # Add all changes
            packaging_utils.run_subprocess_safe(['git', 'add', '.'], cwd=vault_path, check=True)
            
            # Commit with offline indicator
            commit_msg = f"Offline sync commit - {session_id}"
            result = packaging_utils.run_subprocess_safe(['git', 'commit', '-m', commit_msg], 
                                  cwd=vault_path, capture_output=True, text=True)
        else:
            import subprocess
            
            # Add all changes
            run_subprocess_safe(['git', 'add', '.'], cwd=vault_path, check=True)
            
            # Commit with offline indicator
            commit_msg = f"Offline sync commit - {session_id}"
            result = run_subprocess_safe(['git', 'commit', '-m', commit_msg], 
                                  cwd=vault_path, capture_output=True, text=True)
        
        local_commits = []
        if result.returncode == 0:
            safe_update_log_func("✅ Local changes committed successfully")
            local_commits = [commit_msg]
        else:
            if "nothing to commit" in result.stdout:
                safe_update_log_func("ℹ️ No changes detected this session")
            else:
                safe_update_log_func(f"⚠️ Commit warning: {result.stderr}")
        
        # End session
        network_end = manager.check_network_availability()
        needs_resolution = manager.end_sync_session(session_id, network_end, local_commits)
        
        if needs_resolution:
            safe_update_log_func("📋 Session completed - conflict resolution will be available when online")
        else:
            safe_update_log_func("✅ Offline session completed successfully")
            
    except Exception as e:
        safe_update_log_func(f"❌ Error committing changes: {e}")


if __name__ == "__main__":
    # Test the offline sync manager
    print("Testing Offline Sync Manager...")
    
    test_vault = "test_vault"
    test_config = {
        "VAULT_PATH": test_vault,
        "OBSIDIAN_PATH": "obsidian",
        "GITHUB_REMOTE_URL": "git@github.com:user/repo.git"
    }
    
    manager = create_offline_sync_manager(test_vault, test_config)
    network_state = manager.check_network_availability()
    
    print(f"Network state: {network_state}")
    print(f"Should trigger conflict resolution: {manager.should_trigger_conflict_resolution()}")
    print(f"Session summary: {manager.get_session_summary()}")
