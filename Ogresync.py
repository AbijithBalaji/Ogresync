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
import ui_elements # Import the new UI module
try:
    import Stage1_conflict_resolution as conflict_resolution # Import the enhanced conflict resolution module
    CONFLICT_RESOLUTION_AVAILABLE = True
except ImportError:
    conflict_resolution = None
    CONFLICT_RESOLUTION_AVAILABLE = False
import setup_wizard # Import the new setup wizard module

# ------------------------------------------------
# CONFIG / GLOBALS
# ------------------------------------------------

CONFIG_FILE = "config.txt"  # Stores vault path, Obsidian path, setup_done flag, etc.
config_data = {
    "VAULT_PATH": "",
    "OBSIDIAN_PATH": "",
    "GITHUB_REMOTE_URL": "",
    "SETUP_DONE": "0"
}

SSH_KEY_PATH = os.path.expanduser("~/.ssh/id_rsa.pub")

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
    """
    if not os.path.exists(CONFIG_FILE):
        return
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if "=" in line:
                key, val = line.split("=", 1)
                config_data[key.strip()] = val.strip()

def save_config():
    """
    Writes config_data dict to config.txt.
    """
    print(f"DEBUG: Saving config to {CONFIG_FILE}")
    for k, v in config_data.items():
        print(f"DEBUG: Saving config - {k}: {v}")
    
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        for k, v in config_data.items():
            f.write(f"{k}={v}\n")
    
    print(f"DEBUG: Config saved successfully")

# ------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------

def run_command(command, cwd=None, timeout=None):
    """
    Runs a shell command, returning (stdout, stderr, return_code).
    Safe to call in a background thread.
    """
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
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

def disable_ui_updates():
    """Disable UI updates during transition"""
    global _ui_updating_enabled
    with _ui_lock:
        _ui_updating_enabled = False

def enable_ui_updates():
    """Re-enable UI updates after transition"""
    global _ui_updating_enabled
    with _ui_lock:
        _ui_updating_enabled = True

def safe_update_log(message, progress=None):
    # Always print to console for debugging
    print(f"LOG: {message}")
    
    # Check if UI updates are enabled
    with _ui_lock:
        if not _ui_updating_enabled:
            return
    
    # Check if we have valid UI components
    if not (log_text and progress_bar and root):
        return
        
    def _update():
        try:
            # Double-check that UI is still valid inside the update function
            with _ui_lock:
                if not _ui_updating_enabled:
                    return
                    
            if not (log_text and root):
                return
                
            # Verify root window still exists
            if not root.winfo_exists():
                return
                
            # Update log text
            if log_text is not None:
                try:
                    log_text.config(state='normal')
                    log_text.insert(tk.END, message + "\n")
                    log_text.config(state='disabled')
                    log_text.yview_moveto(1)
                except tk.TclError:
                    # Widget destroyed between checks
                    return
                    
            # Update progress bar
            if progress is not None and progress_bar is not None:
                try:
                    progress_bar["value"] = progress
                except tk.TclError:
                    # Progress bar destroyed between checks
                    pass
                    
            # Force immediate UI update only if we're in main thread
            current_thread = threading.current_thread()
            is_main_thread = current_thread == threading.main_thread()
            
            if is_main_thread and root is not None:
                try:
                    root.update_idletasks()
                    root.update()  # Force full update cycle
                except tk.TclError:
                    # Root destroyed during update
                    pass
                    
        except (tk.TclError, AttributeError, RuntimeError):
            # Widget destroyed or invalid - silently ignore
            pass
            
    try:
        # Check if we're in the main thread
        current_thread = threading.current_thread()
        is_main_thread = current_thread == threading.main_thread()
        
        if is_main_thread:
            # We're in main thread, update immediately
            _update()
        else:
            # We're in background thread, schedule update more safely
            try:
                # Use a simple flag check to prevent scheduling on destroyed UI
                if root is not None and root.winfo_exists():
                    root.after_idle(_update)
                    # Very small delay to allow UI processing
                    time.sleep(0.01)
            except (tk.TclError, RuntimeError):
                # Root destroyed while scheduling - silently ignore
                pass
                
    except (tk.TclError, AttributeError, RuntimeError):
        # Any other error - silently ignore to prevent crashes
        pass

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
    Launches Obsidian in a cross-platform manner.
    On Linux, if obsidian_path is a command string (e.g., from Flatpak), it is split properly;
    otherwise, it launches using shell=True.
    """ 
    if sys.platform.startswith("linux"):
        cmd = shlex.split(obsidian_path)
        subprocess.Popen(cmd)
    else:
        subprocess.Popen([obsidian_path], shell=True)


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

# ------------------------------------------------
# GITHUB SETUP FUNCTIONS
# ------------------------------------------------
def is_git_repo(folder_path):
    """
    Checks if a folder is already a Git repository.
    Returns True if the folder is a Git repo, otherwise False.
    """
    out, err, rc = run_command("git rev-parse --is-inside-work-tree", cwd=folder_path)
    return rc == 0

def initialize_git_repo(vault_path):
    """
    Initializes a Git repository in the selected vault folder if it's not already a repo.
    Also sets the branch to 'main'.
    """
    if not is_git_repo(vault_path):
        safe_update_log("Initializing Git repository in vault...", 15)
        out, err, rc = run_command("git init", cwd=vault_path)
        if rc == 0:
            run_command("git branch -M main", cwd=vault_path)
            safe_update_log("Git repository initialized successfully.", 20)
        else:
            safe_update_log("Error initializing Git repository: " + err, 20)
    else:
        safe_update_log("Vault is already a Git repository.", 20)

def set_github_remote(vault_path):
    """
    Prompts the user to link an existing GitHub repository.
    If the user chooses not to link (or closes the dialog without providing a URL),
    an error is shown indicating that linking a repository is required.
    Returns True if the repository is linked successfully; otherwise, returns False.
    """
    # Check if a remote named 'origin' already exists
    existing_remote_url, err, rc = run_command("git remote get-url origin", cwd=vault_path)
    if rc == 0:
        safe_update_log(f"A remote named 'origin' already exists: {existing_remote_url}", 25)
        override = ui_elements.ask_yes_no(
            "Existing Remote",
            f"A remote 'origin' already points to:\n{existing_remote_url}\n\n"
            "Do you want to override it with a new URL?"
        )
        if not override:
            safe_update_log("Keeping the existing 'origin' remote. Skipping new remote configuration.", 25)
            return True
        else:
            out, err, rc = run_command("git remote remove origin", cwd=vault_path)
            if rc != 0:
                safe_update_log(f"Error removing existing remote: {err}", 25)
                return False
            safe_update_log("Existing 'origin' remote removed.", 25)

    # Prompt for linking a repository
    # Instead of allowing a "No" option, we require linking.
    use_existing_repo = ui_elements.ask_yes_no(
        "GitHub Repository",
        "A GitHub repository is required for synchronization.\n"
        "Do you have an existing repository you would like to link?\n"
        "(If not, please create a private repository on GitHub and then link to it.)"
    )
    if use_existing_repo:
        repo_url = ui_elements.ask_string_dialog(
            "GitHub Repository",
            "Enter your GitHub repository URL (e.g., git@github.com:username/repo.git):",
            icon=ui_elements.Icons.LINK  # Added icon
        )
        if repo_url:
            out, err, rc = run_command(f"git remote add origin {repo_url}", cwd=vault_path)
            if rc == 0:
                safe_update_log(f"Git remote 'origin' set to: {repo_url}", 25)
                
                # Save the remote URL to config for future use
                config_data["GITHUB_REMOTE_URL"] = repo_url
                save_config()
                safe_update_log("GitHub remote URL saved to configuration.", 25)
                
                # Analyze repository state for potential conflicts
                safe_update_log("Analyzing repository content for conflicts...", 30)
                analysis = analyze_repository_state(vault_path)
                
                if analysis["conflict_detected"]:
                    safe_update_log("Repository content conflict detected. Starting conflict resolution...", 30)
                    if not handle_initial_repository_conflict(vault_path, analysis, root):
                        ui_elements.show_error_message("Conflict Resolution Failed", 
                                               "Failed to resolve repository content conflict.\n"
                                               "Please try again or resolve manually.")
                        return False
                    safe_update_log("Repository conflict resolved successfully.", 35)
                elif analysis["has_remote_files"]:
                    safe_update_log("Remote repository contains files. Downloading...", 30)
                    # Simple case: remote has files, local is empty - just pull
                    pull_out, pull_err, pull_rc = run_command("git pull origin main", cwd=vault_path)
                    if pull_rc == 0:
                        safe_update_log("Remote files downloaded successfully.", 35)
                    elif "CONFLICT" in (pull_out + pull_err):
                        # Unexpected conflict during repository linking - use enhanced conflict resolution
                        safe_update_log("❌ Unexpected merge conflict during repository linking.", 32)
                        safe_update_log("Using enhanced conflict resolution system...", 33)
                        
                        try:
                            # Create backup branch before conflict resolution
                            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                            backup_branch = f"backup-before-linking-conflict-{timestamp}"
                            run_command(f"git branch {backup_branch}", cwd=vault_path)
                            safe_update_log(f"State backed up to: {backup_branch}", 33)
                              # Use enhanced conflict resolver
                            import Stage1_conflict_resolution as cr_module
                            resolver = cr_module.ConflictResolver(vault_path, root)
                            remote_url = config_data.get("GITHUB_REMOTE_URL", "")
                            resolution_result = resolver.resolve_initial_setup_conflicts(remote_url)
                            
                            if resolution_result.success:
                                safe_update_log("✅ Repository linking conflicts resolved successfully", 35)
                            else:
                                if "cancelled by user" in resolution_result.message.lower():
                                    safe_update_log("❌ Repository linking conflict resolution was cancelled", 35)
                                    return False
                                else:
                                    safe_update_log("❌ Enhanced conflict resolution failed during repository linking", 35)
                                    return False
                                
                        except Exception as e:
                            safe_update_log(f"❌ Error in enhanced conflict resolution during repository linking: {e}", 35)
                            return False
                    else:
                        safe_update_log(f"Warning: Could not download remote files: {pull_err}", 35)
                elif analysis["has_local_files"]:
                    safe_update_log("Local vault has files, remote is empty. Files will be uploaded during first sync.", 30)
                else:
                    safe_update_log("Both local and remote are empty. Ready for first use.", 30)
                
                return True
            else:
                ui_elements.show_error_message("Error", f"Error setting Git remote: {err}\nPlease try again.")
                return False
        else:
            ui_elements.show_error_message("Error", "Repository URL not provided. You must link to a GitHub repository.")
            return False
    else:
        ui_elements.show_error_message("GitHub Repository Required", 
                             "Linking a GitHub repository is required for synchronization.\n"
                             "Please create a repository on GitHub (private is recommended) and then link to it.")
        return False

def ensure_placeholder_file(vault_path):
    """
    Creates a placeholder file (README.md) in the vault ONLY if the vault is empty.
    This ensures that there's at least one file to commit for empty vaults.
    Handles directory creation if needed.
    """
    try:
        # Ensure the vault directory exists
        os.makedirs(vault_path, exist_ok=True)
        
        # Check if the vault has any files (excluding .git directory)
        vault_files = []
        for root, dirs, files in os.walk(vault_path):
            # Skip .git directory
            if '.git' in dirs:
                dirs.remove('.git')
            # Add files from this directory level
            vault_files.extend([os.path.join(root, f) for f in files])
        
        # Only create placeholder if vault is completely empty
        if not vault_files:
            placeholder_path = os.path.join(vault_path, "README.md")
            with open(placeholder_path, "w", encoding="utf-8") as f:
                f.write("# Welcome to your Obsidian Vault\n\nThis placeholder file was generated automatically by Ogresync to initialize the repository.")
            safe_update_log("Placeholder file 'README.md' created, as the vault was empty.", 5)
        else:
            safe_update_log(f"Vault contains {len(vault_files)} files - no placeholder needed.", 5)
            
    except Exception as e:
        safe_update_log(f"❌ Error checking/creating placeholder file: {e}", 5)
        raise  # Re-raise to be handled by caller

def configure_remote_url_for_vault(vault_path):
    """
    Configures the remote URL for a vault directory.
    If a URL is already saved in config, offers to reuse it.
    Otherwise, prompts for a new URL.
    Returns True if successful, False otherwise.
    """
    saved_url = config_data.get("GITHUB_REMOTE_URL", "").strip()
    
    if saved_url:
        # Offer to reuse the saved URL
        reuse_url = ui_elements.ask_yes_no(
            "Use Existing Repository",
            f"A GitHub repository URL is already configured:\n\n{saved_url}\n\n"
            "Would you like to use this repository for the recreated vault?"
        )
        
        if reuse_url:
            # Use the saved URL
            safe_update_log(f"Using saved remote URL: {saved_url}", None)
            out, err, rc = run_command(f"git remote add origin {saved_url}", cwd=vault_path)
            if rc == 0:
                safe_update_log("Git remote configured successfully.", None)
                # Ensure the URL is saved in config (it should be, but make sure)
                config_data["GITHUB_REMOTE_URL"] = saved_url
                save_config()
                safe_update_log("GitHub remote URL confirmed in configuration.", None)
                return True
            else:
                safe_update_log(f"❌ Failed to configure remote: {err}", None)
                # Fall through to ask for new URL
        else:
            # User wants to use a different URL
            safe_update_log("User chose to configure a different repository URL.", None)
    
    # Ask for new URL (either no saved URL or user declined to reuse)
    repo_url = ui_elements.ask_string_dialog(
        "GitHub Repository",
        "Enter your GitHub repository URL (e.g., git@github.com:username/repo.git):",
        initial_value=saved_url,  # Pre-fill with saved URL if available
        icon=ui_elements.Icons.LINK
    )
    
    if repo_url and repo_url.strip():
        repo_url = repo_url.strip()
        out, err, rc = run_command(f"git remote add origin {repo_url}", cwd=vault_path)
        if rc == 0:
            safe_update_log(f"Git remote configured: {repo_url}", None)
            
            # Update config with new URL
            config_data["GITHUB_REMOTE_URL"] = repo_url
            save_config()
            safe_update_log("GitHub remote URL updated in configuration.", None)
            return True
        else:
            safe_update_log(f"❌ Failed to configure remote: {err}", None)
            ui_elements.show_error_message(
                "Git Remote Error",
                f"Failed to configure GitHub remote:\n{err}\n\nPlease check the URL and try again."
            )
            return False
    else:
        safe_update_log("❌ No repository URL provided.", None)
        ui_elements.show_error_message(
            "URL Required",
            "A GitHub repository URL is required to sync your vault."
        )
        return False

def validate_vault_directory(vault_path):
    """
    Validates that the vault directory exists and is accessible.
    If not, offers recovery options to the user.
    
    Returns:
        tuple: (is_valid: bool, should_continue: bool, new_vault_path: str|None)
        - is_valid: True if vault exists and is accessible
        - should_continue: True if user wants to continue (either vault exists or recovery chosen)
        - new_vault_path: New vault path if user selected a different directory
    """
    if not vault_path:
        return False, False, None
    
    # Check if directory exists
    if not os.path.exists(vault_path):
        safe_update_log(f"❌ Vault directory not found: {vault_path}", None)
        
        # Offer recovery options
        choice = ui_elements.create_vault_recovery_dialog(root, vault_path)
        
        if choice == "recreate":
            # Recreate the directory and continue
            try:
                os.makedirs(vault_path, exist_ok=True)
                safe_update_log(f"✅ Vault directory recreated: {vault_path}", None)
                
                # Initialize git repository in the recreated directory
                initialize_git_repo(vault_path)
                
                # Configure remote URL (reuse saved URL or ask for new one)
                if configure_remote_url_for_vault(vault_path):
                    # Try to pull remote files if they exist
                    safe_update_log("Checking for remote files to download...", None)
                    pull_out, pull_err, pull_rc = run_command("git pull origin main", cwd=vault_path)
                    if pull_rc == 0:
                        safe_update_log("✅ Remote files downloaded successfully.", None)
                    elif "CONFLICT" in (pull_out + pull_err):
                        # Conflict during vault recovery - use enhanced conflict resolution
                        safe_update_log("❌ Merge conflict detected during vault recovery.", None)
                        safe_update_log("Using enhanced conflict resolution system...", None)
                        
                        try:
                            # Create backup branch before conflict resolution
                            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                            backup_branch = f"backup-before-recovery-conflict-{timestamp}"
                            run_command(f"git branch {backup_branch}", cwd=vault_path)
                            safe_update_log(f"State backed up to: {backup_branch}", None)
                              # Use enhanced conflict resolver
                            import Stage1_conflict_resolution as cr_module
                            resolver = cr_module.ConflictResolver(vault_path, root)
                            remote_url = config_data.get("GITHUB_REMOTE_URL", "")
                            resolution_result = resolver.resolve_initial_setup_conflicts(remote_url)
                            
                            if resolution_result.success:
                                safe_update_log("✅ Vault recovery conflicts resolved successfully", None)
                            else:
                                if "cancelled by user" in resolution_result.message.lower():
                                    safe_update_log("❌ Vault recovery conflict resolution was cancelled", None)
                                else:
                                    safe_update_log("❌ Enhanced conflict resolution failed during vault recovery", None)
                                
                        except Exception as e:
                            safe_update_log(f"❌ Error in enhanced conflict resolution during vault recovery: {e}", None)
                    else:
                        # Remote might be empty or main branch doesn't exist yet
                        if "couldn't find remote ref" in pull_err.lower() or "fatal: couldn't find remote ref main" in pull_err.lower():
                            safe_update_log("Remote repository is empty. This is normal for new repositories.", None)
                        else:
                            safe_update_log(f"Note: Could not pull remote files: {pull_err}", None)
                    
                    return True, True, None
                else:
                    # Failed to configure remote
                    safe_update_log("❌ Failed to configure GitHub remote. Vault recreation incomplete.", None)
                    return False, False, None
                    
            except Exception as e:
                safe_update_log(f"❌ Failed to recreate vault directory: {e}", None)
                ui_elements.show_error_message(
                    "Directory Creation Failed",
                    f"Failed to recreate vault directory:\n{e}\n\nPlease check permissions and try again."
                )
                return False, False, None
        
        elif choice == "select_new":
            # Let user select a new vault directory
            new_vault = ui_elements.ask_directory_dialog("Select New Vault Directory")
            if new_vault:
                # Update configuration with new path
                config_data["VAULT_PATH"] = new_vault
                save_config()
                safe_update_log(f"✅ Vault path updated to: {new_vault}", None)
                
                # Set up the new vault directory (git init, remote config, conflict resolution)
                if setup_new_vault_directory(new_vault):
                    safe_update_log("✅ New vault directory setup completed successfully.", None)
                    return True, True, new_vault
                else:
                    safe_update_log("❌ Failed to set up new vault directory.", None)
                    return False, False, None
            else:
                safe_update_log("❌ No new vault directory selected.", None)
                return False, False, None
        
        elif choice == "setup":
            # Run setup wizard again
            safe_update_log("User chose to run setup wizard again.", None)
            return False, True, "run_setup"
        
        else:
            # User cancelled or closed dialog
            safe_update_log("❌ User cancelled vault recovery.", None)
            return False, False, None
    
    # Check if directory is accessible
    if not os.access(vault_path, os.R_OK | os.W_OK):
        safe_update_log(f"❌ Vault directory is not accessible (permissions): {vault_path}", None)
        ui_elements.show_error_message(
            "Permission Error",
            f"Cannot access vault directory:\n{vault_path}\n\n"
            "Please check directory permissions and try again."
        )
        return False, False, None
    
    return True, True, None

# ------------------------------------------------
# MISSING UTILITY FUNCTIONS
# ------------------------------------------------

def setup_new_vault_directory(vault_path):
    """
    Set up a new vault directory with git initialization and remote configuration.
    
    Args:
        vault_path: Path to the new vault directory
    
    Returns:
        bool: True if setup was successful, False otherwise
    """
    try:
        safe_update_log(f"Setting up new vault directory: {vault_path}", None)
        
        # Initialize git repository
        if not initialize_git_repo(vault_path):
            safe_update_log("❌ Failed to initialize git repository", None)
            return False
        
        # Configure remote URL
        if not configure_remote_url_for_vault(vault_path):
            safe_update_log("❌ Failed to configure remote repository", None)
            return False
        
        # Analyze and handle any repository conflicts
        analysis = analyze_repository_state(vault_path)
        if analysis["conflict_detected"]:
            safe_update_log("Repository conflicts detected, resolving...", None)
            if not handle_initial_repository_conflict(vault_path, analysis, root):
                safe_update_log("❌ Failed to resolve repository conflicts", None)
                return False
        
        safe_update_log("✅ New vault directory setup completed successfully", None)
        return True
        
    except Exception as e:
        safe_update_log(f"❌ Error setting up new vault directory: {e}", None)
        return False

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
    """
    global root, log_text, progress_bar
    
    try:
        print("DEBUG: Transitioning to sync mode...")
        
        # CRITICAL: Disable UI updates immediately to prevent threading conflicts
        disable_ui_updates()
        
        # Kill any remaining background threads that might call safe_update_log
        print("DEBUG: Stopping any remaining background operations...")
        
        # Clean shutdown of existing UI with better thread safety
        if root is not None:
            try:
                # Cancel all pending after() calls to prevent threading issues
                print("DEBUG: Cancelling pending UI callbacks...")
                for after_id in getattr(root, '_after_ids', []):
                    try:
                        root.after_cancel(after_id)
                    except:
                        pass
                
                # Clear the tracking list
                if hasattr(root, '_after_ids'):
                    getattr(root, '_after_ids').clear()
                
                # Stop any pending after() calls
                try:
                    root.after_idle(lambda: None)  # Flush pending events
                except:
                    pass
                
                # Proper cleanup sequence
                print("DEBUG: Destroying UI...")
                root.quit()  
                root.update_idletasks()  # Process pending updates
                time.sleep(0.5)  # Allow threads to finish UI operations
                root.destroy()
                
                # Clear global references immediately
                root = None
                log_text = None
                progress_bar = None
                
                print("DEBUG: UI destroyed successfully")
                
            except Exception as cleanup_error:
                print(f"UI cleanup warning: {cleanup_error}")
        
        # Longer delay to ensure complete cleanup and avoid threading conflicts
        print("DEBUG: Waiting for complete cleanup...")
        time.sleep(1.5)
        
        # Create new minimal UI for sync mode  
        print("DEBUG: Creating new UI...")
        root, log_text, progress_bar = ui_elements.create_minimal_ui(auto_run=False)
        
        # Ensure UI is fully rendered and stable before starting sync
        root.update()
        root.update_idletasks()
        time.sleep(0.3)  # Additional stability delay
        
        # Re-enable UI updates now that new UI is ready
        enable_ui_updates()
        
        print("DEBUG: UI transition complete, starting sync")
        
        # During transition, run sync in main thread to avoid threading conflicts
        # This is safer during the critical transition period
        def delayed_sync():
            try:
                print("DEBUG: Starting sync in main thread during transition")
                # Run sync directly in main thread during transition to avoid threading issues
                auto_sync(use_threading=False)
            except Exception as sync_error:
                safe_update_log(f"❌ Error during sync: {sync_error}", None)
                print(f"Sync error: {sync_error}")
        
        # Use delay to ensure UI is completely stable
        root.after(1000, delayed_sync)  # 1 second delay for stability
        
        # Run the main loop
        root.mainloop()
        
    except Exception as e:
        print(f"Error transitioning to sync mode: {e}")
        # Ensure UI updates are re-enabled even in error case
        enable_ui_updates()
        
        # Fallback: create simple console-based sync
        try:
            print("Falling back to console mode...")
            # Call auto_sync without threading in fallback mode
            auto_sync(use_threading=False)
            
        except Exception as fallback_error:
            print(f"Console fallback failed: {fallback_error}")
            print("Manual intervention required. Please check configuration.")

# ------------------------------------------------
# WIZARD STEPS (Used Only if SETUP_DONE=0)
# ------------------------------------------------

def find_obsidian_path():
    """
    Attempts to locate Obsidian’s installation or launch command based on the OS.
    
    Windows:
      - Checks common installation directories for "Obsidian.exe".
    Linux:
      - Checks if 'obsidian' is in PATH.
      - Checks common Flatpak paths.
      - Checks common Snap path.
      - As a fallback, returns the Flatpak command string.
    macOS:
      - Checks the default /Applications folder.
      - Checks PATH.
    
    If not found, it prompts the user to manually locate the executable.
    
    Returns the path or command string to launch Obsidian, or None.
    """
    if sys.platform.startswith("win"):
        possible_paths = [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Obsidian\Obsidian.exe"),
            os.path.expandvars(r"%PROGRAMFILES%\Obsidian\Obsidian.exe"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%\Obsidian\Obsidian.exe")
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
        response = ui_elements.ask_yes_no("Obsidian Not Found",
                                       "Obsidian was not detected in standard locations.\n"
                                       "Would you like to locate the Obsidian executable manually?")
        if response:
            selected_path = ui_elements.ask_file_dialog(
                "Select Obsidian Executable",
                [("Obsidian Executable", "*.exe")]
            )
            if selected_path:
                return selected_path
        return None

    elif sys.platform.startswith("linux"):
        # Option 1: Check if 'obsidian' is in PATH.
        obsidian_cmd = shutil.which("obsidian")
        if obsidian_cmd:
            return obsidian_cmd
        # Option 2: Check common Flatpak paths.
        flatpak_paths = [
            os.path.expanduser("~/.local/share/flatpak/exports/bin/obsidian"),
            "/var/lib/flatpak/exports/bin/obsidian"
        ]
        for path in flatpak_paths:
            if os.path.exists(path):
                return path
        # Option 3: Check Snap installation.
        snap_path = "/snap/bin/obsidian"
        if os.path.exists(snap_path):
            return snap_path
        # Option 4: Fallback to a command string.
        # (You can modify this if you want to prompt the user instead.)
        return "flatpak run md.obsidian.Obsidian"

    elif sys.platform.startswith("darwin"):
        # macOS: Check default location in /Applications.
        obsidian_app = "/Applications/Obsidian.app/Contents/MacOS/Obsidian"
        if os.path.exists(obsidian_app):
            return obsidian_app
        # Option 2: Check if a command is available in PATH.
        obsidian_cmd = shutil.which("obsidian")
        if obsidian_cmd:
            return obsidian_cmd
        response = ui_elements.ask_yes_no("Obsidian Not Found",
                                       "Obsidian was not detected in standard locations.\n"
                                       "Would you like to locate the Obsidian application manually?")
        if response:
            selected_path = ui_elements.ask_file_dialog(
                "Select Obsidian Application",
                filetypes=[("Obsidian Application", "*.app")]
            )
            if selected_path:
                return selected_path
        return None


def select_vault_path():
    """
    Asks user to select Obsidian Vault folder. Returns path or None if canceled.
    """
    selected = ui_elements.ask_directory_dialog("Select Obsidian Vault Folder")
    return selected if selected else None

def is_git_installed():
    """
    Returns True if Git is installed, else False.
    """
    out, err, rc = run_command("git --version")
    return rc == 0

def test_ssh_connection_sync():
    """
    Synchronously tests SSH to GitHub. Returns True if OK, False otherwise.
    """
    out, err, rc = run_command("ssh -T git@github.com")
    print("DEBUG: SSH OUT:", out)
    print("DEBUG: SSH ERR:", err)
    print("DEBUG: SSH RC:", rc)
    if "successfully authenticated" in (out + err).lower():
        return True
    return False

def re_test_ssh():
    """
    Re-tests the SSH connection in a background thread.
    If successful, automatically performs an initial commit/push if none exists yet.
    """
    def _test_thread():
        safe_update_log("Re-testing SSH connection to GitHub...", 35)
        ensure_github_known_host()  # ensures no prompt for 'yes/no'

        if test_ssh_connection_sync():
            safe_update_log("SSH connection successful!", 40)
            
            # Perform the initial commit/push if there are no local commits yet
            perform_initial_commit_and_push(config_data["VAULT_PATH"])

            # Mark setup as done
            config_data["SETUP_DONE"] = "1"
            save_config()

            safe_update_log("Setup complete! You can now close this window or start sync.", 100)
        else:
            safe_update_log("SSH connection still failed. Check your GitHub key or generate a new one.", 40)

    threading.Thread(target=_test_thread, daemon=True).start()


def perform_initial_commit_and_push(vault_path):
    """
    Checks if the local repository has any commits.
    If not, creates an initial commit and pushes it to the remote 'origin' on the 'main' branch.
    """
    out, err, rc = run_command("git rev-parse HEAD", cwd=vault_path)
    if rc != 0:
        # rc != 0 implies 'git rev-parse HEAD' failed => no commits (unborn branch)
        safe_update_log("No local commits detected. Creating initial commit...", 50)

        # Stage all files
        run_command("git add .", cwd=vault_path)

        # Commit
        out_commit, err_commit, rc_commit = run_command('git commit -m "Initial commit"', cwd=vault_path)
        if rc_commit == 0:
            # Check if remote has commits before pushing
            ls_out, ls_err, ls_rc = run_command("git ls-remote --heads origin main", cwd=vault_path)
            
            if ls_out.strip():
                # Remote has commits, need to pull first
                safe_update_log("Remote repository has existing commits. Pulling before push...", 55)
                pull_out, pull_err, pull_rc = run_command("git pull origin main --allow-unrelated-histories", cwd=vault_path)
                if pull_rc == 0:
                    safe_update_log("Successfully pulled remote commits. Now pushing...", 58)
                    # Now try to push
                    out_push, err_push, rc_push = run_command("git push -u origin main", cwd=vault_path)
                    if rc_push == 0:
                        safe_update_log("Initial commit pushed to remote repository successfully.", 60)
                    else:
                        safe_update_log(f"Error pushing after pull: {err_push}", 60)
                elif "CONFLICT" in (pull_out + pull_err):
                    # Conflict during initial setup pull - use 2-stage conflict resolution
                    safe_update_log("❌ Merge conflict detected during initial setup pull.", 56)
                    safe_update_log("🔧 Activating 2-stage conflict resolution system...", 57)
                    
                    # Abort the current merge to get to a clean state
                    run_command("git merge --abort", cwd=vault_path)
                    
                    try:
                        if not CONFLICT_RESOLUTION_AVAILABLE:
                            safe_update_log("❌ Enhanced conflict resolution system not available. Manual resolution required.", 59)
                            safe_update_log("Please resolve conflicts manually and try again.", 59)
                            return
                        
                        # Create backup using backup manager if available
                        backup_id = None
                        if 'backup_manager' in sys.modules:
                            try:
                                from backup_manager import create_setup_safety_backup
                                backup_id = create_setup_safety_backup(vault_path, "initial-setup-conflict")
                                if backup_id:
                                    safe_update_log(f"✅ Safety backup created: {backup_id}", 57)
                            except Exception as backup_err:
                                safe_update_log(f"⚠️ Could not create backup: {backup_err}", 57)
                        
                        # Import and use the proper conflict resolution modules
                        import Stage1_conflict_resolution as cr_module
                        
                        # Create conflict resolver for initial setup conflicts
                        resolver = cr_module.ConflictResolver(vault_path, root)
                        remote_url = config_data.get("GITHUB_REMOTE_URL", "")
                        
                        # Resolve conflicts using the 2-stage system
                        resolution_result = resolver.resolve_initial_setup_conflicts(remote_url)
                        
                        if resolution_result.success:
                            safe_update_log("✅ Initial setup conflicts resolved successfully", 59)
                            if backup_id:
                                safe_update_log(f"📝 Note: Safety backup available if needed: {backup_id}", 59)
                            # Try to push again after resolution
                            out_push, err_push, rc_push = run_command("git push -u origin main", cwd=vault_path)
                            if rc_push == 0:
                                safe_update_log("Initial commit pushed to remote repository successfully.", 60)
                            else:
                                safe_update_log(f"Warning: Could not push after conflict resolution: {err_push}", 60)
                        else:
                            if "cancelled by user" in resolution_result.message.lower():
                                safe_update_log("❌ Initial setup conflict resolution was cancelled by user", 59)
                                safe_update_log("Setup cannot continue without resolving conflicts.", 59)
                                return
                            else:
                                safe_update_log(f"❌ Initial setup conflict resolution failed: {resolution_result.message}", 59)
                                if backup_id:
                                    safe_update_log(f"📝 Your work is safe in backup: {backup_id}", 59)
                                return
                            
                    except Exception as e:
                        safe_update_log(f"❌ Error in 2-stage conflict resolution during setup: {e}", 59)
                        safe_update_log("Initial setup may be incomplete. Please resolve conflicts manually.", 59)
                        import traceback
                        traceback.print_exc()
                else:
                    safe_update_log(f"Error pulling remote commits: {pull_err}", 60)
            else:
                # Remote is empty, safe to push
                out_push, err_push, rc_push = run_command("git push -u origin main", cwd=vault_path)
                if rc_push == 0:
                    safe_update_log("Initial commit pushed to remote repository successfully.", 60)
                else:
                    safe_update_log(f"Error pushing initial commit: {err_push}", 60)
        else:
            safe_update_log(f"Error committing files: {err_commit}", 60)
    else:
        # We already have at least one commit in this repo
        safe_update_log("Local repository already has commits. Skipping initial commit step.", 50)


# -- SSH Key Generation in Background

def generate_ssh_key():
    """
    Prompts for the user's email and starts a background thread for SSH key generation.
    """
    user_email = ui_elements.ask_string_dialog(
        "SSH Key Generation",
        "Enter your email address for the SSH key:",
        icon=ui_elements.Icons.GEAR  # Added icon
    )
    if not user_email:
        ui_elements.show_error_message("Email Required", "No email address provided. SSH key generation canceled.")
        return

    threading.Thread(target=generate_ssh_key_async, args=(user_email,), daemon=True).start()


def generate_ssh_key_async(user_email):
    """
    Runs in a background thread to:
      1) Generate an SSH key if it doesn't already exist.
      2) Copy the public key to the clipboard.
      3) Show an info dialog on the main thread.
      4) After the user closes the dialog, open GitHub's SSH settings in the browser.
    """
    key_path_private = SSH_KEY_PATH.replace("id_rsa.pub", "id_rsa")

    # 1) Generate key if it doesn't exist
    if not os.path.exists(SSH_KEY_PATH):
        safe_update_log("Generating SSH key...", 25)
        out, err, rc = run_command(f'ssh-keygen -t rsa -b 4096 -C "{user_email}" -f "{key_path_private}" -N ""')
        if rc != 0:
            safe_update_log(f"SSH key generation failed: {err}", 25)
            return
        safe_update_log("SSH key generated successfully.", 30)
    else:
        safe_update_log("SSH key already exists. Overwriting is not performed here.", 30)

    # 2) Read the public key and attempt to copy to the clipboard
    try:
        with open(SSH_KEY_PATH, "r", encoding="utf-8") as key_file:
            public_key = key_file.read().strip()
        pyperclip.copy(public_key)
        # Verify that clipboard contains the expected key
        copied = pyperclip.paste().strip()
        if copied != public_key:
            raise Exception("Clipboard copy failed: content mismatch.")
        safe_update_log("Public key successfully copied to clipboard.", 35)
    except Exception as e:
        safe_update_log(f"Error copying SSH key to clipboard: {e}", 35)
        # 3) Fallback: show a dialog with manual instructions and the public key
        ui_elements.show_info_message(
            "Manual SSH Key Copy Required",
            "Automatic copying of your SSH key failed.\n\n"
            "Please open a terminal and run:\n\n"
            "   cat ~/.ssh/id_rsa.pub\n\n"
            "Then copy the output manually and add it to your GitHub account."
        )

    # 4) Show final info dialog and open GitHub's SSH keys page
    def show_dialog_then_open_browser():
        ui_elements.show_info_message(
            "SSH Key Generated",
            "Your SSH key has been generated and copied to the clipboard (if successful).\n\n"
            "If automatic copying failed, please manually copy the key as described.\n\n"
            "Click OK to open GitHub's SSH keys page to add your key."
        )
        webbrowser.open("https://github.com/settings/keys")
    
    if root is not None:
        root.after(0, show_dialog_then_open_browser)


def copy_ssh_key():
    """
    Copies the SSH key to clipboard and opens GitHub SSH settings.
    """
    if os.path.exists(SSH_KEY_PATH):
        with open(SSH_KEY_PATH, "r", encoding="utf-8") as key_file:
            ssh_key = key_file.read().strip()
            pyperclip.copy(ssh_key)
        webbrowser.open("https://github.com/settings/keys")
        ui_elements.show_info_message("SSH Key Copied",
                            "Your SSH key has been copied to the clipboard.\n"
                            "Paste it into GitHub.")
    else:
        ui_elements.show_error_message("Error", "No SSH key found. Generate one first.")

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
        
        # Ensure immediate UI update
        time.sleep(0.1)
        
        # Step 0: Validate vault directory exists
        is_valid, should_continue, new_vault_path = validate_vault_directory(vault_path)
        
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
        git_check_out, git_check_err, git_check_rc = run_command("git status", cwd=vault_path)
        if git_check_rc != 0:
            # Not a git repository - this shouldn't happen if setup was done correctly
            safe_update_log("❌ Directory is not a git repository. Initializing...", 5)
            initialize_git_repo(vault_path)
            
            # Try to configure remote if we have a saved URL
            saved_url = config_data.get("GITHUB_REMOTE_URL", "").strip()
            if saved_url:
                safe_update_log(f"Configuring remote with saved URL: {saved_url}", 5)
                run_command(f"git remote add origin {saved_url}", cwd=vault_path)
            else:
                safe_update_log("❌ No remote URL configured. Please run setup again.", 5)
                return
        
        # Check if repository has any commits
        out, err, rc = run_command("git rev-parse HEAD", cwd=vault_path)
        if rc != 0:
            safe_update_log("No existing commits found in your vault. Verifying if the vault is empty...", 5)
            
            # Safely ensure placeholder file with error handling
            try:
                ensure_placeholder_file(vault_path)
            except Exception as e:
                safe_update_log(f"❌ Error creating placeholder file: {e}", 5)
                return
            
            safe_update_log("Creating an initial commit to initialize the repository...", 5)
            run_command("git add -A", cwd=vault_path)
            out_commit, err_commit, rc_commit = run_command('git commit -m "Initial commit (auto-sync)"', cwd=vault_path)
            if rc_commit == 0:
                safe_update_log("Initial commit created successfully.", 5)
            else:
                safe_update_log(f"❌ Error creating initial commit: {err_commit}", 5)
                return
        else:
            safe_update_log("Local repository already contains commits.", 5)

        # Step 2: Check network connectivity
        network_available = is_network_available()
        if not network_available:
            safe_update_log("No internet connection detected. Skipping remote sync operations and proceeding in offline mode.", 10)
        else:
            safe_update_log("Internet connection detected. Proceeding with remote synchronization.", 10)
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
                            # Conflict during sync initialization - use enhanced conflict resolution
                            safe_update_log("❌ Merge conflict detected during sync initialization.", 16)
                            safe_update_log("Using enhanced conflict resolution system...", 17)
                            
                            try:                                # Create backup branch before any operation for safety
                                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                                backup_branch = f"backup-local-before-sync-init-{timestamp}"
                                run_command(f"git branch {backup_branch}", cwd=vault_path)
                                safe_update_log(f"Local state backed up to: {backup_branch}", 17)
                                
                                # For sync initialization, we want remote content to take precedence
                                # Use reset --hard to replace local with remote content (your preference)
                                safe_update_log("Replacing local content with remote content...", 17)
                                reset_out, reset_err, reset_rc = run_command("git reset --hard origin/main", cwd=vault_path)
                                
                                if reset_rc == 0:
                                    safe_update_log("✅ Successfully synchronized with remote repository", 18)
                                    safe_update_log(f"📝 Note: Previous local state preserved in backup branch: {backup_branch}", 18)
                                else:
                                    safe_update_log(f"❌ Failed to synchronize with remote: {reset_err}", 18)
                                    safe_update_log(f"📝 Your local work is safe in backup branch: {backup_branch}", 18)
                                    network_available = False
                                    
                            except Exception as e:
                                safe_update_log(f"❌ Error in enhanced conflict resolution during sync init: {e}", 18)
                                safe_update_log("Sync initialization may be incomplete. Manual resolution required.", 18)
                                network_available = False
                        else:
                            safe_update_log(f"Error pulling remote commits: {pull_err}", 15)
                    else:
                        safe_update_log(f"❌ Error pushing initial commit: {err_push}", 15)
                        network_available = False
            else:
                safe_update_log("Remote branch 'main' found. Proceeding to pull updates from GitHub...", 10)

        # Step 3: Stash local changes
        safe_update_log("Stashing any local changes...", 15)
        run_command("git stash", cwd=vault_path)

        # Step 4: If online, pull the latest updates (with conflict resolution)
        if network_available:
            # First, fetch remote refs to ensure we have latest info
            safe_update_log("Fetching latest remote information...", 18)
            fetch_out, fetch_err, fetch_rc = run_command("git fetch origin", cwd=vault_path)
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
                                # Fallback: Create git branch backup
                                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                                backup_branch = f"backup-local-before-initial-sync-{timestamp}"
                                run_command(f"git branch {backup_branch}", cwd=vault_path)
                                safe_update_log(f"📝 Note: Previous local state preserved in backup branch: {backup_branch}", 25)
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
                        out, err, rc = "", "", 0  # Simulate successful pull                else:
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
                    
                    # Abort the current rebase to get to a clean state
                    run_command("git rebase --abort", cwd=vault_path)
                    
                    # Create backup before resolving conflicts
                    backup_id = None
                    if 'backup_manager' in sys.modules:
                        try:
                            from backup_manager import create_conflict_resolution_backup
                            backup_id = create_conflict_resolution_backup(vault_path, "auto-remote-wins-resolution")
                            if backup_id:
                                safe_update_log(f"✅ Safety backup created: {backup_id}", 33)
                        except Exception as backup_err:
                            safe_update_log(f"⚠️ Could not create backup: {backup_err}", 33)
                    
                    # Automatic "remote wins" resolution - much simpler and more reliable
                    safe_update_log("📥 Automatically choosing remote content (remote wins policy)...", 34)
                    
                    # Use reset --hard to make remote content win completely
                    reset_out, reset_err, reset_rc = run_command("git reset --hard origin/main", cwd=vault_path)
                    if reset_rc == 0:
                        safe_update_log("✅ Conflicts resolved automatically using 'remote wins' policy", 35)
                        if backup_id:
                            safe_update_log(f"📝 Note: Local changes backed up as: {backup_id}", 35)
                        else:
                            # Fallback: git branch backup
                            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                            backup_branch = f"backup-before-remote-wins-{timestamp}"
                            run_command(f"git branch {backup_branch}", cwd=vault_path)
                            safe_update_log(f"📝 Note: Local changes backed up in branch: {backup_branch}", 35)
                        
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
            safe_update_log("Skipping pull operation due to offline mode.", 20)        # Step 5: Handle stashed changes - Always discard during initial sync (before Obsidian)
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
        remote_changes_detected = False          # Re-check network connectivity before checking remote changes  
        network_available = is_network_available()
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
            safe_update_log("No network detected. Skipping remote check and proceeding to push.", 58)

        # Step 9: Push changes if network is available (local changes already committed in Step 8A)
        network_available = is_network_available()
        if network_available:
            unpushed = get_unpushed_commits(vault_path)
            if unpushed:
                safe_update_log("Pushing all unpushed commits to GitHub...", 70)
                out, err, rc = run_command("git push origin main", cwd=vault_path)
                if rc != 0:
                    if "Could not resolve hostname" in err or "network" in err.lower():
                        safe_update_log("❌ Unable to push changes due to network issues. Your changes remain locally committed and will be pushed once connectivity is restored.", 80)
                    else:
                        safe_update_log(f"❌ Push operation failed: {err}", 80)
                    return
                safe_update_log("✅ All changes have been successfully pushed to GitHub.", 80)
            else:
                safe_update_log("No new commits to push.", 80)
        else:
            safe_update_log("Offline mode: Changes have been committed locally. They will be automatically pushed when an internet connection is available.", 80)        # Step 10: Final message  
        if remote_changes_detected and local_changes_committed:
            safe_update_log("🎉 Synchronization complete! Remote changes were detected and resolved, your local changes have been committed and pushed.", 100)
        elif local_changes_committed:
            safe_update_log("🎉 Synchronization complete! Your local changes have been committed and pushed to GitHub.", 100)
        else:
            safe_update_log("🎉 Synchronization complete! No changes were made during this session.", 100)
        
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

# ------------------------------------------------
# MAIN ENTRY POINT
# ------------------------------------------------

def main():
    global root, log_text, progress_bar
    
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
        root, log_text, progress_bar = ui_elements.create_minimal_ui(auto_run=True)
        auto_sync()
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