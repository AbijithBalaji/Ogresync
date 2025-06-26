"""
Wizard Steps Functions Module

This module contains all the setup wizard step functions that were previously in Ogresync.py
to reduce the main file's complexity.

These functions handle:
- Finding Obsidian installation paths
- Vault directory selection
- Git installation checking
- SSH connection testing and key generation
- Initial repository setup and commits
"""

import os
import sys
import shutil
import subprocess
import threading
import time
import platform
import webbrowser
import pyperclip
from typing import Optional


# Dependency injection pattern - these will be set by the main module
_ui_elements = None
_config_data = None
_save_config_func = None
_safe_update_log_func = None
_run_command_func = None

def set_dependencies(ui_elements=None, config_data=None, save_config_func=None, 
                    safe_update_log_func=None, run_command_func=None):
    """Set the dependencies from the main module"""
    global _ui_elements, _config_data, _save_config_func, _safe_update_log_func, _run_command_func
    _ui_elements = ui_elements
    _config_data = config_data
    _save_config_func = save_config_func
    _safe_update_log_func = safe_update_log_func
    _run_command_func = run_command_func


def safe_update_log(message, progress=None):
    """Log function that uses the injected dependency or falls back to print"""
    if _safe_update_log_func:
        _safe_update_log_func(message, progress)
    else:
        print(f"LOG: {message}")


def run_command(command, cwd=None, timeout=None):
    """Command execution function that uses the injected dependency or falls back to subprocess"""
    if _run_command_func:
        return _run_command_func(command, cwd, timeout)
    else:
        # Fallback implementation
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


# ------------------------------------------------
# WIZARD STEPS FUNCTIONS
# ------------------------------------------------

def find_obsidian_path():
    """
    Attempts to locate Obsidian's installation or launch command based on the OS.
    
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
    ui_elements = _ui_elements
    
    if sys.platform.startswith("win"):
        possible_paths = [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Obsidian\Obsidian.exe"),
            os.path.expandvars(r"%PROGRAMFILES%\Obsidian\Obsidian.exe"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%\Obsidian\Obsidian.exe")
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        if ui_elements:
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
            else:
                # User chose not to locate manually - offer download guidance
                download_response = ui_elements.ask_yes_no(
                    "Download Obsidian",
                    "Obsidian is required for Ogresync to work.\n\n"
                    "Would you like to go to the Obsidian download page now?\n"
                    "After installation, you can restart the setup wizard."
                )
                if download_response:
                    import webbrowser
                    webbrowser.open("https://obsidian.md/download")
                    ui_elements.show_info_message(
                        "Download Started",
                        "The Obsidian download page has been opened in your browser.\n\n"
                        "Please install Obsidian and restart Ogresync to continue setup."
                    )
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
        
        if ui_elements:
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

    return None


def select_vault_path():
    """
    Asks user to select Obsidian Vault folder. Returns path or None if canceled.
    """
    ui_elements = _ui_elements
    if ui_elements:
        selected = ui_elements.ask_directory_dialog("Select Obsidian Vault Folder")
        return selected if selected else None
    return None


def is_git_installed():
    """
    Returns True if Git is installed, else False.
    """
    out, err, rc = run_command("git --version")
    return rc == 0


def detect_git_path():
    """
    Attempts to detect Git installation path with OS-specific fallbacks.
    Returns the path to git executable if found, None otherwise.
    """
    import platform
    
    # First try to find git in PATH
    git_cmd = shutil.which("git")
    if git_cmd:
        return git_cmd
    
    # OS-specific common installation paths
    if platform.system() == "Windows":
        common_paths = [
            "C:\\Program Files\\Git\\bin\\git.exe",
            "C:\\Program Files (x86)\\Git\\bin\\git.exe",
            "C:\\Users\\{}\\AppData\\Local\\Programs\\Git\\bin\\git.exe".format(os.getenv('USERNAME', '')),
            "C:\\Program Files\\GitHub Desktop\\resources\\app\\git\\cmd\\git.exe",
            "C:\\Program Files (x86)\\GitHub Desktop\\resources\\app\\git\\cmd\\git.exe"
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
                
        # Check if user wants to locate manually on Windows
        if _ui_elements:
            response = _ui_elements.ask_yes_no(
                "Git Not Found",
                "Git was not detected in standard locations.\n\n"
                "Would you like to locate the Git executable manually?\n"
                "(Look for git.exe in your Git installation folder)"
            )
            if response:
                selected_path = _ui_elements.ask_file_dialog(
                    "Select Git Executable",
                    filetypes=[("Git Executable", "git.exe"), ("All Files", "*.*")]
                )
                if selected_path and os.path.exists(selected_path):
                    return selected_path
            else:
                # User chose not to locate manually - offer download guidance
                download_response = _ui_elements.ask_yes_no(
                    "Download Git",
                    "Git is required for Ogresync to work with version control.\n\n"
                    "Would you like to go to the Git download page now?\n"
                    "After installation, you can restart the setup wizard."
                )
                if download_response:
                    import webbrowser
                    webbrowser.open("https://git-scm.com/download/win")
                    _ui_elements.show_info_message(
                        "Download Started",
                        "The Git download page has been opened in your browser.\n\n"
                        "Please install Git and restart Ogresync to continue setup.\n"
                        "Tip: Use the default installation options for best compatibility."
                    )
        return None
        
    elif platform.system() == "Darwin":  # macOS
        common_paths = [
            "/usr/bin/git",
            "/usr/local/bin/git",
            "/opt/homebrew/bin/git",
            "/Applications/GitHub Desktop.app/Contents/Resources/app/git/bin/git"
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
                
        # Check if user wants to locate manually on macOS
        if _ui_elements:
            response = _ui_elements.ask_yes_no(
                "Git Not Found",
                "Git was not detected in standard locations.\n\n"
                "Would you like to locate the Git executable manually?\n"
                "(Usually found in /usr/bin/git or /usr/local/bin/git)"
            )
            if response:
                selected_path = _ui_elements.ask_file_dialog(
                    "Select Git Executable",
                    filetypes=[("Git Executable", "git"), ("All Files", "*")]
                )
                if selected_path and os.path.exists(selected_path):
                    return selected_path
            else:
                # User chose not to locate manually - offer download guidance
                download_response = _ui_elements.ask_yes_no(
                    "Install Git",
                    "Git is required for Ogresync to work with version control.\n\n"
                    "Would you like to install Git using Xcode Command Line Tools?\n"
                    "This is the recommended method on macOS."
                )
                if download_response:
                    _ui_elements.show_info_message(
                        "Install Git",
                        "To install Git on macOS:\n\n"
                        "1. Open Terminal (Cmd+Space, type 'Terminal')\n"
                        "2. Run: xcode-select --install\n"
                        "3. Follow the installation prompts\n"
                        "4. Restart Ogresync after installation\n\n"
                        "Alternative: Visit git-scm.com/download/mac for other options."
                    )
        return None
        
    else:  # Linux and others
        common_paths = [
            "/usr/bin/git",
            "/usr/local/bin/git",
            "/bin/git"
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
                
        # Check if user wants to locate manually on Linux
        if _ui_elements:
            response = _ui_elements.ask_yes_no(
                "Git Not Found", 
                "Git was not detected in standard locations.\n\n"
                "Would you like to locate the Git executable manually?\n"
                "(Usually found in /usr/bin/git)"
            )
            if response:
                selected_path = _ui_elements.ask_file_dialog(
                    "Select Git Executable",
                    filetypes=[("Git Executable", "git"), ("All Files", "*")]
                )
                if selected_path and os.path.exists(selected_path):
                    return selected_path
            else:
                # User chose not to locate manually - offer installation guidance
                download_response = _ui_elements.ask_yes_no(
                    "Install Git",
                    "Git is required for Ogresync to work with version control.\n\n"
                    "Would you like to see installation instructions for your system?"
                )
                if download_response:
                    _ui_elements.show_info_message(
                        "Install Git on Linux",
                        "To install Git on Linux, use your package manager:\n\n"
                        "• Ubuntu/Debian: sudo apt update && sudo apt install git\n"
                        "• Fedora: sudo dnf install git\n"
                        "• CentOS/RHEL: sudo yum install git\n"
                        "• Arch Linux: sudo pacman -S git\n"
                        "• openSUSE: sudo zypper install git\n\n"
                        "After installation, restart Ogresync to continue setup."
                    )
        return None


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
    config_data = _config_data
    
    def _test_thread():
        safe_update_log("Re-testing SSH connection to GitHub...", 35)
        ensure_github_known_host()  # ensures no prompt for 'yes/no'

        if test_ssh_connection_sync():
            safe_update_log("SSH connection successful!", 40)
            
            # Perform the initial commit/push if there are no local commits yet
            if config_data:
                perform_initial_commit_and_push(config_data["VAULT_PATH"])

                # Mark setup as done
                config_data["SETUP_DONE"] = "1"
                if _save_config_func:
                    _save_config_func()

            safe_update_log("Setup complete! You can now close this window or start sync.", 100)
        else:
            safe_update_log("SSH connection still failed. Check your GitHub key or generate a new one.", 40)

    threading.Thread(target=_test_thread, daemon=True).start()


def ensure_github_known_host():
    """
    Adds GitHub's RSA key to known_hosts if not already present.
    This prevents the 'Are you sure you want to continue connecting?' prompt.
    """
    # Check if GitHub is already in known_hosts
    known_hosts_path = os.path.expanduser("~/.ssh/known_hosts")
    if os.path.exists(known_hosts_path):
        with open(known_hosts_path, "r", encoding="utf-8") as f:
            if "github.com" in f.read():
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
                # Remote main exists, try to pull first
                safe_update_log("Remote 'main' branch exists. Pulling before push...", 55)
                pull_out, pull_err, pull_rc = run_command("git pull origin main --allow-unrelated-histories", cwd=vault_path)
                if pull_rc == 0:
                    safe_update_log("Successfully merged with remote. Pushing initial commit...", 60)
                else:
                    safe_update_log(f"Pull failed: {pull_err}. Pushing anyway...", 60)
            else:
                safe_update_log("Remote 'main' branch does not exist. Creating it...", 55)
            
            # Push to main
            push_out, push_err, push_rc = run_command("git push -u origin main", cwd=vault_path)
            if push_rc == 0:
                safe_update_log("Initial commit pushed successfully to GitHub.", 70)
            else:
                safe_update_log(f"Push failed: {push_err}", 70)
        else:
            safe_update_log(f"Error committing files: {err_commit}", 60)
    else:
        # We already have at least one commit in this repo
        safe_update_log("Local repository already has commits. Skipping initial commit step.", 50)


def generate_ssh_key():
    """
    Prompts for the user's email and starts a background thread for SSH key generation.
    """
    ui_elements = _ui_elements
    
    if not ui_elements:
        print("UI elements not available for SSH key generation")
        return
    
    user_email = ui_elements.ask_string_dialog(
        "SSH Key Generation",
        "Enter your email address for the SSH key:",
        icon=getattr(ui_elements.Icons, 'GEAR', None) if hasattr(ui_elements, 'Icons') else None
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
    ui_elements = _ui_elements
    
    # Cross-platform SSH key paths
    ssh_dir = os.path.expanduser(os.path.join("~", ".ssh"))
    SSH_KEY_PATH = os.path.join(ssh_dir, "id_rsa.pub")
    key_path_private = os.path.join(ssh_dir, "id_rsa")
    
    # Ensure .ssh directory exists with proper permissions
    if not os.path.exists(ssh_dir):
        try:
            os.makedirs(ssh_dir, mode=0o700)
            safe_update_log("Created .ssh directory", 20)
        except Exception as e:
            safe_update_log(f"Failed to create .ssh directory: {e}", 25)
            return

    # 1) Generate key if it doesn't exist
    if not os.path.exists(SSH_KEY_PATH):
        safe_update_log("Generating SSH key...", 25)
        
        # Cross-platform SSH key generation command
        if platform.system() == "Windows":
            # On Windows, ensure proper quote handling
            ssh_cmd = f'ssh-keygen -t rsa -b 4096 -C "{user_email}" -f "{key_path_private}" -N ""'
        else:
            # On Unix-like systems, use proper escaping
            ssh_cmd = f"ssh-keygen -t rsa -b 4096 -C '{user_email}' -f '{key_path_private}' -N ''"
        
        out, err, rc = run_command(ssh_cmd)
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
        if ui_elements:
            ui_elements.show_info_message(
                "Manual SSH Key Copy Required",
                "Automatic copying of your SSH key failed.\n\n"
                "Please open a terminal and run:\n\n"
                "   cat ~/.ssh/id_rsa.pub\n\n"
                "Then copy the output manually and add it to your GitHub account."
            )

    # 4) Show final info dialog and open GitHub's SSH keys page
    def show_dialog_then_open_browser():
        if ui_elements:
            ui_elements.show_info_message(
                "SSH Key Generated",
                "Your SSH key has been generated and copied to the clipboard (if successful).\n\n"
                "If automatic copying failed, please manually copy the key as described.\n\n"
                "Click OK to open GitHub's SSH keys page to add your key."
            )
        webbrowser.open("https://github.com/settings/keys")
    
    # We need to get the root window from somewhere - this might need adjustment
    # For now, we'll just call it directly
    try:
        show_dialog_then_open_browser()
    except Exception as e:
        safe_update_log(f"Error showing dialog: {e}", 35)


def copy_ssh_key():
    """
    Copies the SSH key to clipboard and opens GitHub SSH settings.
    """
    ui_elements = _ui_elements
    SSH_KEY_PATH = os.path.expanduser(os.path.join("~", ".ssh", "id_rsa.pub"))
    
    if os.path.exists(SSH_KEY_PATH):
        with open(SSH_KEY_PATH, "r", encoding="utf-8") as key_file:
            ssh_key = key_file.read().strip()
            pyperclip.copy(ssh_key)
        webbrowser.open("https://github.com/settings/keys")
        if ui_elements:
            ui_elements.show_info_message("SSH Key Copied",
                                "Your SSH key has been copied to the clipboard.\n"
                                "Paste it into GitHub.")
    else:
        if ui_elements:
            ui_elements.show_error_message("Error", "No SSH key found. Generate one first.")
