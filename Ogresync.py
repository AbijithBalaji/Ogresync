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
from tkinter import ttk, scrolledtext
from typing import Optional
import webbrowser
import pyperclip
import requests
import ui_elements # Import the new UI module
import conflict_resolution # Import the new conflict resolution module
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

def safe_update_log(message, progress=None):
    if log_text and progress_bar and root and root.winfo_exists():
        def _update():
            if log_text is not None:
                log_text.config(state='normal')
                log_text.insert(tk.END, message + "\n")
                log_text.config(state='disabled')
                log_text.yview_moveto(1)
            if progress is not None and progress_bar is not None:
                progress_bar["value"] = progress
        try:
            if root is not None:
                root.after(0, _update)
        except Exception as e:
            print("Error scheduling UI update:", e)
    else:
        print(message)

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
    try:
        # Create conflict analysis from the conflict files
        analysis = conflict_resolution.ConflictAnalysis()
        analysis.has_conflicts = True
        analysis.conflict_type = conflict_resolution.ConflictType.MERGE_CONFLICT
        analysis.summary = f"Merge conflicts detected in files: {conflict_files}"
        
        # Parse conflict files and create conflict info objects
        if conflict_files and conflict_files.strip():
            for file_path in conflict_files.strip().split('\n'):
                if file_path.strip():
                    conflict_info = conflict_resolution.FileConflictInfo(file_path.strip(), 'both_modified')
                    conflict_info.has_content_conflict = True
                    analysis.conflicted_files.append(conflict_info)
        
        # Get vault path from config
        vault_path = config_data.get("VAULT_PATH", "")
        
        # Create conflict resolver
        resolver = conflict_resolution.ConflictResolver(vault_path, root)
        resolution_result = resolver.resolve_conflicts(conflict_resolution.ConflictType.MERGE_CONFLICT)
        
        if not resolution_result['success']:
            # Fallback to simple choice if resolution failed
            return None
        
        strategy = resolution_result['strategy']
        
        # Map new strategies to old format for backward compatibility
        if strategy == 'keep_local':
            return 'ours'
        elif strategy == 'keep_remote':
            return 'theirs'
        elif strategy == 'smart_merge':
            # Apply the smart merge resolution
            if conflict_resolution.apply_conflict_resolution(vault_path, resolution_result):
                return 'manual'  # Indicates resolution was handled
            else:
                return None  # Resolution failed
        else:
            return None
            
    except Exception as e:
        print(f"Error in enhanced conflict resolution: {e}")
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
    
    try:
        # Use the enhanced two-stage conflict resolution system
        dialog_parent = parent_window if parent_window is not None else root
        
        # Create enhanced conflict analysis for the new system
        enhanced_analysis = conflict_resolution.ConflictAnalysis()
        enhanced_analysis.has_conflicts = True
        enhanced_analysis.conflict_type = conflict_resolution.ConflictType.REPOSITORY_SETUP
        enhanced_analysis.summary = "Repository setup conflicts detected"
        
        # Convert analysis data to enhanced format
        enhanced_analysis.local_only_files = analysis.get("local_files", [])
        enhanced_analysis.remote_only_files = analysis.get("remote_files", [])
        
        # Create file conflict info for files that exist in both but might be different
        for local_file in analysis.get("local_files", []):
            if local_file in analysis.get("remote_files", []):
                conflict_info = conflict_resolution.FileConflictInfo(local_file, 'both_modified')
                conflict_info.has_content_conflict = True
                enhanced_analysis.conflicted_files.append(conflict_info)
        
        # Use the enhanced conflict resolver
        resolver = conflict_resolution.ConflictResolver(vault_path, dialog_parent, enhanced_analysis)    
        resolution_result = resolver.resolve_conflicts(conflict_resolution.ConflictType.REPOSITORY_SETUP)
        
        if resolution_result['success']:
            strategy = resolution_result['strategy']
            
            if strategy == 'keep_local':
                # Use the new conflict resolution system for keep_local
                success = conflict_resolution.apply_conflict_resolution(vault_path, resolution_result)
                return success
            elif strategy == 'keep_remote':
                # Use the new conflict resolution system for keep_remote
                success = conflict_resolution.apply_conflict_resolution(vault_path, resolution_result)
                return success
            elif strategy == 'smart_merge':
                # Apply smart merge with file-by-file resolution
                success = conflict_resolution.apply_conflict_resolution(vault_path, resolution_result)
                if not success:
                    # Fallback to simple merge strategy
                    safe_update_log("Enhanced resolution failed, falling back to simple merge...", None)
                    success = handle_merge_strategy(vault_path)
                return success
            elif strategy == 'no_conflicts':
                # No conflicts detected - this is a successful resolution
                safe_update_log("No conflicts detected - proceeding with setup", None)
                return True
            elif strategy == 'cancelled':
                # User cancelled the dialog
                safe_update_log("Conflict resolution cancelled by user", None)
                return False
            else:
                safe_update_log("Unknown resolution strategy selected.", None)
                return False
        else:
            safe_update_log("Conflict resolution was cancelled or failed.", None)
            return False
            
    except Exception as e:
        safe_update_log(f"Error in enhanced conflict resolution: {e}", None)
        # Fallback to original conflict resolution dialog
        message = (
            "Both your local vault and the remote repository contain files. "
            "How would you like to resolve this conflict?"
        )
        dialog_parent = parent_window if parent_window is not None else root
        choice = ui_elements.create_repository_conflict_dialog(dialog_parent, message, analysis)
        
        if choice == "merge":
            return handle_merge_strategy(vault_path)
        elif choice == "local":
            return handle_local_strategy(vault_path)
        elif choice == "remote":
            return handle_remote_strategy(vault_path, analysis)
        else:
            safe_update_log("No conflict resolution strategy selected.", None)
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

def handle_merge_strategy(vault_path):
    """
    Handles the merge strategy - combines local and remote files.
    """
    try:
        # Ensure Git user configuration is set
        ensure_git_user_config()
        
        safe_update_log("Resolving conflict using merge strategy...", None)
        
        # First, commit any local changes
        safe_update_log("Committing local files before merge...", None)
        run_command("git add -A", cwd=vault_path)
        commit_out, commit_err, commit_rc = run_command('git commit -m "Local files before merge"', cwd=vault_path)
        
        if commit_rc != 0:
            safe_update_log(f"⚠️ Warning: Could not commit local files: {commit_err}", None)
            # Continue anyway - might be no changes to commit
        
        # Pull remote changes with merge strategy
        safe_update_log("Attempting to merge remote changes...", None)
        merge_out, merge_err, merge_rc = run_command("git pull origin main --no-rebase --allow-unrelated-histories", cwd=vault_path)
        
        safe_update_log(f"Merge command output: {merge_out}", None)
        if merge_err:
            safe_update_log(f"Merge command stderr: {merge_err}", None)
        
        if merge_rc == 0:
            safe_update_log("✅ Files merged successfully. Both local and remote files are now combined.", None)
            # Push the merged result back to remote repository
            safe_update_log("Pushing merged files to remote repository...", None)
            push_out, push_err, push_rc = run_command("git push origin main", cwd=vault_path)
            if push_rc == 0:
                safe_update_log("✅ Merged files successfully pushed to remote repository.", None)
            else:
                safe_update_log(f"⚠️ Warning: Could not push merged files: {push_err}", None)
                safe_update_log("💡 You can push the changes manually later.", None)
            return True
        elif "CONFLICT" in (merge_out + merge_err):
            safe_update_log("⚠️ Automatic merge created conflicts. These will need to be resolved manually during first use.", None)
            # For now, let's still consider this a success since user can resolve later
            return True
        elif "Already up to date" in (merge_out + merge_err):
            safe_update_log("✅ Repository is already up to date. Merge completed.", None)
            return True
        else:
            # More detailed error reporting
            safe_update_log(f"❌ Merge failed with return code {merge_rc}", None)
            safe_update_log(f"❌ Error details: {merge_err}", None)
            safe_update_log("💡 Don't worry - files will be merged during regular sync process.", None)
            # Instead of failing completely, let's allow setup to continue
            return True
            
    except Exception as e:
        safe_update_log(f"❌ Error in merge strategy: {e}", None)
        safe_update_log("💡 Don't worry - files will be merged during regular sync process.", None)
        # Instead of failing completely, let's allow setup to continue
        return True

def handle_local_strategy(vault_path):
    """
    Handles the local strategy - keeps local files, overwrites remote.
    """
    try:
        safe_update_log("Resolving conflict using local strategy (keeping local files)...", None)
        
        # Commit local files
        run_command("git add -A", cwd=vault_path)
        commit_out, commit_err, commit_rc = run_command('git commit -m "Initial commit with local files"', cwd=vault_path)
        
        if commit_rc == 0:
            # Force push to overwrite remote
            push_out, push_err, push_rc = run_command("git push origin main --force", cwd=vault_path)
            if push_rc == 0:
                safe_update_log("✅ Local files have been pushed to remote repository.", None)
                return True
            else:
                safe_update_log(f"❌ Error pushing local files: {push_err}", None)
                return False
        else:
            safe_update_log(f"❌ Error committing local files: {commit_err}", None)
            return False
            
    except Exception as e:
        safe_update_log(f"❌ Error in local strategy: {e}", None)
        return False

def handle_remote_strategy(vault_path, analysis):
    """
    Handles the remote strategy - downloads remote files, backs up local files.
    """
    try:
        safe_update_log("Resolving conflict using remote strategy (downloading remote files)...", None)
        
        # Create backup of local files with descriptive naming
        backup_dir, backup_name = create_descriptive_backup_dir(vault_path, "before_remote_download", analysis["local_files"])
        
        # Move local content files to backup
        for file_path in analysis["local_files"]:
            full_path = os.path.join(vault_path, file_path)
            if os.path.exists(full_path):
                backup_path = os.path.join(backup_dir, file_path)
                os.makedirs(os.path.dirname(backup_path), exist_ok=True)
                shutil.move(full_path, backup_path)
        
        # Pull remote files
        pull_out, pull_err, pull_rc = run_command("git pull origin main", cwd=vault_path)
        
        if pull_rc == 0:
            safe_update_log(f"✅ Remote files downloaded successfully. Local files backed up to: {backup_name}", None)
            return True
        else:
            safe_update_log(f"❌ Error downloading remote files: {pull_err}", None)
            # Restore backup if pull failed
            for file_path in analysis["local_files"]:
                backup_path = os.path.join(backup_dir, file_path)
                if os.path.exists(backup_path):
                    full_path = os.path.join(vault_path, file_path)
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    shutil.move(backup_path, full_path)
            os.rmdir(backup_dir) if os.path.exists(backup_dir) and not os.listdir(backup_dir) else None
            return False
            
    except Exception as e:
        safe_update_log(f"❌ Error in remote strategy: {e}", None)
        return False

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
    Creates a placeholder file (README.md) in the vault if it doesn't already exist.
    This ensures that there's at least one file to commit.
    Handles directory creation if needed.
    """
    try:
        # Ensure the vault directory exists
        os.makedirs(vault_path, exist_ok=True)
        
        placeholder_path = os.path.join(vault_path, "README.md")
        if not os.path.exists(placeholder_path):
            with open(placeholder_path, "w", encoding="utf-8") as f:
                f.write("# Welcome to your Obsidian Vault\n\nThis placeholder file was generated automatically by Ogresync to initialize the repository.")
            safe_update_log("Placeholder file 'README.md' created, as the vault was empty.", 5)
        else:
            safe_update_log("Placeholder file 'README.md' already exists.", 5)
    except Exception as e:
        safe_update_log(f"❌ Error ensuring placeholder file: {e}", 5)
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

def auto_sync():
    """
    This function is executed if setup is complete.
    It performs the following steps:
      1. Validates that the vault directory exists (offers recovery if missing)
      2. Ensures that the vault has at least one commit (creating an initial commit if necessary, 
         including generating a placeholder file if the vault is empty).
      3. Checks network connectivity.
         - If online, it verifies that the remote branch ('main') exists (pushing the initial commit if needed)
           and pulls the latest updates from GitHub (using rebase and prompting for conflict resolution if required).
         - If offline, it skips remote operations.
      4. Stashes any local changes before pulling.
      5. Reapplies stashed changes.
      6. Opens Obsidian for editing and waits until it is closed.
      7. Upon Obsidian closure, stages and commits any changes.
      8. If online, pushes any unpushed commits to GitHub.
      9. Displays a final synchronization completion message.
    """
    vault_path = config_data["VAULT_PATH"]
    obsidian_path = config_data["OBSIDIAN_PATH"]

    if not vault_path or not obsidian_path:
        safe_update_log("Vault path or Obsidian path not set. Please run setup again.", 0)
        return

    def sync_thread():
        nonlocal vault_path
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
            
            if only_has_readme:
                safe_update_log("Local repository only has README. Checking for remote files to download...", 20)
                # Check if remote has actual content files
                ls_out, ls_err, ls_rc = run_command("git ls-tree -r --name-only origin/main", cwd=vault_path)
                if ls_rc == 0 and ls_out.strip():
                    remote_files = [f.strip() for f in ls_out.splitlines() if f.strip()]
                    content_files = [f for f in remote_files if f not in ['README.md', '.gitignore']]
                    
                    if content_files:
                        safe_update_log(f"Remote has {len(content_files)} content files. Downloading them...", 22)
                        # Use reset to get all remote files (safe since local only has README)
                        reset_out, reset_err, reset_rc = run_command("git reset --hard origin/main", cwd=vault_path)
                        if reset_rc == 0:
                            safe_update_log(f"Successfully downloaded all remote files! ({len(content_files)} files)", 25)
                            # Verify files were actually downloaded
                            new_local_files = []
                            for root_dir, dirs, files in os.walk(vault_path):
                                if '.git' in root_dir:
                                    continue
                                for file in files:
                                    if not file.startswith('.'):
                                        new_local_files.append(file)
                            safe_update_log(f"Local directory now has {len(new_local_files)} files", 25)
                            out, err, rc = reset_out, reset_err, reset_rc
                        else:
                            safe_update_log(f"Error with reset, trying pull: {reset_err}", 22)
                            # Fall back to pull with unrelated histories
                            out, err, rc = run_command("git pull origin main --allow-unrelated-histories", cwd=vault_path)
                            if rc == 0:
                                safe_update_log("Successfully pulled remote files using fallback method", 25)
                    else:
                        safe_update_log("Remote repository only has README/gitignore - no content to pull", 20)
                        out, err, rc = "", "", 0  # Simulate successful pull
                else:
                    safe_update_log("Remote repository is empty - no files to pull", 20)
                    out, err, rc = "", "", 0  # Simulate successful pull
            else:
                safe_update_log("Pulling the latest updates from GitHub...", 20)
                out, err, rc = run_command("git pull --rebase origin main", cwd=vault_path)
            if rc != 0:
                if "Could not resolve hostname" in err or "network" in err.lower():
                    safe_update_log("❌ Unable to pull updates due to a network error. Local changes remain safely stashed.", 30)
                elif "CONFLICT" in (out + err):  # Detect merge conflicts
                    safe_update_log("❌ A merge conflict was detected during the pull operation.", 30)
                    # Retrieve the list of conflicting files
                    conflict_files, _, _ = run_command("git diff --name-only --diff-filter=U", cwd=vault_path)
                    if not conflict_files.strip():
                        conflict_files = "Unknown files"
                    # Prompt user for resolution choice
                    choice = conflict_resolution_dialog(conflict_files)
                    if choice == "ours":
                        safe_update_log("Resolving conflict by keeping local changes...", 30)
                        run_command("git checkout --ours .", cwd=vault_path)
                        run_command("git add -A", cwd=vault_path)
                        rc_rebase, err_rebase, _ = run_command("git rebase --continue", cwd=vault_path)
                        if rc_rebase != 0:
                            safe_update_log(f"Error continuing rebase: {err_rebase}", 30)
                            run_command("git rebase --abort", cwd=vault_path)
                    elif choice == "theirs":
                        safe_update_log("Resolving conflict by using remote changes...", 30)
                        run_command("git checkout --theirs .", cwd=vault_path)
                        run_command("git add -A", cwd=vault_path)
                        rc_rebase, err_rebase, _ = run_command("git rebase --continue", cwd=vault_path)
                        if rc_rebase != 0:
                            safe_update_log(f"Error continuing rebase: {err_rebase}", 30)
                            run_command("git rebase --abort", cwd=vault_path)
                    elif choice == "manual":
                        safe_update_log("Please resolve the conflicts manually. After resolving, click OK to continue.", 30)
                        ui_elements.show_info_message("Manual Merge", "Please resolve the conflicts in the affected files manually and then click OK.")
                        run_command("git add -A", cwd=vault_path)
                        rc_rebase, err_rebase, _ = run_command("git rebase --continue", cwd=vault_path)
                        if rc_rebase != 0:
                            safe_update_log(f"Error continuing rebase after manual merge: {err_rebase}", 30)
                            run_command("git rebase --abort", cwd=vault_path)
                    else:
                        safe_update_log("No valid conflict resolution chosen. Aborting rebase.", 30)
                        run_command("git rebase --abort", cwd=vault_path)
                else:
                    safe_update_log("Pull operation completed successfully. Your vault is updated with the latest changes from GitHub.", 30)
                    # Log pulled files
                    for line in out.splitlines():
                        safe_update_log(f"✓ Pulled: {line}", 30)
            else:
                safe_update_log("Pull operation completed successfully. Your vault is up to date.", 30)
        else:
            safe_update_log("Skipping pull operation due to offline mode.", 20)

        # Step 5: Reapply stashed changes
        out, err, rc = run_command("git stash pop", cwd=vault_path)
        if rc != 0 and "No stash" not in err:
            if "CONFLICT" in (out + err):
                safe_update_log("❌ A merge conflict occurred while reapplying stashed changes. Please resolve manually.", 35)
                return
            else:
                safe_update_log(f"Stash pop operation failed: {err}", 35)
                return
        safe_update_log("Successfully reapplied stashed local changes.", 35)

        # Step 6: Open Obsidian for editing using the helper function
        safe_update_log("Launching Obsidian. Please edit your vault and close Obsidian when finished.", 40)
        try:
            open_obsidian(obsidian_path)
        except Exception as e:
            safe_update_log(f"Error launching Obsidian: {e}", 40)
            return
        safe_update_log("Waiting for Obsidian to close...", 45)
        while is_obsidian_running():
            time.sleep(0.5)


        # Step 7: Pull any new changes from GitHub after Obsidian closes
        safe_update_log("Obsidian has been closed. Checking for new remote changes before committing...", 50)

        # Re-check network connectivity before pulling
        network_available = is_network_available()
        if network_available:
            safe_update_log("Pulling any new updates from GitHub before committing...", 50)
            out, err, rc = run_command("git pull --rebase origin main", cwd=vault_path)
            if rc != 0:
                if "Could not resolve hostname" in err or "network" in err.lower():
                    safe_update_log("❌ Unable to pull updates due to network error. Continuing with local commit.", 50)
                elif "CONFLICT" in (out + err):  # Detect merge conflicts
                    safe_update_log("❌ Merge conflict detected in new remote changes.", 50)
                    # Retrieve the list of conflicting files
                    conflict_files, _, _ = run_command("git diff --name-only --diff-filter=U", cwd=vault_path)
                    if not conflict_files.strip():
                        conflict_files = "Unknown files"
                    # Prompt user for conflict resolution
                    choice = conflict_resolution_dialog(conflict_files)
                    if choice == "ours":
                        safe_update_log("Resolving conflict by keeping local changes...", 50)
                        run_command("git checkout --ours .", cwd=vault_path)
                        run_command("git add -A", cwd=vault_path)
                        rc_rebase, err_rebase, _ = run_command("git rebase --continue", cwd=vault_path)
                        if rc_rebase != 0:
                            safe_update_log(f"Error continuing rebase: {err_rebase}", 50)
                            run_command("git rebase --abort", cwd=vault_path)
                    elif choice == "theirs":
                        safe_update_log("Resolving conflict by using remote changes...", 50)
                        run_command("git checkout --theirs .", cwd=vault_path)
                        run_command("git add -A", cwd=vault_path)
                        rc_rebase, err_rebase, _ = run_command("git rebase --continue", cwd=vault_path)
                        if rc_rebase != 0:
                            safe_update_log(f"Error continuing rebase: {err_rebase}", 50)
                            run_command("git rebase --abort", cwd=vault_path)
                    elif choice == "manual":
                        safe_update_log("Please resolve the conflicts manually. After resolving, click OK to continue.", 50)
                        ui_elements.show_info_message("Manual Merge", "Please resolve the conflicts in the affected files manually and then click OK.")
                        run_command("git add -A", cwd=vault_path)
                        rc_rebase, err_rebase, _ = run_command("git rebase --continue", cwd=vault_path)
                        if rc_rebase != 0:
                            safe_update_log(f"Error continuing rebase after manual merge: {err_rebase}", 50)
                            run_command("git rebase --abort", cwd=vault_path)
                    else:
                        safe_update_log("No valid conflict resolution chosen. Aborting rebase.", 50)
                        run_command("git rebase --abort", cwd=vault_path)
                else:
                    safe_update_log("New remote updates have been successfully pulled.", 50)
                    # Log pulled files
                    for line in out.splitlines():
                        safe_update_log(f"✓ Pulled: {line}", 50)
        else:
            safe_update_log("No network detected. Skipping remote check and proceeding with local commit.", 50)

        # Step 8: Commit changes after Obsidian closes
        safe_update_log("Obsidian has been closed. Committing any local changes...", 50)
        run_command("git add -A", cwd=vault_path)
        out, err, rc = run_command('git commit -m "Auto sync commit"', cwd=vault_path)
        committed = True
        if rc != 0 and "nothing to commit" in (out + err).lower():
            safe_update_log("No changes detected during this session. Nothing to commit.", 55)
            committed = False
        elif rc != 0:
            safe_update_log(f"❌ Commit operation failed: {err}", 55)
            return
        else:
            safe_update_log("Local changes have been committed successfully.", 55)
            commit_details, err_details, rc_details = run_command("git diff-tree --no-commit-id --name-status -r HEAD", cwd=vault_path)
            if rc_details == 0 and commit_details.strip():
                for line in commit_details.splitlines():
                    safe_update_log(f"✓ {line}", None)

        # Step 9: Push changes if network is available
        network_available = is_network_available()
        if network_available:
            unpushed = get_unpushed_commits(vault_path)
            if unpushed:
                safe_update_log("Pushing all unpushed commits to GitHub...", 60)
                out, err, rc = run_command("git push origin main", cwd=vault_path)
                if rc != 0:
                    if "Could not resolve hostname" in err or "network" in err.lower():
                        safe_update_log("❌ Unable to push changes due to network issues. Your changes remain locally committed and will be pushed once connectivity is restored.", 70)
                    else:
                        safe_update_log(f"❌ Push operation failed: {err}", 70)
                    return
                safe_update_log("✅ All changes have been successfully pushed to GitHub.", 70)
            else:
                safe_update_log("No new commits to push.", 70)
        else:
            safe_update_log("Offline mode: Changes have been committed locally. They will be automatically pushed when an internet connection is available.", 70)

        # Step 9: Final message
        safe_update_log("Synchronization complete. You may now close this window.", 100)

    threading.Thread(target=sync_thread, daemon=True).start()


# ------------------------------------------------
# ONE-TIME SETUP WORKFLOW
# ------------------------------------------------

def run_setup_wizard():
    """
    Runs the new progressive setup wizard that guides users through all setup steps.
    """
    try:
        success, wizard_state = setup_wizard.run_setup_wizard()
        
        if success:
            # Setup completed successfully
            return True
        else:
            # Setup was cancelled or failed
            return False
            
    except Exception as e:
        if ui_elements:
            ui_elements.show_error_message(
                "Setup Error",
                f"An error occurred during setup: {str(e)}"
            )
        else:
            print(f"Setup Error: {str(e)}")
        return False

def setup_new_vault_directory(vault_path):
    """
    Sets up a newly selected vault directory by:
    1. Checking if it has existing files
    2. Initializing git repository
    3. Configuring remote URL (reuse or ask for new)
    4. Handling conflicts between local and remote content
    
    Returns True if setup successful, False otherwise.
    """
    try:
        # Check if directory has existing files (excluding common non-content files)
        existing_files = []
        if os.path.exists(vault_path):
            for root_dir, dirs, files in os.walk(vault_path):
                # Skip .git directory if it exists
                if '.git' in root_dir:
                    continue
                for file in files:
                    # Skip hidden files and common non-content files
                    if not file.startswith('.') and file not in ['README.md', '.gitignore']:
                        rel_path = os.path.relpath(os.path.join(root_dir, file), vault_path)
                        existing_files.append(rel_path)
        
        has_existing_files = len(existing_files) > 0
        
        if has_existing_files:
            safe_update_log(f"New vault directory contains {len(existing_files)} existing files.", None)
        else:
            safe_update_log("New vault directory is empty.", None)
        
        # Initialize git repository
        initialize_git_repo(vault_path)
        
        # Ask user about remote repository configuration
        saved_url = config_data.get("GITHUB_REMOTE_URL", "").strip()
        
        if saved_url:
            # Offer to reuse existing remote URL
            reuse_remote = ui_elements.ask_yes_no(
                "Use Existing Repository",
                f"A GitHub repository URL is already configured:\n\n{saved_url}\n\n"
                "Would you like to use this repository for the new vault directory?"
            )
        else:
            reuse_remote = False
        
        if reuse_remote:
            # Use existing remote URL
            repo_url = saved_url
            safe_update_log(f"Using existing remote URL: {repo_url}", None)
        else:
            # Ask for new repository URL
            prompt_msg = "Enter your GitHub repository URL (e.g., git@github.com:username/repo.git):"
            if saved_url:
                prompt_msg += f"\n\nCurrent URL: {saved_url}"
            
            repo_url = ui_elements.ask_string_dialog(
                "GitHub Repository",
                prompt_msg,
                initial_value=saved_url if saved_url else "",
                icon=ui_elements.Icons.LINK
            )
            
            if not repo_url or not repo_url.strip():
                safe_update_log("❌ No repository URL provided.", None)
                ui_elements.show_error_message(
                    "URL Required",
                    "A GitHub repository URL is required to sync your vault."
                )
                return False
            
            repo_url = repo_url.strip()
        
        # Configure git remote
        out, err, rc = run_command(f"git remote add origin {repo_url}", cwd=vault_path)
        if rc != 0:
            safe_update_log(f"❌ Failed to configure remote: {err}", None)
            ui_elements.show_error_message(
                "Git Remote Error",
                f"Failed to configure GitHub remote:\n{err}\n\nPlease check the URL and try again."
            )
            return False
        
        # Update config with the repository URL
        config_data["GITHUB_REMOTE_URL"] = repo_url
        save_config()
        safe_update_log("GitHub remote URL updated in configuration.", None)
        
        # Analyze repository state for potential conflicts
        safe_update_log("Analyzing local and remote repository content...", None)
        analysis = analyze_repository_state(vault_path)
        
        if has_existing_files:
            # Commit existing local files first
            safe_update_log("Committing existing local files...", None)
            run_command("git add -A", cwd=vault_path)
            commit_out, commit_err, commit_rc = run_command('git commit -m "Initial commit with existing local files"', cwd=vault_path)
            
            if commit_rc != 0:
                safe_update_log(f"❌ Failed to commit local files: {commit_err}", None)
                return False
        
        # Check if there are conflicts between local and remote
        if analysis["conflict_detected"]:
            safe_update_log("Content conflict detected between local and remote repositories.", None)
            
            # Use the new two-stage conflict resolution system
            try:
                # Create enhanced conflict analysis
                enhanced_analysis = conflict_resolution.ConflictAnalysis()
                enhanced_analysis.has_conflicts = True
                enhanced_analysis.conflict_type = conflict_resolution.ConflictType.REPOSITORY_SETUP
                enhanced_analysis.summary = f"Repository setup conflicts detected"
                
                # Convert analysis data to enhanced format
                enhanced_analysis.local_only_files = analysis.get("local_files", [])
                enhanced_analysis.remote_only_files = analysis.get("remote_files", [])
                
                # Create file conflict info for files that exist in both but are different
                for local_file in analysis.get("local_files", []):
                    if local_file in analysis.get("remote_files", []):
                        conflict_info = conflict_resolution.FileConflictInfo(local_file, 'both_modified')
                        conflict_info.has_content_conflict = True
                        enhanced_analysis.conflicted_files.append(conflict_info)
                
                # Use the enhanced conflict resolver
                resolver = conflict_resolution.ConflictResolver(vault_path, root, enhanced_analysis)    
                resolution_result = resolver.resolve_conflicts(conflict_resolution.ConflictType.REPOSITORY_SETUP)
                
                if resolution_result['success']:
                    strategy = resolution_result['strategy']
                    
                    if strategy == 'keep_local':
                        # Use the new conflict resolution system for keep_local
                        success = conflict_resolution.apply_conflict_resolution(vault_path, resolution_result)
                    elif strategy == 'keep_remote':
                        # Use the new conflict resolution system for keep_remote
                        success = conflict_resolution.apply_conflict_resolution(vault_path, resolution_result)
                    elif strategy == 'smart_merge':
                        # Apply smart merge with file-by-file resolution
                        success = conflict_resolution.apply_conflict_resolution(vault_path, resolution_result)
                        if not success:
                            # Fallback to simple merge strategy
                            success = handle_merge_strategy(vault_path)
                    elif strategy == 'no_conflicts':
                        # No conflicts detected - this is a successful resolution
                        safe_update_log("No conflicts detected - proceeding with setup", None)
                        success = True
                    elif strategy == 'cancelled':
                        # User cancelled the dialog
                        safe_update_log("Conflict resolution cancelled by user", None)
                        success = False
                    else:
                        safe_update_log("Unknown resolution strategy selected.", None)
                        success = False
                else:
                    safe_update_log("Conflict resolution was cancelled or failed.", None)
                    success = False
                    
            except Exception as e:
                safe_update_log(f"Error in enhanced conflict resolution: {e}", None)
                # Fallback to original conflict resolution dialog
                message = (
                    "Both your new vault directory and the remote repository contain files. "
                    "How would you like to resolve this conflict?"
                )
                choice = ui_elements.create_repository_conflict_dialog(root, message, analysis)
                
                if choice == "merge":
                    success = handle_merge_strategy(vault_path)
                elif choice == "local":
                    success = handle_local_strategy(vault_path)
                elif choice == "remote":
                    success = handle_remote_strategy(vault_path, analysis)
                else:
                    safe_update_log("No conflict resolution strategy selected.", None)
                    success = False
            
            if not success:
                safe_update_log("❌ Failed to resolve repository conflict.", None)
                return False
                
            safe_update_log("✅ Repository conflict resolved successfully.", None)
        
        elif analysis["has_remote_files"]:
            # Remote has files, local is empty or no conflicts - just pull
            safe_update_log("Downloading remote files...", None)
            pull_out, pull_err, pull_rc = run_command("git pull origin main", cwd=vault_path)
            if pull_rc == 0:
                safe_update_log("✅ Remote files downloaded successfully.", None)
            else:
                if "couldn't find remote ref" in pull_err.lower():
                    safe_update_log("Remote repository is empty. This is normal for new repositories.", None)
                else:
                    safe_update_log(f"Note: Could not pull remote files: {pull_err}", None)
        
        elif has_existing_files:
            # Local has files, remote is empty - files will be pushed during regular sync
            safe_update_log("Local files will be uploaded during the next sync.", None)
        
        else:
            # Both local and remote are empty
            safe_update_log("Both local and remote are empty. Ready for first use.", None)
        
        return True
        
    except Exception as e:
        safe_update_log(f"❌ Error setting up new vault directory: {e}", None)
        ui_elements.show_error_message(
            "Setup Failed",
            f"Failed to set up new vault directory:\n{e}\n\nPlease try again."
        )
        return False

# ------------------------------------------------
# UTILITY FUNCTIONS
# ------------------------------------------------

def restart_for_setup():
    """
    Restarts the application in setup mode by resetting configuration and restarting the main loop.
    """
    try:
        # Don't reset SETUP_DONE here - only reset if specifically restarting for setup
        # config_data["SETUP_DONE"] = "0"
        # save_config()
        
        # Close current window
        if root:
            root.destroy()
        
        # Restart main function
        main()
    except Exception as e:
        print(f"Error restarting for setup: {e}")
        # Fallback: just show error and exit
        sys.exit(1)

def restart_to_sync_mode():
    """
    Transitions the application to sync mode after setup completion.
    """
    global root, log_text, progress_bar
    
    try:
        print("DEBUG: Starting transition to sync mode")
        
        # Ensure we have the latest config before transitioning
        load_config()
        
        # Verify the config is properly saved
        if config_data.get("SETUP_DONE", "0") != "1":
            config_data["SETUP_DONE"] = "1"
            save_config()
        
        print("DEBUG: Config verified for sync mode")
        
        # Safer approach: directly restart the process instead of trying to transition UI
        print("DEBUG: Restarting process in sync mode")
        
        # Close current window cleanly
        if root and root.winfo_exists():
            try:
                root.quit()
                root.destroy()
            except Exception as e:
                print(f"DEBUG: Error closing window: {e}")
        
        # Restart the process
        import sys
        import os
        print("DEBUG: Restarting Python process")
        
        # Use os.execv to replace the current process completely
        python_executable = sys.executable
        script_path = os.path.abspath(__file__)
        os.execv(python_executable, [python_executable, script_path])
        
    except Exception as e:
        print(f"Error transitioning to sync mode: {e}")
        # Fallback: try to create minimal UI directly
        try:
            root, log_text, progress_bar = ui_elements.create_minimal_ui(auto_run=True)
            auto_sync()
            root.mainloop()
        except Exception as e2:
            print(f"Fallback also failed: {e2}")
            sys.exit(1)

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
        success = run_setup_wizard()
        
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