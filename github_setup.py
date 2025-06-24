"""
GitHub Setup Functions Module

This module contains all the GitHub repository setup and configuration functions
that were previously in Ogresync.py to reduce the main file's complexity.

These functions handle:
- Git repository initialization
- GitHub remote configuration
- Repository state analysis
- Conflict resolution during setup
- SSH key management
- Placeholder file creation
"""

import os
import subprocess
import threading
import time
from typing import Optional, Tuple


# Dependency injection pattern - these will be set by the main module
_ui_elements = None
_config_data = None
_save_config_func = None
_conflict_resolution_module = None
_safe_update_log_func = None

def set_dependencies(ui_elements=None, config_data=None, save_config_func=None, 
                    conflict_resolution_module=None, safe_update_log_func=None):
    """Set the dependencies from the main module"""
    global _ui_elements, _config_data, _save_config_func, _conflict_resolution_module, _safe_update_log_func
    _ui_elements = ui_elements
    _config_data = config_data
    _save_config_func = save_config_func
    _conflict_resolution_module = conflict_resolution_module
    _safe_update_log_func = safe_update_log_func


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


def safe_update_log(message, progress=None):
    """
    Log function that uses the injected dependency or falls back to print
    """
    if _safe_update_log_func:
        _safe_update_log_func(message, progress)
    else:
        print(f"LOG: {message}")


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
            return True
        else:
            safe_update_log("Error initializing Git repository: " + err, 20)
            return False
    else:
        safe_update_log("Vault is already a Git repository.", 20)
        return True


def set_github_remote(vault_path, ui_elements=None, config_data=None):
    """
    Prompts the user to link an existing GitHub repository.
    If the user chooses not to link (or closes the dialog without providing a URL),
    an error is shown indicating that linking a repository is required.
    Returns True if the repository is linked successfully; otherwise, returns False.
    """
    # Use injected dependencies if not provided
    if ui_elements is None:
        ui_elements = _ui_elements
    if config_data is None:
        config_data = _config_data
    # Check if a remote named 'origin' already exists
    existing_remote_url, err, rc = run_command("git remote get-url origin", cwd=vault_path)
    if rc == 0:
        safe_update_log(f"A remote named 'origin' already exists: {existing_remote_url}", 25)
        if ui_elements:
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
                    safe_update_log(f"Failed to remove existing remote: {err}", 25)
                safe_update_log("Existing 'origin' remote removed.", 25)

    # Prompt for linking a repository
    if ui_elements:
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
                icon=getattr(ui_elements.Icons, 'LINK', None) if hasattr(ui_elements, 'Icons') else None
            )
            if repo_url:
                out, err, rc = run_command(f"git remote add origin {repo_url}", cwd=vault_path)
                if rc == 0:
                    safe_update_log(f"Git remote added: {repo_url}", 30)
                    if config_data:
                        config_data["GITHUB_REMOTE_URL"] = repo_url
                    return True
                else:
                    safe_update_log(f"Failed to add remote: {err}", 30)
                    if ui_elements:
                        ui_elements.show_error_message("Git Remote Error", f"Failed to add GitHub remote:\n{err}")
                    return False
            else:
                if ui_elements:
                    ui_elements.show_error_message("Error", "Repository URL not provided. You must link to a GitHub repository.")
                return False
        else:
            if ui_elements:
                ui_elements.show_error_message("GitHub Repository Required", 
                                     "Linking a GitHub repository is required for synchronization.\n"
                                     "Please create a repository on GitHub (private is recommended) and then link to it.")
            return False
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
                f.write("# My Obsidian Vault\n\n")
                f.write("This vault is synchronized with GitHub using Ogresync.\n")
                f.write("You can safely delete this README.md file and start adding your notes.\n")
            safe_update_log("Placeholder file 'README.md' created, as the vault was empty.", 5)
        else:
            safe_update_log(f"Vault contains {len(vault_files)} files - no placeholder needed.", 5)
            
    except Exception as e:
        safe_update_log(f"❌ Error checking/creating placeholder file: {e}", 5)
        raise  # Re-raise to be handled by caller


def configure_remote_url_for_vault(vault_path, ui_elements=None, config_data=None, save_config_func=None):
    """
    Configures the remote URL for a vault directory.
    If a URL is already saved in config, offers to reuse it.
    Otherwise, prompts for a new URL.
    Returns True if successful, False otherwise.
    """
    # Use injected dependencies if not provided
    if ui_elements is None:
        ui_elements = _ui_elements
    if config_data is None:
        config_data = _config_data
    if save_config_func is None:
        save_config_func = _save_config_func
    saved_url = config_data.get("GITHUB_REMOTE_URL", "").strip() if config_data else ""
    
    if saved_url and ui_elements:
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
                safe_update_log(f"Git remote configured: {saved_url}", None)
                return True
            else:
                safe_update_log(f"❌ Failed to configure remote: {err}", None)
                return False
        else:
            # User wants to use a different URL
            safe_update_log("User chose to configure a different repository URL.", None)
    
    # Ask for new URL (either no saved URL or user declined to reuse)
    if ui_elements:
        repo_url = ui_elements.ask_string_dialog(
            "GitHub Repository",
            "Enter your GitHub repository URL (e.g., git@github.com:username/repo.git):",
            initial_value=saved_url,  # Pre-fill with saved URL if available
            icon=getattr(ui_elements.Icons, 'LINK', None) if hasattr(ui_elements, 'Icons') else None
        )
        
        if repo_url and repo_url.strip():
            repo_url = repo_url.strip()
            out, err, rc = run_command(f"git remote add origin {repo_url}", cwd=vault_path)
            if rc == 0:
                safe_update_log(f"Git remote configured: {repo_url}", None)
                
                # Update config with new URL
                if config_data:
                    config_data["GITHUB_REMOTE_URL"] = repo_url
                if save_config_func:
                    save_config_func()
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
    return False


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
                analysis["local_files"].append(os.path.join(root_dir, file))
        
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
                analysis["remote_files"] = ls_out.strip().split('\n')
                analysis["has_remote_files"] = True
    except Exception as e:
        safe_update_log(f"Error analyzing remote repository: {e}", None)
    
    # Determine if there's a conflict (both local and remote have content files)
    analysis["conflict_detected"] = analysis["has_local_files"] and analysis["has_remote_files"]
    
    return analysis


def handle_initial_repository_conflict(vault_path, analysis, parent_window=None, 
                                     conflict_resolution_module=None, config_data=None):
    """
    Handles repository content conflicts during initial setup using the enhanced two-stage resolution system.
    Returns True if resolved successfully, False otherwise.
    """
    # Use injected dependencies if not provided
    if conflict_resolution_module is None:
        conflict_resolution_module = _conflict_resolution_module
    if config_data is None:
        config_data = _config_data
    if not analysis["conflict_detected"]:
        return True
    
    if not conflict_resolution_module:
        # Fall back to simple dialog
        safe_update_log("Enhanced conflict resolution not available, using fallback", None)
        return False
    
    try:
        # Use the enhanced two-stage conflict resolution system
        resolver = conflict_resolution_module.ConflictResolver(vault_path, parent_window)
        
        # Get GitHub URL for analysis
        github_url = config_data.get("GITHUB_REMOTE_URL", "") if config_data else ""
        
        # Use the enhanced conflict resolution system
        result = resolver.resolve_initial_setup_conflicts(github_url)
        
        if result.success:
            safe_update_log(f"Repository conflict resolved successfully: {result.message}", None)
            return True
        else:
            if "cancelled by user" in result.message.lower():
                safe_update_log("Conflict resolution cancelled by user.", None)
            else:
                safe_update_log(f"Conflict resolution failed: {result.message}", None)
            return False
                
    except Exception as e:
        safe_update_log(f"Error in enhanced repository conflict resolution: {e}", None)
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


def validate_vault_directory(vault_path, ui_elements=None, setup_new_vault_func=None):
    """
    Validates that the vault directory exists and is accessible.
    If not, offers recovery options to the user.
    
    Returns:
        tuple: (is_valid: bool, should_continue: bool, new_vault_path: str|None)
        - is_valid: True if vault exists and is accessible
        - should_continue: True if user wants to continue (either vault exists or recovery chosen)
        - new_vault_path: New vault path if user selected a different directory
    """
    # Use injected dependencies if not provided
    if ui_elements is None:
        ui_elements = _ui_elements
    if not vault_path:
        return False, False, None
    
    # Check if directory exists
    if not os.path.exists(vault_path):
        safe_update_log(f"❌ Vault directory not found: {vault_path}", None)
        
        if ui_elements:
            # Offer recovery options
            choice = ui_elements.create_vault_recovery_dialog(None, vault_path)
            
            if choice == "recreate":
                # Recreate the directory and continue
                try:
                    os.makedirs(vault_path, exist_ok=True)
                    safe_update_log(f"✅ Recreated vault directory: {vault_path}", None)
                    return True, True, None
                except Exception as e:
                    safe_update_log(f"❌ Failed to recreate directory: {e}", None)
                    return False, False, None
            
            elif choice == "select_new":
                # Let user select a new vault directory
                new_vault = ui_elements.ask_directory_dialog("Select New Vault Directory")
                if new_vault:
                    safe_update_log(f"✅ New vault directory selected: {new_vault}", None)
                    return True, True, new_vault
                else:
                    safe_update_log("❌ No directory selected.", None)
                    return False, False, None
            
            elif choice == "setup":
                # Run setup wizard again
                safe_update_log("User chose to run setup wizard again.", None)
                return False, True, "run_setup"
            
            else:
                # User cancelled or closed dialog
                safe_update_log("❌ User cancelled vault recovery.", None)
                return False, False, None
        else:
            return False, False, None
    
    # Check if directory is accessible
    if not os.access(vault_path, os.R_OK | os.W_OK):
        safe_update_log(f"❌ Vault directory is not accessible (permissions): {vault_path}", None)
        if ui_elements:
            ui_elements.show_error_message(
                "Permission Error",
                f"Cannot access vault directory:\n{vault_path}\n\n"
                "Please check directory permissions and try again."
            )
        return False, False, None
    
    return True, True, None


def setup_new_vault_directory(vault_path, ui_elements=None, config_data=None, 
                            save_config_func=None, conflict_resolution_module=None):
    """
    Set up a new vault directory with git initialization and remote configuration.
    
    Args:
        vault_path: Path to the new vault directory
        ui_elements: UI elements module for dialogs
        config_data: Configuration dictionary
        save_config_func: Function to save configuration
        conflict_resolution_module: Conflict resolution module
    
    Returns:
        bool: True if setup was successful, False otherwise
    """
    # Use injected dependencies if not provided
    if ui_elements is None:
        ui_elements = _ui_elements
    if config_data is None:
        config_data = _config_data
    if save_config_func is None:
        save_config_func = _save_config_func
    if conflict_resolution_module is None:
        conflict_resolution_module = _conflict_resolution_module
    try:
        safe_update_log(f"Setting up new vault directory: {vault_path}", None)
        
        # Initialize git repository
        if not initialize_git_repo(vault_path):
            safe_update_log("❌ Failed to initialize git repository", None)
            return False
        
        # Configure remote URL
        if not configure_remote_url_for_vault(vault_path, ui_elements, config_data, save_config_func):
            safe_update_log("❌ Failed to configure remote repository", None)
            return False
        
        # Analyze and handle any repository conflicts
        analysis = analyze_repository_state(vault_path)
        if analysis["conflict_detected"]:
            safe_update_log("Repository conflicts detected, resolving...", None)
            if not handle_initial_repository_conflict(vault_path, analysis, None, 
                                                    conflict_resolution_module, config_data):
                safe_update_log("❌ Failed to resolve repository conflicts", None)
                return False
        
        safe_update_log("✅ New vault directory setup completed successfully", None)
        return True
        
    except Exception as e:
        safe_update_log(f"❌ Error setting up new vault directory: {e}", None)
        return False
