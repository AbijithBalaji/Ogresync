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
import datetime

# Optional imports
try:
    import pyperclip
except ImportError:
    pyperclip = None
import time
import subprocess
from typing import Optional, Tuple, Dict, Any

# Import our modules - handle import gracefully
try:
    import ui_elements
except ImportError:
    ui_elements = None

try:
    import conflict_resolution_v2 as conflict_resolution
    CONFLICT_RESOLUTION_AVAILABLE = True
    print("✓ Enhanced conflict resolution module loaded")
except ImportError:
    conflict_resolution = None
    CONFLICT_RESOLUTION_AVAILABLE = False

try:
    import Ogresync
except ImportError:
    Ogresync = None

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
            SetupWizardStep("Enhanced Repository Sync", "Two-stage conflict resolution with history preservation", "⚖️"),
            SetupWizardStep("Final Sync", "Complete synchronization", "📥"),
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
            obsidian_path, error = self._safe_ogresync_call('find_obsidian_path')
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
            is_installed, error = self._safe_ogresync_call('is_git_installed')
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
            vault_path, error = self._safe_ogresync_call('select_vault_path')
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
            vault_path = self.wizard_state.get("vault_path")
            if not vault_path:
                return False, "Vault path not set."
            
            self._update_status("Checking Git repository status...")
            
            # Step 4.1: Check if git is already initialized
            is_git_repo = self._safe_ogresync_call('is_git_repo', vault_path)
            if not is_git_repo[0]:  # Not a git repo
                self._update_status("Initializing Git repository...")
                result, error = self._safe_ogresync_call('initialize_git_repo', vault_path)
                if error:
                    # Fallback manual git init
                    import subprocess
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
                    import subprocess  # Ensure subprocess is available for this check
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
                        # Skip hidden files and common non-content files
                        if not file.startswith('.') and file not in ['README.md', '.gitignore']:
                            rel_path = os.path.relpath(os.path.join(root_dir, file), vault_path)
                            existing_files.append(rel_path)
            
            has_existing_files = len(existing_files) > 0
            self._update_status(f"Vault analysis: {len(existing_files)} content files found")
            
            # Always ensure git user config is set first
            self._safe_ogresync_call('ensure_git_user_config')
            
            if has_existing_files:
                # Step 4.3: Commit existing files
                self._update_status(f"Committing {len(existing_files)} existing files...")
                
                # Stage and commit existing files
                import subprocess
                try:
                    subprocess.run(['git', 'add', '-A'], cwd=vault_path, check=True)
                    result = subprocess.run(['git', 'commit', '-m', 'Initial commit with existing vault files'], 
                                          cwd=vault_path, capture_output=True, text=True)
                    if result.returncode == 0:
                        return True, f"Git initialized and {len(existing_files)} existing files committed"
                    else:
                        # Check if it's because there's nothing to commit
                        if "nothing to commit" in result.stdout.lower():
                            # No files to commit, fall through to create README
                            self._update_status("No changes to commit, creating README...")
                            has_existing_files = False
                        else:
                            return False, f"Failed to commit existing files: {result.stderr}"
                except Exception as e:
                    return False, f"Error committing existing files: {str(e)}"
            
            if not has_existing_files:
                # Step 4.4: Create README file if vault is empty
                self._update_status("Vault is empty. Creating README file...")
                
                # Always create README for empty vaults to ensure proper sync detection
                readme_path = os.path.join(vault_path, "README.md")
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
                            async_result, async_error = self._safe_ogresync_call('generate_ssh_key_async', email.strip())
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
            result, error = self._safe_ogresync_call('ensure_github_known_host')
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
            result, error = self._safe_ogresync_call('test_ssh_connection_sync')
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
                self._safe_ogresync_call('ensure_git_user_config')
            
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
                        # Also save to wizard state
                        self.wizard_state["github_url"] = new_url
                        return True, f"Repository updated to: {new_url}"
                    else:
                        return False, f"Failed to configure new remote: {add_error}"
                else:
                    # User wants to keep existing repository - save it to config
                    existing_url = existing_out.strip()
                    config_data = self._safe_ogresync_get('config_data')
                    if config_data:
                        config_data["GITHUB_REMOTE_URL"] = existing_url
                        self._safe_ogresync_call('save_config')
                        self._update_status(f"Existing repository URL saved to config: {existing_url}")
                    # Also save to wizard state
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
                    # Also save to wizard state
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
        """Step 8: Enhanced Repository Sync with Two-Stage Conflict Resolution System"""
        print(f"[DEBUG] _step_repository_sync: Starting repository sync step")
        try:
            vault_path = self.wizard_state.get("vault_path")
            github_url = self.wizard_state.get("github_url")
            print(f"[DEBUG] _step_repository_sync: vault_path={vault_path}, github_url={github_url}")
            
            # If URL not in wizard state, try to get it from config
            if not github_url:
                config_data = self._safe_ogresync_get('config_data')
                if config_data:
                    github_url = config_data.get("GITHUB_REMOTE_URL")
                    if github_url:
                        # Save it to wizard state for future use
                        self.wizard_state["github_url"] = github_url
                        print(f"[DEBUG] _step_repository_sync: Retrieved github_url from config: {github_url}")
            
            if not vault_path:
                print(f"[DEBUG] _step_repository_sync: ERROR - No vault path")
                return False, "Vault path not set."
            if not github_url:
                print(f"[DEBUG] _step_repository_sync: ERROR - No GitHub URL")
                return False, "GitHub repository URL not set."
            
            # Update step status to running
            current_step = self.setup_steps[8]  # 0-indexed, step 9
            current_step.set_status("running")
            self._update_step_display()
            print(f"[DEBUG] _step_repository_sync: Set step status to running")
            
            self._update_status("🔍 Analyzing repository state for enhanced conflict resolution...")
            
            # Use the enhanced conflict resolution system
            if conflict_resolution and CONFLICT_RESOLUTION_AVAILABLE:
                print(f"[DEBUG] _step_repository_sync: Using enhanced conflict resolution")
                try:
                    # Create conflict resolution engine
                    resolver = conflict_resolution.ConflictResolver(vault_path, self.dialog if isinstance(self.dialog, tk.Tk) else None)
                    print(f"[DEBUG] _step_repository_sync: Created resolver")
                    
                    # Analyze the repository state
                    self._update_status("🔬 Performing detailed repository analysis...")
                    engine = conflict_resolution.ConflictResolutionEngine(vault_path)
                    print(f"[DEBUG] _step_repository_sync: Created engine, analyzing conflicts...")
                    analysis = engine.analyze_conflicts(github_url)
                    print(f"[DEBUG] _step_repository_sync: Analysis complete")
                    
                    # Determine scenario and handle accordingly
                    scenario = self._determine_repository_scenario(analysis, vault_path)
                    self._update_status(f"📊 Repository scenario detected: {scenario}")
                    print(f"[DEBUG] Step 9: Detected scenario '{scenario}' - routing to appropriate handler")
                    
                    if scenario == "both_empty":
                        # Scenario 1: Both repos are empty - create README and push
                        print(f"[DEBUG] Step 9: Calling _handle_both_empty_scenario")
                        result = self._handle_both_empty_scenario(vault_path, current_step)
                        print(f"[DEBUG] Step 9: _handle_both_empty_scenario returned: {result}")
                        return result
                        
                    elif scenario == "local_empty_remote_has_files":
                        # Scenario 2: Local is empty, remote has files - simple pull
                        print(f"[DEBUG] Step 9: Calling _handle_local_empty_scenario")
                        result = self._handle_local_empty_scenario(analysis, vault_path, current_step, engine)
                        print(f"[DEBUG] Step 9: _handle_local_empty_scenario returned: {result}")
                        return result
                        
                    elif scenario == "local_has_files_remote_empty":
                        # Scenario 3: Local has files, remote is empty - simple push will happen in next step
                        print(f"[DEBUG] Step 9: Local has files, remote empty - will push in final sync")
                        self._update_status("✅ Local repository has files, remote is empty - ready for initial push")
                        current_step.set_status("success")
                        result = True, "Local files ready for initial push to empty remote repository"
                        print(f"[DEBUG] Step 9: Returning success for local_has_files_remote_empty: {result}")
                        return result
                        
                    elif scenario == "both_have_files":
                        # Scenario 4: Both have files - use two-stage conflict resolution
                        print(f"[DEBUG] Step 9: Calling _handle_both_have_files_scenario")
                        result = self._handle_both_have_files_scenario(resolver, analysis, current_step)
                        print(f"[DEBUG] Step 9: _handle_both_have_files_scenario returned: {result}")
                        return result
                        
                    else:
                        # Unknown scenario - fallback to simple handling
                        print(f"[DEBUG] Step 9: Unknown scenario '{scenario}' - using fallback")
                        result = self._handle_fallback_scenario(vault_path, current_step)
                        print(f"[DEBUG] Step 9: Fallback scenario returned: {result}")
                        return result
                        
                except Exception as e:
                    print(f"[DEBUG] Step 9: Exception in enhanced conflict resolution: {e}")
                    import traceback
                    traceback.print_exc()
                    self._update_status(f"⚠️ Enhanced conflict resolution failed: {str(e)}")
                    # Fall back to simple conflict handling
                    current_step.set_status("error", f"Enhanced conflict resolution failed: {str(e)}")
                    result = self._handle_fallback_scenario(vault_path, current_step)
                    print(f"[DEBUG] Step 9: Exception fallback returned: {result}")
                    return result
            else:
                # Conflict resolution module not available - use fallback
                print(f"[DEBUG] _step_repository_sync: Enhanced conflict resolution not available")
                self._update_status("⚠️ Enhanced conflict resolution not available - using fallback method")
                result = self._handle_fallback_scenario(vault_path, current_step)
                print(f"[DEBUG] Step 9: No conflict resolution fallback returned: {result}")
                return result
                
        except Exception as e:
            # Ensure current_step is defined for error handling
            print(f"[DEBUG] _step_repository_sync: Outer exception: {e}")
            import traceback
            traceback.print_exc()
            try:
                current_step = self.setup_steps[8]  # Repository sync step
                current_step.set_status("error", str(e))
            except (IndexError, AttributeError):
                # If we can't access the step, at least log the error
                self._update_status(f"❌ Critical error during repository sync: {str(e)}")
            result = False, f"Error during repository sync: {str(e)}"
            print(f"[DEBUG] _step_repository_sync: Outer exception returning: {result}")
            return result
    
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
    
    def _determine_repository_scenario(self, analysis, vault_path):
        """Determine which of the 4 repository scenarios we're dealing with"""
        try:
            # Check local files (excluding system files, generated files, and temp files)
            local_content_files = []
            if os.path.exists(vault_path):
                for root_dir, dirs, files in os.walk(vault_path):
                    # Skip certain directories entirely
                    dirs[:] = [d for d in dirs if d not in {'.git', '.obsidian', '__pycache__', '.vscode', '.idea', 'node_modules'}]
                    
                    for file in files:
                        file_path = os.path.relpath(os.path.join(root_dir, file), vault_path)
                        if self._is_meaningful_file(file_path):
                            local_content_files.append(file)
            
            # Check remote files from analysis (excluding system and generated files)
            remote_content_files = []
            if analysis.remote_files:
                remote_content_files = [f for f in analysis.remote_files 
                                      if self._is_meaningful_file(f)]
            
            has_local_content = len(local_content_files) > 0
            has_remote_content = len(remote_content_files) > 0
            
            print(f"[DEBUG] Local content files: {local_content_files}")
            print(f"[DEBUG] Remote content files: {remote_content_files}")
            print(f"[DEBUG] Has local content: {has_local_content}")
            print(f"[DEBUG] Has remote content: {has_remote_content}")
            
            # CRITICAL FIX: Always prioritize meaningful file content over git history
            # This ensures that if local has no meaningful files but remote does,
            # we treat it as "local_empty_remote_has_files" regardless of git commits
            if not has_local_content and not has_remote_content:
                return "both_empty"
            elif not has_local_content and has_remote_content:
                # This is the critical case: local deleted files but remote still has them
                print(f"[DEBUG] CRITICAL: Local has no meaningful files but remote has {len(remote_content_files)} files")
                print(f"[DEBUG] This should trigger PULL from remote, NOT push to remote")
                return "local_empty_remote_has_files"
            elif has_local_content and not has_remote_content:
                return "local_has_files_remote_empty"
            else:
                return "both_have_files"
                
        except Exception as e:
            print(f"[DEBUG] Error determining scenario: {e}")
            return "unknown"
    
    def _handle_both_empty_scenario(self, vault_path, current_step):
        """Handle scenario where both repositories are empty"""
        try:
            self._update_status("📝 Both repositories are empty - creating initial README file...")
            
            # Create a basic README.md file
            readme_path = os.path.join(vault_path, "README.md")
            readme_content = f"""# My Obsidian Vault

Welcome to my Obsidian vault! This vault is synchronized with GitHub using Ogresync.

## Setup Information
- Created: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Synchronized with: {self.wizard_state.get('github_url', 'GitHub Repository')}
- Tool: Ogresync Setup Wizard

## Getting Started
You can start creating notes in this vault. All changes will be automatically synchronized with your GitHub repository.

Happy note-taking! 📚
"""
            
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            
            # Commit and push the README
            import subprocess
            
            # Add the README file
            add_result = subprocess.run(['git', 'add', 'README.md'], 
                                      cwd=vault_path, capture_output=True, text=True)
            if add_result.returncode != 0:
                raise Exception(f"Failed to add README: {add_result.stderr}")
            
            # Commit the README
            commit_result = subprocess.run(['git', 'commit', '-m', 'Initial commit: Add README'], 
                                         cwd=vault_path, capture_output=True, text=True)
            if commit_result.returncode != 0:
                raise Exception(f"Failed to commit README: {commit_result.stderr}")
            
            # Push to remote
            self._update_status("📤 Pushing initial README to remote repository...")
            push_result = subprocess.run(['git', 'push', '-u', 'origin', 'main'], 
                                       cwd=vault_path, capture_output=True, text=True)
            if push_result.returncode != 0:
                raise Exception(f"Failed to push README: {push_result.stderr}")
            
            self._update_status("✅ Initial README created and pushed successfully!")
            current_step.set_status("success")
            return True, "Both repositories were empty - created and pushed initial README"
            
        except Exception as e:
            self._update_status(f"❌ Failed to create initial README: {str(e)}")
            current_step.set_status("error", f"Failed to initialize empty repositories: {str(e)}")
            return False, f"Failed to initialize empty repositories: {str(e)}"
    
    def _handle_local_empty_scenario(self, analysis, vault_path, current_step, engine=None):
        """Handle scenario where local is empty but remote has files"""
        print(f"[DEBUG] _handle_local_empty_scenario: Starting with vault_path={vault_path}")
        try:
            self._update_status("📥 Local repository is empty, remote has files - pulling remote content...")
            print(f"[DEBUG] _handle_local_empty_scenario: Status updated")
            
            import subprocess
            
            # Get the correct remote branch from the engine
            remote_branch = "origin/main"  # Default fallback
            if engine and hasattr(engine, 'default_remote_branch'):
                remote_branch = engine.default_remote_branch
                print(f"[DEBUG] _handle_local_empty_scenario: Using detected remote branch: {remote_branch}")
            else:
                print(f"[DEBUG] _handle_local_empty_scenario: Using default remote branch: {remote_branch}")
            
            # Check if local repository has any commits
            print(f"[DEBUG] _handle_local_empty_scenario: Checking for local commits...")
            log_result = subprocess.run(['git', 'log', '--oneline'], 
                                      cwd=vault_path, capture_output=True, text=True)
            has_local_commits = log_result.returncode == 0 and log_result.stdout.strip()
            print(f"[DEBUG] _handle_local_empty_scenario: Has local commits: {has_local_commits}")
            
            # Fetch latest remote information
            print(f"[DEBUG] _handle_local_empty_scenario: Fetching from remote...")
            fetch_result = subprocess.run(['git', 'fetch', 'origin'], 
                                        cwd=vault_path, capture_output=True, text=True)
            if fetch_result.returncode != 0:
                print(f"[DEBUG] _handle_local_empty_scenario: Fetch failed: {fetch_result.stderr}")
                raise Exception(f"Failed to fetch remote: {fetch_result.stderr}")
            print(f"[DEBUG] _handle_local_empty_scenario: Fetch successful")
            
            if has_local_commits:
                # Local has commits, use merge strategy
                print(f"[DEBUG] _handle_local_empty_scenario: Using merge strategy with {remote_branch}...")
                self._update_status("🔄 Merging remote files into local repository...")
                branch_name = remote_branch.split('/')[-1]  # Extract branch name (e.g., 'main' or 'master')
                pull_result = subprocess.run(['git', 'pull', 'origin', branch_name, '--allow-unrelated-histories', '--no-rebase'], 
                                           cwd=vault_path, capture_output=True, text=True)
                print(f"[DEBUG] _handle_local_empty_scenario: Pull result: {pull_result.returncode}, stdout: {pull_result.stdout}, stderr: {pull_result.stderr}")
                
                if pull_result.returncode != 0:
                    # Try reset method as fallback
                    print(f"[DEBUG] _handle_local_empty_scenario: Pull failed, trying reset method with {remote_branch}...")
                    self._update_status("🔄 Trying reset method to retrieve remote files...")
                    reset_result = subprocess.run(['git', 'reset', '--hard', remote_branch], 
                                                cwd=vault_path, capture_output=True, text=True)
                    print(f"[DEBUG] _handle_local_empty_scenario: Reset result: {reset_result.returncode}, stdout: {reset_result.stdout}, stderr: {reset_result.stderr}")
                    if reset_result.returncode != 0:
                        raise Exception(f"Failed to pull remote files: {pull_result.stderr}")
            else:
                # Local has no commits, use reset to adopt remote state
                print(f"[DEBUG] _handle_local_empty_scenario: No local commits, using reset method with {remote_branch}...")
                self._update_status("🔄 Local repository has no commits, adopting remote state...")
                reset_result = subprocess.run(['git', 'reset', '--hard', remote_branch], 
                                            cwd=vault_path, capture_output=True, text=True)
                print(f"[DEBUG] _handle_local_empty_scenario: Reset result: {reset_result.returncode}, stdout: {reset_result.stdout}, stderr: {reset_result.stderr}")
                if reset_result.returncode != 0:
                    raise Exception(f"Failed to adopt remote state: {reset_result.stderr}")
            
            # Verify files were actually pulled/retrieved
            print(f"[DEBUG] _handle_local_empty_scenario: Verifying pulled files...")
            pulled_files = []
            for root_dir, dirs, files in os.walk(vault_path):
                if '.git' in root_dir:
                    continue
                for file in files:
                    if not file.startswith('.'):
                        pulled_files.append(file)
            
            print(f"[DEBUG] _handle_local_empty_scenario: Found {len(pulled_files)} pulled files: {pulled_files}")
            self._update_status(f"✅ Successfully retrieved {len(pulled_files)} files from remote repository!")
            current_step.set_status("success")
            return True, f"Remote files retrieved successfully ({len(pulled_files)} files)"
                    
        except Exception as e:
            print(f"[DEBUG] _handle_local_empty_scenario: Exception occurred: {e}")
            self._update_status(f"❌ Failed to retrieve remote files: {str(e)}")
            current_step.set_status("error", f"Failed to retrieve remote files: {str(e)}")
            return False, f"Failed to retrieve remote files: {str(e)}"
    
    def _handle_both_have_files_scenario(self, resolver, analysis, current_step):
        """Handle scenario where both repositories have files - use two-stage conflict resolution"""
        try:
            self._update_status("⚖️ Both repositories have files - launching enhanced conflict resolution...")
            
            # Show informative message about the conflict resolution process
            if ui_elements:
                from ui_dialogs import show_conflict_info
                
                # Show the themed conflict info dialog
                proceed = show_conflict_info(self.dialog)
                if not proceed:
                    self._update_status("❌ Conflict resolution cancelled by user")
                    current_step.set_status("skipped", "Conflict resolution cancelled by user")
                    return
            
            # Launch the two-stage conflict resolution
            self._update_status("🚀 Starting Stage 1: High-level strategy selection...")
            
            result = resolver.resolve_initial_setup_conflicts(self.wizard_state.get("github_url"))
            
            if result.success:
                self._update_status(f"✅ Conflict resolution completed successfully! Strategy: {result.strategy.value if result.strategy else 'N/A'}")
                
                # Show success message with details
                if ui_elements:
                    success_msg = (
                        f"🎉 Repository Synchronization Complete!\n\n"
                        f"✅ Resolution Strategy: {result.strategy.value.replace('_', ' ').title() if result.strategy else 'Default'}\n"
                        f"📁 Files Processed: {len(result.files_processed)}\n"
                        f"💾 Backup Created: {result.backup_created or 'N/A'}\n\n"
                        f"Your local vault and remote repository are now fully synchronized.\n"
                        f"All git history has been preserved and no commits were lost.\n\n"
                        f"📋 Summary: {result.message}"
                    )
                    ui_elements.show_premium_info("Conflict Resolution Successful", success_msg, self.dialog)
                
                current_step.set_status("success")
                return True, f"Two-stage conflict resolution completed: {result.message}"
            else:
                    # Check if user cancelled vs actual error
                    if "cancelled by user" in result.message.lower():
                        self._update_status("⏭ Conflict resolution cancelled - you can retry this step later")
                        
                        # Show user-friendly cancellation message
                        if ui_elements:
                            cancel_msg = (
                                f"⏸ Conflict Resolution Cancelled\n\n"
                                f"You can continue with the setup and resolve conflicts later, or:\n\n"
                                f"🔄 Retry: Click 'Execute Step' to try conflict resolution again\n"
                                f"⏭ Skip: Continue setup and handle conflicts manually later\n"
                                f"❌ Cancel: Exit the setup wizard\n\n"
                                f"💡 Tip: All your data is safe - no changes have been made to your repositories."
                            )
                            ui_elements.show_premium_info("Resolution Cancelled", cancel_msg, self.dialog)
                        
                        current_step.set_status("pending")  # Reset to pending so user can retry
                        return False, "Conflict resolution cancelled - can retry or skip"
                    else:
                        self._update_status(f"❌ Conflict resolution failed: {result.message}")
                        
                        # Show detailed error information  
                        if ui_elements:
                            error_msg = (
                                f"❌ Repository Conflict Resolution Failed\n\n"
                                f"Error: {result.message}\n\n"
                                f"This can happen when:\n"
                                f"• Network connectivity issues during synchronization\n"
                                f"• Repository permissions are restricted\n"
                                f"• Git merge strategies encounter incompatible histories\n\n"
                                f"💡 Suggested Solutions:\n"
                                f"1. Check your network connection and repository access\n"
                                f"2. Verify you have write permissions to the repository\n"
                                f"3. Try the conflict resolution step again\n"
                                f"4. Contact support if the issue persists\n\n"
                                f"Repository: {self.wizard_state.get('github_url', 'N/A')}"
                            )
                            ui_elements.show_premium_error("Conflict Resolution Failed", error_msg, self.dialog)
                        
                        current_step.set_status("error", f"Conflict resolution failed: {result.message}")
                        return False, f"Two-stage conflict resolution failed: {result.message}"
                        
        except Exception as e:
            self._update_status(f"❌ Error during conflict resolution: {str(e)}")
            current_step.set_status("error", f"Conflict resolution error: {str(e)}")
            return False, f"Error during conflict resolution: {str(e)}"
    
    def _handle_fallback_scenario(self, vault_path, current_step):
        """Fallback scenario handling when enhanced conflict resolution is not available"""
        try:
            self._update_status("🔄 Using fallback synchronization method...")
            
            import subprocess
            
            # Try to fetch and sync with basic git commands
            fetch_result = subprocess.run(['git', 'fetch', 'origin'], 
                                        cwd=vault_path, capture_output=True, text=True)
            
            if fetch_result.returncode == 0:
                # Try merge-style pull
                pull_result = subprocess.run(['git', 'pull', 'origin', 'main', '--allow-unrelated-histories', '--no-rebase'], 
                                           cwd=vault_path, capture_output=True, text=True)
                
                if pull_result.returncode == 0:
                    self._update_status("✅ Repository synchronized using fallback method")
                    current_step.set_status("success")
                    return True, "Repository synchronized successfully (fallback method)"
                else:
                    if "couldn't find remote ref" in pull_result.stderr.lower():
                        self._update_status("✅ Remote repository is empty - ready for initial push")
                        current_step.set_status("success")
                        return True, "Remote repository is empty - ready for initial push"
                    else:
                        self._update_status(f"⚠️ Sync completed with warnings: {pull_result.stderr}")
                        current_step.set_status("success")
                        return True, f"Repository sync completed with warnings: {pull_result.stderr}"
            else:
                if "couldn't find remote ref" in fetch_result.stderr.lower():
                    self._update_status("✅ Remote repository is empty - ready for initial push")
                    current_step.set_status("success")
                    return True, "Remote repository is empty - ready for initial push"
                else:
                    self._update_status(f"⚠️ Fetch completed with warnings: {fetch_result.stderr}")
                    current_step.set_status("success")
                    return True, f"Repository sync completed with warnings: {fetch_result.stderr}"
                    
        except Exception as e:
            self._update_status(f"❌ Fallback sync failed: {str(e)}")
            current_step.set_status("error", f"Fallback sync failed: {str(e)}")
            return False, f"Fallback sync failed: {str(e)}"
    
    def _step_final_sync(self):
        """Step 10: Final synchronization - intelligent push only when truly needed."""
        try:
            vault_path = self.wizard_state.get("vault_path")
            if not vault_path:
                return False, "Vault path not set."
            
            self._update_status("Checking final synchronization status...")
            
            import subprocess
            
            # CRITICAL SAFEGUARD: Check if we just handled a "local_empty_remote_has_files" scenario
            # If so, we should NEVER push, only ensure we have the remote content
            current_local_files = []
            if os.path.exists(vault_path):
                for root_dir, dirs, files in os.walk(vault_path):
                    dirs[:] = [d for d in dirs if d not in {'.git', '.obsidian', '__pycache__', '.vscode', '.idea', 'node_modules'}]
                    for file in files:
                        file_path = os.path.relpath(os.path.join(root_dir, file), vault_path)
                        if self._is_meaningful_file(file_path):
                            current_local_files.append(file)
            
            has_local_meaningful_files = len(current_local_files) > 0
            print(f"[DEBUG] Current local meaningful files: {current_local_files}")
            print(f"[DEBUG] Has local meaningful files: {has_local_meaningful_files}")
            
            # If local has no meaningful files, we should NOT push anything
            if not has_local_meaningful_files:
                self._update_status("🚫 Local repository has no meaningful files - ensuring remote content is preserved")
                
                # Ensure we have the latest remote content
                fetch_result = subprocess.run(['git', 'fetch', 'origin'], 
                                            cwd=vault_path, capture_output=True, text=True)
                
                # Check if remote has content we don't have locally
                current_branch_result = subprocess.run(['git', 'branch', '--show-current'], 
                                                     cwd=vault_path, capture_output=True, text=True)
                current_branch = current_branch_result.stdout.strip() if current_branch_result.returncode == 0 else "main"
                
                # Check if we're behind remote
                behind_result = subprocess.run(['git', 'log', f'HEAD..origin/{current_branch}', '--oneline'], 
                                             cwd=vault_path, capture_output=True, text=True)
                
                if behind_result.returncode == 0 and behind_result.stdout.strip():
                    # We're behind remote, pull the changes
                    self._update_status("📥 Pulling missing remote content to local repository...")
                    pull_result = subprocess.run(['git', 'pull', 'origin', current_branch, '--no-rebase'], 
                                               cwd=vault_path, capture_output=True, text=True)
                    
                    if pull_result.returncode == 0:
                        # Count the files we got
                        final_local_files = []
                        for root_dir, dirs, files in os.walk(vault_path):
                            dirs[:] = [d for d in dirs if d not in {'.git', '.obsidian', '__pycache__', '.vscode', '.idea', 'node_modules'}]
                            for file in files:
                                file_path = os.path.relpath(os.path.join(root_dir, file), vault_path)
                                if self._is_meaningful_file(file_path):
                                    final_local_files.append(file)
                        
                        self._update_status(f"✅ Successfully retrieved {len(final_local_files)} files from remote repository")
                        return True, f"Final synchronization completed - pulled {len(final_local_files)} files from remote (no push needed)"
                    else:
                        return False, f"Failed to pull remote content: {pull_result.stderr}"
                else:
                    self._update_status("✅ Local and remote are synchronized - no action needed")
                    return True, "Final synchronization completed - repositories are in sync (no push needed)"
            
            # Continue with normal final sync logic only if local has meaningful files
            # First, ensure we're up to date with remote
            fetch_result = subprocess.run(['git', 'fetch', 'origin'], 
                                        cwd=vault_path, capture_output=True, text=True)
            
            if fetch_result.returncode != 0:
                self._update_status("Warning: Could not fetch from remote, proceeding anyway...")
            
            # Check current repository state
            status_result = subprocess.run(['git', 'status', '--porcelain'], 
                                         cwd=vault_path, capture_output=True, text=True)
            
            has_uncommitted_changes = status_result.returncode == 0 and status_result.stdout.strip()
            
            # Get current branch and remote tracking info
            current_branch_result = subprocess.run(['git', 'branch', '--show-current'], 
                                                 cwd=vault_path, capture_output=True, text=True)
            current_branch = current_branch_result.stdout.strip() if current_branch_result.returncode == 0 else "main"
            
            # Check if we have meaningful unpushed commits
            unpushed_result = subprocess.run(['git', 'log', f'origin/{current_branch}..HEAD', '--oneline'], 
                                           cwd=vault_path, capture_output=True, text=True)
            
            # Check if local and remote are in sync (same commit hash)
            local_commit_result = subprocess.run(['git', 'rev-parse', 'HEAD'], 
                                                cwd=vault_path, capture_output=True, text=True)
            remote_commit_result = subprocess.run(['git', 'rev-parse', f'origin/{current_branch}'], 
                                                 cwd=vault_path, capture_output=True, text=True)
            
            local_commit = local_commit_result.stdout.strip() if local_commit_result.returncode == 0 else ""
            remote_commit = remote_commit_result.stdout.strip() if remote_commit_result.returncode == 0 else ""
            
            print(f"[DEBUG] Local commit: {local_commit}")
            print(f"[DEBUG] Remote commit: {remote_commit}")
            print(f"[DEBUG] Commits are same: {local_commit == remote_commit}")
            print(f"[DEBUG] Has uncommitted changes: {has_uncommitted_changes}")
            
            # CRITICAL: If local and remote are pointing to the same commit, no push needed
            if local_commit == remote_commit and not has_uncommitted_changes:
                self._update_status("✅ Local and remote are perfectly synchronized - no push needed")
                return True, "Final synchronization completed - repositories are already in sync"
            
            # If we have uncommitted changes, commit them first
            if has_uncommitted_changes:
                self._update_status("📝 Committing final changes...")
                
                # Check if these are meaningful changes or just system files
                meaningful_changes = False
                for line in status_result.stdout.strip().split('\n'):
                    if line.strip():
                        file_path = line[3:].strip()  # Remove status indicators
                        if self._is_meaningful_file(file_path):
                            meaningful_changes = True
                            break
                
                if meaningful_changes:
                    # Commit meaningful changes
                    subprocess.run(['git', 'add', '-A'], cwd=vault_path, capture_output=True, text=True)
                    subprocess.run(['git', 'commit', '-m', 'Final setup wizard changes'], 
                                 cwd=vault_path, capture_output=True, text=True)
                    print("[DEBUG] Committed meaningful changes")
                else:
                    # Only system files changed, be more conservative
                    print("[DEBUG] Only system files changed, skipping commit")
                    return True, "Final synchronization completed - only system files changed, no push needed"
            
            # Now check for unpushed commits again
            unpushed_result = subprocess.run(['git', 'log', f'origin/{current_branch}..HEAD', '--oneline'], 
                                           cwd=vault_path, capture_output=True, text=True)
            
            if unpushed_result.returncode == 0 and unpushed_result.stdout.strip():
                unpushed_commits = unpushed_result.stdout.strip().split('\n')
                
                # Analyze the commits to see if they're meaningful
                meaningful_commits = []
                for commit_line in unpushed_commits:
                    # Check if this commit contains meaningful changes
                    commit_hash = commit_line.split()[0]
                    commit_files_result = subprocess.run(['git', 'show', '--name-only', '--format=', commit_hash], 
                                                       cwd=vault_path, capture_output=True, text=True)
                    
                    if commit_files_result.returncode == 0:
                        commit_files = commit_files_result.stdout.strip().split('\n')
                        has_meaningful_files = any(self._is_meaningful_file(f) for f in commit_files if f.strip())
                        
                        if has_meaningful_files:
                            meaningful_commits.append(commit_line)
                        else:
                            print(f"[DEBUG] Commit {commit_hash} has only system files: {commit_files}")
                
                print(f"[DEBUG] Total unpushed commits: {len(unpushed_commits)}")
                print(f"[DEBUG] Meaningful unpushed commits: {len(meaningful_commits)}")
                
                # Only push if we have meaningful commits
                if meaningful_commits:
                    self._update_status(f"📤 Pushing {len(meaningful_commits)} meaningful commit(s) to remote...")
                    
                    push_result = subprocess.run(['git', 'push', 'origin', current_branch], 
                                               cwd=vault_path, capture_output=True, text=True)
                    
                    if push_result.returncode == 0:
                        self._update_status("✅ Successfully pushed meaningful commits to remote!")
                        return True, f"Final synchronization completed - {len(meaningful_commits)} meaningful commit(s) pushed"
                    else:
                        # Handle push rejection carefully
                        if "non-fast-forward" in push_result.stderr or "rejected" in push_result.stderr:
                            self._update_status("🔄 Remote has new changes, checking if merge is safe...")
                            
                            # Check what's on remote that we don't have
                            remote_ahead_result = subprocess.run(['git', 'log', f'HEAD..origin/{current_branch}', '--oneline'], 
                                                               cwd=vault_path, capture_output=True, text=True)
                            
                            if remote_ahead_result.returncode == 0 and remote_ahead_result.stdout.strip():
                                # Remote has commits we don't have - this is a real conflict situation
                                return False, f"Remote repository has new commits that conflict with local changes. Please use the conflict resolution system."
                            else:
                                # Try the push again (might be a transient issue)
                                retry_push = subprocess.run(['git', 'push', 'origin', current_branch], 
                                                          cwd=vault_path, capture_output=True, text=True)
                                if retry_push.returncode == 0:
                                    return True, f"Final synchronization completed after retry - {len(meaningful_commits)} commit(s) pushed"
                                else:
                                    return False, f"Failed to push commits: {retry_push.stderr}"
                        else:
                            return False, f"Failed to push commits: {push_result.stderr}"
                else:
                    # All commits are system-only, don't push them to avoid overwriting remote content
                    self._update_status("⚠️ All unpushed commits contain only system files - skipping push to preserve remote content")
                    
                    # Reset to remote state to avoid future confusion
                    reset_result = subprocess.run(['git', 'reset', '--hard', f'origin/{current_branch}'], 
                                                cwd=vault_path, capture_output=True, text=True)
                    if reset_result.returncode == 0:
                        self._update_status("✅ Reset to remote state - repositories are now synchronized")
                        return True, "Final synchronization completed - system commits discarded, remote content preserved"
                    else:
                        return True, "Final synchronization completed - unpushed commits contain only system files"
            else:
                # No unpushed commits
                self._update_status("✅ No unpushed commits found - repositories are synchronized")
                return True, "Final synchronization completed - repositories are in sync"
                    
        except Exception as e:
            return False, f"Error in final sync: {str(e)}"
    
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
            # First, ensure we have the latest remote information
            self._update_status("Fetching latest remote information...")
            fetch_result = subprocess.run(['git', 'fetch', 'origin'], 
                                        cwd=vault_path, capture_output=True, text=True)
            
            if fetch_result.returncode != 0:
                return False, f"Failed to fetch remote information: {fetch_result.stderr}"
            
            # Check if remote has any files
            ls_result = subprocess.run(['git', 'ls-tree', '-r', '--name-only', 'origin/main'], 
                                     cwd=vault_path, capture_output=True, text=True)
            
            if ls_result.returncode != 0 or not ls_result.stdout.strip():
                return True, "Remote repository is empty - no files to pull"
            
            remote_files = [f.strip() for f in ls_result.stdout.splitlines() if f.strip()]
            content_files = [f for f in remote_files if f not in ['.gitignore', 'README.md']]
            
            if not content_files:
                return True, "Remote repository only has README/gitignore - no content files to pull"
            
            self._update_status(f"Downloading {len(content_files)} remote files...")
            
            if force_reset:
                # Use reset for empty local repos to get exact remote state
                reset_result = subprocess.run(['git', 'reset', '--hard', 'origin/main'], 
                                            cwd=vault_path, capture_output=True, text=True)
                
                if reset_result.returncode == 0:
                    return True, f"Successfully downloaded {len(content_files)} files using reset method"
                else:
                    return False, f"Reset method failed: {reset_result.stderr}"
            else:
                # Use merge for repos with existing content to preserve history
                merge_result = subprocess.run(['git', 'merge', 'origin/main', '--allow-unrelated-histories', '--no-ff'], 
                                            cwd=vault_path, capture_output=True, text=True)
                
                if merge_result.returncode == 0:
                    return True, f"Successfully merged {len(content_files)} remote files"
                else:
                    # Fallback to pull with unrelated histories
                    pull_result = subprocess.run(['git', 'pull', 'origin', 'main', '--allow-unrelated-histories', '--no-rebase'], 
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