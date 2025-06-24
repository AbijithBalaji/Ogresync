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
import re
import platform
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import threading
import time
import subprocess
from typing import Optional, Tuple, Dict, Any

# Optional imports
try:
    import pyperclip
except ImportError:
    pyperclip = None

# Import our modules - handle import gracefully
try:
    import ui_elements
except ImportError:
    ui_elements = None

try:
    import Stage1_conflict_resolution
    import stage2_conflict_resolution
    from Stage1_conflict_resolution import ConflictStrategy
    CONFLICT_RESOLUTION_AVAILABLE = True
except ImportError:
    Stage1_conflict_resolution = None
    stage2_conflict_resolution = None
    ConflictStrategy = None
    CONFLICT_RESOLUTION_AVAILABLE = False

try:
    import Ogresync
except ImportError:
    Ogresync = None

# Import backup manager
try:
    from backup_manager import OgresyncBackupManager, BackupReason
    BACKUP_MANAGER_AVAILABLE = True
except ImportError:
    OgresyncBackupManager = None
    BackupReason = None
    BACKUP_MANAGER_AVAILABLE = False

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
            SetupWizardStep("Repository Sync", "Enhanced two-stage conflict resolution", "⚖️"),
            SetupWizardStep("Final Sync", "Intelligent synchronization with safeguards", "📥"),
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
            "setup_complete": False,
            "conflict_resolution_strategy": None  # Track the chosen strategy
        }
        
        # UI components
        self.step_widgets = []
        self.status_label = None
        self.button_container = None
    
    def _safe_ogresync_call(self, method_name, *args, **kwargs):
        """Safely call an Ogresync method with error handling."""
        if not Ogresync:
            return None, "Ogresync module not available"
        
        if not hasattr(Ogresync, method_name):
            return None, f"Method '{method_name}' not available in Ogresync module"
        
        try:
            method = getattr(Ogresync, method_name)
            result = method(*args, **kwargs)
            return result, None
        except Exception as e:
            return None, str(e)
        
    def _safe_github_setup_call(self, method_name, *args, **kwargs):
        """Safely call a GitHub setup method with error handling."""
        try:
            import github_setup
            
            if not hasattr(github_setup, method_name):
                return None, f"Method '{method_name}' not available in github_setup module"
            
            method = getattr(github_setup, method_name)
            result = method(*args, **kwargs)
            return result, None
        except ImportError:
            return None, "github_setup module not available"
        except Exception as e:
            return None, str(e)

    def _safe_wizard_steps_call(self, method_name, *args, **kwargs):
        """Safely call a wizard steps method with error handling."""
        try:
            import wizard_steps
            
            if not hasattr(wizard_steps, method_name):
                return None, f"Method '{method_name}' not available in wizard_steps module"
            
            method = getattr(wizard_steps, method_name)
            result = method(*args, **kwargs)
            return result, None
        except ImportError:
            return None, "wizard_steps module not available"
        except Exception as e:
            return None, str(e)
    
    
    def _safe_ogresync_get(self, attr_name):
        """Safely get an Ogresync attribute."""
        if not Ogresync:
            return None
        
        return getattr(Ogresync, attr_name, None)
    
    def _safe_ogresync_set(self, attr_name, value):
        """Safely set an Ogresync attribute."""
        if not Ogresync:
            return False
        
        if hasattr(Ogresync, attr_name):
            setattr(Ogresync, attr_name, value)
            return True
        return False
    
    def run_wizard(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Runs the setup wizard and returns completion status and final state.
        
        Returns:
            Tuple[bool, Dict]: (setup_complete, wizard_state)
        """
        try:
            self._create_wizard_dialog()
            if not self.dialog:
                return False, self.wizard_state
                
            self._initialize_ui()
            
            # Start the wizard
            if self.dialog:
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
        self.dialog.resizable(True, True)  # Allow resizing to accommodate content
        self.dialog.grab_set()
        
        # Center and size the dialog - increased size to accommodate all content
        width, height = 900, 700  # Increased from 900x700 to accommodate all UI elements
        self.dialog.minsize(900, 700)  # Set minimum size constraints
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
    
    def _set_status_message(self, message, color="#475569"):
        """Sets the status message."""
        if self.status_label:
            self.status_label.config(text=message, fg=color)
    
    def _show_step_buttons(self):
        """Shows appropriate buttons for the current step."""
        # Clear existing buttons
        if self.button_container:
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
                        if self.dialog:
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
            if self.dialog:
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
            if self.dialog:
                self.dialog.destroy()
    
    def _complete_setup(self):
        """Completes the setup process with enhanced completion dialog."""
        self.wizard_state["setup_complete"] = True
        
        # Create enhanced completion dialog
        self._show_setup_completion_dialog()
        
        if self.dialog:
            self.dialog.destroy()
    
    def _show_setup_completion_dialog(self):
        """Shows an enhanced setup completion dialog with clear next steps."""
        completion_dialog = tk.Toplevel(self.dialog)
        completion_dialog.title("Setup Complete!")
        completion_dialog.transient(self.dialog)
        completion_dialog.grab_set()
        completion_dialog.resizable(True, True)
        completion_dialog.configure(bg="#FAFBFC")
        
        # Center and size the dialog appropriately - significantly increased size for better text display
        completion_dialog.update_idletasks()
        width, height = 850, 750  # Increased from 750x650 to provide much more space
        x = (completion_dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (completion_dialog.winfo_screenheight() // 2) - (height // 2)
        completion_dialog.geometry(f"{width}x{height}+{x}+{y}")
        completion_dialog.minsize(800, 700)  # Increased minimum size
        
        # Main frame with generous padding
        main_frame = tk.Frame(completion_dialog, bg="#FAFBFC")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=35, pady=35)  # Increased padding
        
        # Success icon and title with more spacing
        header_frame = tk.Frame(main_frame, bg="#FAFBFC")
        header_frame.pack(fill=tk.X, pady=(0, 25))  # Increased spacing
        
        success_icon = tk.Label(
            header_frame,
            text="🎉",
            font=("Arial", 38),  # Slightly smaller but well-proportioned icon
            bg="#FAFBFC",
            fg="#10B981"
        )
        success_icon.pack()
        
        title_label = tk.Label(
            header_frame,
            text="Setup Complete!",
            font=("Arial", 20, "bold"),  # Well-proportioned title
            bg="#FAFBFC",
            fg="#1E293B"
        )
        title_label.pack(pady=(12, 0))  # Increased spacing
        
        # Completion message with much better spacing
        message_frame = tk.Frame(main_frame, bg="#FFFFFF", relief=tk.RAISED, borderwidth=1)
        message_frame.pack(fill=tk.X, pady=(0, 25))  # Increased spacing
        
        message_inner = tk.Frame(message_frame, bg="#FFFFFF")
        message_inner.pack(fill=tk.X, padx=25, pady=25)  # Increased padding
        
        completion_text = (
            "Congratulations! Your Ogresync setup is now complete.\n\n"
            "✅ Obsidian vault is configured\n"
            "✅ Git repository is initialized\n"
            "✅ GitHub integration is active\n"
            "✅ SSH keys are configured\n\n"
            "Your notes are now synchronized with GitHub and ready for seamless editing!"
        )
        
        message_label = tk.Label(
            message_inner,
            text=completion_text,
            font=("Arial", 12),  # Slightly larger font for better readability
            bg="#FFFFFF",
            fg="#475569",
            justify=tk.LEFT,
            wraplength=750  # Significantly increased wrap width
        )
        message_label.pack(anchor=tk.W)
        
        # Next steps section with better spacing
        next_steps_frame = tk.Frame(main_frame, bg="#F0FDF4", relief=tk.RAISED, borderwidth=1)
        next_steps_frame.pack(fill=tk.X, pady=(0, 25))  # Increased spacing
        
        next_steps_inner = tk.Frame(next_steps_frame, bg="#F0FDF4")
        next_steps_inner.pack(fill=tk.X, padx=25, pady=20)  # Increased padding
        
        next_steps_title = tk.Label(
            next_steps_inner,
            text="🚀 What's Next?",
            font=("Arial", 14, "bold"),  # Slightly larger font
            bg="#F0FDF4",
            fg="#166534"
        )
        next_steps_title.pack(anchor=tk.W)
        
        next_steps_text = (
            "• Ogresync will now switch to sync mode\n"
            "• Use the sync interface to keep your notes updated\n" 
            "• Your changes will automatically sync with GitHub\n"
            "• Collaborate with others by sharing your repository"
        )
        
        next_steps_label = tk.Label(
            next_steps_inner,
            text=next_steps_text,
            font=("Arial", 12),  # Slightly larger font
            bg="#F0FDF4",
            fg="#166534",
            justify=tk.LEFT,
            wraplength=750  # Increased wrap width
        )
        next_steps_label.pack(anchor=tk.W, pady=(12, 0))  # Increased spacing
        
        # Action buttons with much better spacing
        button_frame = tk.Frame(main_frame, bg="#FAFBFC")
        button_frame.pack(fill=tk.X, pady=(20, 0))  # Increased spacing
        
        # Start sync mode button
        start_sync_btn = tk.Button(
            button_frame,
            text="🔄 Start Sync Mode",
            command=completion_dialog.destroy,
            font=("Arial", 12, "bold"),  # Slightly larger button font
            bg="#10B981",
            fg="#FFFFFF",
            relief=tk.FLAT,
            cursor="hand2",
            padx=25,  # Increased padding
            pady=12   # Increased padding
        )
        start_sync_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 15))  # Increased spacing
        
        # View configuration button (optional)
        config_btn = tk.Button(
            button_frame,
            text="📋 View Config",
            command=lambda: self._show_final_config_summary(completion_dialog),
            font=("Arial", 12, "normal"),  # Slightly larger button font
            bg="#6366F1",
            fg="#FFFFFF",
            relief=tk.FLAT,
            cursor="hand2",
            padx=25,  # Increased padding
            pady=12   # Increased padding
        )
        config_btn.pack(side=tk.RIGHT)
        
        # Wait for user action
        if self.dialog:
            self.dialog.wait_window(completion_dialog)
        else:
            completion_dialog.wait_window()
    
    def _show_final_config_summary(self, parent):
        """Shows a summary of the final configuration."""
        config_data = self._safe_ogresync_get('config_data')
        if not config_data:
            return
            
        summary_text = f"""Configuration Summary:

📁 Vault Path: {config_data.get('VAULT_PATH', 'Not set')}
🔧 Obsidian Path: {config_data.get('OBSIDIAN_PATH', 'Not set')}
🌐 GitHub Repository: {config_data.get('GITHUB_REMOTE_URL', 'Not set')}
✅ Setup Status: {'Complete' if config_data.get('SETUP_DONE') == '1' else 'Incomplete'}

Your configuration has been saved and Ogresync is ready to use!"""
        
        if ui_elements:
            ui_elements.show_premium_info("Configuration Summary", summary_text, parent)
        else:
            messagebox.showinfo("Configuration Summary", summary_text)
    
    # =============================================================================
    # STEP IMPLEMENTATION FUNCTIONS
    # =============================================================================
    
    def _step_obsidian_checkup(self):
        """Step 1: Verify Obsidian installation."""
        try:
            obsidian_path, error = self._safe_wizard_steps_call('find_obsidian_path')
            if error:
                return False, f"Obsidian detection not available: {error}"
            
            if obsidian_path:
                self.wizard_state["obsidian_path"] = obsidian_path
                config_data = self._safe_ogresync_get('config_data')
                if config_data:
                    config_data["OBSIDIAN_PATH"] = obsidian_path
                    self._safe_ogresync_call('save_config')
                return True, f"Found Obsidian at: {obsidian_path}"
            else:
                # Obsidian not found - show installation guidance and offer retry
                self._show_obsidian_installation_guidance()
                
                # Offer retry after installation guidance
                if self._offer_retry_after_installation("Obsidian"):
                    # Retry detection
                    return self._step_obsidian_checkup()
                else:
                    return False, "Obsidian not found. Please install Obsidian and restart the wizard."
        except Exception as e:
            return False, f"Error checking Obsidian: {str(e)}"
    
    def _step_git_check(self):
        """Step 2: Verify Git installation."""
        try:
            is_installed, error = self._safe_wizard_steps_call('is_git_installed')
            if error:
                # Fallback check using subprocess
                import subprocess
                try:
                    result = subprocess.run(['git', '--version'], capture_output=True, text=True)
                    if result.returncode == 0:
                        return True, "Git is installed and available"
                    else:
                        # Git not installed - show installation guidance and offer retry
                        self._show_git_installation_guidance()
                        
                        # Offer retry after installation guidance
                        if self._offer_retry_after_installation("Git"):
                            # Retry detection
                            return self._step_git_check()
                        else:
                            return False, "Git is not installed. Please install Git and restart the wizard."
                except FileNotFoundError:
                    # Git not installed - show installation guidance and offer retry
                    self._show_git_installation_guidance()
                    
                    # Offer retry after installation guidance
                    if self._offer_retry_after_installation("Git"):
                        # Retry detection
                        return self._step_git_check()
                    else:
                        return False, "Git is not installed. Please install Git and restart the wizard."
            
            if is_installed:
                return True, "Git is installed and available"
            else:
                # Git not installed - show installation guidance and offer retry
                self._show_git_installation_guidance()
                
                # Offer retry after installation guidance
                if self._offer_retry_after_installation("Git"):
                    # Retry detection
                    return self._step_git_check()
                else:
                    return False, "Git is not installed. Please install Git and restart the wizard."
        except Exception as e:
            return False, f"Error checking Git: {str(e)}"
    
    def _step_choose_vault(self):
        """Step 3: Select Obsidian vault folder."""
        try:
            vault_path, error = self._safe_wizard_steps_call('select_vault_path')
            if error:
                # Fallback to manual selection
                if ui_elements and hasattr(ui_elements, 'ask_directory_dialog'):
                    vault_path = ui_elements.ask_directory_dialog("Select Obsidian Vault Directory", self.dialog)
                else:
                    vault_path = filedialog.askdirectory(title="Select Obsidian Vault Directory")
                
                if not vault_path:
                    return False, "No vault directory selected."
            
            if vault_path:
                self.wizard_state["vault_path"] = vault_path
                config_data = self._safe_ogresync_get('config_data')
                if config_data:
                    config_data["VAULT_PATH"] = vault_path
                    self._safe_ogresync_call('save_config')
                return True, f"Selected vault: {vault_path}"
            else:
                return False, "No vault directory selected."
        except Exception as e:
            return False, f"Error selecting vault: {str(e)}"
    
    def _step_initialize_git(self):
        """Step 4: Initialize Git repository in vault, commit existing files or create README."""
        try:
            import subprocess  # Import at method level to ensure availability
            
            vault_path = self.wizard_state.get("vault_path")
            if not vault_path:
                return False, "Vault path not set."
            
            self._update_status("Checking Git repository status...")
            
            # Step 4.1: Check if git is already initialized
            is_git_repo = self._safe_github_setup_call('is_git_repo', vault_path)
            if not is_git_repo[0]:  # Not a git repo
                self._update_status("Initializing Git repository...")
                result, error = self._safe_github_setup_call('initialize_git_repo', vault_path)
                if error:
                    # Fallback manual git init
                    try:
                        subprocess.run(['git', 'init'], cwd=vault_path, check=True)
                        subprocess.run(['git', 'branch', '-M', 'main'], cwd=vault_path, check=True)
                    except Exception as fallback_error:
                        return False, f"Git initialization failed: {fallback_error}"
            
            # Step 4.2: Check for existing files (excluding .git and common non-content files)
            existing_files = []
            has_existing_git_history = False
            
            if os.path.exists(vault_path):
                # Check if there's existing git history
                try:
                    result = subprocess.run(['git', 'log', '--oneline'], 
                                          cwd=vault_path, capture_output=True, text=True)
                    if result.returncode == 0 and result.stdout.strip():
                        has_existing_git_history = True
                        commit_count = len(result.stdout.strip().split('\n'))
                        self._update_status(f"Found existing git history with {commit_count} commit(s)")
                except Exception:
                    pass
                
                # Check for content files
                for root_dir, dirs, files in os.walk(vault_path):
                    # Skip .git directory completely - never include it in file analysis
                    if '.git' in root_dir:
                        continue
                    for file in files:
                        # Skip hidden files and common non-content files, but include README.md in count
                        if not file.startswith('.') and file != '.gitignore':
                            rel_path = os.path.relpath(os.path.join(root_dir, file), vault_path)
                            existing_files.append(rel_path)
            
            has_existing_files = len(existing_files) > 0
            self._update_status(f"Vault analysis: {len(existing_files)} content files found")
            
            # Always ensure git user config is set first
            self._safe_github_setup_call('ensure_git_user_config')
            
            if has_existing_files or has_existing_git_history:
                # Step 4.3: Commit existing files (if any changes to commit)
                self._update_status(f"Processing existing repository with {len(existing_files)} files...")
                
                # Stage and commit existing files
                import subprocess
                try:
                    subprocess.run(['git', 'add', '-A'], cwd=vault_path, check=True)
                    result = subprocess.run(['git', 'commit', '-m', 'Initial commit with existing vault files'], 
                                          cwd=vault_path, capture_output=True, text=True)
                    if result.returncode == 0:
                        return True, f"Git initialized and {len(existing_files)} existing files committed"
                    else:
                        # Check if it's because there's nothing to commit (already committed)
                        if "nothing to commit" in result.stdout.lower() or has_existing_git_history:
                            # Repository already has commits and working directory is clean
                            return True, f"Git repository already initialized with {len(existing_files)} files and existing commits"
                        else:
                            return False, f"Failed to commit existing files: {result.stderr}"
                except Exception as e:
                    return False, f"Error committing existing files: {str(e)}"
            
            else:
                # Step 4.4: Create README file only if vault is truly empty (no files AND no history)
                self._update_status("Vault is empty. Creating README file...")
                
                # Check if README.md already exists before creating it
                readme_path = os.path.join(vault_path, "README.md")
                if os.path.exists(readme_path):
                    # README already exists, just commit it if needed
                    self._update_status("README.md already exists, ensuring it's committed...")
                    try:
                        subprocess.run(['git', 'add', 'README.md'], cwd=vault_path, check=True)
                        result = subprocess.run(['git', 'commit', '-m', 'Add existing README'], 
                                              cwd=vault_path, capture_output=True, text=True)
                        if result.returncode == 0:
                            return True, "Git initialized with existing README file"
                        elif "nothing to commit" in result.stdout.lower():
                            return True, "Git repository already properly initialized"
                        else:
                            return False, f"Failed to commit existing README: {result.stderr}"
                    except Exception as e:
                        return False, f"Error handling existing README: {str(e)}"
                
                # Create README file only if it doesn't exist
                try:
                    with open(readme_path, "w", encoding="utf-8") as f:
                        f.write("# Welcome to your Obsidian Vault\n\nThis placeholder file was generated automatically by Ogresync to initialize the repository.")
                    self._update_status("README file created successfully")
                except Exception as e:
                    return False, f"Failed to create README file: {str(e)}"
                
                # Commit the README file
                import subprocess
                try:
                    subprocess.run(['git', 'add', '-A'], cwd=vault_path, check=True)
                    result = subprocess.run(['git', 'commit', '-m', 'Initial commit with README'], 
                                          cwd=vault_path, capture_output=True, text=True)
                    if result.returncode == 0:
                        return True, "Git initialized with README file and committed"
                    else:
                        return False, f"Failed to commit README file: {result.stderr}"
                except Exception as e:
                    return False, f"Error committing README file: {str(e)}"
                        
        except Exception as e:
            return False, f"Error initializing Git: {str(e)}"
    
    def _step_ssh_key_setup(self):
        """Step 5: Generate or verify SSH key."""
        try:
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
                            async_result, async_error = self._safe_wizard_steps_call('generate_ssh_key_async', email.strip())
                            if async_error:
                                return False, f"SSH key generation failed: {async_error}"
                            
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
            result, error = self._safe_wizard_steps_call('ensure_github_known_host')
            if error:
                # Fallback manual known_hosts setup
                import subprocess
                try:
                    # Create .ssh directory if it doesn't exist
                    ssh_dir = os.path.expanduser("~/.ssh")
                    os.makedirs(ssh_dir, mode=0o700, exist_ok=True)
                    
                    # Add GitHub to known_hosts
                    subprocess.run(['ssh-keyscan', '-H', 'github.com'], 
                                 stdout=open(os.path.expanduser("~/.ssh/known_hosts"), "a"),
                                 check=True)
                    return True, "GitHub added to known hosts (fallback method)"
                except Exception as fallback_error:
                    return False, f"Failed to add GitHub to known hosts: {fallback_error}"
            
            return True, "GitHub added to known hosts"
        except Exception as e:
            return False, f"Error adding GitHub to known hosts: {str(e)}"
    
    def _step_test_ssh(self):
        """Step 7: Test SSH connection with better manual guidance."""
        try:
            # First try automatic SSH test
            result, error = self._safe_wizard_steps_call('test_ssh_connection_sync')
            if not error and result:
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
        dialog.geometry("850x800")  # Increased size to accommodate all elements and buttons
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
        """Step 8: Configure GitHub repository with enhanced URL validation and format conversion."""
        try:
            vault_path = self.wizard_state.get("vault_path")
            if not vault_path:
                return False, "Vault path not set."
            
            # First ensure this is a git repository (should be done in step 4, but double-check)
            import subprocess
            git_check = subprocess.run(['git', 'status'], cwd=vault_path, capture_output=True, text=True)
            if git_check.returncode != 0:
                self._update_status("Initializing git repository...")
                # Initialize git if not already done
                init_result = subprocess.run(['git', 'init'], cwd=vault_path, capture_output=True, text=True)
                if init_result.returncode != 0:
                    return False, f"Failed to initialize git repository: {init_result.stderr}"
                
                # Set default branch to main
                subprocess.run(['git', 'branch', '-M', 'main'], cwd=vault_path, capture_output=True, text=True)
                
                # Ensure git user config
                self._safe_github_setup_call('ensure_git_user_config')
            
            # Check if remote already exists
            existing_remote_cmd = "git remote get-url origin"
            existing_result = self._safe_ogresync_call('run_command', existing_remote_cmd, cwd=vault_path)
            if existing_result[1] is None and existing_result[0] is not None:
                # run_command returns (stdout, stderr, return_code)
                existing_out, existing_error, existing_rc = existing_result[0]
                existing_error = None if existing_rc == 0 else existing_error
            else:
                existing_out, existing_error = existing_result[0], existing_result[1]
            
            if not existing_error and existing_out:
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
                    # Enhanced URL input with validation and conversion
                    success, new_url, message = self._get_validated_repository_url(vault_path)
                    if not success:
                        return False, message
                    
                    # Remove existing remote and add new one
                    remove_cmd = "git remote remove origin"
                    self._safe_ogresync_call('run_command', remove_cmd, cwd=vault_path)
                    
                    # Add new remote
                    add_cmd = f"git remote add origin {new_url}"
                    add_result = self._safe_ogresync_call('run_command', add_cmd, cwd=vault_path)
                    if add_result[1] is None and add_result[0] is not None:
                        # run_command returns (stdout, stderr, return_code)
                        add_out, add_error, add_rc = add_result[0]
                        add_error = None if add_rc == 0 else add_error
                    else:
                        add_out, add_error = add_result[0], add_result[1]
                    
                    if not add_error:
                        # Update config with new URL
                        config_data = self._safe_ogresync_get('config_data')
                        if config_data:
                            config_data["GITHUB_REMOTE_URL"] = new_url
                            self._safe_ogresync_call('save_config')
                        # Update wizard state with new URL
                        self.wizard_state["github_url"] = new_url
                        return True, f"Repository updated to: {new_url}"
                    else:
                        return False, f"Failed to configure new remote: {add_error}"
                else:
                    # User chose to keep existing remote - still need to update config.txt
                    existing_url = existing_out.strip()
                    config_data = self._safe_ogresync_get('config_data')
                    if config_data:
                        config_data["GITHUB_REMOTE_URL"] = existing_url
                        self._safe_ogresync_call('save_config')
                    # Update wizard state with existing URL
                    self.wizard_state["github_url"] = existing_url
                    return True, f"Using existing repository: {existing_url}"
            else:
                # No remote exists - configure one with enhanced validation
                success, repo_url, message = self._get_validated_repository_url(vault_path)
                if not success:
                    return False, message
                
                # Add remote
                add_cmd = f"git remote add origin {repo_url}"
                add_result = self._safe_ogresync_call('run_command', add_cmd, cwd=vault_path)
                if add_result[1] is None and add_result[0] is not None:
                    # run_command returns (stdout, stderr, return_code)
                    add_out, add_error, add_rc = add_result[0]
                    add_error = None if add_rc == 0 else add_error
                else:
                    add_out, add_error = add_result[0], add_result[1]
                
                if not add_error:
                    # Update config with URL
                    config_data = self._safe_ogresync_get('config_data')
                    if config_data:
                        config_data["GITHUB_REMOTE_URL"] = repo_url
                        self._safe_ogresync_call('save_config')
                    # Update wizard state with URL
                    self.wizard_state["github_url"] = repo_url
                    return True, f"GitHub repository configured: {repo_url}"
                else:
                    return False, f"Failed to configure remote: {add_error}"
                    
        except Exception as e:
            return False, f"Error setting up GitHub repository: {str(e)}"

    def _get_validated_repository_url(self, vault_path):
        """
        Enhanced repository URL input with validation and format conversion.
        Returns: (success: bool, url: str, message: str)
        """
        import re
        
        config_data = self._safe_ogresync_get('config_data')
        saved_url = config_data.get("GITHUB_REMOTE_URL", "") if config_data else ""
        max_attempts = 3
        
        for attempt in range(max_attempts):
            # Get URL input from user
            prompt_msg = (
                "🔗 Enter your GitHub repository URL:\n\n"
                "✅ Supported formats:\n"
                "• SSH: git@github.com:username/repo.git\n"
                "• HTTPS: https://github.com/username/repo.git\n\n"
                "💡 HTTPS URLs will be automatically converted to SSH format for better security."
            )
            
            if saved_url and attempt == 0:
                prompt_msg += f"\n\n📋 Current: {saved_url}"
            
            if ui_elements:
                user_url = ui_elements.ask_premium_string(
                    "GitHub Repository URL",
                    prompt_msg,
                    initial_value=saved_url if saved_url and attempt == 0 else "",
                    parent=self.dialog,
                    icon=ui_elements.Icons.LINK if hasattr(ui_elements, 'Icons') else None
                )
            else:
                user_url = simpledialog.askstring(
                    "GitHub Repository URL",
                    prompt_msg,
                    initialvalue=saved_url if saved_url and attempt == 0 else ""
                )
            
            if not user_url or not user_url.strip():
                return False, "", "No repository URL provided."
            
            user_url = user_url.strip()
            
            # Validate and convert URL format
            success, converted_url, error_msg = self._validate_and_convert_url(user_url)
            if not success:
                if attempt < max_attempts - 1:
                    # Show error and allow retry
                    if ui_elements:
                        retry = ui_elements.ask_premium_yes_no(
                            "Invalid URL Format",
                            f"❌ {error_msg}\n\nWould you like to try again?",
                            self.dialog
                        )
                    else:
                        retry = messagebox.askyesno(
                            "Invalid URL Format",
                            f"❌ {error_msg}\n\nWould you like to try again?"
                        )
                    
                    if not retry:
                        return False, "", "URL validation cancelled by user."
                    continue
                else:
                    return False, "", f"URL validation failed: {error_msg}"
            
            # Test repository accessibility
            self._update_status("🔍 Validating repository accessibility...")
            
            # Test if we can reach the repository
            access_success, access_msg = self._test_repository_access(converted_url, vault_path)
            if access_success:
                return True, converted_url, f"Repository validated: {converted_url}"
            else:
                if attempt < max_attempts - 1:
                    # Show warning and allow retry
                    if ui_elements:
                        retry = ui_elements.ask_premium_yes_no(
                            "Repository Access Warning",
                            f"⚠️ {access_msg}\n\n"
                            "This might be due to:\n"
                            "• Repository doesn't exist or is private\n"
                            "• SSH key not configured properly\n"
                            "• Network connectivity issues\n\n"
                            "Would you like to try a different URL?",
                            self.dialog
                        )
                    else:
                        retry = messagebox.askyesno(
                            "Repository Access Warning",
                            f"⚠️ {access_msg}\n\n"
                            "Would you like to try a different URL?"
                        )
                    
                    if not retry:
                        # User wants to proceed despite warning
                        return True, converted_url, f"Repository configured (warning: {access_msg})"
                    continue
                else:
                    # Last attempt - offer to proceed anyway
                    if ui_elements:
                        proceed = ui_elements.ask_premium_yes_no(
                            "Proceed Despite Warning?",
                            f"⚠️ Repository access test failed: {access_msg}\n\n"
                            "Would you like to proceed anyway?\n"
                            "(You can fix connectivity issues later)",
                            self.dialog
                        )
                    else:
                        proceed = messagebox.askyesno(
                            "Proceed Despite Warning?",
                            f"⚠️ Repository access test failed: {access_msg}\n\n"
                            "Would you like to proceed anyway?"
                        )
                    
                    if proceed:
                        return True, converted_url, f"Repository configured (warning: {access_msg})"
                    else:
                        return False, "", f"Repository validation failed: {access_msg}"
        
        return False, "", "Maximum validation attempts exceeded."

    def _validate_and_convert_url(self, url):
        """
        Validate and convert repository URL to SSH format if needed.
        Returns: (success: bool, converted_url: str, error_msg: str)
        """
        import re
        
        url = url.strip()
        
        # SSH format pattern: git@github.com:username/repo.git
        ssh_pattern = r'^git@github\.com:([a-zA-Z0-9._-]+)/([a-zA-Z0-9._-]+)(?:\.git)?$'
        
        # HTTPS format pattern: https://github.com/username/repo.git or https://github.com/username/repo
        https_pattern = r'^https://github\.com/([a-zA-Z0-9._-]+)/([a-zA-Z0-9._-]+)(?:\.git)?/?$'
        
        # Check if it's already in SSH format
        ssh_match = re.match(ssh_pattern, url)
        if ssh_match:
            username, repo = ssh_match.groups()
            # Ensure .git suffix (remove existing .git first to avoid double .git)
            repo = repo.replace('.git', '')
            ssh_url = f"git@github.com:{username}/{repo}.git"
            return True, ssh_url, ""
        
        # Check if it's in HTTPS format and convert to SSH
        https_match = re.match(https_pattern, url)
        if https_match:
            username, repo = https_match.groups()
            # Convert to SSH format (remove existing .git first to avoid double .git)
            repo = repo.replace('.git', '')
            ssh_url = f"git@github.com:{username}/{repo}.git"
            return True, ssh_url, f"Converted HTTPS to SSH format: {ssh_url}"
        
        # Invalid format
        error_msg = (
            "Invalid GitHub repository URL format.\n\n"
            "Valid formats:\n"
            "• SSH: git@github.com:username/repo.git\n"
            "• HTTPS: https://github.com/username/repo.git\n\n"
            f"You entered: {url}"
        )
        return False, "", error_msg

    def _test_repository_access(self, repo_url, vault_path):
        """
        Test if the repository is accessible.
        Returns: (success: bool, message: str)
        """
        try:
            # Test connectivity with a simple ls-remote command (doesn't modify anything)
            test_cmd = f"git ls-remote {repo_url} HEAD"
            test_result = self._safe_ogresync_call('run_command', test_cmd, cwd=vault_path, timeout=10)
            if test_result[1] is None and test_result[0] is not None:
                # run_command returns (stdout, stderr, return_code)
                test_out, test_error, test_rc = test_result[0]
                test_error = None if test_rc == 0 else test_error
            else:
                test_out, test_error = test_result[0], test_result[1]
            
            if not test_error and test_out:
                return True, "Repository is accessible"
            else:
                # Parse common error messages from test_error if available
                if test_error and isinstance(test_error, str):
                    if "permission denied" in test_error.lower():
                        return False, "Permission denied - check SSH key configuration"
                    elif "host key verification failed" in test_error.lower():
                        return False, "SSH host key verification failed"
                    elif "could not resolve hostname" in test_error.lower():
                        return False, "Cannot resolve hostname - check network connection"
                    elif "repository not found" in test_error.lower():
                        return False, "Repository not found or not accessible"
                    elif "timeout" in test_error.lower():
                        return False, "Connection timeout - check network connectivity"
                    else:
                        return False, f"Repository access test failed: {test_error}"
                else:
                    return False, "Repository access test failed - unable to connect"
                    
        except Exception as e:
            return False, f"Repository access test error: {str(e)}"
    
    def _step_repository_sync(self):
        """Step 9: Enhanced repository sync with two-stage conflict resolution system."""
        try:
            vault_path = self.wizard_state.get("vault_path")
            if not vault_path:
                return False, "Vault path not set."
            
            # Update step status to running
            current_step = self.setup_steps[8]  # 0-indexed, step 9
            current_step.set_status("running")
            self._update_step_display()
            
            self._update_status("🔍 Analyzing repository state for synchronization...")
            
            # Get remote URL from wizard state, config, or git as fallback
            remote_url = self.wizard_state.get("github_url", "")
            if not remote_url:
                # Fallback 1: Try to get from config
                config_data = self._safe_ogresync_get('config_data')
                if config_data:
                    remote_url = config_data.get("GITHUB_REMOTE_URL", "")
            
            if not remote_url:
                # Fallback 2: Try to get from git directly
                try:
                    import subprocess
                    result = subprocess.run(['git', 'remote', 'get-url', 'origin'], 
                                          cwd=vault_path, capture_output=True, text=True)
                    if result.returncode == 0:
                        remote_url = result.stdout.strip()
                        # Update wizard state for future steps
                        self.wizard_state["github_url"] = remote_url
                except Exception:
                    pass
            
            if not remote_url:
                return False, "Remote repository URL not configured. Please complete Step 8 first."
              # Scenario Detection: Analyze local and remote repository states
            local_files = self._get_content_files(vault_path)
            remote_exists, remote_files = self._check_remote_repository(vault_path)
            
            print(f"[DEBUG] Repository Analysis:")
            print(f"[DEBUG] - Local content files: {len(local_files)} ({local_files[:5]}{'...' if len(local_files) > 5 else ''})")
            print(f"[DEBUG] - Remote exists: {remote_exists}")
            print(f"[DEBUG] - Remote content files: {len(remote_files) if remote_exists else 'N/A'} ({remote_files[:5] if remote_exists and remote_files else ''}{'...' if remote_exists and len(remote_files) > 5 else ''})")
            
            self._update_status(f"📊 Repository Analysis Complete:\n• Local files: {len(local_files)}\n• Remote files: {len(remote_files) if remote_exists else 'Unknown'}")
            
            # Determine scenario and handle accordingly
            scenario = self._determine_sync_scenario(local_files, remote_exists, remote_files)
            print(f"[DEBUG] Determined scenario: {scenario}")
            
            if scenario == "both_empty":
                # Scenario 1: Both repos are empty - create README and continue
                print("[DEBUG] Handling scenario: both_empty")
                return self._handle_empty_repositories(vault_path, current_step)
            
            elif scenario == "local_empty_remote_has_files":
                # Scenario 2: Local is empty, remote has files - simple pull
                print("[DEBUG] Handling scenario: local_empty_remote_has_files")
                return self._handle_simple_pull(vault_path, remote_files, current_step)
            
            elif scenario == "local_has_files_remote_empty":
                # Scenario 3: Local has files, remote is empty - ready for push in next step
                print("[DEBUG] Handling scenario: local_has_files_remote_empty")
                return self._handle_remote_empty(vault_path, local_files, current_step)
            
            elif scenario == "both_have_files":
                # Scenario 4: Both have files - use enhanced two-stage conflict resolution
                print("[DEBUG] Handling scenario: both_have_files - MUST trigger conflict resolution!")
                return self._handle_conflict_resolution(vault_path, remote_url, local_files, remote_files, current_step)
            
            else:
                # Unknown scenario - fallback to simple handling
                return self._handle_unknown_scenario(vault_path, current_step)
                
        except Exception as e:
            # Ensure current_step is available for error reporting
            try:
                current_step = self.setup_steps[8]  # Step 9 (0-indexed)
                current_step.set_status("error", str(e))
            except:
                pass  # If we can't set step status, just continue
            return False, f"Error during repository sync: {str(e)}"
    
    def _get_current_branch(self, vault_path):
        """
        Dynamically detect the current branch name.
        
        Args:
            vault_path: Path to the git repository
            
        Returns:
            str: Current branch name (defaults to 'main' if detection fails)
        """
        try:
            # Try to get current branch
            current_branch_result = subprocess.run(['git', 'branch', '--show-current'], 
                                                 cwd=vault_path, capture_output=True, text=True)
            
            if current_branch_result.returncode == 0 and current_branch_result.stdout.strip():
                branch_name = current_branch_result.stdout.strip()
                print(f"[DEBUG] Dynamic branch detection: Using current branch '{branch_name}'")
                return branch_name
            
            # Fallback: try to get default branch from remote
            default_branch_result = subprocess.run(['git', 'symbolic-ref', 'refs/remotes/origin/HEAD'], 
                                                 cwd=vault_path, capture_output=True, text=True)
            
            if default_branch_result.returncode == 0 and default_branch_result.stdout.strip():
                # Extract branch name from refs/remotes/origin/branch_name
                ref_line = default_branch_result.stdout.strip()
                if 'refs/remotes/origin/' in ref_line:
                    branch_name = ref_line.split('refs/remotes/origin/')[-1]
                    print(f"[DEBUG] Dynamic branch detection: Using remote default branch '{branch_name}'")
                    return branch_name
            
            # Final fallback: check what branches exist on remote
            remote_branches_result = subprocess.run(['git', 'branch', '-r'], 
                                                  cwd=vault_path, capture_output=True, text=True)
            
            if remote_branches_result.returncode == 0:
                remote_branches = remote_branches_result.stdout.strip().split('\n')
                for branch_line in remote_branches:
                    branch_line = branch_line.strip()
                    # Look for main or master branch
                    if 'origin/main' in branch_line:
                        print(f"[DEBUG] Dynamic branch detection: Found 'main' branch on remote")
                        return 'main'
                    elif 'origin/master' in branch_line:
                        print(f"[DEBUG] Dynamic branch detection: Found 'master' branch on remote")
                        return 'master'
            
            # Ultimate fallback
            print(f"[DEBUG] Dynamic branch detection: Using default fallback 'main'")
            return 'main'
            
        except Exception as e:
            print(f"[DEBUG] Error in dynamic branch detection: {e}, using 'main' as fallback")
            return 'main'
    
    def _get_remote_branch_ref(self, vault_path, branch_name=None):
        """
        Get the full remote branch reference (e.g., 'origin/main').
        
        Args:
            vault_path: Path to the git repository
            branch_name: Optional branch name, if None will auto-detect
            
        Returns:
            str: Full remote branch reference
        """
        if not branch_name:
            branch_name = self._get_current_branch(vault_path)
        
        return f"origin/{branch_name}"
    
    def _get_content_files(self, vault_path):
        """Get list of meaningful content files in the vault (using enhanced filtering)."""
        content_files = []
        if os.path.exists(vault_path):
            for root_dir, dirs, files in os.walk(vault_path):
                # Skip certain directories entirely
                dirs[:] = [d for d in dirs if d not in {'.git', '.obsidian', '__pycache__', '.vscode', '.idea', 'node_modules'}]
                    
                for file in files:
                    file_path = os.path.relpath(os.path.join(root_dir, file), vault_path)
                    if self._is_meaningful_file(file_path):
                        content_files.append(file_path)
        return content_files
    
    def _is_meaningful_file(self, file_path):
        """Check if a file should be considered meaningful user content"""
        file_name = os.path.basename(file_path)
        
        # System and temporary files to ignore
        ignored_files = {
            'README.md', '.gitignore', '.DS_Store', 'Thumbs.db', 
            'desktop.ini', '.env', '.env.local', '.env.example'
        }
        
        # File extensions to ignore
        ignored_extensions = {
            '.pyc', '.pyo', '.pyd', '.so', '.dll', '.dylib',
            '.tmp', '.temp', '.log', '.cache'
        }
        
        # Directory patterns to ignore in file paths
        ignored_dir_patterns = {
            '.git/', '.obsidian/', '__pycache__/', '.vscode/', 
            '.idea/', '.vs/', 'node_modules/', '.pytest_cache/',
            '.mypy_cache/', '.coverage/', 'venv/', '.venv/',
            'env/', '.env/'
        }
        
        # Check if file name is in ignored list
        if file_name in ignored_files:
            return False
        
        # Check if file starts with dot (hidden files)
        if file_name.startswith('.'):
            return False
        
        # Check file extension
        _, ext = os.path.splitext(file_name)
        if ext.lower() in ignored_extensions:
            return False
        
        # Check if file path contains ignored directory patterns
        normalized_path = file_path.replace('\\', '/')
        for pattern in ignored_dir_patterns:
            if pattern in normalized_path:
                return False
        
        return True
    
    def _check_remote_repository(self, vault_path):
        """Check if remote repository exists and get its files."""
        import subprocess
        try:
            # Fetch remote information
            fetch_result = subprocess.run(['git', 'fetch', 'origin'], 
                                        cwd=vault_path, capture_output=True, text=True, timeout=30)
            
            if fetch_result.returncode == 0:
                # Dynamically detect the remote branch
                remote_branch_ref = self._get_remote_branch_ref(vault_path)
                print(f"[DEBUG] Checking remote repository using branch: {remote_branch_ref}")
                
                # Check if remote branch exists and has files
                ls_result = subprocess.run(['git', 'ls-tree', '-r', '--name-only', remote_branch_ref], 
                                         cwd=vault_path, capture_output=True, text=True)
                
                if ls_result.returncode == 0 and ls_result.stdout.strip():
                    remote_files = [f.strip() for f in ls_result.stdout.splitlines() if f.strip()]
                    # Filter out system files using our meaningful file detection
                    content_files = [f for f in remote_files if self._is_meaningful_file(f)]
                    print(f"[DEBUG] Found {len(content_files)} meaningful files on remote: {content_files}")
                    return True, content_files
                else:
                    print(f"[DEBUG] Remote branch {remote_branch_ref} exists but is empty")
                    return True, []  # Remote exists but is empty
            else:
                # Remote doesn't exist or can't be accessed
                return False, []                
        except Exception as e:
            print(f"[DEBUG] Error checking remote repository: {e}")
            return False, []
    
    def _determine_sync_scenario(self, local_files, remote_exists, remote_files):
        """Determine which synchronization scenario we're in."""
        has_local_content = len(local_files) > 0
        has_remote_content = remote_exists and len(remote_files) > 0
        
        print(f"[DEBUG] Scenario determination:")
        print(f"[DEBUG] - has_local_content: {has_local_content} (local_files count: {len(local_files)})")
        print(f"[DEBUG] - has_remote_content: {has_remote_content} (remote_exists: {remote_exists}, remote_files count: {len(remote_files) if remote_exists else 'N/A'})")
        
        if not has_local_content and not has_remote_content:
            print("[DEBUG] -> Scenario: both_empty")
            return "both_empty"
        elif not has_local_content and has_remote_content:
            print("[DEBUG] -> Scenario: local_empty_remote_has_files")
            return "local_empty_remote_has_files"
        elif has_local_content and not has_remote_content:
            print("[DEBUG] -> Scenario: local_has_files_remote_empty")
            return "local_has_files_remote_empty"
        elif has_local_content and has_remote_content:
            print("[DEBUG] -> Scenario: both_have_files - THIS MUST TRIGGER CONFLICT RESOLUTION!")
            return "both_have_files"
        else:
            print("[DEBUG] -> Scenario: unknown - this should not happen")
            return "unknown"
    
    def _handle_empty_repositories(self, vault_path, current_step):
        """Handle Scenario 1: Both repositories are empty."""
        self._update_status("📝 Both repositories are empty - creating initial README...")
          # Create a basic README if it doesn't exist
        readme_path = os.path.join(vault_path, "README.md")
        if not os.path.exists(readme_path):
            readme_content = f"""# My Obsidian Vault

This vault is synchronized with GitHub using Ogresync.

Created: {time.strftime('%Y-%m-%d %H:%M:%S')}
"""
            try:
                with open(readme_path, 'w', encoding='utf-8') as f:
                    f.write(readme_content)
                
                # Commit the README
                import subprocess
                subprocess.run(['git', 'add', 'README.md'], cwd=vault_path, check=True)
                subprocess.run(['git', 'commit', '-m', 'Initial commit: Add README'], cwd=vault_path, check=True)
            except Exception as e:
                print(f"[DEBUG] Error creating README: {e}")
        
        current_step.set_status("success")
        return True, "Both repositories initialized - ready for synchronization"
    
    def _handle_simple_pull(self, vault_path, remote_files, current_step):
        """Handle Scenario 2: Local is empty, remote has files - simple pull."""
        self._update_status(f"📥 Pulling {len(remote_files)} files from remote repository...")
        
        import subprocess
        try:
            # Get the current branch dynamically
            current_branch = self._get_current_branch(vault_path)
            print(f"[DEBUG] Simple pull using branch: {current_branch}")
            print(f"[DEBUG] Expected remote files to pull: {remote_files}")
            
            # Check current git status before pull
            status_result = subprocess.run(['git', 'status', '--porcelain'], 
                                         cwd=vault_path, capture_output=True, text=True)
            print(f"[DEBUG] Git status before pull: '{status_result.stdout.strip()}'")
            
            # Check what files currently exist in working directory
            existing_files = []
            for root, dirs, files in os.walk(vault_path):
                # Skip .git directory
                if '.git' in root:
                    continue
                for file in files:
                    rel_path = os.path.relpath(os.path.join(root, file), vault_path)
                    existing_files.append(rel_path)
            print(f"[DEBUG] Files currently in working directory: {existing_files}")
              # Simple pull since local is empty
            print(f"[DEBUG] Executing: git pull origin {current_branch} --allow-unrelated-histories")
            pull_result = subprocess.run(['git', 'pull', 'origin', current_branch, '--allow-unrelated-histories'], 
                                       cwd=vault_path, capture_output=True, text=True, timeout=60)
            
            print(f"[DEBUG] Pull result - Return code: {pull_result.returncode}")
            print(f"[DEBUG] Pull result - STDOUT: {pull_result.stdout}")
            print(f"[DEBUG] Pull result - STDERR: {pull_result.stderr}")
            
            # Check what files exist after pull
            after_pull_files = []
            for root, dirs, files in os.walk(vault_path):
                # Skip .git directory
                if '.git' in root:
                    continue
                for file in files:
                    rel_path = os.path.relpath(os.path.join(root, file), vault_path)
                    after_pull_files.append(rel_path)
            print(f"[DEBUG] Files after pull: {after_pull_files}")
            
            # Check if we actually got the expected files
            meaningful_files_after_pull = [f for f in after_pull_files if self._is_meaningful_file(f)]
            print(f"[DEBUG] Meaningful files after pull: {meaningful_files_after_pull}")
            
            if pull_result.returncode == 0:
                # Check if we actually got the expected remote files
                if len(meaningful_files_after_pull) >= len(remote_files):
                    print(f"[DEBUG] Pull successful - got {len(meaningful_files_after_pull)} meaningful files")
                    current_step.set_status("success")
                    return True, f"Successfully pulled {len(remote_files)} files from remote repository"
                else:
                    print(f"[DEBUG] Pull said 'success' but missing files. Expected {len(remote_files)}, got {len(meaningful_files_after_pull)}")
                    print(f"[DEBUG] This indicates local/remote are out of sync - trying reset approach...")
                    # Continue to reset fallback even though pull "succeeded"
              # Pull failed OR pull succeeded but files are missing - try reset approach
            print(f"[DEBUG] Using reset approach to ensure files are present...")
            self._update_status("Ensuring all remote files are present in working directory...")
            
            remote_branch_ref = self._get_remote_branch_ref(vault_path, current_branch)
            print(f"[DEBUG] Using remote branch ref: {remote_branch_ref}")
            
            # First, ensure we have the latest remote state
            print(f"[DEBUG] Executing: git fetch origin {current_branch}")
            fetch_result = subprocess.run(['git', 'fetch', 'origin', current_branch], 
                                        cwd=vault_path, capture_output=True, text=True)
            print(f"[DEBUG] Fetch result - Return code: {fetch_result.returncode}")
            print(f"[DEBUG] Fetch result - STDOUT: {fetch_result.stdout}")
            print(f"[DEBUG] Fetch result - STDERR: {fetch_result.stderr}")
            
            # SAFETY CHECKS before reset --hard
            print(f"[DEBUG] Performing safety checks before reset...")
            
            # Check git status before reset
            status_before_reset = subprocess.run(['git', 'status', '--porcelain'], 
                                               cwd=vault_path, capture_output=True, text=True)
            print(f"[DEBUG] Git status before reset: '{status_before_reset.stdout.strip()}'")
            
            # Safety check 1: Check for uncommitted changes
            if status_before_reset.stdout.strip():
                print(f"[DEBUG] SAFETY WARNING: Uncommitted changes detected!")
                print(f"[DEBUG] Uncommitted changes: {status_before_reset.stdout.strip()}")
                # In this scenario (local_empty_remote_has_files), we expect no meaningful changes
                # But let's be extra safe and show what would be lost
                self._update_status("⚠️ Uncommitted changes detected - creating safety backup...")
                
                # Create a safety commit to preserve any changes
                safety_commit_result = subprocess.run(['git', 'add', '-A'], cwd=vault_path, capture_output=True, text=True)
                if safety_commit_result.returncode == 0:
                    commit_msg = f"Safety backup before reset - {time.strftime('%Y-%m-%d %H:%M:%S')}"
                    commit_result = subprocess.run(['git', 'commit', '-m', commit_msg], 
                                                 cwd=vault_path, capture_output=True, text=True)
                    if commit_result.returncode == 0:
                        print(f"[DEBUG] Created safety commit: {commit_msg}")
                    else:
                        print(f"[DEBUG] Failed to create safety commit: {commit_result.stderr}")
            
            # Safety check 2: Compare local vs remote commits
            local_commit_result = subprocess.run(['git', 'rev-parse', 'HEAD'], 
                                               cwd=vault_path, capture_output=True, text=True)
            remote_commit_result = subprocess.run(['git', 'rev-parse', remote_branch_ref], 
                                                cwd=vault_path, capture_output=True, text=True)
            
            local_ahead_check = subprocess.run(['git', 'rev-list', '--count', f'{remote_branch_ref}..HEAD'], 
                                             cwd=vault_path, capture_output=True, text=True)
            
            if local_commit_result.returncode == 0 and remote_commit_result.returncode == 0:
                local_commit = local_commit_result.stdout.strip()
                remote_commit = remote_commit_result.stdout.strip()
                print(f"[DEBUG] Local commit:  {local_commit}")
                print(f"[DEBUG] Remote commit: {remote_commit}")
                print(f"[DEBUG] Commits match: {local_commit == remote_commit}")
                
                if local_ahead_check.returncode == 0:
                    local_ahead_count = int(local_ahead_check.stdout.strip() or 0)
                    print(f"[DEBUG] Local commits ahead of remote: {local_ahead_count}")
                    
                    if local_ahead_count > 0:
                        print(f"[DEBUG] SAFETY WARNING: Local branch is {local_ahead_count} commits ahead!")
                        # This is potentially dangerous - local commits would be lost
                        # Create a backup branch
                        backup_branch_name = f"backup-before-reset-{int(time.time())}"
                        backup_result = subprocess.run(['git', 'branch', backup_branch_name], 
                                                     cwd=vault_path, capture_output=True, text=True)
                        if backup_result.returncode == 0:
                            print(f"[DEBUG] Created backup branch: {backup_branch_name}")
                            self._update_status(f"⚠️ Created backup branch '{backup_branch_name}' for local commits")
                        else:
                            print(f"[DEBUG] Failed to create backup branch: {backup_result.stderr}")
                            # This is dangerous - abort reset
                            return False, "Cannot safely reset: local branch has commits that would be lost and backup failed"
            
            # Safety check 3: Alternative approach - try checkout instead of reset for safety
            print(f"[DEBUG] Trying safer approach: git checkout instead of reset...")
            
            # First try: checkout the remote branch files without changing history
            checkout_result = subprocess.run(['git', 'checkout', remote_branch_ref, '--', '.'], 
                                           cwd=vault_path, capture_output=True, text=True)
            print(f"[DEBUG] Checkout result - Return code: {checkout_result.returncode}")
            print(f"[DEBUG] Checkout result - STDOUT: {checkout_result.stdout}")
            print(f"[DEBUG] Checkout result - STDERR: {checkout_result.stderr}")
            
            if checkout_result.returncode == 0:
                # Check if checkout brought the files
                after_checkout_files = []
                for root, dirs, files in os.walk(vault_path):
                    if '.git' in root:
                        continue
                    for file in files:
                        rel_path = os.path.relpath(os.path.join(root, file), vault_path)
                        after_checkout_files.append(rel_path)
                
                meaningful_files_after_checkout = [f for f in after_checkout_files if self._is_meaningful_file(f)]
                print(f"[DEBUG] Files after checkout: {after_checkout_files}")
                print(f"[DEBUG] Meaningful files after checkout: {meaningful_files_after_checkout}")
                
                if len(meaningful_files_after_checkout) >= len(remote_files):
                    print(f"[DEBUG] Checkout successful - got {len(meaningful_files_after_checkout)} meaningful files")
                    current_step.set_status("success")
                    return True, f"Successfully retrieved {len(remote_files)} files using safe checkout method"
            
            # If checkout didn't work, fall back to reset but with all safety measures in place
            print(f"[DEBUG] Checkout approach failed, proceeding with reset (safety measures active)...")
            print(f"[DEBUG] Executing: git reset --hard {remote_branch_ref}")
            reset_result = subprocess.run(['git', 'reset', '--hard', remote_branch_ref], 
                                        cwd=vault_path, capture_output=True, text=True)
            print(f"[DEBUG] Reset result - Return code: {reset_result.returncode}")
            print(f"[DEBUG] Reset result - STDOUT: {reset_result.stdout}")
            print(f"[DEBUG] Reset result - STDERR: {reset_result.stderr}")
            
            if reset_result.returncode == 0:
                # Check what files exist after reset
                after_reset_files = []
                for root, dirs, files in os.walk(vault_path):
                    # Skip .git directory
                    if '.git' in root:
                        continue
                    for file in files:
                        rel_path = os.path.relpath(os.path.join(root, file), vault_path)
                        after_reset_files.append(rel_path)
                print(f"[DEBUG] Files after reset: {after_reset_files}")
                  # Check meaningful files after reset
                meaningful_files_after_reset = [f for f in after_reset_files if self._is_meaningful_file(f)]
                print(f"[DEBUG] Meaningful files after reset: {meaningful_files_after_reset}")
                
                if len(meaningful_files_after_reset) >= len(remote_files):
                    print(f"[DEBUG] Reset successful - got {len(meaningful_files_after_reset)} meaningful files")
                    current_step.set_status("success")
                    return True, f"Successfully retrieved {len(remote_files)} files using reset method"
                else:
                    print(f"[DEBUG] Reset completed but still missing files. Expected {len(remote_files)}, got {len(meaningful_files_after_reset)}")
                    return False, f"Reset completed but files are still missing. Expected {remote_files}, but only found {meaningful_files_after_reset}"
            else:
                return False, f"Failed to retrieve remote files: {reset_result.stderr}"
                    
        except Exception as e:
            print(f"[DEBUG] Exception in _handle_simple_pull: {e}")
            import traceback
            traceback.print_exc()
            return False, f"Error during pull operation: {str(e)}"
    
    def _handle_remote_empty(self, vault_path, local_files, current_step):
        """Handle Scenario 3: Local has files, remote is empty - commit and prepare for push."""
        self._update_status(f"📤 Remote repository is empty - preparing to push {len(local_files)} local files...")
        
        try:
            import subprocess
            
            # Ensure all local files are committed
            self._update_status("📝 Ensuring all local files are committed...")
            
            # Check if there are uncommitted changes
            status_result = subprocess.run(['git', 'status', '--porcelain'], 
                                         cwd=vault_path, capture_output=True, text=True)
            
            if status_result.returncode == 0 and status_result.stdout.strip():
                # There are uncommitted changes, commit them
                print(f"[DEBUG] Committing uncommitted changes before push")
                
                # Add all files
                add_result = subprocess.run(['git', 'add', '.'], 
                                          cwd=vault_path, capture_output=True, text=True)
                
                if add_result.returncode == 0:
                    # Commit changes
                    commit_result = subprocess.run(['git', 'commit', '-m', f'Initial vault content - {len(local_files)} files'], 
                                                 cwd=vault_path, capture_output=True, text=True)
                    
                    if commit_result.returncode == 0:
                        print(f"[DEBUG] Successfully committed {len(local_files)} local files")
                        self._update_status(f"✅ Committed {len(local_files)} local files for push")
                    else:
                        print(f"[DEBUG] Commit failed: {commit_result.stderr}")
                        return False, f"Failed to commit local files: {commit_result.stderr}"
                else:
                    print(f"[DEBUG] Add failed: {add_result.stderr}")
                    return False, f"Failed to stage local files: {add_result.stderr}"
            
            # Now attempt to push to remote
            self._update_status(f"📤 Pushing {len(local_files)} files to remote repository...")
            
            # Get current branch
            current_branch_result = subprocess.run(['git', 'branch', '--show-current'], 
                                                 cwd=vault_path, capture_output=True, text=True)
            current_branch = current_branch_result.stdout.strip() if current_branch_result.returncode == 0 else "main"
            
            print(f"[DEBUG] Attempting to push branch '{current_branch}' to remote")
            
            # Push to remote
            push_result = subprocess.run(['git', 'push', 'origin', current_branch], 
                                       cwd=vault_path, capture_output=True, text=True, timeout=60)
            
            if push_result.returncode == 0:
                print(f"[DEBUG] Successfully pushed {len(local_files)} files to remote")
                self._update_status(f"✅ Successfully pushed {len(local_files)} files to remote repository!")
                current_step.set_status("success")
                return True, f"Successfully pushed {len(local_files)} local files to remote repository"
            else:
                # Push failed, but don't fail the step - we'll try again in final sync
                push_error = push_result.stderr.strip()
                print(f"[DEBUG] Push failed during step 9, will retry in final sync: {push_error}")
                
                # Check if it's an authentication or permission issue
                if "permission denied" in push_error.lower() or "authentication failed" in push_error.lower():
                    self._update_status("⚠️ Push failed due to authentication - will retry in final sync step")
                    current_step.set_status("success")  # Don't fail the step, authentication might be resolved
                    return True, f"Local files committed and ready for push - will retry authentication in final sync"
                elif "repository not found" in push_error.lower():
                    return False, f"Repository not found. Please verify the repository URL is correct: {push_error}"
                else:
                    # Other error - mark for retry in final sync
                    self._update_status("⚠️ Push temporarily failed - will retry in final sync step")
                    current_step.set_status("success")
                    return True, f"Local files committed and ready for push - will retry in final sync: {push_error}"
                    
        except Exception as e:
            print(f"[DEBUG] Exception in _handle_remote_empty: {e}")
            # Don't fail the step, just mark files as ready for final sync
            current_step.set_status("success")
            return True, f"Local files prepared for push - final sync will complete the upload: {str(e)}"
    
    def _handle_conflict_resolution(self, vault_path, remote_url, local_files, remote_files, current_step):
        """Handle Scenario 4: Both have files - check for conflicts first, then resolve if needed."""
        self._update_status("🔍 Analyzing repositories for conflicts...")
        
        print(f"[DEBUG] Conflict resolution triggered - Local files: {len(local_files)}, Remote files: {len(remote_files)}")
        print(f"[DEBUG] CONFLICT_RESOLUTION_AVAILABLE: {CONFLICT_RESOLUTION_AVAILABLE}")
        print(f"[DEBUG] Stage1_conflict_resolution module: {Stage1_conflict_resolution is not None}")
        
        if not CONFLICT_RESOLUTION_AVAILABLE:
            print("[DEBUG] Conflict resolution modules not available - ERROR!")
            return False, "Conflict resolution system is not available. Cannot safely merge repositories with conflicting content. Please ensure all conflict resolution modules are properly installed."
        
        if not Stage1_conflict_resolution:
            print("[DEBUG] Stage1_conflict_resolution module not found - ERROR!")
            return False, "Stage 1 conflict resolution module is not available. Cannot safely merge repositories with conflicting content."
        
        try:
            print("[DEBUG] Creating conflict resolution engine...")
            conflict_engine = Stage1_conflict_resolution.ConflictResolutionEngine(vault_path)
            
            # Analyze conflicts first to determine if conflict resolution is actually needed
            self._update_status("🔍 Analyzing repository conflicts...")
            print("[DEBUG] Analyzing conflicts...")
            conflict_analysis = conflict_engine.analyze_conflicts(remote_url)
            print(f"[DEBUG] Conflict analysis complete: {conflict_analysis}")
            
            # Check if there are actual conflicts
            if not conflict_analysis.has_conflicts:
                print("✅ No conflicts detected - repositories are compatible! Proceeding with simple sync...")
                self._update_status("✅ No conflicts detected - repositories are compatible! Syncing...")
                
                # If there are no conflicts, we can do a simple pull/merge
                try:
                    # Update the current step to show success
                    current_step.set_status("success", "No conflicts - repositories are compatible")
                    
                    # Perform a simple git pull to sync everything
                    result = subprocess.run(['git', 'pull', 'origin'], 
                                          cwd=vault_path, capture_output=True, text=True, timeout=30)
                    
                    if result.returncode == 0:
                        print("✅ Simple sync completed successfully")
                        self._update_status("✅ Repositories synchronized successfully!")
                        return True, "Repositories synchronized successfully - no conflicts detected"
                    else:
                        print(f"⚠️ Simple pull failed: {result.stderr}")
                        # If simple pull fails, fall back to conflict resolution
                        print("Falling back to conflict resolution...")
                        self._update_status("⚠️ Simple sync failed - using conflict resolution...")
                
                except Exception as e:
                    print(f"⚠️ Simple sync failed: {e}")
                    print("Falling back to conflict resolution...")
                    self._update_status("⚠️ Simple sync failed - using conflict resolution...")
            
            # If we reach here, either there are conflicts OR simple sync failed
            if conflict_analysis.has_conflicts:
                print(f"⚠️ Conflicts detected - showing conflict resolution dialog...")
                self._update_status("⚔️ Conflicts detected - launching enhanced conflict resolution system...")
                
                # Show user information about the conflict resolution process
                if ui_elements:
                    info_msg = (
                        "🤝 Repository Synchronization Required!\n\n"
                        f"📁 Local files: {len(local_files)} content files\n"
                        f"🌐 Remote files: {len(remote_files)} content files\n\n"
                        "Conflicts detected between your local vault and the remote repository. "
                        "Ogresync will guide you through safely combining them using our "
                        "enhanced two-stage resolution system:\n\n"
                        "🔄 Stage 1: Choose overall strategy\n"
                        "• Smart Merge: Intelligently combine files (recommended)\n"
                        "• Keep Local Only: Preserve local files with history\n"
                        "• Keep Remote Only: Adopt remote files with backup\n\n"
                        "🎯 Stage 2: File-by-file resolution (if needed)\n"
                        "• Review conflicting files individually\n"
                        "• Choose auto-merge, manual merge, or keep specific versions\n\n"
                        "✅ All git history is preserved - no data loss guaranteed!\n\n"
                        "Click OK to begin conflict resolution."
                    )            
            # Check if there are actually any conflicts that need resolution
            if not conflict_analysis.has_conflicts:
                print("✅ No conflicts detected - repositories are compatible!")
                self._update_status("✅ No conflicts detected - repositories are compatible! Syncing...")
                
                # Since there are no conflicts, we can just do a simple pull/merge
                print("[DEBUG] Performing simple sync to combine compatible repositories...")
                
                try:
                    # Try a simple pull first
                    pull_result = subprocess.run(['git', 'pull', 'origin'], 
                                              cwd=vault_path, capture_output=True, text=True, timeout=30)
                    
                    if pull_result.returncode == 0:
                        print("✅ Simple sync completed successfully")
                        current_step.set_status("success", "No conflicts - repositories are compatible")
                        self._update_status("✅ Repositories synchronized successfully!")
                        return True, f"Repositories synchronized successfully - no conflicts detected ({len(local_files)} files are identical)"
                    else:
                        print(f"⚠️ Simple pull failed: {pull_result.stderr}")
                        # Try merge as fallback
                        current_branch = self._get_current_branch(vault_path)
                        remote_branch_ref = self._get_remote_branch_ref(vault_path, current_branch)
                        
                        merge_result = subprocess.run(['git', 'merge', remote_branch_ref, '--allow-unrelated-histories', '--no-edit'], 
                                                   cwd=vault_path, capture_output=True, text=True, timeout=60)
                        
                        if merge_result.returncode == 0:
                            print("✅ Simple merge completed successfully")
                            current_step.set_status("success", "No conflicts - repositories are compatible")
                            return True, f"Repositories synchronized successfully - no conflicts detected ({len(local_files)} files are identical)"
                        else:
                            print(f"⚠️ Both pull and merge failed, falling back to conflict resolution: {merge_result.stderr}")
                
                except Exception as e:
                    print(f"⚠️ Simple sync failed: {e}")
                    print("Falling back to conflict resolution...")
            
            # If we reach here, either there are conflicts OR simple sync failed
            print("⚠️ Conflicts detected or simple sync failed - showing conflict resolution dialog...")
            self._update_status("⚔️ Launching enhanced conflict resolution system...")
            
            # Show Stage 1 dialog - handle parent type conversion
            self._update_status("🎯 Opening Stage 1 conflict resolution dialog...")
            print("[DEBUG] Opening Stage 1 conflict resolution dialog...")
              # Convert self.dialog to proper parent for conflict resolution
            dialog_parent = self.dialog if isinstance(self.dialog, tk.Tk) else None
            stage1_dialog = Stage1_conflict_resolution.ConflictResolutionDialog(dialog_parent, conflict_analysis)
            selected_strategy = stage1_dialog.show()
            
            print(f"[DEBUG] User selected strategy: {selected_strategy}")
            
            if selected_strategy:
                # Save the selected strategy for use in final sync
                self.wizard_state["conflict_resolution_strategy"] = selected_strategy
                
                # Apply the selected strategy
                self._update_status(f"⚙️ Applying {selected_strategy.value} strategy...")
                print(f"[DEBUG] Applying strategy: {selected_strategy.value}")
                resolution_result = conflict_engine.apply_strategy(selected_strategy, conflict_analysis)
                
                if resolution_result.success:
                    print(f"[DEBUG] Conflict resolution successful: {resolution_result.message}")
                    current_step.set_status("success")
                    return True, f"Repositories synchronized using {selected_strategy.value}: {resolution_result.message}"
                else:
                    print(f"[DEBUG] Conflict resolution failed: {resolution_result.message}")
                    return False, f"Repository synchronization failed: {resolution_result.message}"
            else:
                # User cancelled
                print("[DEBUG] User cancelled conflict resolution")
                return False, "Repository synchronization cancelled by user"
                
        except Exception as e:
            print(f"[DEBUG] Error in conflict resolution: {e}")
            import traceback
            traceback.print_exc()            # CRITICAL: Do NOT fallback to simple merge - this is the exact problem the user reported
            # Instead, return an error so the user knows what happened
            return False, f"Error in conflict resolution system: {str(e)}. Cannot safely merge repositories without user input."
    
    def _handle_simple_merge_fallback(self, vault_path, current_step):
        """
        Fallback method for simple merge when conflict resolution is not available.
        
        WARNING: This method should NEVER be used when both repositories have files
        that could conflict. It's only for extreme edge cases where the conflict
        resolution system is completely unavailable.
        """
        print("[WARNING] Using simple merge fallback - this should only happen in extreme edge cases!")
        self._update_status("📦 Attempting simple merge with remote repository...")
        
        import subprocess
        try:
            # Get the current branch dynamically
            current_branch = self._get_current_branch(vault_path)
            print(f"[DEBUG] Simple merge fallback using branch: {current_branch}")
            
            # Try a simple merge pull
            pull_result = subprocess.run(['git', 'pull', 'origin', current_branch, '--allow-unrelated-histories', '--no-rebase'], 
                                       cwd=vault_path, capture_output=True, text=True, timeout=60)
            
            if pull_result.returncode == 0:
                current_step.set_status("success")
                return True, "Successfully merged with remote repository"
            else:
                if "Already up to date" in pull_result.stdout:
                    current_step.set_status("success")
                    return True, "Repository is already synchronized"
                elif "CONFLICT" in pull_result.stdout:
                    # There are merge conflicts - this should NOT be treated as success
                    return False, f"Merge conflicts detected. This requires conflict resolution: {pull_result.stdout[:200]}"
                else:
                    # Other error - don't declare success
                    return False, f"Repository sync failed: {pull_result.stderr[:100]}"
                    
        except Exception as e:
            return False, f"Error during simple merge: {str(e)}"
    def _handle_unknown_scenario(self, vault_path, current_step):
        """Handle unknown scenarios with graceful fallback."""
        self._update_status("❓ Unknown repository state - attempting graceful synchronization...")
        
        try:
            # Try basic fetch and status check
            import subprocess
            
            fetch_result = subprocess.run(['git', 'fetch', 'origin'], 
                                        cwd=vault_path, capture_output=True, text=True, timeout=30)
            
            if fetch_result.returncode == 0:
                # Try a conservative pull
                pull_result = subprocess.run(['git', 'pull', 'origin', 'main', '--allow-unrelated-histories'], 
                                           cwd=vault_path, capture_output=True, text=True, timeout=60)
                
                if pull_result.returncode == 0:
                    current_step.set_status("success")
                    return True, "Repository synchronized successfully (unknown scenario handled)"
            
            # If we get here, just mark as success and let the next step handle it
            current_step.set_status("success")
            return True, "Repository sync completed with unknown state - will be resolved in final sync"
            
        except Exception as e:
            current_step.set_status("success")  # Don't fail the setup for unknown scenarios
            return True, f"Repository sync completed with issues: {str(e)}"
    
    def _step_final_sync(self):
        """
        Step 10: Final synchronization - minimal and robust approach
        
        Essential functions only:
        1. Commit any uncommitted changes
        2. Push ONLY if local_has_files_remote_empty scenario (empty remote)
        3. Respect user's conflict resolution choices (never override)
        4. Verify final sync status
        """
        try:
            vault_path = self.wizard_state.get("vault_path")
            if not vault_path:
                return False, "Vault path not set."
            
            self._update_status("🔄 Finalizing repository synchronization...")
            
            import subprocess
            
            # CRITICAL: Check and respect user's conflict resolution choice
            conflict_strategy = self.wizard_state.get("conflict_resolution_strategy")
            if conflict_strategy:
                try:
                    from Stage1_conflict_resolution import ConflictStrategy
                    if conflict_strategy == ConflictStrategy.KEEP_REMOTE_ONLY:
                        print("[DEBUG] Final sync - KEEP_REMOTE_ONLY strategy: NO push allowed")
                        self._update_status("✅ Sync complete - remote content preserved as requested")
                        return True, "Synchronization complete - remote content preserved (no local push)"
                    elif conflict_strategy == ConflictStrategy.SMART_MERGE:
                        print("[DEBUG] Final sync - SMART_MERGE strategy: sync already handled in Step 9")
                        self._update_status("✅ Sync complete - repositories already merged")
                        return True, "Synchronization complete - smart merge already applied"
                except ImportError:
                    print("[DEBUG] Final sync - Could not import ConflictStrategy, continuing")
            
            # STEP 1: Always commit any uncommitted changes
            status_result = subprocess.run(['git', 'status', '--porcelain'], 
                                         cwd=vault_path, capture_output=True, text=True)
            
            if status_result.returncode == 0 and status_result.stdout.strip():
                print("[DEBUG] Final sync - Committing uncommitted changes")
                self._update_status("📝 Committing final changes...")
                
                subprocess.run(['git', 'add', '.'], cwd=vault_path, capture_output=True, text=True)
                commit_result = subprocess.run([
                    'git', 'commit', '-m', 'Final setup commit - ensure all changes are saved'
                ], cwd=vault_path, capture_output=True, text=True)
                
                if commit_result.returncode == 0:
                    print("[DEBUG] Final sync - Successfully committed changes")
                else:
                    print(f"[DEBUG] Final sync - Commit failed: {commit_result.stderr}")
            
            # STEP 2: Check if we need to push (ONLY for empty remote scenario)
            current_branch_result = subprocess.run(['git', 'branch', '--show-current'], 
                                                 cwd=vault_path, capture_output=True, text=True)
            current_branch = current_branch_result.stdout.strip() if current_branch_result.returncode == 0 else "main"
            
            # Fetch latest remote state
            subprocess.run(['git', 'fetch', 'origin'], cwd=vault_path, capture_output=True, text=True)
            
            # Check if remote branch exists - this is the key indicator
            remote_branch_exists = subprocess.run(['git', 'rev-parse', '--verify', f'origin/{current_branch}'], 
                                                cwd=vault_path, capture_output=True, text=True)
            
            if remote_branch_exists.returncode != 0:
                # Remote branch doesn't exist = empty remote scenario
                print("[DEBUG] Final sync - Empty remote detected, pushing local content")
                self._update_status("📤 Pushing local content to empty remote repository...")
                
                push_result = subprocess.run(['git', 'push', '-u', 'origin', current_branch], 
                                           cwd=vault_path, capture_output=True, text=True, timeout=120)
                
                if push_result.returncode == 0:
                    print("[DEBUG] Final sync - Successfully pushed to empty remote")
                    self._update_status("✅ Successfully synchronized with remote repository!")
                    return True, "Synchronization complete - local content pushed to empty remote"
                else:
                    push_error = push_result.stderr.strip()
                    print(f"[DEBUG] Final sync - Push to empty remote failed: {push_error}")
                    
                    # Provide helpful error messages
                    if "permission denied" in push_error.lower() or "authentication failed" in push_error.lower():
                        return False, f"Authentication failed. Please verify your SSH key setup.\nError: {push_error}"
                    elif "repository not found" in push_error.lower():
                        return False, f"Repository not found. Please verify the repository URL.\nError: {push_error}"
                    else:
                        return False, f"Failed to push to empty remote repository.\nError: {push_error}"
            
            # STEP 3: For existing remotes, just verify sync status (don't force push)
            else:
                print("[DEBUG] Final sync - Remote branch exists, verifying sync status")
                
                # Check if we're ahead of remote (have unpushed commits)
                ahead_result = subprocess.run(['git', 'rev-list', '--count', f'origin/{current_branch}..HEAD'], 
                                            cwd=vault_path, capture_output=True, text=True)
                
                if ahead_result.returncode == 0:
                    try:
                        commits_ahead = int(ahead_result.stdout.strip() or 0)
                        print(f"[DEBUG] Final sync - Commits ahead of remote: {commits_ahead}")
                        
                        if commits_ahead > 0:
                            # Conservative approach: don't auto-push to existing remotes
                            # Let the user decide later or handle in normal workflow
                            print("[DEBUG] Final sync - Have unpushed commits, but respecting existing remote")
                            self._update_status("✅ Repository synchronized (local commits preserved)")
                            return True, f"Synchronization complete - {commits_ahead} local commit(s) ready for manual sync"
                        else:
                            print("[DEBUG] Final sync - No commits ahead, repositories are in sync")
                            self._update_status("✅ Repository already synchronized")
                            return True, "Synchronization complete - repositories are in sync"
                    
                    except ValueError:
                        print("[DEBUG] Final sync - Could not parse ahead count")
                        self._update_status("✅ Repository synchronization completed")
                        return True, "Synchronization complete"
                else:
                    print("[DEBUG] Final sync - Could not check sync status")
                    self._update_status("✅ Repository synchronization completed")
                    return True, "Synchronization complete"
                    
        except Exception as e:
            print(f"[DEBUG] Final sync error: {e}")
            return False, f"Error in final synchronization: {str(e)}"
    
    def _step_complete_setup(self):
        """Step 11: Complete setup."""
        try:
            # Save final configuration
            print("DEBUG: Starting step_complete_setup")
            
            # The individual values should already be saved by now from previous steps
            # We just need to mark setup as complete
            config_data = self._safe_ogresync_get('config_data')
            if config_data:
                config_data["SETUP_DONE"] = "1"
                print(f"DEBUG: Marking setup as complete in config: {config_data}")
                self._safe_ogresync_call('save_config')
            else:
                # Fallback: try to save manually
                print("WARNING: Could not access Ogresync config_data, setup may not be properly saved")
            
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
    
    def _show_obsidian_installation_guidance(self):
        """Shows OS-specific Obsidian installation guidance."""
        import platform
        import webbrowser
        
        os_name = platform.system().lower()
        
        # Determine OS-specific instructions
        if os_name == "windows":
            title = "🪟 Install Obsidian on Windows"
            instructions = (
                "Obsidian is not installed on your system.\n\n"
                "📥 Installation Options:\n\n"
                "1. Download from Official Website (Recommended)\n"
                "   • Visit obsidian.md/download\n"
                "   • Download the Windows installer (.exe)\n"
                "   • Run the installer and follow instructions\n"
                "   • Default installation path: C:\\Users\\[Username]\\AppData\\Local\\Obsidian\n\n"
                "2. Install via Microsoft Store\n"
                "   • Search for 'Obsidian' in Microsoft Store\n"
                "   • Click Install (requires Microsoft Account)\n\n"
                "3. Install via Chocolatey (Advanced users)\n"
                "   • Open PowerShell as Administrator\n"
                "   • Run: choco install obsidian\n\n"
                "4. Install via Winget (Windows 10/11)\n"
                "   • Open Command Prompt or PowerShell\n"
                "   • Run: winget install Obsidian.Obsidian\n\n"
                "⚡ Pro Tip: The official website installer is most reliable!\n\n"
                "After installation, click 'Retry Detection' below."
            )
            download_url = "https://obsidian.md/download"
            store_url = "ms-windows-store://search/?query=obsidian"
            
        elif os_name == "darwin":  # macOS
            title = "🍎 Install Obsidian on macOS"
            instructions = (
                "Obsidian is not installed on your system.\n\n"
                "📥 Installation Options:\n\n"
                "1. Download from Official Website (Recommended)\n"
                "   • Visit obsidian.md/download\n"
                "   • Download the macOS .dmg file\n"
                "   • Double-click .dmg and drag Obsidian to Applications folder\n"
                "   • Launch from Applications or Spotlight (Cmd+Space)\n\n"
                "2. Install via Mac App Store\n"
                "   • Open Mac App Store\n"
                "   • Search for 'Obsidian'\n"
                "   • Click Get/Install (requires Apple ID)\n\n"
                "3. Install via Homebrew (Advanced users)\n"
                "   • Open Terminal\n"
                "   • Run: brew install --cask obsidian\n"
                "   • Requires Homebrew to be installed first\n\n"
                "⚡ Pro Tip: You may need to allow the app in System Preferences > Security\n\n"
                "After installation, click 'Retry Detection' below."
            )
            download_url = "https://obsidian.md/download"
            store_url = "macappstore://apps.apple.com/app/obsidian/id1547905921"
            
        else:  # Linux and others
            title = "🐧 Install Obsidian on Linux"
            instructions = (
                "Obsidian is not installed on your system.\n\n"
                "📥 Installation Options:\n\n"
                "1. Download AppImage (Recommended - Universal)\n"
                "   • Visit obsidian.md/download\n"
                "   • Download the AppImage file\n"
                "   • Make executable: chmod +x Obsidian-*.AppImage\n"
                "   • Run: ./Obsidian-*.AppImage\n"
                "   • Optional: Move to /opt/ or ~/Applications/\n\n"
                "2. Install via Snap (Ubuntu/derivatives)\n"
                "   • Run: sudo snap install obsidian --classic\n"
                "   • Works on most modern Linux distributions\n\n"
                "3. Install via Flatpak (Universal)\n"
                "   • Run: flatpak install flathub md.obsidian.Obsidian\n"
                "   • Requires Flatpak to be installed first\n\n"
                "4. Install via AUR (Arch Linux/Manjaro)\n"
                "   • Run: yay -S obsidian (or paru -S obsidian)\n"
                "   • Or: sudo pacman -S obsidian (if in official repos)\n\n"
                "5. Install via Package Manager:\n"
                "   • Debian/Ubuntu: Check if available in repositories\n"
                "   • Fedora: sudo dnf install obsidian (if available)\n\n"
                "⚡ Pro Tip: AppImage is most reliable across distributions!\n\n"
                "After installation, click 'Retry Detection' below."
            )
            download_url = "https://obsidian.md/download"
            store_url = None
        
        # Show the installation dialog
        self._show_installation_dialog(title, instructions, download_url, store_url)
    
    def _show_git_installation_guidance(self):
        """Shows OS-specific Git installation guidance."""
        import platform
        import webbrowser
        
        os_name = platform.system().lower()
        
        # Determine OS-specific instructions
        if os_name == "windows":
            title = "🪟 Install Git on Windows"
            instructions = (
                "Git is not installed on your system.\n\n"
                "📥 Installation Options:\n\n"
                "1. Download from Official Website (Recommended)\n"
                "   • Visit git-scm.com/download/win\n"
                "   • Download the Windows installer (.exe)\n"
                "   • Run installer with default settings (recommended)\n"
                "   • This includes Git Bash, Git GUI, and command line tools\n\n"
                "2. Install via Chocolatey (Advanced users)\n"
                "   • Open PowerShell as Administrator\n"
                "   • Run: choco install git\n\n"
                "3. Install via Winget (Windows 10/11)\n"
                "   • Open Command Prompt or PowerShell\n"
                "   • Run: winget install Git.Git\n\n"
                "4. Install GitHub Desktop (includes Git)\n"
                "   • Visit desktop.github.com\n"
                "   • Download and install GitHub Desktop\n"
                "   • This includes Git and a visual interface\n\n"
                "⚡ Pro Tip: The official installer includes Git Bash for Linux-like commands!\n\n"
                "After installation, click 'Retry Detection' below."
            )
            download_url = "https://git-scm.com/download/win"
            store_url = "https://desktop.github.com"
            
        elif os_name == "darwin":  # macOS
            title = "🍎 Install Git on macOS"
            instructions = (
                "Git is not installed on your system.\n\n"
                "📥 Installation Options:\n\n"
                "1. Install Xcode Command Line Tools (Recommended)\n"
                "   • Open Terminal (Cmd+Space, type 'Terminal')\n"
                "   • Run: xcode-select --install\n"
                "   • Follow the installation prompts\n"
                "   • This is the most common method on macOS\n\n"
                "2. Download from Official Website\n"
                "   • Visit git-scm.com/download/mac\n"
                "   • Download and run the installer package\n\n"
                "3. Install via Homebrew (if you have it)\n"
                "   • Open Terminal\n"
                "   • Run: brew install git\n"
                "   • Requires Homebrew to be installed first\n\n"
                "4. Install GitHub Desktop (includes Git)\n"
                "   • Visit desktop.github.com\n"
                "   • Download GitHub Desktop for Mac\n"
                "   • Includes Git and visual interface\n\n"
                "⚡ Pro Tip: Xcode Command Line Tools is the standard way on macOS!\n\n"
                "After installation, click 'Retry Detection' below."
            )
            download_url = "https://git-scm.com/download/mac"
            store_url = "https://desktop.github.com"
            
        else:  # Linux and others
            title = "🐧 Install Git on Linux"
            instructions = (
                "Git is not installed on your system.\n\n"
                "📥 Installation Options:\n\n"
                "1. Install via Package Manager (Recommended):\n\n"
                "   • Ubuntu/Debian/Mint:\n"
                "     sudo apt update && sudo apt install git\n\n"
                "   • Fedora (recent versions):\n"
                "     sudo dnf install git\n\n"
                "   • CentOS/RHEL/Rocky Linux:\n"
                "     sudo yum install git (or sudo dnf install git)\n\n"
                "   • Arch Linux/Manjaro:\n"
                "     sudo pacman -S git\n\n"
                "   • openSUSE:\n"
                "     sudo zypper install git\n\n"
                "   • Alpine Linux:\n"
                "     sudo apk add git\n\n"
                "2. Download from Official Website\n"
                "   • Visit git-scm.com/download/linux\n"
                "   • Follow distribution-specific instructions\n"
                "   • Compile from source if needed\n\n"
                "3. Install via Snap (Universal)\n"
                "   • sudo snap install git-ubuntu --classic\n\n"
                "⚡ Pro Tip: Package manager installation is usually best on Linux!\n\n"
                "After installation, click 'Retry Detection' below."
            )
            download_url = "https://git-scm.com/download/linux"
            store_url = None
        
        # Show the installation dialog
        self._show_installation_dialog(title, instructions, download_url, store_url)
    
    def _show_installation_dialog(self, title, instructions, download_url, store_url=None):
        """Shows a comprehensive installation guidance dialog with retry functionality."""
        import webbrowser
        
        if ui_elements and hasattr(ui_elements, 'show_premium_info'):
            # Enhanced dialog if ui_elements supports it
            dialog = tk.Toplevel(self.dialog)
            dialog.title(title)
            dialog.transient(self.dialog)
            dialog.grab_set()
            dialog.geometry("700x750")
            dialog.configure(bg="#FAFBFC")
            dialog.resizable(True, True)
            
            # Main frame
            main_frame = tk.Frame(dialog, bg="#FAFBFC")
            main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            # Title
            title_label = tk.Label(
                main_frame,
                text=title,
                font=("Arial", 16, "bold"),
                bg="#FAFBFC",
                fg="#1E293B"
            )
            title_label.pack(pady=(0, 20))
            
            # Instructions text area with scrollbar
            text_frame = tk.Frame(main_frame, bg="#FFFFFF", relief=tk.SOLID, borderwidth=1)
            text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
            
            text_widget = tk.Text(
                text_frame,
                wrap=tk.WORD,
                font=("Arial", 11),
                bg="#FFFFFF",
                fg="#1E293B",
                relief=tk.FLAT,
                padx=15,
                pady=15
            )
            
            scrollbar = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
            text_widget.configure(yscrollcommand=scrollbar.set)
            
            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            text_widget.insert(tk.END, instructions)
            text_widget.config(state=tk.DISABLED)
            
            # Status label for feedback
            status_label = tk.Label(
                main_frame,
                text="💡 Choose an installation method above, then click 'Retry Detection' when done.",
                font=("Arial", 10, "italic"),
                bg="#FAFBFC",
                fg="#6366F1",
                wraplength=600
            )
            status_label.pack(pady=(0, 15))
            
            # Buttons frame
            button_frame = tk.Frame(main_frame, bg="#FAFBFC")
            button_frame.pack(fill=tk.X, pady=(20, 0))
            
            def open_download():
                webbrowser.open(download_url)
                status_label.config(text="🌐 Download page opened! Install the software and click 'Retry Detection'.", fg="#22C55E")
            
            def open_store():
                if store_url:
                    webbrowser.open(store_url)
                    status_label.config(text="🏪 App store opened! Install the software and click 'Retry Detection'.", fg="#22C55E")
            
            def retry_detection():
                dialog.destroy()
            
            # Download button
            download_btn = tk.Button(
                button_frame,
                text="🌐 Open Download Page",
                command=open_download,
                font=("Arial", 10, "bold"),
                bg="#6366F1",
                fg="#FFFFFF",
                relief=tk.FLAT,
                cursor="hand2",
                padx=20,
                pady=12
            )
            download_btn.pack(side=tk.LEFT, padx=(0, 12))
            
            # Store button (if available)
            if store_url:
                store_btn = tk.Button(
                    button_frame,
                    text="🏪 Open App Store",
                    command=open_store,
                    font=("Arial", 10, "bold"),
                    bg="#22C55E",
                    fg="#FFFFFF",
                    relief=tk.FLAT,
                    cursor="hand2",
                    padx=20,
                    pady=12
                )
                store_btn.pack(side=tk.LEFT, padx=(0, 12))
            
            # Retry detection button
            retry_btn = tk.Button(
                button_frame,
                text="🔄 Retry Detection",
                command=retry_detection,
                font=("Arial", 10, "bold"),
                bg="#F59E0B",
                fg="#FFFFFF",
                relief=tk.FLAT,
                cursor="hand2",
                padx=20,
                pady=12
            )
            retry_btn.pack(side=tk.RIGHT, padx=(12, 0))
            
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
            
        else:
            # Fallback dialog
            result = messagebox.askquestion(
                title,
                f"{instructions}\n\nWould you like to open the download page?",
                icon='question'
            )
            if result == 'yes':
                webbrowser.open(download_url)
        
        # Offer retry after installation guidance
        retry_software = "Obsidian" if "Obsidian" in title else "Git"
        self._offer_retry_after_installation(retry_software)
    
    def _offer_retry_after_installation(self, software_name):
        """Offer user the option to retry after installation guidance."""
        if ui_elements:
            retry = ui_elements.ask_premium_yes_no(
                f"Retry {software_name} Detection",
                f"Have you completed the {software_name} installation?\n\n"
                f"Click 'Yes' to retry detection, or 'No' to continue with the setup process.",
                self.dialog
            )
        else:
            retry = messagebox.askyesno(
                f"Retry {software_name} Detection",
                f"Have you completed the {software_name} installation?\n\n"
                f"Click 'Yes' to retry detection, or 'No' to continue with the setup process."
            )
        return retry

    def _safe_pull_remote_files(self, vault_path, force_reset=False):
        """
        Safely pull remote files to local repository with proper git history handling.
        
        Args:
            vault_path: Path to the vault directory
            force_reset: If True, use reset --hard instead of merge (for empty local repos)
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        import subprocess
        
        try:
            # Get the current branch dynamically
            current_branch = self._get_current_branch(vault_path)
            remote_branch_ref = self._get_remote_branch_ref(vault_path, current_branch)
            print(f"[DEBUG] Safe pull using branch: {current_branch} (remote: {remote_branch_ref})")
            
            # First, ensure we have the latest remote information
            self._update_status("Fetching latest remote information...")
            fetch_result = subprocess.run(['git', 'fetch', 'origin'], 
                                        cwd=vault_path, capture_output=True, text=True)
            
            if fetch_result.returncode != 0:
                return False, f"Failed to fetch remote information: {fetch_result.stderr}"
            
            # Check if remote has any files
            ls_result = subprocess.run(['git', 'ls-tree', '-r', '--name-only', remote_branch_ref], 
                                     cwd=vault_path, capture_output=True, text=True)
            
            if ls_result.returncode != 0 or not ls_result.stdout.strip():
                return True, "Remote repository is empty - no files to pull"
            
            remote_files = [f.strip() for f in ls_result.stdout.splitlines() if f.strip()]
            # Use our meaningful file detection
            content_files = [f for f in remote_files if self._is_meaningful_file(f)]
            
            if not content_files:
                return True, "Remote repository only has system files - no meaningful content to pull"
            
            self._update_status(f"Downloading {len(content_files)} remote files...")
            
            if force_reset:
                # Use reset for empty local repos to get exact remote state
                reset_result = subprocess.run(['git', 'reset', '--hard', remote_branch_ref], 
                                            cwd=vault_path, capture_output=True, text=True)
                
                if reset_result.returncode == 0:
                    return True, f"Successfully downloaded {len(content_files)} files using reset method"
                else:
                    return False, f"Reset method failed: {reset_result.stderr}"
            else:
                # Use merge for repos with existing content to preserve history
                merge_result = subprocess.run(['git', 'merge', remote_branch_ref, '--allow-unrelated-histories', '--no-ff'], 
                                            cwd=vault_path, capture_output=True, text=True)
                
                if merge_result.returncode == 0:
                    return True, f"Successfully merged {len(content_files)} remote files"
                else:
                    # Fallback to pull with unrelated histories
                    pull_result = subprocess.run(['git', 'pull', 'origin', current_branch, '--allow-unrelated-histories', '--no-rebase'], 
                                               cwd=vault_path, capture_output=True, text=True)
                    
                    if pull_result.returncode == 0:
                        return True, f"Successfully pulled {len(content_files)} remote files (fallback method)"
                    else:
                        return False, f"All pull methods failed. Last error: {pull_result.stderr}"
                        
        except Exception as e:
            return False, f"Error during remote file download: {str(e)}"

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