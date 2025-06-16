"""
Ogresync Setup Wizard Module

This module provides a comprehensive 11-step setup wizard for first-time Ogresync configuration.
It handles all aspects of initial setup including:
- Obsidian detection and configuration
- Git installation verification 
- Vault selection and initialization
- SSH key generation and GitHub integration
- Repository conflict resolution using enhanced two-stage system
- Final synchronization and configuration

The wizard is designed for maximum user experience with clear progress indication,
robust error handling, and seamless integration with the enhanced conflict resolution system.
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
import time
from typing import Optional, Tuple, Dict, Any

# Import our modules - handle import gracefully
try:
    import ui_elements
except ImportError:
    ui_elements = None

try:
    import conflict_resolution
except ImportError:
    conflict_resolution = None

# =============================================================================
# SETUP WIZARD STEP DEFINITION
# =============================================================================

class SetupWizardStep:
    """Represents a single step in the setup wizard."""
    def __init__(self, title, description, icon="⚪", status="pending"):
        self.title = title
        self.description = description
        self.icon = icon
        self.status = status  # "pending", "running", "success", "error"
        self.error_message = ""
    
    def set_status(self, status, error_message=""):
        self.status = status
        self.error_message = error_message
    
    def get_status_icon(self):
        if self.status == "success":
            return "✅"
        elif self.status == "error":
            return "❌"
        elif self.status == "running":
            return "🔄"
        else:
            return "⚪"

# =============================================================================
# MAIN SETUP WIZARD CLASS
# =============================================================================

class OgresyncSetupWizard:
    """Main setup wizard class that orchestrates the 11-step setup process."""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.dialog = None
        
        # Define all setup steps
        self.setup_steps = [
            SetupWizardStep("Obsidian Checkup", "Verify Obsidian installation", "🔍"),
            SetupWizardStep("Git Check", "Verify Git installation", "🔧"),
            SetupWizardStep("Choose Vault", "Select Obsidian vault folder", "📁"),
            SetupWizardStep("Initialize Git", "Setup Git repository in vault", "📋"),
            SetupWizardStep("SSH Key Setup", "Generate or verify SSH key", "🔑"),
            SetupWizardStep("Known Hosts", "Add GitHub to known hosts", "🌐"),
            SetupWizardStep("Test SSH", "Test SSH connection to GitHub (manual step)", "🔐"),
            SetupWizardStep("GitHub Repository", "Link GitHub repository", "🔗"),
            SetupWizardStep("Repository Sync", "Handle repository conflicts", "⚖️"),
            SetupWizardStep("Final Sync", "Pull latest changes", "📥"),
            SetupWizardStep("Complete Setup", "Finalize configuration", "🎉")
        ]
        
        # State management
        self.wizard_state = {
            "current_step": 0,
            "steps": self.setup_steps,
            "config_data": {},
            "vault_path": "",
            "obsidian_path": "",
            "github_url": "",
            "setup_complete": False
        }
        
        # UI components
        self.step_widgets = []
        self.status_label = None
        self.button_container = None
    
    def run_wizard(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Runs the setup wizard and returns completion status and final state.
        
        Returns:
            Tuple[bool, Dict]: (setup_complete, wizard_state)
        """
        try:
            self._create_wizard_dialog()
            self._initialize_ui()
            
            # Start the wizard
            self.dialog.after(1000, self._execute_current_step)
            self.dialog.mainloop()
            
            return self.wizard_state["setup_complete"], self.wizard_state
            
        except Exception as e:
            self._show_error("Setup Wizard Error", f"An error occurred during setup: {str(e)}")
            return False, self.wizard_state
    
    def _create_wizard_dialog(self):
        """Creates the main wizard dialog window."""
        if self.parent:
            self.dialog = tk.Toplevel(self.parent)
        else:
            self.dialog = tk.Tk()
        
        self.dialog.title("Ogresync Setup Wizard")
        self.dialog.configure(bg=ui_elements.Colors.BG_PRIMARY if ui_elements else "#FAFBFC")
        self.dialog.resizable(False, False)
        self.dialog.grab_set()
        
        # Center and size the dialog
        width, height = 900, 700
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # Initialize fonts and styles if ui_elements is available
        if ui_elements:
            try:
                ui_elements.init_font_config()
                ui_elements.setup_premium_styles()
            except Exception:
                pass
    
    def _initialize_ui(self):
        """Initializes the wizard user interface."""
        # Main container
        main_frame = tk.Frame(self.dialog, bg=ui_elements.Colors.BG_PRIMARY if ui_elements else "#FAFBFC")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header
        self._create_header(main_frame)
        
        # Content area with card styling
        content_card = self._create_content_card(main_frame)
        
        # Steps display
        self._create_steps_display(content_card)
        
        # Control buttons area
        self._create_control_area(content_card)
    
    def _create_header(self, parent):
        """Creates the wizard header."""
        header_frame = tk.Frame(parent, bg=ui_elements.Colors.BG_PRIMARY if ui_elements else "#FAFBFC")
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = tk.Label(
            header_frame,
            text="🚀 Ogresync Setup Wizard",
            font=("Arial", 18, "bold"),
            bg=ui_elements.Colors.BG_PRIMARY if ui_elements else "#FAFBFC",
            fg=ui_elements.Colors.TEXT_PRIMARY if ui_elements else "#1E293B"
        )
        title_label.pack()
        
        subtitle_label = tk.Label(
            header_frame,
            text="Setting up your Obsidian vault synchronization with GitHub",
            font=("Arial", 12, "normal"),
            bg=ui_elements.Colors.BG_PRIMARY if ui_elements else "#FAFBFC",
            fg=ui_elements.Colors.TEXT_SECONDARY if ui_elements else "#475569"
        )
        subtitle_label.pack(pady=(8, 0))
    
    def _create_content_card(self, parent):
        """Creates the main content card."""
        if ui_elements and hasattr(ui_elements, 'PremiumCard'):
            return ui_elements.PremiumCard.create(parent, padding=20)
        else:
            # Fallback card
            card = tk.Frame(parent, bg="#FFFFFF", relief=tk.RAISED, borderwidth=1)
            card.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
            return card
    
    def _create_steps_display(self, parent):
        """Creates the steps display area."""
        steps_frame = tk.Frame(parent, bg="#FFFFFF")
        steps_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Create two-column layout for steps
        left_column = tk.Frame(steps_frame, bg="#FFFFFF")
        left_column.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        right_column = tk.Frame(steps_frame, bg="#FFFFFF")
        right_column.pack(side="right", fill="both", expand=True, padx=(10, 0))
        
        # Create step widgets in two columns
        total_steps = len(self.setup_steps)
        mid_point = 6  # First 6 steps in left column
        
        for i, step in enumerate(self.setup_steps):
            parent_frame = left_column if i < mid_point else right_column
            widget = self._create_step_widget(step, i, parent_frame)
            self.step_widgets.append(widget)
        
        # Add control area to right column
        self._create_button_spacer(right_column)
    
    def _create_step_widget(self, step, index, parent_frame):
        """Creates a widget for displaying a single step."""
        step_container = tk.Frame(parent_frame, bg="#FFFFFF")
        step_container.pack(fill=tk.X, pady=4, padx=10)
        
        # Step frame with border
        step_frame = tk.Frame(
            step_container,
            bg="#FFFFFF",
            relief=tk.SOLID,
            borderwidth=1
        )
        step_frame.pack(fill=tk.X, ipady=8, ipadx=12)
        
        # Left side - status icon
        icon_label = tk.Label(
            step_frame,
            text=step.get_status_icon(),
            font=("Arial", 14),
            bg="#FFFFFF",
            fg="#1E293B",
            width=3
        )
        icon_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Middle - step info
        info_frame = tk.Frame(step_frame, bg="#FFFFFF")
        info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        title_label = tk.Label(
            info_frame,
            text=f"{index + 1}. {step.title}",
            font=("Arial", 11, "bold"),
            bg="#FFFFFF",
            fg="#1E293B",
            anchor="w"
        )
        title_label.pack(fill=tk.X)
        
        desc_label = tk.Label(
            info_frame,
            text=step.description,
            font=("Arial", 9, "normal"),
            bg="#FFFFFF",
            fg="#475569",
            anchor="w",
            wraplength=280
        )
        desc_label.pack(fill=tk.X)
        
        # Error message (initially hidden)
        error_label = tk.Label(
            info_frame,
            text="",
            font=("Arial", 9, "normal"),
            bg="#FFFFFF",
            fg="#EF4444",
            anchor="w",
            wraplength=280
        )
        error_label.pack(fill=tk.X)
        error_label.pack_forget()  # Hide initially
        
        return {
            "container": step_container,
            "frame": step_frame,
            "icon": icon_label,
            "title": title_label,
            "description": desc_label,
            "error": error_label
        }
    
    def _create_button_spacer(self, parent):
        """Creates the button control area."""
        button_spacer_frame = tk.Frame(
            parent, 
            bg="#FFFFFF",
            relief=tk.SOLID,
            borderwidth=1
        )
        button_spacer_frame.pack(fill=tk.X, pady=20, padx=10)
        
        # Header for button area
        button_header = tk.Label(
            button_spacer_frame,
            text="🎯 Setup Actions",
            font=("Arial", 12, "bold"),
            bg="#FFFFFF",
            fg="#1E293B"
        )
        button_header.pack(anchor=tk.W, padx=12, pady=(8, 0))
        
        # Separator line
        separator = tk.Frame(button_spacer_frame, bg="#E2E8F0", height=1)
        separator.pack(fill=tk.X, pady=(8, 0), padx=12)
        
        # Status message
        self.status_label = tk.Label(
            button_spacer_frame,
            text="Ready to start setup",
            font=("Arial", 10, "normal"),
            bg="#FFFFFF",
            fg="#475569"
        )
        self.status_label.pack(anchor=tk.W, padx=12, pady=(8, 4))
        
        # Button container
        self.button_container = tk.Frame(button_spacer_frame, bg="#FFFFFF", height=80)
        self.button_container.pack(fill=tk.X, padx=12, pady=(0, 12))
        self.button_container.pack_propagate(False)
    
    def _create_control_area(self, parent):
        """Creates the control area - this is now handled in _create_button_spacer."""
        pass
    
    def _update_step_display(self):
        """Updates the visual display of all steps."""
        for i, (step, widget) in enumerate(zip(self.setup_steps, self.step_widgets)):
            # Update icon
            widget["icon"].config(text=step.get_status_icon())
            
            # Update frame styling based on current step
            if i == self.wizard_state["current_step"]:
                widget["frame"].config(
                    bg="#E0E7FF",
                    highlightbackground="#6366F1",
                    highlightcolor="#6366F1",
                    highlightthickness=2
                )
                widget["icon"].config(bg="#E0E7FF")
                widget["title"].config(bg="#E0E7FF")
                widget["description"].config(bg="#E0E7FF")
                widget["error"].config(bg="#E0E7FF")
            else:
                widget["frame"].config(
                    bg="#FFFFFF",
                    highlightthickness=1
                )
                widget["icon"].config(bg="#FFFFFF")
                widget["title"].config(bg="#FFFFFF")
                widget["description"].config(bg="#FFFFFF")
                widget["error"].config(bg="#FFFFFF")
            
            # Show/hide error message
            if step.status == "error" and step.error_message:
                widget["error"].config(text=step.error_message)
                widget["error"].pack(fill=tk.X)
            else:
                widget["error"].pack_forget()
    
    def _set_status_message(self, message, color="#475569"):
        """Sets the status message."""
        if self.status_label:
            self.status_label.config(text=message, fg=color)
    
    def _show_step_buttons(self):
        """Shows appropriate buttons for the current step."""
        # Clear existing buttons
        for widget in self.button_container.winfo_children():
            widget.destroy()
        
        current_step = self.wizard_state["current_step"]
        
        if current_step < len(self.setup_steps):
            step = self.setup_steps[current_step]
            
            # Execute button
            exec_btn = tk.Button(
                self.button_container,
                text=f"▶ Execute: {step.title}",
                command=self._execute_current_step,
                font=("Arial", 10, "bold"),
                bg="#6366F1",
                fg="#FFFFFF",
                relief=tk.FLAT,
                cursor="hand2",
                padx=16,
                pady=8
            )
            exec_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
            
        else:
            # Setup is complete - show Complete Setup button
            complete_btn = tk.Button(
                self.button_container,
                text="🎉 Complete Setup",
                command=self._complete_setup,
                font=("Arial", 10, "bold"),
                bg="#10B981",
                fg="#FFFFFF",
                relief=tk.FLAT,
                cursor="hand2",
                padx=16,
                pady=8
            )
            complete_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        
        # Cancel button
        cancel_btn = tk.Button(
            self.button_container,
            text="Cancel Setup",
            command=self._cancel_setup,
            font=("Arial", 10, "normal"),
            bg="#EF4444",
            fg="#FFFFFF",
            relief=tk.FLAT,
            cursor="hand2",
            padx=16,
            pady=8
        )
        cancel_btn.pack(side=tk.RIGHT)
    
    def _update_status(self, message):
        """Update the status label with a message."""
        if self.status_label:
            self.status_label.config(text=message)
        if self.dialog:
            self.dialog.update_idletasks()
    
    def _update_step_display(self):
        """Update the visual display of all steps."""
        for i, (step, widget) in enumerate(zip(self.setup_steps, self.step_widgets)):
            if widget and isinstance(widget, dict):
                # Update the step icon based on status
                icon_label = widget.get("icon")
                if icon_label:
                    icon_label.config(text=step.get_status_icon())
                    
                    # Update colors based on status
                    if step.status == "running":
                        icon_label.config(fg="#F59E0B")  # Orange for running
                    elif step.status == "success":
                        icon_label.config(fg="#10B981")  # Green for success
                    elif step.status == "error":
                        icon_label.config(fg="#EF4444")  # Red for error
                    else:
                        icon_label.config(fg="#6B7280")  # Gray for pending
        
        if self.dialog:
            self.dialog.update_idletasks()
    
    def _execute_current_step(self):
        """Executes the current step."""
        current_index = self.wizard_state["current_step"]
        
        if current_index >= len(self.setup_steps):
            # Setup complete - show completion
            self._complete_setup()
            return
        
        step = self.setup_steps[current_index]
        step.set_status("running")
        self._update_step_display()
        
        # Map step functions
        step_functions = {
            0: self._step_obsidian_checkup,
            1: self._step_git_check,
            2: self._step_choose_vault,
            3: self._step_initialize_git,
            4: self._step_ssh_key_setup,
            5: self._step_known_hosts,
            6: self._step_test_ssh,
            7: self._step_github_repository,
            8: self._step_repository_sync,
            9: self._step_final_sync,
            10: self._step_complete_setup
        }
        
        try:
            step_function = step_functions.get(current_index)
            if step_function:
                success, error_message = step_function()
                if success:
                    step.set_status("success")
                    self._set_status_message(f"✅ {step.title} completed successfully", "#10B981")
                    self.wizard_state["current_step"] += 1
                    self._update_step_display()
                    self._show_step_buttons()
                    
                    # Check if this was the last step
                    if self.wizard_state["current_step"] >= len(self.setup_steps):
                        self._set_status_message("🎉 All steps completed! Ready to finish setup.", "#10B981")
                    else:
                        # Auto-advance to next step if not the last one
                        self.dialog.after(1500, self._execute_current_step)
                else:
                    step.set_status("error", error_message)
                    self._set_status_message(f"❌ {step.title} failed: {error_message}", "#EF4444")
                    self._update_step_display()
            else:
                step.set_status("error", "Step function not implemented")
                self._set_status_message(f"❌ Step function not implemented", "#EF4444")
                self._update_step_display()
        except Exception as e:
            step.set_status("error", str(e))
            self._set_status_message(f"❌ Error: {str(e)}", "#EF4444")
            self._update_step_display()
    
    def _skip_current_step(self):
        """Skips the current step (for manual steps)."""
        current_index = self.wizard_state["current_step"]
        step = self.setup_steps[current_index]
        step.set_status("success")
        self._set_status_message(f"⏭ {step.title} skipped (manual completion)", "#F59E0B")
        self.wizard_state["current_step"] += 1
        self._update_step_display()
        self._show_step_buttons()
        
        # Auto-advance to next step
        if self.wizard_state["current_step"] < len(self.setup_steps):
            self.dialog.after(1500, self._execute_current_step)
        else:
            self._set_status_message("🎉 Setup completed!", "#10B981")
    
    def _cancel_setup(self):
        """Cancels the setup process."""
        if ui_elements:
            result = ui_elements.ask_premium_yes_no(
                "Cancel Setup",
                "Are you sure you want to cancel the setup process?\n\nAny progress will be lost.",
                self.dialog
            )
        else:
            result = messagebox.askyesno(
                "Cancel Setup",
                "Are you sure you want to cancel the setup process?\n\nAny progress will be lost."
            )
        
        if result:
            self.wizard_state["setup_complete"] = False
            self.dialog.destroy()
    
    def _complete_setup(self):
        """Completes the setup process."""
        self.wizard_state["setup_complete"] = True
        
        if ui_elements:
            ui_elements.show_premium_info(
                "Setup Complete!",
                "🎉 Congratulations! Ogresync setup is now complete.\n\n"
                "Your Obsidian vault is now synchronized with GitHub.\n"
                "You can now use Ogresync to keep your notes in sync.",
                self.dialog
            )
        else:
            messagebox.showinfo(
                "Setup Complete!",
                "🎉 Congratulations! Ogresync setup is now complete.\n\n"
                "Your Obsidian vault is now synchronized with GitHub.\n"
                "You can now use Ogresync to keep your notes in sync."
            )
        
        self.dialog.destroy()
    
    # =============================================================================
    # STEP IMPLEMENTATION FUNCTIONS
    # =============================================================================
    
    def _step_obsidian_checkup(self):
        """Step 1: Verify Obsidian installation."""
        try:
            import Ogresync
            obsidian_path = Ogresync.find_obsidian_path()
            if obsidian_path:
                self.wizard_state["obsidian_path"] = obsidian_path
                Ogresync.config_data["OBSIDIAN_PATH"] = obsidian_path
                Ogresync.save_config()
                return True, f"Found Obsidian at: {obsidian_path}"
            else:
                return False, "Obsidian not found. Please install Obsidian first."
        except Exception as e:
            return False, f"Error checking Obsidian: {str(e)}"
    
    def _step_git_check(self):
        """Step 2: Verify Git installation."""
        try:
            import Ogresync
            if Ogresync.is_git_installed():
                return True, "Git is installed and available"
            else:
                return False, "Git is not installed. Please install Git first."
        except Exception as e:
            return False, f"Error checking Git: {str(e)}"
    
    def _step_choose_vault(self):
        """Step 3: Select Obsidian vault folder."""
        try:
            import Ogresync
            vault_path = Ogresync.select_vault_path()
            if vault_path:
                self.wizard_state["vault_path"] = vault_path
                Ogresync.config_data["VAULT_PATH"] = vault_path
                Ogresync.save_config()
                return True, f"Selected vault: {vault_path}"
            else:
                return False, "No vault directory selected."
        except Exception as e:
            return False, f"Error selecting vault: {str(e)}"
    
    def _step_initialize_git(self):
        """Step 4: Initialize Git repository in vault."""
        try:
            import Ogresync
            vault_path = self.wizard_state.get("vault_path")
            if not vault_path:
                return False, "Vault path not set."
            
            Ogresync.initialize_git_repo(vault_path)
            return True, "Git repository initialized"
        except Exception as e:
            return False, f"Error initializing Git: {str(e)}"
    
    def _step_ssh_key_setup(self):
        """Step 5: Generate or verify SSH key."""
        try:
            import Ogresync
            import tkinter.simpledialog as simpledialog
            import subprocess
            import time
            
            # Check if SSH key exists
            ssh_key_path = os.path.expanduser("~/.ssh/id_rsa.pub")
            if os.path.exists(ssh_key_path):
                return True, "SSH key already exists"
            else:
                # Generate SSH key
                email = None
                if ui_elements and hasattr(ui_elements, 'ask_premium_string'):
                    email = ui_elements.ask_premium_string(
                        "SSH Key Generation",
                        "Enter your email address for SSH key generation:",
                        parent=self.dialog,
                        icon=ui_elements.Icons.KEY if hasattr(ui_elements, 'Icons') else None
                    )
                else:
                    email = simpledialog.askstring(
                        "SSH Key Generation",
                        "Enter your email address for SSH key generation:",
                        parent=self.dialog
                    )
                
                if email and email.strip():
                    # Update status to show we're generating the key
                    self._update_status("Generating SSH key... Please wait.")
                    
                    # Use synchronous SSH key generation for better reliability
                    try:
                        # Create .ssh directory if it doesn't exist
                        ssh_dir = os.path.expanduser("~/.ssh")
                        os.makedirs(ssh_dir, mode=0o700, exist_ok=True)
                        
                        # Generate SSH key synchronously
                        ssh_key_base = os.path.expanduser("~/.ssh/id_rsa")
                        result = subprocess.run([
                            'ssh-keygen', '-t', 'rsa', '-b', '4096', 
                            '-C', email.strip(), 
                            '-f', ssh_key_base,
                            '-N', ''  # No passphrase
                        ], capture_output=True, text=True, timeout=30)
                        
                        if result.returncode == 0:
                            # Verify the key was created
                            if os.path.exists(ssh_key_path):
                                return True, "SSH key generated successfully"
                            else:
                                return False, "SSH key generation completed but file not found"
                        else:
                            # Fallback to async method if direct generation fails
                            self._update_status("Trying alternative SSH key generation...")
                            Ogresync.generate_ssh_key_async(email.strip())
                            
                            # Wait longer and check multiple times
                            for i in range(10):  # Wait up to 10 seconds
                                time.sleep(1)
                                if os.path.exists(ssh_key_path):
                                    return True, "SSH key generated successfully"
                                self._update_status(f"Generating SSH key... ({i+1}/10)")
                            
                            return False, "SSH key generation failed. Please try again."
                            
                    except subprocess.TimeoutExpired:
                        return False, "SSH key generation timed out"
                    except FileNotFoundError:
                        return False, "ssh-keygen command not found. Please install OpenSSH."
                    except Exception as gen_error:
                        return False, f"SSH key generation failed: {str(gen_error)}"
                else:
                    return False, "Email required for SSH key generation"
        except Exception as e:
            return False, f"Error with SSH key setup: {str(e)}"
    
    def _step_known_hosts(self):
        """Step 6: Add GitHub to known hosts."""
        try:
            import Ogresync
            Ogresync.ensure_github_known_host()
            return True, "GitHub added to known hosts"
        except Exception as e:
            return False, f"Error adding GitHub to known hosts: {str(e)}"
    
    def _step_test_ssh(self):
        """Step 7: Test SSH connection with better manual guidance."""
        try:
            import Ogresync
            
            # First try automatic SSH test
            if Ogresync.test_ssh_connection_sync():
                return True, "SSH connection successful"
            else:
                # SSH test failed - show enhanced manual setup dialog
                self._show_enhanced_manual_ssh_dialog()
                
                # Ask user if they want to skip this step after manual setup
                if ui_elements:
                    user_choice = ui_elements.ask_premium_yes_no(
                        "SSH Setup",
                        "SSH connection failed. Have you manually added your SSH key to GitHub?\n\n"
                        "If yes, click 'Yes' to continue setup.\n"
                        "If no, click 'No' to try again.",
                        self.dialog
                    )
                else:
                    import tkinter.messagebox as messagebox
                    user_choice = messagebox.askyesno(
                        "SSH Setup",
                        "SSH connection failed. Have you manually added your SSH key to GitHub?\n\n"
                        "If yes, click 'Yes' to continue setup.\n"
                        "If no, click 'No' to try again."
                    )
                
                if user_choice:
                    return True, "SSH setup completed manually"
                else:
                    return False, "SSH connection failed - please add SSH key to GitHub and try again"
        except Exception as e:
            return False, f"Error testing SSH: {str(e)}"
    
    def _show_enhanced_manual_ssh_dialog(self):
        """Show enhanced manual SSH setup dialog with clear instructions and SSH key display."""
        try:
            # Read the SSH key
            ssh_key_path = os.path.expanduser("~/.ssh/id_rsa.pub")
            ssh_key_content = ""
            
            if os.path.exists(ssh_key_path):
                with open(ssh_key_path, 'r') as f:
                    ssh_key_content = f.read().strip()
            
            if ui_elements and hasattr(ui_elements, 'show_ssh_key_success_dialog'):
                # Use the enhanced SSH dialog from ui_elements (now improved)
                ui_elements.show_ssh_key_success_dialog(ssh_key_content, self.dialog)
            else:
                # Fallback dialog (also improved)
                self._show_fallback_manual_ssh_dialog(ssh_key_content)
                
        except Exception as e:
            print(f"Error showing manual SSH dialog: {e}")
            # Show simple fallback
            if ui_elements:
                ui_elements.show_premium_info(
                    "Manual SSH Setup Required",
                    "SSH connection failed. Please manually add your SSH key to GitHub:\n\n"
                    "1. Copy your SSH key from ~/.ssh/id_rsa.pub\n"
                    "2. Go to GitHub.com → Settings → SSH and GPG keys\n"
                    "3. Click 'New SSH key' and paste your key\n"
                    "4. Return to Ogresync and click 'Execute: Test SSH' again",
                    self.dialog
                )
    
    def _show_fallback_manual_ssh_dialog(self, ssh_key_content):
        """Show fallback manual SSH dialog."""
        dialog = tk.Toplevel(self.dialog)
        dialog.title("Manual SSH Setup Required")
        dialog.transient(self.dialog)
        dialog.grab_set()
        dialog.geometry("800x750")  # Increased size to accommodate all elements and buttons
        dialog.configure(bg="#FAFBFC")
        dialog.resizable(True, True)  # Allow resizing
        
        # Main frame
        main_frame = tk.Frame(dialog, bg="#FAFBFC")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = tk.Label(
            main_frame,
            text="🔑 Manual SSH Setup Required",
            font=("Arial", 16, "bold"),
            bg="#FAFBFC",
            fg="#1E293B"
        )
        title_label.pack(pady=(0, 20))
        
        # Instructions
        instructions = (
            "SSH connection to GitHub failed. Please follow these steps:\n\n"
            "1. Copy your SSH key below (click 'Copy SSH Key')\n"
            "2. Go to GitHub.com → Settings → SSH and GPG keys\n"
            "3. Click 'New SSH key'\n"
            "4. Paste your key and give it a title (e.g., 'Ogresync Key')\n"
            "5. Click 'Add SSH key'\n"
            "6. Return to Ogresync and click 'Execute: Test SSH' to continue\n\n"
            "After adding the key to GitHub, the SSH test should pass."
        )
        
        instr_label = tk.Label(
            main_frame,
            text=instructions,
            font=("Arial", 11),
            bg="#FAFBFC",
            fg="#475569",
            justify=tk.LEFT,
            wraplength=700
        )
        instr_label.pack(pady=(0, 20))
        
        # SSH Key display
        if ssh_key_content:
            key_frame = tk.LabelFrame(
                main_frame,
                text="Your SSH Public Key",
                font=("Arial", 10, "bold"),
                bg="#FAFBFC",
                fg="#1E293B",
                padx=10,
                pady=10
            )
            key_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
            
            # Create a scrollable text widget for the SSH key
            key_scroll_frame = tk.Frame(key_frame, bg="#F8F9FA")
            key_scroll_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            key_text = tk.Text(
                key_scroll_frame,
                height=8,  # Increased height to show full key
                wrap=tk.WORD,
                font=("Courier", 9),
                bg="#F8F9FA",
                fg="#1E293B",
                relief=tk.FLAT,
                borderwidth=1
            )
            
            # Add scrollbar for the text widget
            scrollbar = tk.Scrollbar(key_scroll_frame, orient=tk.VERTICAL, command=key_text.yview)
            key_text.configure(yscrollcommand=scrollbar.set)
            
            key_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Insert the full SSH key content
            key_text.insert(tk.END, ssh_key_content)
            key_text.config(state=tk.DISABLED)
        
        # Buttons frame with increased spacing
        button_frame = tk.Frame(main_frame, bg="#FAFBFC")
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        def copy_ssh_key():
            try:
                import pyperclip
                pyperclip.copy(ssh_key_content)
                if ui_elements:
                    ui_elements.show_premium_info("Success", "SSH key copied to clipboard!", dialog)
                else:
                    messagebox.showinfo("Success", "SSH key copied to clipboard!")
            except ImportError:
                if ui_elements:
                    ui_elements.show_premium_error("Error", "Could not copy to clipboard. Please copy manually.", dialog)
                else:
                    messagebox.showerror("Error", "Could not copy to clipboard. Please copy manually.")
        
        def open_github():
            import webbrowser
            webbrowser.open("https://github.com/settings/ssh/new")  # Direct link to add SSH key page
        
        # Copy button
        copy_btn = tk.Button(
            button_frame,
            text="📋 Copy SSH Key",
            command=copy_ssh_key,
            font=("Arial", 10, "bold"),
            bg="#6366F1",
            fg="#FFFFFF",
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=12
        )
        copy_btn.pack(side=tk.LEFT, padx=(0, 12))
        
        # GitHub button - direct link to add SSH key page
        github_btn = tk.Button(
            button_frame,
            text="🌐 Add SSH Key to GitHub",
            command=open_github,
            font=("Arial", 10, "bold"),
            bg="#22C55E",
            fg="#FFFFFF",
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=12
        )
        github_btn.pack(side=tk.LEFT, padx=(0, 12))
        
        # Close button
        close_btn = tk.Button(
            button_frame,
            text="Close",
            command=dialog.destroy,
            font=("Arial", 10, "normal"),
            bg="#EF4444",
            fg="#FFFFFF",
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=12
        )
        close_btn.pack(side=tk.RIGHT)
    
    def _step_github_repository(self):
        """Step 8: Configure GitHub repository."""
        try:
            import Ogresync
            vault_path = self.wizard_state.get("vault_path")
            if not vault_path:
                return False, "Vault path not set."
            
            # Check if remote already exists
            existing_remote_cmd = "git remote get-url origin"
            existing_out, existing_err, existing_rc = Ogresync.run_command(existing_remote_cmd, cwd=vault_path)
            
            if existing_rc == 0:
                # Remote exists, ask if user wants to change it
                if ui_elements:
                    change_remote = ui_elements.ask_premium_yes_no(
                        "Existing Repository",
                        f"A repository is already configured:\n{existing_out.strip()}\n\n"
                        "Do you want to change it?",
                        self.dialog
                    )
                else:
                    change_remote = messagebox.askyesno(
                        "Existing Repository",
                        f"A repository is already configured:\n{existing_out.strip()}\n\n"
                        "Do you want to change it?"
                    )
                
                if change_remote:
                    saved_url = Ogresync.config_data.get("GITHUB_REMOTE_URL", "")
                    if ui_elements:
                        new_url = ui_elements.ask_premium_string(
                            "New GitHub Repository",
                            "Enter the new GitHub repository URL (e.g., git@github.com:username/repo.git):",
                            initial_value=saved_url if saved_url else "",
                            parent=self.dialog,
                            icon=ui_elements.Icons.LINK if hasattr(ui_elements, 'Icons') else None
                        )
                    else:
                        new_url = tk.simpledialog.askstring(
                            "New GitHub Repository",
                            "Enter the new GitHub repository URL (e.g., git@github.com:username/repo.git):",
                            initialvalue=saved_url if saved_url else ""
                        )
                    
                    if not new_url or not new_url.strip():
                        return False, "No repository URL provided."
                    
                    new_url = new_url.strip()
                    
                    # Remove existing remote and add new one
                    remove_cmd = "git remote remove origin"
                    remove_out, remove_err, remove_rc = Ogresync.run_command(remove_cmd, cwd=vault_path)
                    
                    if remove_rc != 0:
                        return False, f"Failed to remove existing remote: {remove_err}"
                    
                    # Add new remote
                    add_cmd = f"git remote add origin {new_url}"
                    add_out, add_err, add_rc = Ogresync.run_command(add_cmd, cwd=vault_path)
                    
                    if add_rc == 0:
                        # Update config with new URL
                        Ogresync.config_data["GITHUB_REMOTE_URL"] = new_url
                        Ogresync.save_config()
                        return True, f"Repository updated to: {new_url}"
                    else:
                        return False, f"Failed to configure new remote: {add_err}"
                else:
                    return True, f"Using existing repository: {existing_out.strip()}"
            else:
                # No remote exists - configure one
                if Ogresync.configure_remote_url_for_vault(vault_path):
                    return True, "GitHub repository configured"
                else:
                    return False, "Failed to configure GitHub repository."
        except Exception as e:
            return False, f"Error setting up GitHub repository: {str(e)}"
    
    def _step_repository_sync(self):
        """Step 9: Handle repository conflicts using enhanced two-stage system."""
        try:
            import Ogresync
            vault_path = self.wizard_state.get("vault_path")
            if not vault_path:
                return False, "Vault path not set."
            
            # Update step status to running
            current_step = self.setup_steps[8]  # 0-indexed, step 9
            current_step.set_status("running")
            self._update_step_display()
            
            # Analyze repository state for conflicts
            self._update_status("Analyzing repository for conflicts...")
            analysis = Ogresync.analyze_repository_state(vault_path)
            
            if analysis["conflict_detected"]:
                self._update_status("Repository conflicts detected - launching resolution dialog...")
                
                # Show user-friendly message about conflict resolution
                if ui_elements:
                    info_msg = (
                        "🤝 Repository conflicts detected!\n\n"
                        "Both your local vault and the remote repository contain files. "
                        "Ogresync will now help you resolve these conflicts using our "
                        "enhanced two-stage resolution system.\n\n"
                        "You'll be able to:\n"
                        "• Choose a high-level strategy (Smart Merge, Keep Local, Keep Remote)\n"
                        "• For Smart Merge: resolve conflicts file-by-file with detailed options\n\n"
                        "Click OK to continue to the conflict resolution dialog."
                    )
                    ui_elements.show_premium_info("Conflict Resolution", info_msg, self.dialog)
                
                # Use the enhanced conflict resolution system
                success = Ogresync.handle_initial_repository_conflict(vault_path, analysis, self.dialog)
                
                if success:
                    self._update_status("Repository conflicts resolved successfully!")
                    current_step.set_status("success")
                    return True, "Repository conflicts resolved successfully using enhanced two-stage system"
                else:
                    self._update_status("Failed to resolve repository conflicts")
                    current_step.set_status("error", "Failed to resolve repository conflicts")
                    return False, "Failed to resolve repository conflicts."
            else:
                self._update_status("No repository conflicts detected")
                current_step.set_status("success")
                return True, "No repository conflicts detected - ready to proceed"
                
        except Exception as e:
            current_step = self.setup_steps[8]  # 0-indexed, step 9
            current_step.set_status("error", str(e))
            self._update_step_display()
            return False, f"Error handling repository sync: {str(e)}"
    
    def _step_final_sync(self):
        """Step 10: Final synchronization."""
        try:
            import Ogresync
            vault_path = self.wizard_state.get("vault_path")
            if not vault_path:
                return False, "Vault path not set."
            
            # Perform initial commit and push
            Ogresync.perform_initial_commit_and_push(vault_path)
            return True, "Final synchronization completed"
        except Exception as e:
            return False, f"Error in final sync: {str(e)}"
    
    def _step_complete_setup(self):
        """Step 11: Complete setup."""
        try:
            # Save final configuration
            import Ogresync
            
            print("DEBUG: Starting step_complete_setup")
            
            # The individual values should already be saved by now from previous steps
            # We just need to mark setup as complete
            Ogresync.config_data["SETUP_DONE"] = "1"
            
            print(f"DEBUG: Marking setup as complete in config: {Ogresync.config_data}")
            
            Ogresync.save_config()
            
            print("DEBUG: step_complete_setup completed successfully")
            self.wizard_state["setup_complete"] = True
            return True, "Setup completed successfully"
        except Exception as e:
            print(f"DEBUG: Error in step_complete_setup: {e}")
            return False, f"Error completing setup: {str(e)}"
    
    def _show_error(self, title, message):
        """Shows an error message."""
        if ui_elements:
            ui_elements.show_premium_error(title, message, self.dialog)
        else:
            messagebox.showerror(title, message)

# =============================================================================
# CONVENIENCE FUNCTIONS FOR INTEGRATION
# =============================================================================

def run_setup_wizard(parent=None) -> Tuple[bool, Dict[str, Any]]:
    """
    Convenience function to run the setup wizard.
    
    Args:
        parent: Parent window for the wizard dialog
    
    Returns:
        Tuple[bool, Dict]: (setup_complete, wizard_state)
    """
    wizard = OgresyncSetupWizard(parent)
    return wizard.run_wizard()

def create_progressive_setup_wizard(parent=None):
    """
    Compatibility function for existing code that expects the old interface.
    
    Returns:
        Tuple: (dialog, wizard_state) - For compatibility with existing code
    """
    wizard = OgresyncSetupWizard(parent)
    
    # Create and return the dialog and state for compatibility
    success, state = wizard.run_wizard()
    
    # Return in the format expected by existing code
    return wizard.dialog, state

# =============================================================================
# ERROR RECOVERY AND VALIDATION
# =============================================================================

class SetupError(Exception):
    """Custom exception for setup-related errors."""
    def __init__(self, step_name, message, recoverable=True):
        self.step_name = step_name
        self.message = message
        self.recoverable = recoverable
        super().__init__(f"Setup error in {step_name}: {message}")

def validate_setup_prerequisites():
    """
    Validates that all prerequisites for setup are met.
    
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    try:
        # Check if we can import required modules
        import Ogresync
        
        # Check basic system requirements
        if not sys.platform in ['win32', 'linux', 'darwin']:
            return False, f"Unsupported platform: {sys.platform}"
        
        # Check if we have write permissions for config
        try:
            test_file = "test_write_permissions.tmp"
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
        except Exception:
            return False, "No write permissions in current directory"
        
        return True, "Prerequisites validated"
        
    except ImportError as e:
        return False, f"Missing required module: {e}"
    except Exception as e:
        return False, f"Validation error: {e}"

if __name__ == "__main__":
    """Test the setup wizard when run directly."""
    print("Testing Ogresync Setup Wizard...")
    
    # Validate prerequisites
    valid, message = validate_setup_prerequisites()
    if not valid:
        print(f"Prerequisites check failed: {message}")
        sys.exit(1)
    
    # Run the wizard
    try:
        success, state = run_setup_wizard()
        if success:
            print("✅ Setup completed successfully!")
            print(f"Final state: {state}")
        else:
            print("❌ Setup was cancelled or failed.")
    except Exception as e:
        print(f"❌ Error running setup wizard: {e}")
        sys.exit(1)
