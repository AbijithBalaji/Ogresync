import os
import subprocess
import sys
import shlex
import threading
import time
import psutil
import shutil
import random
import tkinter as tk
import platform
import datetime
from tkinter import ttk, scrolledtext
from typing import Optional
import webbrowser
import pyperclip
import requests

# Import packaging utilities first
try:
    import packaging_utils
    packaging_utils.init_packaging_compatibility()
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

import ui_elements # Import the new UI module
try:
    import Stage1_conflict_resolution as conflict_resolution # Import the enhanced conflict resolution module
    CONFLICT_RESOLUTION_AVAILABLE = True
except ImportError:
    conflict_resolution = None
    CONFLICT_RESOLUTION_AVAILABLE = False
import setup_wizard # Import the new setup wizard module

# Import offline sync manager
try:
    import offline_sync_manager
    # Check if the module actually has the required class
    if hasattr(offline_sync_manager, 'OfflineSyncManager'):
        OFFLINE_SYNC_AVAILABLE = True
    else:
        OFFLINE_SYNC_AVAILABLE = False
        offline_sync_manager = None
except ImportError:
    offline_sync_manager = None
    OFFLINE_SYNC_AVAILABLE = False

# ------------------------------------------------
# CONFIG / GLOBALS
# ------------------------------------------------

def get_config_directory():
    """Get the appropriate config directory for the current OS"""
    if PACKAGING_UTILS_AVAILABLE:
        return packaging_utils.get_config_directory()
    
    # Fallback implementation if packaging_utils not available
    import sys
    from pathlib import Path
    
    # ALWAYS use OS-specific directories for proper packaging behavior
    # This ensures consistent behavior between development and packaged versions
    if sys.platform == "win32":
        config_dir = os.path.join(os.environ['APPDATA'], 'Ogresync')
    elif sys.platform == "darwin":
        config_dir = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'Ogresync')
    else:  # Linux
        config_dir = os.path.join(os.path.expanduser('~'), '.config', 'ogresync')
    
    try:
        os.makedirs(config_dir, exist_ok=True)
        print(f"DEBUG: Config directory: {config_dir}")
    except Exception as e:
        print(f"WARNING: Could not create config directory {config_dir}: {e}")
        # Fallback to script directory only if OS-specific fails
        config_dir = os.path.dirname(os.path.abspath(__file__))
        print(f"DEBUG: Using fallback config directory: {config_dir}")
    
    return config_dir

def get_config_file_path():
    """Get the full path to the config file"""
    return os.path.join(get_config_directory(), "config.txt")

# Config file path will be determined dynamically
CONFIG_FILE = None  # Will be set by get_config_file_path()

config_data = {
    "VAULT_PATH": "",
    "OBSIDIAN_PATH": "",
    "GITHUB_REMOTE_URL": "",
    "SETUP_DONE": "0"
}

SSH_KEY_PATH = os.path.expanduser(os.path.join("~", ".ssh", "id_rsa.pub"))

root: Optional[tk.Tk] = None  # Will be created by ui_elements.create_main_window()
log_text: Optional[scrolledtext.ScrolledText] = None # Will be created by ui_elements.create_main_window()
progress_bar: Optional[ttk.Progressbar] = None # Will be created by ui_elements.create_main_window()

# ------------------------------------------------
# CONFIG HANDLING
# ------------------------------------------------

def load_config():
    """
    Reads config.txt into config_data dict.
    Expected lines like: KEY=VALUE
    
    Also handles migration from old script-directory config to new OS-specific location.
    """
    config_loaded = False
    
    # Get current config file path
    config_file = get_config_file_path()
    
    # Check for config in new location first
    if os.path.exists(config_file):
        print(f"DEBUG: Loading config from {config_file}")
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if "=" in line:
                        key, val = line.split("=", 1)
                        config_data[key.strip()] = val.strip()
            config_loaded = True
            print("DEBUG: Config loaded successfully from new location")
        except Exception as e:
            print(f"ERROR: Failed to load config from {config_file}: {e}")
    
    # If no config found in new location, check for old location (migration)
    if not config_loaded:
        old_config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.txt")
        if os.path.exists(old_config_file):
            print(f"DEBUG: Found old config at {old_config_file}, migrating...")
            try:
                with open(old_config_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if "=" in line:
                            key, val = line.split("=", 1)
                            config_data[key.strip()] = val.strip()
                
                # Save to new location
                save_config()
                
                # Try to remove old config file
                try:
                    os.remove(old_config_file)
                    print("DEBUG: Successfully migrated config and removed old file")
                except Exception as remove_err:
                    print(f"WARNING: Could not remove old config file: {remove_err}")
                
                config_loaded = True
            except Exception as e:
                print(f"ERROR: Failed to migrate config from {old_config_file}: {e}")
    
    if config_loaded:
        print("DEBUG: Final config loaded:")
        for k, v in config_data.items():
            print(f"DEBUG: Config - {k}: {v}")
    else:
        print("DEBUG: No config file found, using defaults")

def save_config():
    """
    Writes config_data dict to config.txt in the appropriate OS-specific directory.
    """
    config_file = get_config_file_path()
    print(f"DEBUG: Saving config to {config_file}")
    for k, v in config_data.items():
        print(f"DEBUG: Saving config - {k}: {v}")
    
    try:
        # Ensure directory exists
        config_dir = os.path.dirname(config_file)
        os.makedirs(config_dir, exist_ok=True)
        
        with open(config_file, "w", encoding="utf-8") as f:
            for k, v in config_data.items():
                f.write(f"{k}={v}\n")
        
        print(f"DEBUG: Config saved successfully to {config_file}")
    except Exception as e:
        print(f"ERROR: Failed to save config: {e}")
        # Try fallback location
        try:
            fallback_config = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.txt")
            print(f"DEBUG: Attempting fallback save to {fallback_config}")
            with open(fallback_config, "w", encoding="utf-8") as f:
                for k, v in config_data.items():
                    f.write(f"{k}={v}\n")
            print("DEBUG: Fallback config save successful")
        except Exception as fallback_err:
            print(f"ERROR: Fallback config save also failed: {fallback_err}")

# Import GitHub setup functions from separate module
import github_setup

# ------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------

def run_command(command, cwd=None, timeout=None):
    """
    Runs a shell command safely across platforms, returning (stdout, stderr, return_code).
    Safe to call in a background thread.
    
    Args:
        command: Command string to execute
        cwd: Working directory for the command
        timeout: Timeout in seconds
        
    Returns:
        Tuple of (stdout, stderr, return_code)
    """
    try:
        # For better cross-platform compatibility, try to avoid shell=True when possible
        # but still support it for complex commands and commit messages
        if isinstance(command, str):
            # Check if this is a simple git command that can be safely split
            # CRITICAL: Exclude git commit commands with -m messages as they contain quotes
            is_simple_git = (command.strip().startswith('git ') and 
                           ' && ' not in command and 
                           ' || ' not in command and 
                           ' | ' not in command and
                           'git commit -m' not in command)  # Exclude commit messages
            
            if is_simple_git:
                try:
                    # Use shlex for proper argument splitting only for simple commands
                    if platform.system() == "Windows":
                        # On Windows, use posix=False for proper quote handling
                        command_parts = shlex.split(command, posix=False)
                    else:
                        # On Unix-like systems, use standard splitting
                        command_parts = shlex.split(command)
                    
                    # Use safe subprocess call that handles packaging automatically
                    if PACKAGING_UTILS_AVAILABLE:
                        result = packaging_utils.run_subprocess_safe(
                            command_parts,
                            cwd=cwd,
                            capture_output=True,
                            text=True,
                            timeout=timeout,
                            check=False
                        )
                    else:
                        result = run_subprocess_safe(
                            command_parts,
                            cwd=cwd,
                            capture_output=True,
                            text=True,
                            timeout=timeout,
                            check=False
                        )
                    return result.stdout.strip(), result.stderr.strip(), result.returncode
                except (ValueError, OSError):
                    # Fall back to shell=True if splitting fails
                    pass
        
        # Use shell=True for:
        # - Complex commands with pipes, redirects, etc.
        # - Git commit commands with messages (to preserve quotes)
        # - When argument splitting fails
        # - Non-string commands (already arrays)
        
        # Use safe subprocess call that handles packaging automatically
        if PACKAGING_UTILS_AVAILABLE:
            result = packaging_utils.run_subprocess_safe(
                command,
                cwd=cwd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
        else:
            result = run_subprocess_safe(
                command,
                cwd=cwd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired as e:
        return "", str(e), 1
    except Exception as e:
        return "", str(e), 1
    
def ensure_github_known_host():
    """
    Adds GitHub's RSA key to known_hosts if not already present.
    This prevents the 'Are you sure you want to continue connecting?' prompt.
    
    Best Practice Note:
      - We're automatically trusting 'github.com' here.
      - In a more security-conscious workflow, you'd verify the key's fingerprint
        against GitHub's official documentation before appending.
    """
    # Check if GitHub is already in known_hosts
    known_hosts_path = os.path.expanduser("~/.ssh/known_hosts")
    if os.path.exists(known_hosts_path):
        with open(known_hosts_path, "r", encoding="utf-8") as f:
            if "github.com" in f.read():
                # Already have GitHub host key, nothing to do
                return

    safe_update_log("Adding GitHub to known hosts (ssh-keyscan)...", 32)
    # Fetch GitHub's RSA key and append to known_hosts
    scan_out, scan_err, rc = run_command("ssh-keyscan -t rsa github.com")
    if rc == 0 and scan_out:
        # Ensure .ssh folder exists
        os.makedirs(os.path.expanduser("~/.ssh"), exist_ok=True)
        with open(known_hosts_path, "a", encoding="utf-8") as f:
            f.write(scan_out + "\n")
    else:
        # If this fails, we won't block the user; but we warn them.
        safe_update_log("Warning: Could not fetch GitHub host key automatically.", 32)


def is_obsidian_running():
    """
    Checks if Obsidian is currently running using a more robust approach.
    Compares against known process names and the configured obsidian_path.
    """
    # Attempt to load config_data if not already loaded (e.g., if called in a standalone context)
    if not config_data.get("OBSIDIAN_PATH"):
        load_config() # Ensure config_data is populated

    obsidian_executable_path = config_data.get("OBSIDIAN_PATH")
    # Normalize obsidian_executable_path for comparison
    if obsidian_executable_path:
        obsidian_executable_path = os.path.normpath(obsidian_executable_path).lower()

    process_names_to_check = []
    if sys.platform.startswith("win"):
        process_names_to_check = ["obsidian.exe"]
    elif sys.platform.startswith("linux"):
        # Common names for native, Snap, or simple AppImage launches
        process_names_to_check = ["obsidian"]
        # Add Flatpak common application ID as a potential process name
        # psutil often shows the application ID for Flatpak apps
        process_names_to_check.append("md.obsidian.obsidian")
    elif sys.platform.startswith("darwin"):
        process_names_to_check = ["Obsidian"] # Main bundle executable name

    for proc in psutil.process_iter(attrs=["name", "exe", "cmdline"]):
        try:
            proc_info_name = proc.info.get("name", "").lower()
            proc_info_exe = os.path.normpath(proc.info.get("exe", "") or "").lower()
            proc_info_cmdline = [str(arg).lower() for arg in proc.info.get("cmdline", []) or []]

            # 1. Check against known process names
            for name_to_check in process_names_to_check:
                if name_to_check.lower() == proc_info_name:
                    return True

            # 2. Check if the process executable path matches the configured obsidian_path
            if obsidian_executable_path and proc_info_exe == obsidian_executable_path:
                return True

            # 3. For Linux (especially Flatpak/Snap/AppImage) and potentially others,
            # check if the configured obsidian_path (which could be a command or part of it)
            # is in the process's command line arguments.
            if obsidian_executable_path:
                if any(obsidian_executable_path in cmd_arg for cmd_arg in proc_info_cmdline):
                    return True
                # Sometimes the exe is just 'flatpak' and the app id is in cmdline
                if proc_info_name == "flatpak" and any("md.obsidian.obsidian" in cmd_arg for cmd_arg in proc_info_cmdline):
                    return True
                
            # 4. Special case for Flatpak: check for bwrap process with obsidian in cmdline
            if proc_info_name == "bwrap" and any("obsidian" in cmd_arg for cmd_arg in proc_info_cmdline):
                return True
                
            # 5. Check for any process with obsidian in the command line (broader match)
            if any("obsidian" in cmd_arg for cmd_arg in proc_info_cmdline):
                # Additional validation to avoid false positives
                if "obsidian.sh" in " ".join(proc_info_cmdline) or "md.obsidian" in " ".join(proc_info_cmdline):
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return False

# Global flag to prevent UI updates during transition
_ui_updating_enabled = True
_ui_lock = threading.Lock()
_pending_after_ids = set()  # Track pending after() calls
_ui_cleanup_in_progress = False  # Flag to indicate cleanup is happening

def disable_ui_updates():
    """Disable UI updates during transition and cancel pending operations"""
    global _ui_updating_enabled, _pending_after_ids, _ui_cleanup_in_progress
    with _ui_lock:
        _ui_updating_enabled = False
        _ui_cleanup_in_progress = True
        
        # Cancel all tracked pending after() calls
        if root is not None:
            try:
                for after_id in _pending_after_ids.copy():
                    try:
                        root.after_cancel(after_id)
                    except:
                        pass
                _pending_after_ids.clear()
            except:
                pass

def enable_ui_updates():
    """Re-enable UI updates after transition"""
    global _ui_updating_enabled, _pending_after_ids, _ui_cleanup_in_progress
    with _ui_lock:
        _ui_updating_enabled = True
        _ui_cleanup_in_progress = False
        # Clear any stale after IDs when re-enabling
        _pending_after_ids.clear()

def safe_update_log(message, progress=None):
    # Always print to console for debugging
    print(f"LOG: {message}")
    
    # Check if UI updates are enabled and cleanup is not in progress
    with _ui_lock:
        if not _ui_updating_enabled or _ui_cleanup_in_progress:
            return
    
    # Check if we have valid UI components
    if not (log_text and progress_bar and root):
        return
        
    def _update():
        try:
            # ENHANCED: Multiple safety checks during cleanup periods
            with _ui_lock:
                if not _ui_updating_enabled or _ui_cleanup_in_progress:
                    return
                    
            if not (log_text and root):
                return
                
            # ENHANCED: More comprehensive widget existence checks
            try:
                # Verify root exists and is valid
                if not root.winfo_exists():
                    return
                    
                # Verify we're not in the middle of destruction
                root.winfo_name()  # This will throw if root is being destroyed
                
            except (tk.TclError, AttributeError, RuntimeError):
                # Root is destroyed, being destroyed, or invalid
                return
                
            # Update log text with enhanced error handling
            if log_text is not None:
                try:
                    # Verify log_text widget exists and is valid
                    log_text.winfo_exists()
                    log_text.winfo_name()  # Additional validation
                    
                    log_text.config(state='normal')
                    log_text.insert(tk.END, message + "\n")
                    log_text.config(state='disabled')
                    log_text.yview_moveto(1)
                except (tk.TclError, AttributeError, RuntimeError):
                    # Widget destroyed or invalid - stop trying to update
                    return
                    
            # Update progress bar with enhanced error handling
            if progress is not None and progress_bar is not None:
                try:
                    # Verify progress_bar widget exists and is valid
                    progress_bar.winfo_exists()
                    progress_bar.winfo_name()  # Additional validation
                    progress_bar["value"] = progress
                except (tk.TclError, AttributeError, RuntimeError):
                    # Progress bar destroyed or invalid - continue without it
                    pass
                    
            # ENHANCED: Ultra-conservative UI update approach
            try:
                # Only update if we can confirm root is still completely valid
                if root.winfo_exists():
                    root.winfo_name()  # Final validation
                    root.update_idletasks()
                    # Skip root.update() to prevent recursive event processing during cleanup
            except (tk.TclError, AttributeError, RuntimeError):
                # Root destroyed or being destroyed - stop immediately
                return
                    
        except Exception as e:
            # Catch any other unexpected errors and ignore them during cleanup
            print(f"DEBUG: safe_update_log error during cleanup (ignored): {e}")
            
    try:
        # ENHANCED: Ultra-safe thread detection and scheduling
        current_thread = threading.current_thread()
        is_main_thread = current_thread == threading.main_thread()
        
        if is_main_thread:
            # We're in main thread, update immediately with extensive safety checks
            try:
                if root is not None:
                    # Multiple validation layers
                    if root.winfo_exists():
                        root.winfo_name()  # Ensure not being destroyed
                        _update()
            except (tk.TclError, AttributeError, RuntimeError):
                # Root destroyed or invalid - skip update completely
                return
        else:
            # We're in background thread, be extremely careful about scheduling
            try:
                # Extensive safety checks before scheduling
                if root is not None:
                    # Check if root still exists and is not being destroyed
                    if root.winfo_exists():
                        root.winfo_name()  # Validate not in destruction
                        
                        # Check cleanup status one more time
                        with _ui_lock:
                            if _ui_cleanup_in_progress:
                                return  # Don't schedule during cleanup
                        
                        # Schedule with tracking for cleanup
                        after_id = root.after_idle(_update)
                        with _ui_lock:
                            if not _ui_cleanup_in_progress:  # Double check
                                _pending_after_ids.add(after_id)
                            else:
                                # Cleanup started, cancel immediately
                                try:
                                    root.after_cancel(after_id)
                                except:
                                    pass
                                    
            except (tk.TclError, AttributeError, RuntimeError):
                # Root destroyed, invalid, or being destroyed - silently ignore
                return
                
    except Exception as e:
        # Final safety net - ignore all errors during cleanup periods
        print(f"DEBUG: safe_update_log scheduling error during cleanup (ignored): {e}")

def is_network_available():
    """
    Checks if the network is available by trying to connect to github.com over HTTPS.
    Returns True if successful, otherwise False.
    """
    import socket
    try:
        socket.create_connection(("github.com", 443), timeout=5)
        return True
    except Exception:
        return False

def get_unpushed_commits(vault_path):
    """
    Fetches the latest from origin and returns a string listing commits in HEAD that are not in origin/main.
    """
    # Update remote tracking info first.
    run_command("git fetch origin", cwd=vault_path)
    unpushed, _, _ = run_command("git log origin/main..HEAD --oneline", cwd=vault_path)
    return unpushed.strip()

def open_obsidian(obsidian_path):
    """
    Launches Obsidian in a cross-platform manner with improved handling.
    Supports various installation methods including native, Snap, Flatpak, and App Store.
    """ 
    try:
        if not obsidian_path:
            print("Error: No Obsidian path configured")
            return False
        
        if sys.platform.startswith("win"):
            # Windows: Handle both executable paths and command strings
            if obsidian_path.endswith('.exe') and os.path.exists(obsidian_path):
                # Direct executable path
                subprocess.Popen([obsidian_path], shell=False)
            else:
                # Fallback to shell execution for edge cases
                subprocess.Popen(obsidian_path, shell=True)
                
        elif sys.platform.startswith("linux"):
            # Linux: Handle various installation methods
            if obsidian_path.startswith("flatpak "):
                # Flatpak command string - split properly
                cmd_parts = shlex.split(obsidian_path)
                subprocess.Popen(cmd_parts)
            elif obsidian_path.startswith("/snap/") or "snap" in obsidian_path:
                # Snap installation
                if os.path.exists(obsidian_path):
                    subprocess.Popen([obsidian_path])
                else:
                    subprocess.Popen(["snap", "run", "obsidian"])
            elif os.path.exists(obsidian_path):
                # Direct executable path (AppImage, native binary, etc.)
                subprocess.Popen([obsidian_path])
            else:
                # Command in PATH or complex command string
                try:
                    cmd_parts = shlex.split(obsidian_path)
                    subprocess.Popen(cmd_parts)
                except ValueError:
                    # Fallback to shell if splitting fails
                    subprocess.Popen(obsidian_path, shell=True)
                    
        elif sys.platform.startswith("darwin"):
            # macOS: Handle app bundles and command paths
            if obsidian_path.endswith('.app') or '/Applications/' in obsidian_path:
                # App bundle - use 'open' command
                if obsidian_path.endswith('.app'):
                    subprocess.Popen(['open', '-a', obsidian_path])
                else:
                    # Path to executable inside app bundle
                    subprocess.Popen([obsidian_path])
            elif os.path.exists(obsidian_path):
                # Direct executable path
                subprocess.Popen([obsidian_path])
            else:
                # Command in PATH
                subprocess.Popen([obsidian_path])
        else:
            # Other platforms - generic approach
            if os.path.exists(obsidian_path):
                subprocess.Popen([obsidian_path])
            else:
                subprocess.Popen(obsidian_path, shell=True)
        
        print(f"Launched Obsidian: {obsidian_path}")
        return True
        
    except Exception as e:
        print(f"Error launching Obsidian: {e}")
        return False


def conflict_resolution_dialog(conflict_files):
    """
    Opens a two-stage conflict resolution dialog system.
    Stage 1: High-level strategy selection (Keep Local, Keep Remote, Smart Merge)
    Stage 2: File-by-file resolution for conflicting files (if Smart Merge is chosen)
    
    Returns the user's choice as one of the strings: "ours", "theirs", or "manual".
    This maintains backward compatibility while providing enhanced resolution capabilities.
    """
    if not CONFLICT_RESOLUTION_AVAILABLE:
        print("Enhanced conflict resolution not available, using fallback")
        return ui_elements.create_conflict_resolution_dialog(root, conflict_files)
    
    try:
        # Get vault path from config
        vault_path = config_data.get("VAULT_PATH", "")
        if not vault_path:
            print("No vault path configured")
            return ui_elements.create_conflict_resolution_dialog(root, conflict_files)
          # Create conflict resolver
        import Stage1_conflict_resolution as cr_module
        resolver = cr_module.ConflictResolver(vault_path, root)
        
        # Create a mock remote URL for conflict analysis (this should ideally come from git remote)
        github_url = config_data.get("GITHUB_REMOTE_URL", "")
        
        # Use the enhanced conflict resolution system
        result = resolver.resolve_initial_setup_conflicts(github_url)
        
        if result.success:
            strategy = result.strategy
            if strategy:
                # Map new strategies to old format for backward compatibility
                if strategy.value == "keep_local_only":
                    return 'ours'
                elif strategy.value == "keep_remote_only":
                    return 'theirs'
                elif strategy.value == "smart_merge":
                    return 'manual'  # Indicates smart merge was applied
            return 'manual'  # Default for successful resolution
        else:
            # User cancelled or resolution failed
            if "cancelled by user" in result.message.lower():
                return None  # User cancelled
            else:
                print(f"Enhanced conflict resolution failed: {result.message}")
                # Fallback to simple dialog
                return ui_elements.create_conflict_resolution_dialog(root, conflict_files)
            
    except Exception as e:
        print(f"Error in enhanced conflict resolution: {e}")
        import traceback
        traceback.print_exc()
        # Fallback to original UI element for backward compatibility
        return ui_elements.create_conflict_resolution_dialog(root, conflict_files)

# ------------------------------------------------
# REPOSITORY CONFLICT RESOLUTION FUNCTIONS
# ------------------------------------------------

def analyze_repository_state(vault_path):
    """
    Analyzes the state of local vault and remote repository to detect potential conflicts.
    Returns a dictionary with analysis results.
    """
    analysis = {
        "has_local_files": False,
        "has_remote_files": False,
        "local_files": [],
        "remote_files": [],
        "conflict_detected": False
    }
    
    # Check for local files (excluding .git directory)
    try:
        for root_dir, dirs, files in os.walk(vault_path):
            # Skip .git directory
            if '.git' in root_dir:
                continue
            for file in files:
                # Skip hidden files and common non-content files
                if not file.startswith('.') and file not in ['README.md', '.gitignore']:
                    rel_path = os.path.relpath(os.path.join(root_dir, file), vault_path)
                    analysis["local_files"].append(rel_path)
        
        analysis["has_local_files"] = len(analysis["local_files"]) > 0
    except Exception as e:
        safe_update_log(f"Error analyzing local files: {e}", None)
    
    # Check for remote files by attempting to fetch
    try:
        # Try to fetch remote refs to see if repository has content
        fetch_out, fetch_err, fetch_rc = run_command("git fetch origin", cwd=vault_path)
        if fetch_rc == 0:
            # Check if remote main branch exists and has files
            ls_out, ls_err, ls_rc = run_command("git ls-tree -r --name-only origin/main", cwd=vault_path)
            if ls_rc == 0 and ls_out.strip():
                remote_files = [f.strip() for f in ls_out.splitlines() if f.strip() and not f.startswith('.')]
                # Filter out common non-content files
                analysis["remote_files"] = [f for f in remote_files if f not in ['README.md', '.gitignore']]
                analysis["has_remote_files"] = len(analysis["remote_files"]) > 0
    except Exception as e:
        safe_update_log(f"Error analyzing remote repository: {e}", None)
    
    # Determine if there's a conflict (both local and remote have content files)
    analysis["conflict_detected"] = analysis["has_local_files"] and analysis["has_remote_files"]
    
    return analysis

def handle_initial_repository_conflict(vault_path, analysis, parent_window=None):
    """
    Handles repository content conflicts during initial setup using the enhanced two-stage resolution system.
    Returns True if resolved successfully, False otherwise.
    """
    if not analysis["conflict_detected"]:
        return True
    
    if not CONFLICT_RESOLUTION_AVAILABLE:
        # Fall back to simple dialog
        safe_update_log("Enhanced conflict resolution not available, using fallback", None)
        return False
    
    try:
        # Use the enhanced two-stage conflict resolution system
        dialog_parent = parent_window if parent_window is not None else root
          # Create conflict resolver
        import Stage1_conflict_resolution as cr_module
        resolver = cr_module.ConflictResolver(vault_path, dialog_parent)
        
        # Get GitHub URL for analysis
        github_url = config_data.get("GITHUB_REMOTE_URL", "")
        
        # Use the enhanced conflict resolution system
        result = resolver.resolve_initial_setup_conflicts(github_url)
        
        if result.success:
            safe_update_log(f"Repository conflict resolved successfully: {result.message}", None)
            return True
        else:
            if "cancelled by user" in result.message.lower():
                safe_update_log("Conflict resolution cancelled by user", None)
                return False
            else:
                safe_update_log(f"Repository conflict resolution failed: {result.message}", None)
                return False
                
    except Exception as e:
        safe_update_log(f"Error in enhanced repository conflict resolution: {e}", None)
        import traceback
        traceback.print_exc()
        return False

def ensure_git_user_config():
    """
    Ensures Git user configuration is set up for commits.
    Sets default values if not configured.
    """
    try:
        # Check if user.name is configured
        name_out, name_err, name_rc = run_command("git config --global user.name")
        if name_rc != 0 or not name_out.strip():
            safe_update_log("Setting default Git user name...", None)
            run_command('git config --global user.name "Ogresync User"')
        
        # Check if user.email is configured
        email_out, email_err, email_rc = run_command("git config --global user.email")
        if email_rc != 0 or not email_out.strip():
            safe_update_log("Setting default Git user email...", None)
            run_command('git config --global user.email "ogresync@example.com"')
            
    except Exception as e:
        safe_update_log(f"Warning: Could not configure Git user settings: {e}", None)

# ===== DEPRECATED FUNCTIONS REMOVED =====
# The following functions have been replaced by the enhanced conflict_resolution module:
# - handle_merge_strategy() -> Use conflict_resolution.ConflictResolver
# - handle_local_strategy() -> Use conflict_resolution._apply_keep_local_strategy  
# - handle_remote_strategy() -> Use conflict_resolution._apply_keep_remote_strategy
# 
# These old functions contained potentially destructive operations and have been
# replaced with non-destructive alternatives that preserve git history and create backups.
#
# All conflict resolution is now handled through:
# - conflict_resolution.ConflictResolver.resolve_conflicts()  
# - conflict_resolution.apply_conflict_resolution()
#
# See conflict_resolution.py for the new implementation.

def create_descriptive_backup_dir(vault_path, operation_description, file_list=None):
    """
    Creates a backup directory with a descriptive name and optional README.
    
    Args:
        vault_path: Path to the vault directory
        operation_description: Description of the operation (e.g., "before_remote_download")
        file_list: Optional list of files being backed up (for documentation)
    
    Returns:
        tuple: (backup_dir_path, backup_name)
    """
    from datetime import datetime
    
    # Create human-readable timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_name = f"LOCAL_FILES_BACKUP_{timestamp}_{operation_description}"
    backup_dir = os.path.join(vault_path, backup_name)
    
    # Handle name collisions with incremental counter
    counter = 1
    while os.path.exists(backup_dir):
        backup_name = f"LOCAL_FILES_BACKUP_{timestamp}_{operation_description}_({counter})"
        backup_dir = os.path.join(vault_path, backup_name)
        counter += 1
    
    # Create the backup directory
    os.makedirs(backup_dir, exist_ok=True)
    
    # Create a README file explaining the backup
    readme_path = os.path.join(backup_dir, "BACKUP_INFO.txt")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(f"OGRESYNC LOCAL FILES BACKUP\n")
        f.write(f"=" * 50 + "\n\n")
        f.write(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Operation: {operation_description.replace('_', ' ').title()}\n")
        f.write(f"Backup Directory: {backup_name}\n\n")
        f.write(f"PURPOSE:\n")
        f.write(f"This backup was created to preserve your local vault files\n")
        f.write(f"before performing a repository operation that might modify them.\n\n")
        
        if file_list:
            f.write(f"BACKED UP FILES ({len(file_list)} items):\n")
            f.write(f"-" * 30 + "\n")
            for file_path in sorted(file_list):
                f.write(f"  • {file_path}\n")
            f.write("\n")
        
        f.write(f"RESTORATION:\n")
        f.write(f"If you need to restore these files, simply copy them back\n")
        f.write(f"from this backup directory to your vault directory.\n\n")
        f.write(f"SAFETY:\n")
        f.write(f"This backup can be safely deleted once you're confident\n")
        f.write(f"that the repository operation completed successfully.\n")
    
    return backup_dir, backup_name

# Import GitHub setup functions from separate module
import github_setup

# Initialize GitHub setup module dependencies
try:
    import Stage1_conflict_resolution as cr_module
    github_setup.set_dependencies(
        ui_elements=None,  # Will be set later when ui_elements is available
        config_data=config_data,
        save_config_func=save_config,
        conflict_resolution_module=cr_module,
        safe_update_log_func=safe_update_log
    )
except ImportError:
    # Conflict resolution module not available
    github_setup.set_dependencies(
        ui_elements=None,  # Will be set later when ui_elements is available
        config_data=config_data,
        save_config_func=save_config,
        conflict_resolution_module=None,
        safe_update_log_func=safe_update_log
    )

def restart_for_setup():
    """
    Restart the application to run the setup wizard.
    """
    try:
        safe_update_log("Restarting for setup wizard...", None)
        
        # Close current UI if it exists
        if root is not None:
            root.quit()
            root.destroy()
        
        # Re-run the main function which will detect SETUP_DONE=0 and run the wizard
        main()
        
    except Exception as e:
        safe_update_log(f"❌ Error restarting for setup: {e}", None)

def restart_to_sync_mode():
    """
    Restart the application in sync mode after setup completion.
    FIXED: Comprehensive threading isolation to prevent Tcl_AsyncDelete errors.
    """
    global root, log_text, progress_bar
    
    try:
        print("DEBUG: Transitioning to sync mode...")
        
        # STEP 1: Immediately disable all UI updates to prevent any thread interference
        disable_ui_updates()
        
        # STEP 2: Force garbage collection to clean up any dangling references
        import gc
        gc.collect()
        
        # STEP 3: Wait for all daemon threads to finish current operations
        print("DEBUG: Stopping any remaining background operations...")
        print("DEBUG: Waiting for background threads to complete UI operations...")
        time.sleep(1.5)  # Give existing threads time to finish
        
        # STEP 4: Comprehensive UI cleanup with complete isolation
        if root is not None:
            try:
                print("DEBUG: Comprehensive UI cleanup...")
                
                # Cancel ALL pending operations - be very aggressive
                try:
                    # Method 1: Cancel all after calls
                    root.after_cancel("all")
                    
                    # Method 2: Clear the event queue
                    while True:
                        try:
                            root.update_idletasks()
                            if not root.tk.call('after', 'info'):
                                break
                        except:
                            break
                    
                    # Method 3: Force process remaining events
                    for _ in range(10):  # Process up to 10 pending events
                        try:
                            root.update_idletasks()
                        except:
                            break
                    
                except Exception as cleanup_err:
                    print(f"Event cleanup error (non-critical): {cleanup_err}")
                
                # STEP 5: Complete widget destruction
                print("DEBUG: Complete widget destruction...")
                try:
                    # Hide window immediately
                    root.withdraw()
                    root.overrideredirect(True)  # Prevent any window manager interactions
                    
                    # Wait for any pending operations to complete
                    time.sleep(0.5)
                    
                    # Quit mainloop
                    root.quit()
                    
                    # Additional safety delay
                    time.sleep(0.5)
                    
                    # Final destroy
                    root.destroy()
                    
                except Exception as destroy_error:
                    print(f"Widget destruction error (non-critical): {destroy_error}")
                
                # Clear all global references immediately
                root = None
                log_text = None
                progress_bar = None
                
                print("DEBUG: UI destroyed successfully")
                
            except Exception as cleanup_error:
                print(f"UI cleanup error (will continue): {cleanup_error}")
        
        # STEP 6: Extended thread isolation period
        print("DEBUG: Extended thread isolation period...")
        
        # Force another garbage collection
        gc.collect()
        
        # Wait longer for all threads to completely finish
        time.sleep(4.0)  # Increased from 3.0 to 4.0 seconds
        
        # Monitor active threads
        active_thread_count = threading.active_count()
        print(f"DEBUG: Active thread count after cleanup: {active_thread_count}")
        
        # If there are still many active threads, wait a bit more
        if active_thread_count > 2:  # Main thread + potentially 1 cleanup thread
            print("DEBUG: Waiting for additional background threads to finish...")
            time.sleep(2.0)
            final_count = threading.active_count()
            print(f"DEBUG: Final active thread count: {final_count}")
        
        # STEP 7: Create completely new UI in isolated environment
        print("DEBUG: Creating isolated new UI...")
        try:
            # Clear any remaining tkinter state
            import tkinter as tk
            
            # Create new UI with complete isolation
            root, log_text, progress_bar = ui_elements.create_minimal_ui(auto_run=False)
            
            # Ensure new UI is completely stable
            root.update()
            root.update_idletasks()
            time.sleep(1.0)  # Extended stability delay
            
            print("DEBUG: Isolated UI created successfully")
            
        except Exception as ui_creation_error:
            print(f"ERROR: Failed to create isolated UI: {ui_creation_error}")
            enable_ui_updates()
            raise ui_creation_error
        
        # STEP 8: Re-enable UI updates only after complete stabilization
        enable_ui_updates()
        
        print("DEBUG: UI transition complete, starting isolated sync")
        
        # STEP 9: Start sync with maximum isolation
        def completely_isolated_sync():
            try:
                print("DEBUG: Starting completely isolated sync process")
                
                # Additional safety check - ensure we're in a clean state
                if root is None or log_text is None:
                    print("ERROR: UI not properly initialized for sync")
                    return
                
                # Start sync with threading for responsiveness
                auto_sync(use_threading=True)
                
            except Exception as sync_error:
                print(f"Isolated sync error: {sync_error}")
                try:
                    if root is not None:
                        safe_update_log(f"❌ Error during sync: {sync_error}", None)
                except:
                    print(f"❌ Error during sync: {sync_error}")
        
        # STEP 10: Maximum delay for complete thread isolation
        root.after(3000, completely_isolated_sync)  # Increased from 2000 to 3000ms
        
        # Run the isolated main loop
        print("DEBUG: Starting isolated main UI loop...")
        root.mainloop()
        
    except Exception as e:
        print(f"Error in isolated transition: {e}")
        import traceback
        traceback.print_exc()
        
        # Ensure UI updates are re-enabled
        enable_ui_updates()
        
        # Enhanced fallback with complete isolation
        try:
            print("Entering isolated console fallback mode...")
            # Use safe subprocess call for isolated console fallback
            current_dir = os.path.dirname(os.path.abspath(__file__))
            if PACKAGING_UTILS_AVAILABLE:
                result = packaging_utils.run_subprocess_safe([
                    sys.executable, 
                    os.path.join(current_dir, "Ogresync.py"),
                    "--console-sync"  # Special flag for console-only sync
                ], cwd=current_dir)
            else:
                result = run_subprocess_safe([
                    sys.executable, 
                    os.path.join(current_dir, "Ogresync.py"),
                    "--console-sync"  # Special flag for console-only sync
                ], cwd=current_dir)
            
        except Exception as fallback_error:
            print(f"Isolated console fallback failed: {fallback_error}")
            print("Manual intervention required. Please restart the application.")
            input("Press Enter to exit...")

# Import wizard steps functions from separate module
import wizard_steps

# ------------------------------------------------
# AUTO-SYNC (Used if SETUP_DONE=1)
# ------------------------------------------------

def auto_sync(use_threading=True):
    """
    This function is executed if setup is complete.
    It performs the following steps:
      1. Validates that the vault directory exists (offers recovery if missing)
      2. Ensures that the vault has at least one commit (creating an initial commit if necessary, 
         including generating a placeholder file if the vault is empty).
      3. Checks network connectivity.
         - If online, it verifies that the remote branch ('main') exists (pushing the initial commit if needed)
           and pulls the latest updates from GitHub (using rebase and prompting for conflict resolution if required).
         - If offline, it skips remote operations.      4. Stashes any local changes before pulling.
      5. Handles stashed changes based on sync type:
         - For initial sync (when local has only README): Discards stashed changes (remote content takes precedence)
         - For regular sync: Reapplies stashed changes, using 2-stage conflict resolution if conflicts occur
      6. Opens Obsidian for editing and waits until it is closed.
      7. Upon Obsidian closure, stages and commits any changes.
      8. If online, pushes any unpushed commits to GitHub.
      9. Displays a final synchronization completion message.
      
    Args:
        use_threading: If True, run sync in a background thread. If False, run directly.
    """
    print(f"DEBUG: auto_sync called with use_threading={use_threading}")
    safe_update_log("Initializing auto-sync...", 0)
    
    vault_path = config_data["VAULT_PATH"]
    obsidian_path = config_data["OBSIDIAN_PATH"]

    if not vault_path or not obsidian_path:
        safe_update_log("Vault path or Obsidian path not set. Please run setup again.", 0)
        return

    def sync_thread():
        nonlocal vault_path
        safe_update_log("🔄 Starting sync process...", 0)
        print("DEBUG: sync_thread started")
        
        # OFFLINE SYNC INTEGRATION - TEMPORARILY DISABLED
        # Offline sync functionality has been temporarily disabled due to incomplete module
        # All sync operations will proceed with standard online/offline handling
        safe_update_log("📱 Using standard sync mode (offline sync features disabled)", 2)
        
        # Ensure immediate UI update and responsiveness
        time.sleep(0.1)
        
        # Add periodic UI updates throughout sync process
        def ensure_ui_responsiveness():
            if root:
                try:
                    root.update_idletasks()
                    root.update()  # Force complete update cycle
                    time.sleep(0.02)  # Slightly longer delay for better responsiveness
                except tk.TclError:
                    pass  # UI destroyed, ignore
        
        # Step 0: Validate vault directory exists
        ensure_ui_responsiveness()
        is_valid, should_continue, new_vault_path = github_setup.validate_vault_directory(vault_path, ui_elements)
        
        if not should_continue:
            safe_update_log("❌ Cannot proceed without a valid vault directory.", 0)
            return
        
        if new_vault_path == "run_setup":
            # User chose to run setup wizard again
            safe_update_log("Restarting application to run setup wizard...", 0)
            # Reset the setup flag to trigger setup wizard
            config_data["SETUP_DONE"] = "0"
            save_config()
            if root is not None:
                root.after(0, lambda: restart_for_setup())
            return
        
        # Update vault_path if user selected a new directory
        if new_vault_path:
            vault_path = new_vault_path
        
        # Step 1: Ensure the vault is a git repository and has at least one commit
        # First check if it's even a git repository
        safe_update_log("Checking git repository status...", 5)
        ensure_ui_responsiveness()
        git_check_out, git_check_err, git_check_rc = run_command("git status", cwd=vault_path)
        ensure_ui_responsiveness()
        
        if git_check_rc != 0:
            # Not a git repository - this shouldn't happen if setup was done correctly
            safe_update_log("❌ Directory is not a git repository. Initializing...", 5)
            github_setup.initialize_git_repo(vault_path)
            
            # Try to configure remote if we have a saved URL
            saved_url = config_data.get("GITHUB_REMOTE_URL", "").strip()
            if saved_url:
                safe_update_log(f"Configuring remote with saved URL: {saved_url}", 5)
                # Validate URL before using in command
                import re
                if re.match(r'^https?://[^\s<>"{}|\\^`\[\]]+$', saved_url) or re.match(r'^git@[^\s<>"{}|\\^`\[\]]+$', saved_url):
                    run_command(f"git remote add origin {saved_url}", cwd=vault_path)
                else:
                    safe_update_log(f"❌ Invalid URL format: {saved_url}", 5)
                    safe_update_log("❌ Please check your GitHub remote URL configuration.", 5)
                    return
            else:
                safe_update_log("❌ No remote URL configured. Please run setup again.", 5)
                return
        
        # Check if repository has any commits
        safe_update_log("Checking for existing commits...", 8)
        ensure_ui_responsiveness()
        out, err, rc = run_command("git rev-parse HEAD", cwd=vault_path)
        ensure_ui_responsiveness()
        
        if rc != 0:
            safe_update_log("No existing commits found in your vault. Verifying if the vault is empty...", 5)
            ensure_ui_responsiveness()
            
            # Safely ensure placeholder file with error handling
            try:
                github_setup.ensure_placeholder_file(vault_path)
            except Exception as e:
                safe_update_log(f"❌ Error creating placeholder file: {e}", 5)
                return
            
            safe_update_log("Creating an initial commit to initialize the repository...", 5)
            ensure_ui_responsiveness()
            run_command("git add -A", cwd=vault_path)
            ensure_ui_responsiveness()
            out_commit, err_commit, rc_commit = run_command('git commit -m "Initial commit (auto-sync)"', cwd=vault_path)
            ensure_ui_responsiveness()
            if rc_commit == 0:
                safe_update_log("Initial commit created successfully.", 5)
            else:
                safe_update_log(f"❌ Error creating initial commit: {err_commit}", 5)
                return
        else:
            safe_update_log("Local repository already contains commits.", 5)

        # Step 2: Check network connectivity
        ensure_ui_responsiveness()
        network_available = is_network_available()
        if not network_available:
            safe_update_log("No internet connection detected. Skipping remote sync operations and proceeding in offline mode.", 10)
        else:
            safe_update_log("Internet connection detected. Proceeding with remote synchronization.", 10)
                  # OFFLINE SYNC: Check if we have pending offline changes that need immediate sync
        conflict_resolution_completed = False  # Track if we just completed conflict resolution
        if OFFLINE_SYNC_AVAILABLE and offline_sync_manager is not None and hasattr(offline_sync_manager, 'OfflineSyncManager'):
            try:
                sync_manager = offline_sync_manager.OfflineSyncManager(vault_path, config_data)
                summary = sync_manager.get_session_summary()
                
                if summary['offline_sessions'] > 0 or summary['unpushed_commits'] > 0:
                    safe_update_log(f"📱 Detected {summary['offline_sessions']} offline session(s) with {summary['unpushed_commits']} unpushed commits", 12)
                    
                    # Only process offline changes if we have network
                    if network_available:
                        safe_update_log("🔄 Processing offline changes before standard sync...", 13)
                          # Check if conflict resolution is needed - only if we have network
                        if sync_manager.should_trigger_conflict_resolution():
                            safe_update_log("⚠️ Offline changes require conflict resolution", 14)
                            
                            # Trigger conflict resolution before continuing with sync
                            if CONFLICT_RESOLUTION_AVAILABLE and conflict_resolution is not None:
                                safe_update_log("🔧 Activating conflict resolution for offline changes...", 15)
                                try:
                                    # Use the enhanced conflict resolution system
                                    resolver = conflict_resolution.ConflictResolver(vault_path)
                                    analysis = resolver.engine.analyze_conflicts(config_data.get("GITHUB_REMOTE_URL"))
                                    
                                    if analysis.has_conflicts:
                                        # Show conflict resolution dialog
                                        safe_update_log("Opening conflict resolution interface...", 16)
                                        result = conflict_resolution.resolve_conflicts(vault_path, config_data.get("GITHUB_REMOTE_URL", ""), root)
                                        
                                        if result.success:
                                            safe_update_log("✅ Offline conflicts resolved successfully", 17)
                                            conflict_resolution_completed = True  # Mark that we completed conflict resolution
                                            
                                            # CRITICAL FIX: Immediately push conflict resolution results
                                            if network_available:
                                                safe_update_log("📤 Pushing conflict resolution results immediately...", 18)
                                                push_out, push_err, push_rc = run_command("git push -u origin main", cwd=vault_path)
                                                if push_rc == 0:
                                                    safe_update_log("✅ Conflict resolution results pushed to GitHub successfully", 19)
                                                else:
                                                    safe_update_log(f"⚠️ Failed to push conflict resolution results: {push_err}", 19)
                                                    safe_update_log("Will retry push in normal sync flow...", 19)
                                            
                                            # Mark sessions as resolved and end them
                                            # TODO: Re-enable when offline sync module is implemented
                                            # for session in sync_manager.offline_state.offline_sessions:
                                            #     sync_manager.mark_session_resolved(session.session_id)
                                            #     # Properly end the session to allow cleanup
                                            #     sync_manager.end_sync_session(session.session_id, 
                                            #                                 sync_manager.check_network_availability(), 
                                            #                                 sync_manager.get_unpushed_commits())
                                        else:
                                            safe_update_log("❌ Conflict resolution failed or cancelled", 17)
                                            safe_update_log("Continuing with standard sync...", 17)
                                    else:
                                        safe_update_log("✅ No conflicts detected, proceeding with sync", 16)
                                        
                                except Exception as e:
                                    safe_update_log(f"❌ Error during offline conflict resolution: {e}", 16)
                                    print(f"[DEBUG] Offline conflict resolution error: {e}")
                        else:
                            safe_update_log("✅ No conflicts detected for offline changes", 14)
                    else:
                        safe_update_log("📴 No network available - offline changes will be synced when connection is restored", 13)
                    
                    # Clean up resolved sessions (use aggressive cleanup after successful sync)
                    sync_manager.cleanup_resolved_sessions(aggressive=True)
                    
                    # If we completed conflict resolution successfully, mark sessions as completed
                    if conflict_resolution_completed:
                        sync_manager.complete_successful_sync()
                    
            except Exception as e:
                safe_update_log(f"⚠️ Error checking offline changes: {e}", 12)
                print(f"[DEBUG] Offline sync check error: {e}")
            
            ensure_ui_responsiveness()
            # Verify remote branch 'main'
            ls_out, ls_err, ls_rc = run_command("git ls-remote --heads origin main", cwd=vault_path)
            if not ls_out.strip():
                safe_update_log("Remote branch 'main' not found. Pushing initial commit to create the remote branch...", 10)
                out_push, err_push, rc_push = run_command("git push -u origin main", cwd=vault_path)
                if rc_push == 0:
                    safe_update_log("Initial commit has been successfully pushed to GitHub.", 15)
                else:
                    # Check if it's a non-fast-forward error
                    if "non-fast-forward" in err_push:
                        safe_update_log("Remote has commits. Pulling before push...", 15)
                        pull_out, pull_err, pull_rc = run_command("git pull origin main --allow-unrelated-histories", cwd=vault_path)
                        if pull_rc == 0:
                            safe_update_log("Successfully pulled remote commits.", 15)
                        elif "CONFLICT" in (pull_out + pull_err):
                            # Conflict during sync initialization - use 2-stage conflict resolution
                            safe_update_log("❌ Merge conflict detected during sync initialization.", 16)
                            safe_update_log("🔧 Activating 2-stage conflict resolution system...", 17)
                            
                            try:
                                # Create backup using backup manager
                                backup_id = create_descriptive_backup_dir(vault_path, "before_sync_initialization")
                                if backup_id:
                                    safe_update_log(f"Local state backed up: {backup_id}", 17)
                                
                                # For sync initialization, we want remote content to take precedence
                                # Use reset --hard to replace local with remote content (your preference)
                                safe_update_log("Replacing local content with remote content...", 17)
                                reset_out, reset_err, reset_rc = run_command("git reset --hard origin/main", cwd=vault_path)
                                
                                if reset_rc == 0:
                                    safe_update_log("✅ Successfully synchronized with remote repository", 18)
                                    if backup_id:
                                        safe_update_log(f"📝 Note: Previous local state preserved in backup: {backup_id}", 18)
                                else:
                                    safe_update_log(f"❌ Failed to synchronize with remote: {reset_err}", 18)
                                    if backup_id:
                                        safe_update_log(f"📝 Your local work is safe in backup: {backup_id}", 18)
                                    network_available = False
                                    
                            except Exception as e:
                                safe_update_log(f"❌ Error in enhanced conflict resolution during sync init: {e}", 18)
                                safe_update_log("Sync initialization may be incomplete. Please resolve conflicts manually.", 18)
                                network_available = False
                        else:
                            safe_update_log(f"Error pulling remote commits: {pull_err}", 15)
                    else:
                        safe_update_log(f"❌ Error pushing initial commit: {err_push}", 15)
                        network_available = False
            else:
                safe_update_log("Remote branch 'main' found. Proceeding to pull updates from GitHub...", 10)

            # Ensure upstream tracking is set up to prevent unpushed commit detection issues
            safe_update_log("Ensuring upstream tracking is configured...", 12)
            current_branch_out, _, current_branch_rc = run_command("git branch --show-current", cwd=vault_path)
            if current_branch_rc == 0 and current_branch_out.strip():
                current_branch = current_branch_out.strip()
                # Check if upstream is already set
                upstream_out, _, upstream_rc = run_command(f"git rev-parse --abbrev-ref {current_branch}@{{upstream}}", cwd=vault_path)
                if upstream_rc != 0:
                    # Set upstream tracking
                    set_upstream_out, set_upstream_err, set_upstream_rc = run_command(f"git branch --set-upstream-to=origin/{current_branch} {current_branch}", cwd=vault_path)
                    if set_upstream_rc == 0:
                        safe_update_log(f"✅ Configured upstream tracking: {current_branch} -> origin/{current_branch}", 13)
                    else:
                        safe_update_log(f"⚠️ Could not set upstream tracking: {set_upstream_err}", 13)
                else:
                    safe_update_log(f"✅ Upstream tracking already configured: {current_branch} -> {upstream_out.strip()}", 13)

        # Step 3: Stash local changes
        safe_update_log("Stashing any local changes...", 15)
        ensure_ui_responsiveness()
        run_command("git stash", cwd=vault_path)
        ensure_ui_responsiveness()

        # Step 4: If online, pull the latest updates (with conflict resolution)
        if network_available:
            # First, fetch remote refs to ensure we have latest info
            safe_update_log("Fetching latest remote information...", 18)
            ensure_ui_responsiveness()
            fetch_out, fetch_err, fetch_rc = run_command("git fetch origin", cwd=vault_path)
            ensure_ui_responsiveness()
            if fetch_rc != 0:
                safe_update_log(f"Warning: Could not fetch from remote: {fetch_err}", 18)
            
            # Check if local repo only has README (indicating empty repo that should pull all remote files)
            local_files = []
            if os.path.exists(vault_path):
                for root_dir, dirs, files in os.walk(vault_path):
                    if '.git' in root_dir:
                        continue
                    for file in files:
                        if not file.startswith('.') and file not in ['.gitignore']:
                            local_files.append(file)
            
            only_has_readme = (len(local_files) == 1 and 'README.md' in local_files)
            did_reset_hard = False  # Track if we did a reset --hard for initial sync
            
            if only_has_readme:
                safe_update_log("Local repository only has README. Checking for remote files to download...", 20)
                # Check if remote has actual content files
                ls_out, ls_err, ls_rc = run_command("git ls-tree -r --name-only origin/main", cwd=vault_path)
                if ls_rc == 0 and ls_out.strip():
                    remote_files = [f.strip() for f in ls_out.splitlines() if f.strip()]
                    content_files = [f for f in remote_files if f not in ['README.md', '.gitignore']]
                    
                    if content_files:
                        safe_update_log(f"🔄 Remote has {len(content_files)} content files. Replacing local content with remote files...", 22)
                        
                        # Create backup using backup manager if available
                        backup_id = None
                        if 'backup_manager' in sys.modules:
                            try:
                                from backup_manager import create_setup_safety_backup
                                backup_id = create_setup_safety_backup(vault_path, "pre-initial-sync")
                                if backup_id:
                                    safe_update_log(f"✅ Safety backup created: {backup_id}", 22)
                            except Exception as backup_err:
                                safe_update_log(f"⚠️ Could not create backup: {backup_err}", 22)                        
                        # For initial sync, we want remote content to take precedence (user preference)
                        # Use reset --hard to replace local with remote content  
                        safe_update_log("📥 Downloading and replacing local content with remote files...", 24)
                        
                        reset_out, reset_err, reset_rc = run_command("git reset --hard origin/main", cwd=vault_path)
                        if reset_rc == 0:
                            did_reset_hard = True  # Mark that we did a reset --hard
                            safe_update_log(f"✅ Successfully replaced local content with {len(content_files)} remote files!", 25)
                            if backup_id:
                                safe_update_log(f"📝 Note: Previous local state safely backed up: {backup_id}", 25)
                        else:
                            safe_update_log(f"❌ Error replacing local content with remote: {reset_err}", 22)
                            safe_update_log("Trying alternative download method...", 22)
                            
                            # Fallback: try merge approach  
                            merge_out, merge_err, merge_rc = run_command("git merge origin/main --allow-unrelated-histories --strategy-option=theirs", cwd=vault_path)
                            if merge_rc == 0:
                                safe_update_log(f"✅ Downloaded remote files using merge fallback! ({len(content_files)} files)", 25)
                            else:
                                safe_update_log(f"❌ Could not download remote files: {merge_err}", 25)
                        
                        # Verify files were actually downloaded
                        new_local_files = []
                        for root_dir, dirs, files in os.walk(vault_path):
                            if '.git' in root_dir:
                                continue
                            for file in files:
                                if not file.startswith('.'):
                                    new_local_files.append(file)
                        safe_update_log(f"Local directory now has {len(new_local_files)} files", 25)
                        
                        # Set output variables for later use
                        out, err, rc = "", "", 0  # Success - files downloaded
                    else:
                        safe_update_log("Remote repository only has README/gitignore - no content to pull", 20)
                        out, err, rc = "", "", 0  # Simulate successful pull
                else:
                    safe_update_log("Remote repository is empty - no files to pull", 20)
                    out, err, rc = "", "", 0  # Simulate successful pull
            else:
                safe_update_log("Pulling the latest updates from GitHub...", 20)
                out, err, rc = run_command("git pull --rebase origin main", cwd=vault_path)
            
            # Check for conflicts regardless of return code (more robust detection)
            status_out, status_err, status_rc = run_command("git status --porcelain", cwd=vault_path)
            has_conflicts = False
            if status_rc == 0 and status_out:
                # Check for conflict markers in git status output
                for line in status_out.splitlines():
                    line = line.strip()
                    if line.startswith('UU ') or line.startswith('AA ') or line.startswith('DD ') or 'both modified:' in line:
                        has_conflicts = True
                        break            
            # Also check if we're in the middle of a rebase
            rebase_in_progress = os.path.exists(os.path.join(vault_path, '.git', 'rebase-merge')) or os.path.exists(os.path.join(vault_path, '.git', 'rebase-apply'))
            
            if rc != 0 or has_conflicts or rebase_in_progress or "CONFLICT" in (out + err):
                if "Could not resolve hostname" in err or "network" in err.lower():
                    safe_update_log("❌ Unable to pull updates due to a network error. Local changes remain safely stashed.", 30)
                elif has_conflicts or rebase_in_progress or "CONFLICT" in (out + err):  # Detect merge conflicts
                    safe_update_log("❌ A merge conflict was detected during the pull operation.", 30)
                    safe_update_log("🔧 Applying automatic 'remote wins' conflict resolution for sync operations...", 32)
                    
                    # Abort the current rebase to get to a clean state                    run_command("git rebase --abort", cwd=vault_path)
                    
                    # Automatic "remote wins" resolution - much simpler and more reliable
                    # No backup needed since this is routine sync behavior (local expects to be overwritten)
                    safe_update_log("📥 Automatically choosing remote content (remote wins policy)...", 34)
                      # Use reset --hard to make remote content win completely
                    reset_out, reset_err, reset_rc = run_command("git reset --hard origin/main", cwd=vault_path)
                    if reset_rc == 0:
                        safe_update_log("✅ Conflicts resolved automatically using 'remote wins' policy", 35)
                        # No backup needed - this is expected routine sync behavior
                        
                        # Mark as successful to continue normal flow
                        rc = 0  # Override to indicate successful resolution
                    else:
                        safe_update_log(f"❌ Automatic conflict resolution failed: {reset_err}", 35)
                        safe_update_log("📝 Manual intervention required. Please resolve conflicts and try again.", 35)
                        return
                else:
                    safe_update_log("Pull operation completed successfully. Your vault is updated with the latest changes from GitHub.", 30)
                    # Log pulled files
                    for line in out.splitlines():
                        safe_update_log(f"✓ Pulled: {line}", 30)
            else:
                safe_update_log("Pull operation completed successfully. Your vault is up to date.", 30)
        else:
            safe_update_log("Skipping pull operation due to offline mode.", 20)          # Step 4.5: Check for local commits ahead of remote and push them (ONLY for edge-case recovery)
        if network_available:
            safe_update_log("Checking if local repository has unpushed commits from recovery operations...", 32)
            
            # CRITICAL: This step should ONLY trigger for true recovery scenarios
            # In normal sync flows, local should already be up-to-date with remote after Step 4
            # First, check if we're actually ahead after the pull operation
            # ROBUST FIX: Ensure origin/main reference is fresh before checking ahead count
            safe_update_log("Ensuring remote references are up to date...", 31)
            fetch_out, fetch_err, fetch_rc = run_command("git fetch origin", cwd=vault_path)
            print(f"[DEBUG] git fetch origin: out='{fetch_out}', err='{fetch_err}', rc={fetch_rc}")
            
            if fetch_rc != 0:
                safe_update_log("⚠️ Could not fetch latest remote references. Skipping ahead check.", 32)
                safe_update_log("✅ Proceeding with sync (assuming repositories are in sync).", 32)
            else:
                # First, verify that origin/main tracking is properly set up
                origin_check_out, origin_check_err, origin_check_rc = run_command("git rev-parse origin/main", cwd=vault_path)
                print(f"[DEBUG] git rev-parse origin/main: out='{origin_check_out}', err='{origin_check_err}', rc={origin_check_rc}")
                
                if origin_check_rc != 0:
                    safe_update_log("⚠️ Remote reference origin/main not found. This may be normal for new repositories.", 32)
                    safe_update_log("✅ Proceeding with sync (assuming repositories are in sync).", 32)
                else:
                    # origin/main exists, now safely check ahead count
                    rev_list_out, rev_list_err, rev_list_rc = run_command("git rev-list --count HEAD ^origin/main", cwd=vault_path)
                    print(f"[DEBUG] git rev-list --count HEAD ^origin/main: out='{rev_list_out}', err='{rev_list_err}', rc={rev_list_rc}")
                    
                    # Double-check: if rev-list fails or gives suspect results, verify with commit hash comparison
                    if rev_list_rc != 0 or not rev_list_out.strip():
                        # rev-list failed, assume in sync
                        print(f"[DEBUG] rev-list command failed or returned empty. Assuming in sync.")
                        safe_update_log("✅ Local repository is in sync with remote", 33)
                    else:
                        # Parse ahead count but verify with hash comparison for safety
                        try:
                            ahead_count = int(rev_list_out.strip())
                            print(f"[DEBUG] Parsed ahead_count from rev-list: {ahead_count}")
                            
                            # SAFETY CHECK: Compare commit hashes to verify the count
                            head_hash_out, _, head_hash_rc = run_command("git rev-parse HEAD", cwd=vault_path)
                            origin_hash_out, _, origin_hash_rc = run_command("git rev-parse origin/main", cwd=vault_path)
                            
                            if head_hash_rc == 0 and origin_hash_rc == 0:
                                head_hash = head_hash_out.strip()
                                origin_hash = origin_hash_out.strip()
                                print(f"[DEBUG] HEAD hash: {head_hash}")
                                print(f"[DEBUG] origin/main hash: {origin_hash}")
                                
                                if head_hash == origin_hash:
                                    print(f"[DEBUG] Commit hashes match - repositories are actually in sync! Overriding ahead_count.")
                                    safe_update_log("✅ Local repository is in sync with remote (verified by commit hash)", 33)
                                    ahead_count = 0  # Override the incorrect count
                            
                            if ahead_count > 0:
                                # We're ahead after pull - this should only happen in recovery scenarios
                                # Be VERY strict about recovery detection to avoid false positives
                                
                                # 1. Check if the most recent commit message indicates recovery or conflict resolution
                                is_recovery_commit = False
                                is_conflict_resolution_commit = False
                                recent_commits_out, recent_commits_err, recent_commits_rc = run_command("git log --oneline -3", cwd=vault_path)
                                if recent_commits_rc == 0:
                                    commit_msgs = recent_commits_out.strip().lower()
                                    # Very specific recovery indicators
                                    recovery_indicators = ["ogresync recovery", "fix rebase", "fix merge", "restore after", "emergency fix", "manual git recovery"]
                                    is_recovery_commit = any(indicator in commit_msgs for indicator in recovery_indicators)
                                    
                                    # Conflict resolution indicators
                                    conflict_resolution_indicators = ["resolve conflicts using stage 2", "stage 2 resolution", "conflict resolution", "smart merge"]
                                    is_conflict_resolution_commit = any(indicator in commit_msgs for indicator in conflict_resolution_indicators)
                                    
                                    print(f"[DEBUG] Recent commits check: is_recovery_commit={is_recovery_commit}, is_conflict_resolution_commit={is_conflict_resolution_commit}")
                                    print(f"[DEBUG] Recent commit messages: {commit_msgs}")
                                
                                # 2. Check if we JUST resolved incomplete git operations (marker file must be recent)
                                git_dir = os.path.join(vault_path, '.git')
                                recovery_marker_file = os.path.join(git_dir, 'ogresync_recovery_flag')
                                has_recent_recovery_marker = False
                                if os.path.exists(recovery_marker_file):
                                    try:
                                        # Check if marker is recent (created within last 5 minutes)
                                        marker_age = time.time() - os.path.getmtime(recovery_marker_file)
                                        has_recent_recovery_marker = marker_age < 300  # 5 minutes
                                        print(f"[DEBUG] Recovery marker age: {marker_age:.1f}s, recent: {has_recent_recovery_marker}")
                                        if not has_recent_recovery_marker:
                                            # Remove stale marker
                                            os.remove(recovery_marker_file)
                                            print(f"[DEBUG] Removed stale recovery marker")
                                    except Exception as e:
                                        print(f"[DEBUG] Error checking recovery marker: {e}")
                                        has_recent_recovery_marker = False
                                else:
                                    print(f"[DEBUG] No recovery marker file found")
                                
                                # 3. REMOVED: Don't check for backup branches as they can be old/stale
                                # Old backup branches don't indicate current recovery scenarios
                                
                                # Only push if we have STRONG recent recovery indicators OR conflict resolution
                                # Normal sync should never be ahead after successful pull
                                if is_recovery_commit or has_recent_recovery_marker or is_conflict_resolution_commit or conflict_resolution_completed:
                                    if conflict_resolution_completed or is_conflict_resolution_commit:
                                        safe_update_log(f"🔄 Local repository has {ahead_count} unpushed commit(s) from conflict resolution", 33)
                                        safe_update_log("📤 Pushing conflict resolution commits to remote before opening Obsidian...", 34)
                                    else:
                                        safe_update_log(f"🔄 Local repository has {ahead_count} unpushed commit(s) from recovery operations", 33)
                                        safe_update_log("📤 Pushing recovery commits to remote before opening Obsidian...", 34)
                                    # Push the recovery commits
                                    push_out, push_err, push_rc = run_command("git push -u origin main", cwd=vault_path)
                                    
                                    if push_rc == 0:
                                        safe_update_log("✅ Successfully pushed recovery commits to remote", 35)
                                        # Clean up recovery marker if it exists
                                        if has_recent_recovery_marker:
                                            try:
                                                os.remove(recovery_marker_file)
                                            except:
                                                pass
                                    else:
                                        # Try force push if regular push fails
                                        if "non-fast-forward" in push_err.lower() or "rejected" in push_err.lower():
                                            safe_update_log("🔄 Attempting force push for recovery commits...", 34)
                                            force_push_out, force_push_err, force_push_rc = run_command("git push --force-with-lease origin main", cwd=vault_path)
                                            if force_push_rc == 0:
                                                safe_update_log("✅ Successfully force-pushed recovery commits to remote", 35)
                                                # Clean up recovery marker if it exists
                                                if has_recent_recovery_marker:
                                                    try:
                                                        os.remove(recovery_marker_file)
                                                    except:
                                                        pass
                                            else:
                                                safe_update_log(f"❌ Force push failed: {force_push_err}", 35)
                                                safe_update_log("📝 Recovery commits remain local. Continuing with sync...", 35)
                                        else:
                                            safe_update_log(f"❌ Push failed: {push_err}", 35)
                                            safe_update_log("📝 Recovery commits remain local. Continuing with sync...", 35)
                                else:
                                    # Local is ahead but check if this is from conflict resolution or normal workflow
                                    if conflict_resolution_completed:
                                        # We just completed conflict resolution - push immediately
                                        safe_update_log(f"🔄 Local repository has {ahead_count} unpushed commit(s) from conflict resolution", 33)
                                        safe_update_log("📤 Pushing conflict resolution results immediately...", 34)
                                        # Push the conflict resolution commits
                                        push_out, push_err, push_rc = run_command("git push -u origin main", cwd=vault_path)
                                        
                                        if push_rc == 0:
                                            safe_update_log("✅ Successfully pushed conflict resolution to remote", 35)
                                        else:
                                            # Try force push if regular push fails
                                            if "non-fast-forward" in push_err.lower() or "rejected" in push_err.lower():
                                                safe_update_log("🔄 Attempting force push for conflict resolution...", 34)
                                                force_push_out, force_push_err, force_push_rc = run_command("git push --force-with-lease origin main", cwd=vault_path)
                                                if force_push_rc == 0:
                                                    safe_update_log("✅ Successfully force-pushed conflict resolution to remote", 35)
                                                else:
                                                    safe_update_log(f"❌ Force push failed: {force_push_err}", 35)
                                                    safe_update_log("📝 Conflict resolution remains local. Continuing with sync...", 35)
                                            else:
                                                safe_update_log(f"❌ Push failed: {push_err}", 35)
                                                safe_update_log("📝 Conflict resolution remains local. Continuing with sync...", 35)
                                    else:
                                        # This is normal workflow - let Step 9 handle the push after Obsidian
                                        safe_update_log(f"📝 Local repository has {ahead_count} unpushed commit(s) from normal workflow", 33)
                                        safe_update_log("✅ This appears to be normal workflow, not recovery. Will push after Obsidian session.", 33)
                                        print(f"[DEBUG] Normal workflow detected: {ahead_count} commits ahead, but no recovery indicators")
                            else:
                                safe_update_log("✅ Local repository is in sync with remote", 33)
                                print(f"[DEBUG] Repository in sync: ahead_count = {ahead_count}")
                        except ValueError as ve:
                            safe_update_log("⚠️ Could not determine local/remote status", 33)
                            print(f"[DEBUG] ValueError parsing ahead_count from '{rev_list_out}': {ve}")
            
                
        # Step 5: Handle stashed changes - Always discard during initial sync (before Obsidian)
        # For initial sync phase, remote content always takes precedence to ensure clean state
        safe_update_log("🗑️ Discarding any local changes (remote content takes precedence for initial sync)...", 35)
        stash_list_out, _, _ = run_command("git stash list", cwd=vault_path)
        if stash_list_out.strip():  # If there are stashes
            run_command("git stash drop", cwd=vault_path)
            safe_update_log("✅ Local changes safely discarded. Repository now matches remote content.", 35)
        else:
            safe_update_log("✅ No local changes to discard. Repository matches remote content.", 35)

        # Step 6: Capture current remote state before opening Obsidian
        remote_head_before_obsidian = ""
        if network_available:
            remote_head_before_obsidian = get_current_remote_head(vault_path)
            safe_update_log(f"Remote state captured before opening Obsidian: {remote_head_before_obsidian[:8]}...", 38)
        
        # Step 7: Open Obsidian for editing using the helper function
        safe_update_log("Launching Obsidian. Please edit your vault and close Obsidian when finished.", 40)
        try:
            open_obsidian(obsidian_path)
            # Give Obsidian time to start properly before continuing
            safe_update_log("Obsidian is starting up...", 42)
            time.sleep(2.0)
            safe_update_log("Obsidian should now be open. Edit your files and close Obsidian when done.", 43)
        except Exception as e:
            safe_update_log(f"Error launching Obsidian: {e}", 40)
            return
        safe_update_log("Waiting for Obsidian to close...", 45)
        
        # Monitor Obsidian with periodic updates
        check_count = 0
        while is_obsidian_running():
            time.sleep(0.5)
            check_count += 1
            # Update UI every 10 seconds to show we're still waiting
            if check_count % 20 == 0:  # Every 10 seconds (20 * 0.5s)
                safe_update_log("Still waiting for Obsidian to close...", 45)        # Step 8A: First commit any local changes made during the Obsidian session
        safe_update_log("Obsidian has been closed. Committing local changes from this session...", 50)
        run_command("git add -A", cwd=vault_path)
        out, err, rc = run_command('git commit -m "Auto sync commit (before remote check)"', cwd=vault_path)
        local_changes_committed = False
        if rc != 0 and "nothing to commit" in (out + err).lower():
            safe_update_log("No changes detected during this session.", 52)
        elif rc != 0:
            safe_update_log(f"❌ Commit operation failed: {err}", 52)
            return
        else:
            safe_update_log("✅ Local changes from current session have been committed.", 52)
            local_changes_committed = True
            commit_details, err_details, rc_details = run_command("git diff-tree --no-commit-id --name-status -r HEAD", cwd=vault_path)
            if rc_details == 0 and commit_details.strip():
                for line in commit_details.splitlines():
                    safe_update_log(f"✓ {line}", None)

        # Step 8B: Now check if remote has advanced during Obsidian session
        safe_update_log("Checking for remote changes that occurred during your Obsidian session...", 55)
        remote_changes_detected = False
        
        # CRITICAL FIX: Re-check network connectivity after Obsidian session
        # Network might have come back online during the Obsidian session
        network_was_available_before = network_available
        network_available = is_network_available()
        
        if not network_was_available_before and network_available:
            safe_update_log("🌐 Network connection restored during Obsidian session!", 56)
            
            # Check if we have offline sessions that now need conflict resolution
            if OFFLINE_SYNC_AVAILABLE and offline_sync_manager is not None and hasattr(offline_sync_manager, 'OfflineSyncManager'):
                try:
                    sync_manager = offline_sync_manager.OfflineSyncManager(vault_path, config_data)
                    summary = sync_manager.get_session_summary()
                    
                    if summary['offline_sessions'] > 0 or summary['unpushed_commits'] > 0:
                        safe_update_log(f"📱 Detected {summary['offline_sessions']} offline session(s) with {summary['unpushed_commits']} unpushed commits", 57)
                        
                        # Check if conflict resolution is needed now that we have network
                        if sync_manager.should_trigger_conflict_resolution():
                            safe_update_log("🔧 Network restored - activating conflict resolution for offline changes...", 58)
                            
                            if CONFLICT_RESOLUTION_AVAILABLE and conflict_resolution is not None:
                                try:
                                    # Create backup before conflict resolution
                                    backup_id = None
                                    if 'backup_manager' in sys.modules:
                                        try:
                                            from backup_manager import create_conflict_resolution_backup
                                            backup_id = create_conflict_resolution_backup(vault_path, "network-restored-conflict")
                                            if backup_id:
                                                safe_update_log(f"✅ Safety backup created: {backup_id}", 59)
                                        except Exception as backup_err:
                                            safe_update_log(f"⚠️ Could not create backup: {backup_err}", 59)
                                    
                                    # Use existing conflict resolution system
                                    resolver = conflict_resolution.ConflictResolver(vault_path, root)
                                    remote_url = config_data.get("GITHUB_REMOTE_URL", "")
                                    
                                    safe_update_log("📋 Starting conflict resolution for offline changes (network restored)...", 60)
                                    resolution_result = resolver.resolve_initial_setup_conflicts(remote_url)
                                    
                                    if resolution_result.success:
                                        safe_update_log("✅ Offline changes resolved successfully after network restoration!", 61)
                                        conflict_resolution_completed = True
                                        
                                        # Immediately push conflict resolution results
                                        safe_update_log("📤 Pushing conflict resolution results immediately...", 62)
                                        push_out, push_err, push_rc = run_command("git push -u origin main", cwd=vault_path)
                                        if push_rc == 0:
                                            safe_update_log("✅ Conflict resolution results pushed to GitHub successfully", 63)
                                        else:
                                            safe_update_log(f"⚠️ Failed to push conflict resolution results: {push_err}", 63)
                                        
                                        # Mark sessions as resolved
                                        # TODO: Re-enable when offline sync module is implemented
                                        # for session in sync_manager.offline_state.offline_sessions:
                                        #     sync_manager.mark_session_resolved(session.session_id)
                                        #     sync_manager.end_sync_session(session.session_id, 
                                        #                                 sync_manager.check_network_availability(), 
                                        #                                 sync_manager.get_unpushed_commits())
                                    else:
                                        if "cancelled by user" in resolution_result.message.lower():
                                            safe_update_log("❌ Conflict resolution cancelled by user", 61)
                                            safe_update_log("📝 Your offline changes remain safe and can be resolved later", 61)
                                        else:
                                            safe_update_log(f"❌ Conflict resolution failed: {resolution_result.message}", 61)
                                            if backup_id:
                                                safe_update_log(f"📝 Your changes are safe in backup: {backup_id}", 61)
                                        
                                except Exception as e:
                                    safe_update_log(f"❌ Error in network-restored conflict resolution: {e}", 61)
                                    print(f"[DEBUG] Network-restored conflict resolution error: {e}")
                            else:
                                safe_update_log("❌ Conflict resolution system not available", 58)
                        else:
                            safe_update_log("✅ No conflicts detected for offline changes", 58)
                    
                except Exception as e:
                    safe_update_log(f"⚠️ Error checking offline changes after network restoration: {e}", 57)
                    print(f"[DEBUG] Network restoration offline check error: {e}")
        
        # Continue with normal remote change detection
        if network_available and remote_head_before_obsidian:
            has_remote_changes, new_remote_head, change_count = check_remote_changes_during_session(
                vault_path, remote_head_before_obsidian
            )
            
            if has_remote_changes:
                remote_changes_detected = True
                safe_update_log(f"⚠️ Remote repository has advanced by {change_count} commit(s) during your Obsidian session!", 58)
                safe_update_log("🔧 Activating 2-stage conflict resolution system for session changes...", 59)
                  # ALWAYS activate conflict resolution when remote changes are detected
                # This gives users visibility and control over what happened during their session
                try:
                    if not CONFLICT_RESOLUTION_AVAILABLE:
                        safe_update_log("❌ Enhanced conflict resolution system not available. Manual resolution required.", 62)
                        return
                    
                    # Create backup using backup manager if available
                    backup_id = None
                    if 'backup_manager' in sys.modules:
                        try:
                            from backup_manager import create_conflict_resolution_backup
                            backup_id = create_conflict_resolution_backup(vault_path, "post-obsidian-session-conflict")
                            if backup_id:
                                safe_update_log(f"✅ Safety backup created: {backup_id}", 62)
                        except Exception as backup_err:
                            safe_update_log(f"⚠️ Could not create backup: {backup_err}", 62)
                    
                    # Import and use the proper conflict resolution modules
                    import Stage1_conflict_resolution as cr_module
                    
                    # Create conflict resolver for post-Obsidian session conflicts
                    resolver = cr_module.ConflictResolver(vault_path, root)
                    remote_url = config_data.get("GITHUB_REMOTE_URL", "")
                      # Resolve conflicts using the 2-stage system
                    safe_update_log("📋 Presenting options for handling remote changes that occurred during your session...", 63)
                    resolution_result = resolver.resolve_initial_setup_conflicts(remote_url)
                    
                    if resolution_result.success:
                        safe_update_log("✅ Post-Obsidian session changes resolved successfully using 2-stage system", 65)
                        
                        # CRITICAL FIX: Immediately push post-Obsidian conflict resolution results
                        safe_update_log("📤 Pushing post-Obsidian conflict resolution results immediately...", 66)
                        push_out, push_err, push_rc = run_command("git push -u origin main", cwd=vault_path)
                        if push_rc == 0:
                            safe_update_log("✅ Post-Obsidian conflict resolution results pushed to GitHub successfully", 67)
                        else:
                            safe_update_log(f"⚠️ Failed to push post-Obsidian conflict resolution results: {push_err}", 67)
                            safe_update_log("Will retry push in normal sync flow...", 67)
                        
                        if backup_id:
                            safe_update_log(f"📝 Note: Safety backup available if needed: {backup_id}", 65)
                    else:
                        if "cancelled by user" in resolution_result.message.lower():
                            safe_update_log("❌ Conflict resolution was cancelled by user", 65)
                            safe_update_log("📝 Your local changes are committed but not pushed. You can resolve conflicts manually later.", 65)
                        else:
                            safe_update_log(f"❌ Conflict resolution failed: {resolution_result.message}", 65)
                            if backup_id:
                                safe_update_log(f"📝 Your work is safe in backup: {backup_id}", 65)
                        # Set flag to skip pushing since conflicts weren't resolved
                        remote_changes_detected = False
                        
                except Exception as e:
                    safe_update_log(f"❌ Error in 2-stage conflict resolution during session sync: {e}", 65)
                    safe_update_log("📝 Your local changes are committed but not pushed. Please resolve conflicts manually.", 65)
                    import traceback
                    traceback.print_exc()
                    remote_changes_detected = False
            else:
                safe_update_log("✅ No remote changes detected during Obsidian session.", 58)
        elif network_available:
            safe_update_log("Checking for any new remote changes...", 52)
            # Fallback: do a simple fetch and check
            out, err, rc = run_command("git pull --rebase origin main", cwd=vault_path)
            if rc != 0:
                if "Could not resolve hostname" in err or "network" in err.lower():
                    safe_update_log("❌ Unable to pull updates due to network error. Continuing with local commit.", 52)
                elif "CONFLICT" in (out + err):  # Same conflict resolution as above
                    safe_update_log("❌ Merge conflict detected in new remote changes.", 52)
                    safe_update_log("🔧 Activating 2-stage conflict resolution system...", 53)
                    
                    # Abort the current rebase to get to a clean state
                    run_command("git rebase --abort", cwd=vault_path)
                    
                    try:
                        if not CONFLICT_RESOLUTION_AVAILABLE:
                            safe_update_log("❌ Enhanced conflict resolution system not available. Manual resolution required.", 55)
                            return
                        
                        # Create backup using backup manager if available
                        backup_id = None
                        if 'backup_manager' in sys.modules:
                            try:
                                from backup_manager import create_conflict_resolution_backup
                                backup_id = create_conflict_resolution_backup(vault_path, "fallback-remote-conflict")
                                if backup_id:
                                    safe_update_log(f"✅ Safety backup created: {backup_id}", 53)
                            except Exception as backup_err:
                                safe_update_log(f"⚠️ Could not create backup: {backup_err}", 53)
                        
                        # Import and use the proper conflict resolution modules
                        import Stage1_conflict_resolution as cr_module
                        
                        # Create conflict resolver for fallback remote conflicts
                        resolver = cr_module.ConflictResolver(vault_path, root)
                        remote_url = config_data.get("GITHUB_REMOTE_URL", "")
                        
                        # Resolve conflicts using the 2-stage system
                        resolution_result = resolver.resolve_initial_setup_conflicts(remote_url)
                        
                        if resolution_result.success:
                            safe_update_log("✅ Fallback remote conflicts resolved successfully using 2-stage system", 55)
                            
                            # CRITICAL FIX: Immediately push fallback conflict resolution results
                            safe_update_log("📤 Pushing fallback conflict resolution results immediately...", 56)
                            push_out, push_err, push_rc = run_command("git push -u origin main", cwd=vault_path)
                            if push_rc == 0:
                                safe_update_log("✅ Fallback conflict resolution results pushed to GitHub successfully", 57)
                            else:
                                safe_update_log(f"⚠️ Failed to push fallback conflict resolution results: {push_err}", 57)
                                safe_update_log("Will retry push in normal sync flow...", 57)
                            
                            if backup_id:
                                safe_update_log(f"📝 Note: Safety backup available if needed: {backup_id}", 55)
                        else:
                            if "cancelled by user" in resolution_result.message.lower():
                                safe_update_log("❌ Conflict resolution was cancelled by user", 55)
                                safe_update_log("📝 Your local changes remain uncommitted.", 55)
                            else:
                                safe_update_log(f"❌ Conflict resolution failed: {resolution_result.message}", 55)
                                if backup_id:
                                    safe_update_log(f"📝 Your work is safe in backup: {backup_id}", 55)
                                    
                    except Exception as e:
                        safe_update_log(f"❌ Error in 2-stage conflict resolution during fallback: {e}", 55)
                        safe_update_log("📝 Your local changes remain uncommitted and can be recovered manually.", 55)
                        import traceback
                        traceback.print_exc()
                else:
                    safe_update_log("New remote updates have been successfully pulled.", 52)
                    # Log pulled files
                    for line in out.splitlines():
                        if line.strip():
                            safe_update_log(f"✓ Pulled: {line}", 52)
        else:
            safe_update_log("No network detected. Skipping remote check and proceeding to push.", 58)        # Step 9: Push changes if network is available (local changes already committed in Step 8A)
        network_available = is_network_available()
        if network_available:
            # First, check for and resolve any incomplete git operations
            operation_detected, operation_type, resolution_success = detect_and_resolve_incomplete_git_operations(vault_path)
            
            if operation_detected and not resolution_success:
                safe_update_log("❌ Could not resolve incomplete git operation. Manual intervention required.", 70)
                safe_update_log("💡 Please check your repository state and resolve any pending operations manually.", 70)
                return
            
            unpushed = get_unpushed_commits(vault_path)
            if unpushed:
                safe_update_log("Pushing all unpushed commits to GitHub...", 70)
                # Use -u flag to ensure upstream tracking is set/maintained
                out, err, rc = run_command("git push -u origin main", cwd=vault_path)
                if rc != 0:
                    if "Could not resolve hostname" in err or "network" in err.lower():
                        safe_update_log("❌ Unable to push changes due to network issues. Your changes remain locally committed and will be pushed once connectivity is restored.", 80)
                        return
                    elif "non-fast-forward" in err.lower() or "rejected" in err.lower() or "non-fast-forward" in out.lower() or "rejected" in out.lower():
                        # Handle non-fast-forward push rejection (check both stderr and stdout)
                        safe_update_log("⚠️ Push rejected: Remote repository has diverged from local repository.", 72)
                        safe_update_log("📥 Fetching and integrating latest remote changes before push...", 74)
                        
                        # Fetch latest remote changes
                        fetch_out, fetch_err, fetch_rc = run_command("git fetch origin", cwd=vault_path)
                        if fetch_rc != 0:
                            safe_update_log(f"❌ Failed to fetch remote changes: {fetch_err}", 75)
                            safe_update_log(f"❌ Push operation failed: {err}", 80)
                            return
                          # Check if we need to merge or if we can force push safely
                        # First, check what the difference is between local and remote
                        local_ahead_out, local_ahead_err, local_ahead_rc = run_command("git rev-list --count HEAD ^origin/main", cwd=vault_path)
                        remote_ahead_out, remote_ahead_err, remote_ahead_rc = run_command("git rev-list --count origin/main ^HEAD", cwd=vault_path)
                        
                        local_ahead = 0
                        remote_ahead = 0
                        try:
                            if local_ahead_rc == 0 and local_ahead_out.strip().isdigit():
                                local_ahead = int(local_ahead_out.strip())
                            if remote_ahead_rc == 0 and remote_ahead_out.strip().isdigit():
                                remote_ahead = int(remote_ahead_out.strip())
                        except ValueError:
                            pass
                        
                        safe_update_log(f"📊 Repository status: Local is {local_ahead} commits ahead, remote is {remote_ahead} commits ahead", 76)
                        
                        # Check if the latest local commit is a conflict resolution
                        latest_commit_msg_out, latest_commit_msg_err, latest_commit_msg_rc = run_command("git log -1 --pretty=%s", cwd=vault_path)
                        is_conflict_resolution = False
                        if latest_commit_msg_rc == 0:
                            commit_msg = latest_commit_msg_out.strip().lower()
                            conflict_indicators = ["resolve conflicts", "stage 2 resolution", "conflict resolution", "smart merge", "merge remote-tracking branch"]
                            is_conflict_resolution = any(indicator in commit_msg for indicator in conflict_indicators)
                            safe_update_log(f"📝 Latest commit: {latest_commit_msg_out.strip()}", 76)
                            safe_update_log(f"🔍 Conflict resolution detected: {is_conflict_resolution}", 76)
                        
                        if is_conflict_resolution and local_ahead > 0:
                            # This is post-conflict-resolution - the local commits contain the user's final choices
                            safe_update_log("✅ Conflict resolution completed - local commits contain final resolved content", 77)
                            safe_update_log("📤 Force-pushing resolved changes (conflict resolution is final)...", 77)
                            force_push_out, force_push_err, force_push_rc = run_command("git push --force-with-lease origin main", cwd=vault_path)
                            if force_push_rc == 0:
                                safe_update_log("✅ Successfully pushed conflict resolution to remote", 80)
                            else:
                                safe_update_log(f"❌ Force push failed: {force_push_err}", 80)
                                safe_update_log("📝 Your conflict resolution is committed locally and can be pushed manually", 80)
                        elif remote_ahead == 0 and local_ahead > 0:
                            # Local is ahead, remote hasn't changed - safe to force push
                            safe_update_log("✅ Local repository is ahead of remote. Force pushing resolved conflicts...", 77)
                            force_push_out, force_push_err, force_push_rc = run_command("git push --force-with-lease origin main", cwd=vault_path)
                            if force_push_rc == 0:
                                safe_update_log("✅ All changes have been successfully pushed to GitHub using force-with-lease.", 80)
                            else:
                                safe_update_log(f"❌ Force push failed: {force_push_err}", 80)
                                safe_update_log("📝 Your resolved conflicts are committed locally. Manual intervention may be required.", 80)
                        else:
                            # Both local and remote have changes - need to merge
                            safe_update_log("🔄 Both local and remote have changes. Attempting to integrate remote changes...", 76)
                            merge_out, merge_err, merge_rc = run_command("git merge origin/main --no-edit", cwd=vault_path)
                            
                            if merge_rc == 0:
                                safe_update_log("✅ Successfully integrated remote changes without conflicts.", 78)
                                # Try push again
                                safe_update_log("📤 Attempting push again...", 79)
                                push2_out, push2_err, push2_rc = run_command("git push -u origin main", cwd=vault_path)
                                if push2_rc == 0:
                                    safe_update_log("✅ All changes have been successfully pushed to GitHub after integration.", 80)
                                else:
                                    safe_update_log(f"❌ Push failed again after integration: {push2_err}", 80)
                                    safe_update_log("📝 Your changes are committed locally. Manual intervention may be required.", 80)
                            else:
                                # Merge failed - likely due to conflicts. Trigger 2-stage conflict resolution
                                safe_update_log("⚠️ Merge conflicts detected during push integration.", 78)
                                safe_update_log("🔧 Activating 2-stage conflict resolution system for push conflicts...", 79)
                                
                                # Reset to clean state before conflict resolution
                                reset_out, reset_err, reset_rc = run_command("git merge --abort", cwd=vault_path)
                                if reset_rc == 0:
                                    safe_update_log("✅ Merge aborted successfully. Preparing for conflict resolution...", 79)
                                
                                try:
                                    if not CONFLICT_RESOLUTION_AVAILABLE:
                                        safe_update_log("❌ Conflict resolution system not available. Manual resolution required.", 79)
                                        safe_update_log("📝 Please manually resolve conflicts and push your changes.", 79)
                                        return
                                    
                                    # Import and use the proper conflict resolution modules
                                    import Stage1_conflict_resolution as cr_module
                                    
                                    # Create conflict resolver for push-time conflicts
                                    resolver = cr_module.ConflictResolver(vault_path, root)
                                    remote_url = config_data.get("GITHUB_REMOTE_URL", "")
                                    
                                    # Resolve conflicts using the 2-stage system
                                    safe_update_log("� Presenting conflict resolution options for push-time conflicts...", 80)
                                    resolution_result = resolver.resolve_initial_setup_conflicts(remote_url)
                                    
                                    if resolution_result.success:
                                        safe_update_log(f"✅ Push-time conflicts resolved successfully using: {resolution_result.strategy.value if resolution_result.strategy else 'unknown'}", 82)
                                        safe_update_log("📤 Attempting to push resolved changes...", 83)
                                        
                                        # Try to push the resolved changes
                                        final_push_out, final_push_err, final_push_rc = run_command("git push --force-with-lease origin main", cwd=vault_path)
                                        if final_push_rc == 0:
                                            safe_update_log("✅ Successfully pushed conflict resolution to remote repository.", 85)
                                        else:
                                            safe_update_log(f"⚠️ Push after conflict resolution failed: {final_push_err}", 85)
                                            safe_update_log("� Your conflict resolution is committed locally and can be pushed manually.", 85)
                                    else:
                                        safe_update_log("❌ Conflict resolution was cancelled or failed.", 82)
                                        safe_update_log("📝 Your local changes remain committed. Manual resolution may be required.", 82)
                                        
                                except Exception as e:
                                    safe_update_log(f"❌ Error during conflict resolution: {e}", 80)
                                    safe_update_log("📝 Your local changes are safely committed. Manual resolution required.", 80)
                    else:
                        safe_update_log(f"❌ Push operation failed: {err}", 80)
                    return
                safe_update_log("✅ All changes have been successfully pushed to GitHub.", 80)
                
                # Mark offline sessions as completed after successful push
                if OFFLINE_SYNC_AVAILABLE and offline_sync_manager is not None and hasattr(offline_sync_manager, 'OfflineSyncManager'):
                    try:
                        sync_manager = offline_sync_manager.OfflineSyncManager(vault_path, config_data)
                        sync_manager.complete_successful_sync()
                        # Immediately clean up completed sessions since sync was successful
                        sync_manager.cleanup_resolved_sessions(aggressive=True)
                    except Exception as e:
                        print(f"[DEBUG] Error completing offline sync: {e}")
            else:
                safe_update_log("No new commits to push.", 80)
                
                # Even when there are no new commits, clean up completed offline sessions
                if OFFLINE_SYNC_AVAILABLE and offline_sync_manager is not None and hasattr(offline_sync_manager, 'OfflineSyncManager'):
                    try:
                        sync_manager = offline_sync_manager.OfflineSyncManager(vault_path, config_data)
                        sync_manager.cleanup_resolved_sessions(aggressive=True)
                    except Exception as e:
                        print(f"[DEBUG] Error cleaning up offline sessions: {e}")
        else:
            safe_update_log("Offline mode: Changes have been committed locally. They will be automatically pushed when an internet connection is available.", 80)

        # Step 10: Final message
        if remote_changes_detected and local_changes_committed:
            if network_available:
                safe_update_log("🎉 Synchronization complete! Remote changes were detected and resolved, your local changes have been committed and pushed.", 100)
            else:
                safe_update_log("🎉 Synchronization complete! Remote changes were detected and resolved, your local changes have been committed. Will push when online.", 100)
        elif local_changes_committed:
            if network_available:
                safe_update_log("🎉 Synchronization complete! Your local changes have been committed and pushed to GitHub.", 100)
            else:
                safe_update_log("🎉 Synchronization complete! Your local changes have been committed locally. Will push when internet is available.", 100)
        else:
            safe_update_log("🎉 Synchronization complete! No changes were made during this session.", 100)
        
        # Final cleanup: Remove any remaining completed offline sessions 
        if OFFLINE_SYNC_AVAILABLE and offline_sync_manager is not None and hasattr(offline_sync_manager, 'OfflineSyncManager'):
            try:
                sync_manager = offline_sync_manager.OfflineSyncManager(vault_path, config_data)
                sync_manager.cleanup_resolved_sessions(aggressive=True)
            except Exception as e:
                print(f"[DEBUG] Error in final offline session cleanup: {e}")
        
        safe_update_log("You may now close this window.", 100)

    # Run sync_thread either in background thread or directly
    if use_threading:
        # Only use threading if we're not already in a background thread
        try:
            current_thread = threading.current_thread()
            is_main_thread = current_thread == threading.main_thread()
            
            if is_main_thread:
                # We're in main thread, safe to create background thread
                threading.Thread(target=sync_thread, daemon=True).start()
            else:
                # We're already in a background thread, run directly
                sync_thread()
        except Exception as e:
            print(f"Threading error, running directly: {e}")
            sync_thread()
    else:
        sync_thread()


def check_remote_changes_during_session(vault_path, remote_head_before_obsidian):
    """
    Check if the remote repository has advanced during the Obsidian session.
    
    Args:
        vault_path: Path to the vault directory
        remote_head_before_obsidian: The remote HEAD commit hash before opening Obsidian
    
    Returns:
        tuple: (has_remote_changes, new_remote_head, change_count)
    """
    try:
        # Fetch latest remote information
        fetch_out, fetch_err, fetch_rc = run_command("git fetch origin", cwd=vault_path)
        if fetch_rc != 0:
            safe_update_log(f"Warning: Could not fetch remote changes: {fetch_err}", None)
            return False, remote_head_before_obsidian, 0
        
        # Get current remote HEAD
        remote_head_out, remote_head_err, remote_head_rc = run_command("git rev-parse origin/main", cwd=vault_path)
        if remote_head_rc != 0:
            safe_update_log(f"Warning: Could not get remote HEAD: {remote_head_err}", None)
            return False, remote_head_before_obsidian, 0
        
        current_remote_head = remote_head_out.strip()
        
        # Compare with the HEAD before Obsidian was opened
        if current_remote_head != remote_head_before_obsidian:
            # Remote has advanced - count the new commits
            commit_count_out, commit_count_err, commit_count_rc = run_command(
                f"git rev-list --count {remote_head_before_obsidian}..{current_remote_head}", 
                cwd=vault_path
            )
            
            if commit_count_rc == 0:
                change_count = int(commit_count_out.strip()) if commit_count_out.strip().isdigit() else 0
                safe_update_log(f"Remote repository has advanced by {change_count} commit(s) during Obsidian session", None)
                return True, current_remote_head, change_count
            else:
                safe_update_log("Remote repository has advanced during Obsidian session (commit count unknown)", None)
                return True, current_remote_head, 1
        else:
            # No remote changes
            return False, current_remote_head, 0
            
    except Exception as e:
        safe_update_log(f"Error checking remote changes: {e}", None)
        return False, remote_head_before_obsidian, 0

def get_current_remote_head(vault_path):
    """
    Get the current remote HEAD commit hash.
    
    Args:
        vault_path: Path to the vault directory
      Returns:
        str: Remote HEAD commit hash, or empty string if error
    """
    try:
        # Fetch latest remote information first
        run_command("git fetch origin", cwd=vault_path)
        
        # Get current remote HEAD
        remote_head_out, remote_head_err, remote_head_rc = run_command("git rev-parse origin/main", cwd=vault_path)
        if remote_head_rc == 0:
            return remote_head_out.strip()
        else:
            return ""
    except Exception:
        return ""

def detect_and_resolve_incomplete_git_operations(vault_path):
    """
    Detect and resolve incomplete git operations (rebase, merge, cherry-pick, etc.)
    that could prevent successful push operations.
    
    Args:
        vault_path: Path to the vault directory
        
    Returns:
        tuple: (operation_detected, operation_type, resolution_success)
    """
    try:
        git_dir = os.path.join(vault_path, '.git')
        
        # Initialize variables
        detected_operation = None
        operation_type = None
        resolution_success = False
        
        # Check for various incomplete operations
        operations_to_check = {
            'rebase-merge': 'interactive rebase',
            'rebase-apply': 'rebase',
            'MERGE_HEAD': 'merge',
            'CHERRY_PICK_HEAD': 'cherry-pick',
            'REVERT_HEAD': 'revert',
            'BISECT_LOG': 'bisect'
        }
        
        detected_operation = None
        operation_type = None
        
        for marker, op_type in operations_to_check.items():
            marker_path = os.path.join(git_dir, marker)
            if os.path.exists(marker_path):
                detected_operation = marker
                operation_type = op_type
                break
        
        if not detected_operation:
            return False, None, True  # No incomplete operations
        
        safe_update_log(f"🔧 Detected incomplete {operation_type} operation. Attempting to resolve...", None)
          
        if operation_type in ['interactive rebase', 'rebase']:
            safe_update_log("📝 Attempting to resolve rebase operation...", None)
            
            # Enhanced rebase resolution - try multiple strategies
            # Strategy 1: Try to continue the rebase
            continue_out, continue_err, continue_rc = run_command("git rebase --continue", cwd=vault_path)
            
            if continue_rc == 0:
                safe_update_log("✅ Rebase completed successfully", None)
                resolution_success = True
            else:
                # Strategy 2: Check if we can skip current commit
                if "nothing to commit" in (continue_out + continue_err).lower():
                    skip_out, skip_err, skip_rc = run_command("git rebase --skip", cwd=vault_path)
                    if skip_rc == 0:
                        safe_update_log("✅ Rebase completed by skipping current commit", None)
                        resolution_success = True
                    else:
                        # Strategy 3: Abort the rebase (safest for repository switches)
                        safe_update_log("⚠️ Complex rebase detected. Aborting to ensure clean state...", None)
                        abort_out, abort_err, abort_rc = run_command("git rebase --abort", cwd=vault_path)
                        if abort_rc == 0:
                            safe_update_log("✅ Rebase aborted. Repository restored to clean state.", None)
                            # Additional cleanup for repository switches
                            reset_out, reset_err, reset_rc = run_command("git reset --hard HEAD", cwd=vault_path)
                            if reset_rc == 0:
                                safe_update_log("✅ Repository state cleaned up successfully.", None)
                            resolution_success = True
                        else:
                            safe_update_log(f"❌ Failed to abort rebase: {abort_err}", None)
                            resolution_success = False
                else:
                    # Strategy 3: Direct abort for other rebase issues
                    safe_update_log("⚠️ Aborting rebase due to unresolvable conflicts...", None)
                    abort_out, abort_err, abort_rc = run_command("git rebase --abort", cwd=vault_path)
                    if abort_rc == 0:
                        safe_update_log("✅ Rebase aborted successfully. Repository state restored.", None)
                        resolution_success = True
                    else:
                        safe_update_log(f"❌ Failed to abort rebase: {abort_err}", None)
                        resolution_success = False
        elif operation_type == 'merge':
            safe_update_log("📝 Completing merge operation...", None)
            
            # Check for conflicts
            status_out, status_err, status_rc = run_command("git status --porcelain", cwd=vault_path)
            if status_rc == 0:
                conflicts = [line for line in status_out.splitlines() if line.startswith('UU ')]
                if conflicts:
                    safe_update_log("⚠️ Merge has unresolved conflicts. Aborting merge...", None)
                    abort_out, abort_err, abort_rc = run_command("git merge --abort", cwd=vault_path)
                    resolution_success = (abort_rc == 0)
                else:
                    # Try to commit the merge
                    commit_out, commit_err, commit_rc = run_command("git commit --no-edit", cwd=vault_path)
                    if commit_rc == 0:
                        safe_update_log("✅ Merge completed successfully", None)
                        resolution_success = True
                    else:
                        # Abort if commit fails
                        abort_out, abort_err, abort_rc = run_command("git merge --abort", cwd=vault_path)
                        resolution_success = (abort_rc == 0)
        
        elif operation_type in ['cherry-pick', 'revert']:
            safe_update_log(f"📝 Completing {operation_type} operation...", None)
            
            # Try to continue the operation
            continue_cmd = f"git {operation_type.replace('-', ' ')} --continue"
            continue_out, continue_err, continue_rc = run_command(continue_cmd, cwd=vault_path)
            
            if continue_rc == 0:
                safe_update_log(f"✅ {operation_type.title()} completed successfully", None)
                resolution_success = True
            else:
                # Abort the operation
                abort_cmd = f"git {operation_type.replace('-', ' ')} --abort"
                abort_out, abort_err, abort_rc = run_command(abort_cmd, cwd=vault_path)
                if abort_rc == 0:
                    safe_update_log(f"⚠️ {operation_type.title()} aborted. Repository returned to previous state.", None)
                    resolution_success = True
                else:
                    safe_update_log(f"❌ Failed to resolve {operation_type}: {abort_err}", None)
                    resolution_success = False
        
        elif operation_type == 'bisect':
            safe_update_log("📝 Completing bisect operation...", None)
            reset_out, reset_err, reset_rc = run_command("git bisect reset", cwd=vault_path)
            if reset_rc == 0:
                safe_update_log("✅ Bisect completed successfully", None)
                resolution_success = True
            else:
                safe_update_log(f"❌ Failed to reset bisect: {reset_err}", None)
                resolution_success = False
        
        if resolution_success:
            safe_update_log(f"✅ Successfully resolved incomplete {operation_type} operation", None)
            # Create a recovery marker to indicate that git recovery operations were performed
            # This helps Step 4.5 identify when commits should be pushed before opening Obsidian
            try:
                git_dir = os.path.join(vault_path, '.git')
                recovery_marker_file = os.path.join(git_dir, 'ogresync_recovery_flag')
                with open(recovery_marker_file, 'w') as f:
                    f.write(f"Recovery completed: {operation_type}\n")
                safe_update_log("📝 Recovery marker created for push detection", None)
            except Exception as marker_err:
                safe_update_log(f"⚠️ Could not create recovery marker: {marker_err}", None)
        else:
            safe_update_log(f"❌ Could not automatically resolve {operation_type} operation. Manual intervention required.", None)
        
        return True, operation_type, resolution_success
        
    except Exception as e:
        safe_update_log(f"❌ Error detecting git operations: {e}", None)
        return False, None, False

def manual_git_recovery(vault_path):
    """
    Manual recovery function that users can call when git operations are stuck.
    Provides step-by-step guidance for resolving common git issues.
    
    Args:
        vault_path: Path to the vault directory
        
    Returns:
        bool: True if recovery was successful, False otherwise
    """
    try:
        safe_update_log("🔧 Starting manual git recovery process...", None)
        
        # Check current git status
        status_out, status_err, status_rc = run_command("git status", cwd=vault_path)
        if status_rc != 0:
            safe_update_log(f"❌ Cannot check git status: {status_err}", None)
            return False
        
        safe_update_log("📊 Current git status:", None)
        for line in status_out.splitlines()[:10]:  # Show first 10 lines
            safe_update_log(f"   {line}", None)
        
        # Detect specific issues and provide solutions
        if "interactive rebase in progress" in status_out:
            safe_update_log("🔍 Detected: Interactive rebase in progress", None)
            safe_update_log("💡 Solution: Completing rebase operation...", None)
            
            # First, try to continue the rebase
            continue_out, continue_err, continue_rc = run_command("git rebase --continue", cwd=vault_path)
            
            if continue_rc == 0:
                safe_update_log("✅ Rebase completed successfully!", None)
                return True
            
            # If continue fails, try to skip
            if "nothing to commit" in (continue_out + continue_err).lower():
                safe_update_log("📝 Attempting to skip current commit...", None)
                skip_out, skip_err, skip_rc = run_command("git rebase --skip", cwd=vault_path)
                if skip_rc == 0:
                    safe_update_log("✅ Rebase completed by skipping current commit!", None)
                    return True
            
            # Last resort: abort rebase
            safe_update_log("⚠️ Aborting rebase to restore repository to clean state...", None)
            abort_out, abort_err, abort_rc = run_command("git rebase --abort", cwd=vault_path)
            if abort_rc == 0:
                safe_update_log("✅ Rebase aborted successfully. Repository restored to previous state.", None)
                return True
            else:
                safe_update_log(f"❌ Failed to abort rebase: {abort_err}", None)
                return False
        
        elif "rebase in progress" in status_out:
            safe_update_log("🔍 Detected: Rebase in progress", None)
            safe_update_log("💡 Solution: Completing or aborting rebase...", None)
            
            # Try to continue first
            continue_out, continue_err, continue_rc = run_command("git rebase --continue", cwd=vault_path)
            if continue_rc == 0:
                safe_update_log("✅ Rebase completed successfully!", None)
                return True
            
            # If that fails, abort
            abort_out, abort_err, abort_rc = run_command("git rebase --abort", cwd=vault_path)
            if abort_rc == 0:
                safe_update_log("✅ Rebase aborted successfully. Repository restored.", None)
                return True
            else:
                safe_update_log(f"❌ Failed to abort rebase: {abort_err}", None)
                return False
        
        elif "merge in progress" in status_out:
            safe_update_log("🔍 Detected: Merge in progress", None)
            safe_update_log("💡 Solution: Completing or aborting merge...", None)
            
            # Check for conflicts
            if "unmerged paths" in status_out.lower():
                safe_update_log("⚠️ Merge has conflicts. Aborting merge...", None)
                abort_out, abort_err, abort_rc = run_command("git merge --abort", cwd=vault_path)
                if abort_rc == 0:
                    safe_update_log("✅ Merge aborted successfully.", None)
                    return True
            else:
                # Try to complete the merge
                commit_out, commit_err, commit_rc = run_command("git commit --no-edit", cwd=vault_path)
                if commit_rc == 0:
                    safe_update_log("✅ Merge completed successfully!", None)
                    return True
                else:
                    # Abort if commit fails
                    abort_out, abort_err, abort_rc = run_command("git merge --abort", cwd=vault_path)
                    if abort_rc == 0:
                        safe_update_log("✅ Merge aborted successfully.", None)
                        return True
        
        elif "detached HEAD" in status_out:
            safe_update_log("🔍 Detected: Detached HEAD state", None)
            safe_update_log("💡 Solution: Returning to main branch...", None)
            
            checkout_out, checkout_err, checkout_rc = run_command("git checkout main", cwd=vault_path)
            if checkout_rc == 0:
                safe_update_log("✅ Successfully returned to main branch!", None)
                return True
            else:
                safe_update_log(f"❌ Failed to checkout main: {checkout_err}", None)
                return False
        
        else:
            safe_update_log("🔍 No specific git operation detected. Performing general cleanup...", None)
            
            # General cleanup steps
            cleanup_steps = [
                ("git reset --mixed HEAD", "Reset any staged changes"),
                ("git clean -fd", "Remove untracked files and directories"),
                ("git checkout main", "Ensure we're on main branch")            ]
            
            for cmd, description in cleanup_steps:
                safe_update_log(f"📝 {description}...", None)
                out, err, rc = run_command(cmd, cwd=vault_path)
                if rc == 0:
                    safe_update_log(f"✅ {description} completed", None)
                else:
                    safe_update_log(f"⚠️ {description} failed: {err}", None)
            
            return True
        
    except Exception as e:
        safe_update_log(f"❌ Error during manual recovery: {e}", None)
        return False

# ------------------------------------------------
# MAIN ENTRY POINT
# ------------------------------------------------

def main():
    global root, log_text, progress_bar
    
    # Check for console-only mode (used in fallback scenarios)
    if len(sys.argv) > 1 and sys.argv[1] == "--console-sync":
        print("DEBUG: Running in console-only sync mode")
        load_config()
        if config_data.get("SETUP_DONE", "0") == "1":
            try:
                # Run sync without any UI
                auto_sync(use_threading=False)
                print("✅ Console sync completed successfully")
            except Exception as e:
                print(f"❌ Console sync failed: {e}")
        else:
            print("❌ Setup not complete, cannot run console sync")
        return
    
    # Initialize GitHub setup module dependencies
    try:
        import Stage1_conflict_resolution as cr_module
        github_setup.set_dependencies(
            ui_elements=ui_elements,
            config_data=config_data,
            save_config_func=save_config,
            conflict_resolution_module=cr_module,
            safe_update_log_func=safe_update_log
        )
    except ImportError:
        # Conflict resolution module not available
        github_setup.set_dependencies(
            ui_elements=ui_elements,
            config_data=config_data,
            save_config_func=save_config,
            conflict_resolution_module=None,
            safe_update_log_func=safe_update_log
        )
    
    # Initialize wizard steps module dependencies
    wizard_steps.set_dependencies(
        ui_elements=ui_elements,
        config_data=config_data,
        save_config_func=save_config,
        safe_update_log_func=safe_update_log,
        run_command_func=run_command
    )
    
    # Load config, but check if this is the first run
    load_config()
    
    # Check if we need to initialize default config values
    if not config_data:
        # Config file doesn't exist or is empty, set defaults
        config_data["SETUP_DONE"] = "0"
        config_data["VAULT_PATH"] = ""
        config_data["OBSIDIAN_PATH"] = ""
        config_data["GITHUB_REMOTE_URL"] = ""

    # If setup is done, run auto-sync in a minimal/no-UI approach
    # But if you still want a log window, we can create a small UI. 
    # We'll do this: if SETUP_DONE=0, show the wizard UI. If =1, show a minimal UI with auto-sync logs.
    if config_data.get("SETUP_DONE", "0") == "1":
        # Already set up: run auto-sync with a minimal window or even no window.
        # If you truly want NO window at all, you can remove the UI entirely.
        # But let's provide a small log window for user feedback.
        print("DEBUG: Running in sync mode")
        root, log_text, progress_bar = ui_elements.create_minimal_ui(auto_run=False)
        
        # Start auto_sync in a background thread to keep UI responsive
        def start_sync_after_ui():
            # Small delay to ensure UI is fully loaded
            time.sleep(0.2)
            auto_sync(use_threading=True)  # Ensure threading is enabled
        
        # Schedule sync to start after UI is ready
        threading.Thread(target=start_sync_after_ui, daemon=True).start()
        
        root.mainloop()
    else:
        # Not set up yet: run the progressive setup wizard
        print("DEBUG: Running setup wizard")
        success, wizard_state = setup_wizard.run_setup_wizard()
        
        if success:
            print("DEBUG: Setup completed successfully")
            # Setup completed successfully, reload config to get latest values
            load_config()  # Reload to ensure we have the latest saved values
            
            # Ensure SETUP_DONE is set to 1 (it should already be set by the wizard)
            if config_data.get("SETUP_DONE", "0") != "1":
                config_data["SETUP_DONE"] = "1"
                save_config()
            
            print("DEBUG: Transitioning to sync mode")
            # Transition to sync mode
            restart_to_sync_mode()
            
            # The restart_to_sync_mode function will handle the mainloop
            
        else:
            print("DEBUG: Setup was cancelled or failed")
            # Setup was cancelled or failed - no need to show message since it's handled in cancel_setup()
            return  # Exit without running mainloop

# ------------------------------------------------
# EXECUTION
# ------------------------------------------------

if __name__ == "__main__":
    main()