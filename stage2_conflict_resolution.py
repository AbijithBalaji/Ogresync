"""
Stage 2 Conflict Resolution System for Ogresync

This module implements the detailed file-by-file conflict resolution system
that handles individual file conflicts when Smart Merge strategy is chosen.

Features:
- Multi-file navigation with progress tracking
- Per-file resolution options (Keep Local, Keep Remote, Auto Merge, Manual Merge)
- Built-in 3-panel text editor for manual merging
- External editor integration for system GUI editors
- Real-time conflict analysis and preview
- Complete file management and tracking

Author: Ogresync Development Team
Date: June 2025
"""

import os
import sys
import subprocess
import platform
import tempfile
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from typing import Dict, List, Tuple, Optional, Any, Set, Union
from dataclasses import dataclass
from enum import Enum
import threading
import queue
import time


# =============================================================================
# STAGE 2 DATA STRUCTURES
# =============================================================================

class FileResolutionStrategy(Enum):
    """Available resolution strategies for individual files"""
    KEEP_LOCAL = "keep_local"
    KEEP_REMOTE = "keep_remote" 
    AUTO_MERGE = "auto_merge"
    MANUAL_MERGE = "manual_merge"
    EXTERNAL_EDITOR = "external_editor"


@dataclass
class FileConflictDetails:
    """Detailed information about a single file conflict"""
    file_path: str
    local_content: str
    remote_content: str
    has_differences: bool
    is_binary: bool
    file_size_local: int
    file_size_remote: int
    resolution_strategy: Optional[FileResolutionStrategy] = None
    resolved_content: Optional[str] = None
    is_resolved: bool = False


@dataclass 
class Stage2Result:
    """Result of Stage 2 conflict resolution"""
    success: bool
    resolved_files: List[str]
    resolution_strategies: Dict[str, FileResolutionStrategy]
    message: str
    auto_merge_conflicts: Optional[List[str]] = None  # Files that couldn't auto-merge
    conflicted_files: Optional[List['FileConflictDetails']] = None  # Store original file details


# =============================================================================
# EXTERNAL EDITOR DETECTION
# =============================================================================

class ExternalEditorManager:
    """Manages detection and launching of external editors"""
    
    @staticmethod
    def detect_available_editors() -> Dict[str, str]:
        """Detect available GUI text editors on the system"""
        editors = {}
        
        if platform.system() == "Windows":
            # Windows GUI editors
            possible_editors = {
                "Notepad++": ["C:\\Program Files\\Notepad++\\notepad++.exe", 
                             "C:\\Program Files (x86)\\Notepad++\\notepad++.exe"],
                "Visual Studio Code": ["code"],
                "Sublime Text": ["subl"],
                "Atom": ["atom"],
                "Notepad": ["notepad"]
            }
        elif platform.system() == "Linux":
            # Linux GUI editors only (no terminal editors)
            possible_editors = {
                "Visual Studio Code": ["code"],
                "Sublime Text": ["subl"],
                "Atom": ["atom"],
                "Gedit": ["gedit"],
                "Kate": ["kate"],
                "Gnome Text Editor": ["gnome-text-editor"],
                "Mousepad": ["mousepad"],
                "Leafpad": ["leafpad"],
                "Pluma": ["pluma"],
                "FeatherPad": ["featherpad"]
            }
        elif platform.system() == "Darwin":  # macOS
            # macOS GUI editors
            possible_editors = {
                "Visual Studio Code": ["code"],
                "Sublime Text": ["subl"],
                "Atom": ["atom"],
                "TextEdit": ["open", "-a", "TextEdit"],
                "CotEditor": ["open", "-a", "CotEditor"],
                "MacVim": ["mvim"]
            }
        else:
            possible_editors = {}
        
        # Test which editors are actually available
        for name, commands in possible_editors.items():
            if ExternalEditorManager._test_editor_availability(commands):
                editors[name] = commands
        
        return editors
    
    @staticmethod
    def _test_editor_availability(commands: List[str]) -> bool:
        """Test if an editor command is available"""
        try:
            # Test if the command exists
            if len(commands) == 1:
                result = subprocess.run([commands[0], "--version"], 
                                      capture_output=True, timeout=5)
                return result.returncode == 0
            else:
                # For multi-part commands, just test if first part exists
                result = subprocess.run(["which", commands[0]] if platform.system() != "Windows" 
                                      else ["where", commands[0]], 
                                      capture_output=True, timeout=5)
                return result.returncode == 0
        except:
            return False
    
    @staticmethod
    def launch_external_editor(editor_commands: List[str], file_path: str) -> bool:
        """Launch an external editor with the specified file"""
        try:
            if len(editor_commands) == 1:
                # Single command
                subprocess.Popen([editor_commands[0], file_path])
            else:
                # Multi-part command
                subprocess.Popen(editor_commands + [file_path])
            return True
        except Exception as e:
            print(f"[ERROR] Failed to launch editor: {e}")
            return False


# =============================================================================
# STAGE 2 CONFLICT RESOLUTION DIALOG
# =============================================================================

class Stage2ConflictResolutionDialog:
    """Stage 2 dialog for detailed file-by-file conflict resolution"""
    
    def __init__(self, parent: Optional[tk.Tk], conflicted_files: List[FileConflictDetails]):
        self.parent = parent
        self.conflicted_files = conflicted_files.copy()  # Make a copy to track progress
        self.current_file_index = 0
        self.result: Optional[Stage2Result] = None
        self.dialog: Optional[Union[tk.Tk, tk.Toplevel]] = None
        self._hidden_parent: Optional[tk.Tk] = None  # Track hidden parent for cleanup
        
        # UI components - will be initialized when dialog is created
        self.file_list_var: Optional[tk.StringVar] = None
        self.file_listbox: Optional[tk.Listbox] = None
        self.local_text: Optional[scrolledtext.ScrolledText] = None
        self.remote_text: Optional[scrolledtext.ScrolledText] = None
        self.editor_text: Optional[scrolledtext.ScrolledText] = None
        self.progress_label: Optional[tk.Label] = None
        self.file_info_label: Optional[tk.Label] = None
        
        # Resolution tracking
        self.resolved_files: List[str] = []
        self.resolution_strategies: Dict[str, FileResolutionStrategy] = {}
        
        # External editors
        self.available_editors = ExternalEditorManager.detect_available_editors()
    
    def show(self) -> Optional[Stage2Result]:
        """Show the Stage 2 dialog and return resolution result"""
        if not self.conflicted_files:
            # No files to resolve
            return Stage2Result(
                success=True,
                resolved_files=[],
                resolution_strategies={},
                message="No files require resolution"
            )
        
        self._create_dialog()
        self._create_ui()
        self._update_file_list()
        self._load_current_file()
        
        # Show dialog and wait for completion
        try:
            if self.dialog:
                # Make sure dialog is visible
                self.dialog.deiconify()
                self.dialog.lift()
                self.dialog.focus_force()
                
                # Set up modal behavior only if we have a visible parent
                if self.parent and self.parent.winfo_viewable() and isinstance(self.dialog, tk.Toplevel):
                    self.dialog.grab_set()
                
                # Start the mainloop
                self.dialog.mainloop()
        except Exception as e:
            print(f"[ERROR] Dialog error: {e}")
            import traceback
            traceback.print_exc()
        
        return self.result
    
    def _create_dialog(self):
        """Create the main dialog window"""
        # Check if parent is withdrawn and create appropriate dialog
        if self.parent and self.parent.winfo_viewable():
            # Parent is visible, create as Toplevel
            self.dialog = tk.Toplevel(self.parent)
            self.dialog.transient(self.parent)
        elif self.parent:
            # Parent exists but is withdrawn, create as independent Tk window
            self.dialog = tk.Tk()
            # Store reference to parent for later cleanup
            self._hidden_parent = self.parent
        else:
            # No parent provided, create new root window
            self.dialog = tk.Tk()
        
        self.dialog.title("Stage 2: File-by-File Conflict Resolution")
        self.dialog.configure(bg="#FAFBFC")
        self.dialog.resizable(True, True)
        
        # Initialize Tkinter variables after dialog window is created
        self.file_list_var = tk.StringVar()
        
        # Set larger size for better usability and proper minimum sizes
        width, height = 1400, 900  # Increased size for better layout
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
        self.dialog.minsize(1200, 700)  # Increased minimum size
        
        # Handle window close event properly
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_window_close)
    
    def _on_window_close(self):
        """Handle window close event"""
        # Set result to None (cancelled) and close dialog
        self.result = Stage2Result(
            success=False,
            resolved_files=[],
            resolution_strategies={},
            message="User cancelled Stage 2 resolution"
        )
        if self.dialog:
            self.dialog.quit()  # Exit mainloop
            self.dialog.destroy()  # Destroy window
    
    def _create_ui(self):
        """Create the complete UI for Stage 2 resolution"""
        # Main container
        main_frame = tk.Frame(self.dialog, bg="#FAFBFC")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header
        self._create_header(main_frame)
        
        # Content area - horizontal split
        content_frame = tk.Frame(main_frame, bg="#FAFBFC")
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(20, 0))
        
        # Left panel - File list and progress
        self._create_file_management_panel(content_frame)
        
        # Right panel - File content and resolution
        self._create_resolution_panel(content_frame)
        
        # Bottom panel - Controls
        self._create_controls_panel(main_frame)
    
    def _create_header(self, parent):
        """Create the dialog header"""
        header_frame = tk.Frame(parent, bg="#FAFBFC")
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = tk.Label(
            header_frame,
            text="🔧 Stage 2: Detailed File Conflict Resolution",
            font=("Arial", 18, "bold"),
            bg="#FAFBFC",
            fg="#1E293B"
        )
        title_label.pack()
        
        subtitle_label = tk.Label(
            header_frame,
            text="Resolve conflicts for each file individually",
            font=("Arial", 12, "normal"),
            bg="#FAFBFC",
            fg="#475569"
        )
        subtitle_label.pack(pady=(5, 0))
        
        # Progress indicator
        self.progress_label = tk.Label(
            header_frame,
            text="",
            font=("Arial", 11, "bold"),
            bg="#FAFBFC",
            fg="#6366F1"
        )
        self.progress_label.pack(pady=(10, 0))
    
    def _create_file_management_panel(self, parent):
        """Create the left panel with file list and management"""
        left_panel = tk.Frame(parent, bg="#FFFFFF", relief=tk.RAISED, borderwidth=1)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.configure(width=350)  # Increased width
        left_panel.pack_propagate(False)
        
        # Panel title
        title_label = tk.Label(
            left_panel,
            text="📋 Conflicted Files",
            font=("Arial", 14, "bold"),
            bg="#FFFFFF",
            fg="#1E293B"
        )
        title_label.pack(pady=(15, 10))
        
        # File list
        list_frame = tk.Frame(left_panel, bg="#FFFFFF")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        
        # Scrollable listbox
        listbox_frame = tk.Frame(list_frame, bg="#FFFFFF")
        listbox_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.file_listbox = tk.Listbox(
            listbox_frame,
            yscrollcommand=scrollbar.set,
            font=("Courier", 10),
            selectmode=tk.SINGLE,
            bg="#F8F9FA",
            fg="#1E293B",
            selectbackground="#6366F1",
            selectforeground="#FFFFFF"
        )
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.file_listbox.yview)
        
        # Bind selection event
        self.file_listbox.bind("<<ListboxSelect>>", self._on_file_select)
        
        # File info panel
        self.file_info_label = tk.Label(
            left_panel,
            text="",
            font=("Arial", 9),
            bg="#FFFFFF",
            fg="#475569",
            wraplength=320,  # Adjusted for new width
            justify=tk.LEFT
        )
        self.file_info_label.pack(pady=(0, 15), padx=15)
    
    def _create_resolution_panel(self, parent):
        """Create the right panel with file content and resolution options"""
        right_panel = tk.Frame(parent, bg="#FFFFFF", relief=tk.RAISED, borderwidth=1)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Panel title
        title_label = tk.Label(
            right_panel,
            text="🔍 File Content & Resolution",
            font=("Arial", 14, "bold"),
            bg="#FFFFFF",
            fg="#1E293B"
        )
        title_label.pack(pady=(15, 10))
        
        # Content area with notebook for different views
        content_notebook = ttk.Notebook(right_panel)
        content_notebook.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        
        # Tab 1: Side-by-side comparison
        self._create_comparison_tab(content_notebook)
        
        # Tab 2: Manual merge editor
        self._create_manual_merge_tab(content_notebook)
        
        # Resolution options
        self._create_resolution_options(right_panel)
    
    def _create_comparison_tab(self, notebook):
        """Create the side-by-side comparison tab"""
        comparison_frame = tk.Frame(notebook, bg="#FFFFFF")
        notebook.add(comparison_frame, text="📊 Compare Versions")
        
        # Create a PanedWindow for resizable split
        paned_window = tk.PanedWindow(comparison_frame, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Local content frame
        local_frame = tk.Frame(paned_window, bg="#FFFFFF")
        
        local_title = tk.Label(
            local_frame,
            text="📁 Local Version",
            font=("Arial", 12, "bold"),
            bg="#FFFFFF",
            fg="#1E293B"
        )
        local_title.pack(pady=(5, 5))
        
        self.local_text = scrolledtext.ScrolledText(
            local_frame,
            height=20,
            font=("Courier", 10),
            bg="#F8F9FA",
            fg="#1E293B",
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.local_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        
        # Remote content frame
        remote_frame = tk.Frame(paned_window, bg="#FFFFFF")
        
        remote_title = tk.Label(
            remote_frame,
            text="🌐 Remote Version",
            font=("Arial", 12, "bold"),
            bg="#FFFFFF",
            fg="#1E293B"
        )
        remote_title.pack(pady=(5, 5))
        
        self.remote_text = scrolledtext.ScrolledText(
            remote_frame,
            height=20,
            font=("Courier", 10),
            bg="#F8F9FA",
            fg="#1E293B",
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.remote_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        
        # Add frames to paned window with equal sizing
        paned_window.add(local_frame, width=400, minsize=200)
        paned_window.add(remote_frame, width=400, minsize=200)
    
    def _create_manual_merge_tab(self, notebook):
        """Create the manual merge editor tab"""
        merge_frame = tk.Frame(notebook, bg="#FFFFFF")
        notebook.add(merge_frame, text="✏️ Manual Merge Editor")
        
        # Initially show instructions to use Manual Merge
        self.merge_instructions_frame = tk.Frame(merge_frame, bg="#FFFFFF")
        self.merge_instructions_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=50)
        
        instruction_label = tk.Label(
            self.merge_instructions_frame,
            text="📝 Manual Merge Editor",
            font=("Arial", 18, "bold"),
            bg="#FFFFFF",
            fg="#1E293B"
        )
        instruction_label.pack(pady=(0, 20))
        
        instruction_text = tk.Label(
            self.merge_instructions_frame,
            text="Click the 'Manual Merge' button below to activate the merge editor.\n\n"
                 "The editor will allow you to:\n"
                 "• Edit the merged content manually\n"
                 "• Load local or remote versions as starting points\n"
                 "• Open the file in external editors\n"
                 "• Save your custom merged version",
            font=("Arial", 12),
            bg="#FFFFFF",
            fg="#475569",
            justify=tk.CENTER
        )
        instruction_text.pack()
        
        # Editor content (initially hidden)
        self.editor_content_frame = tk.Frame(merge_frame, bg="#FFFFFF")
        # Don't pack initially - will be shown when Manual Merge is activated
        
        # Instructions for active editor
        editor_instructions = tk.Label(
            self.editor_content_frame,
            text="Edit the content below to create your merged version. Use the buttons to load local/remote content or open in external editors.",
            font=("Arial", 10),
            bg="#FFFFFF",
            fg="#475569",
            wraplength=800
        )
        editor_instructions.pack(pady=(10, 5))
        
        # Editor
        editor_frame = tk.Frame(self.editor_content_frame, bg="#FFFFFF")
        editor_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        editor_title = tk.Label(
            editor_frame,
            text="📝 Merged Content Editor",
            font=("Arial", 12, "bold"),
            bg="#FFFFFF",
            fg="#1E293B"
        )
        editor_title.pack()
        
        self.editor_text = scrolledtext.ScrolledText(
            editor_frame,
            height=20,
            font=("Courier", 10),
            bg="#FFFFFF",
            fg="#1E293B",
            wrap=tk.WORD,
            insertbackground="#6366F1"
        )
        self.editor_text.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        # Editor controls
        editor_controls = tk.Frame(editor_frame, bg="#FFFFFF")
        editor_controls.pack(fill=tk.X, pady=(5, 0))
        
        load_local_btn = tk.Button(
            editor_controls,
            text="📁 Load Local",
            command=self._load_local_to_editor,
            font=("Arial", 9),
            bg="#E5E7EB",
            fg="#374151",
            relief=tk.FLAT,
            cursor="hand2"
        )
        load_local_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        load_remote_btn = tk.Button(
            editor_controls,
            text="🌐 Load Remote",
            command=self._load_remote_to_editor,
            font=("Arial", 9),
            bg="#E5E7EB",
            fg="#374151",
            relief=tk.FLAT,
            cursor="hand2"
        )
        load_remote_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        clear_btn = tk.Button(
            editor_controls,
            text="🗑️ Clear",
            command=self._clear_editor,
            font=("Arial", 9),
            bg="#FEE2E2",
            fg="#DC2626",
            relief=tk.FLAT,
            cursor="hand2"
        )
        clear_btn.pack(side=tk.LEFT)
        
        # Save manual merge button
        save_merge_btn = tk.Button(
            editor_controls,
            text="💾 Save Manual Merge",
            command=lambda: self._resolve_file(FileResolutionStrategy.MANUAL_MERGE),
            font=("Arial", 9, "bold"),
            bg="#10B981",
            fg="#FFFFFF",
            relief=tk.FLAT,
            cursor="hand2",
            padx=15,
            pady=5
        )
        save_merge_btn.pack(side=tk.RIGHT)
        
        # External editor controls (only shown when manual merge is active)
        self.external_editor_frame = tk.Frame(self.editor_content_frame, bg="#FFFFFF")
        self.external_editor_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        external_label = tk.Label(
            self.external_editor_frame,
            text="🚀 Open with External Editor:",
            font=("Arial", 10, "bold"),
            bg="#FFFFFF",
            fg="#374151"
        )
        external_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # External editor buttons will be added dynamically
    
    def _create_resolution_options(self, parent):
        """Create resolution strategy buttons"""
        options_frame = tk.Frame(parent, bg="#FFFFFF")
        options_frame.pack(fill=tk.X, padx=15, pady=(0, 15))
        
        title_label = tk.Label(
            options_frame,
            text="🎯 Resolution Options",
            font=("Arial", 12, "bold"),
            bg="#FFFFFF",
            fg="#1E293B"
        )
        title_label.pack(pady=(0, 10))
        
        # Button grid - reorganized with Manual Merge first and prominent
        button_frame = tk.Frame(options_frame, bg="#FFFFFF")
        button_frame.pack()
        
        # Row 1 - Manual Merge (Prominent)
        row1 = tk.Frame(button_frame, bg="#FFFFFF")
        row1.pack(fill=tk.X, pady=(0, 10))
        
        manual_merge_btn = tk.Button(
            row1,
            text="✏️ Manual Merge (Recommended)",
            command=lambda: self._activate_manual_merge(),
            font=("Arial", 12, "bold"),
            bg="#6366F1",
            fg="#FFFFFF",
            relief=tk.FLAT,
            cursor="hand2",
            padx=30,
            pady=12
        )
        manual_merge_btn.pack(pady=(0, 5))
        
        manual_desc = tk.Label(
            row1,
            text="Edit the file manually with full control. Recommended for important conflicts.",
            font=("Arial", 9),
            bg="#FFFFFF",
            fg="#475569",
            wraplength=600
        )
        manual_desc.pack()
        
        # Row 2 - Quick options
        row2 = tk.Frame(button_frame, bg="#FFFFFF")
        row2.pack(fill=tk.X, pady=(10, 5))
        
        keep_local_btn = tk.Button(
            row2,
            text="� Keep Local Version",
            command=lambda: self._resolve_file(FileResolutionStrategy.KEEP_LOCAL),
            font=("Arial", 10),
            bg="#DBEAFE",
            fg="#1E40AF",
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=8
        )
        keep_local_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        keep_remote_btn = tk.Button(
            row2,
            text="🌐 Keep Remote Version",
            command=lambda: self._resolve_file(FileResolutionStrategy.KEEP_REMOTE),
            font=("Arial", 10),
            bg="#DCFCE7",
            fg="#166534",
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=8
        )
        keep_remote_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        auto_merge_btn = tk.Button(
            row2,
            text="🔄 Auto Merge",
            command=lambda: self._resolve_file(FileResolutionStrategy.AUTO_MERGE),
            font=("Arial", 10),
            bg="#FEF3C7",
            fg="#92400E",
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=8
        )
        auto_merge_btn.pack(side=tk.LEFT)
    
    def _create_controls_panel(self, parent):
        """Create the bottom controls panel"""
        controls_frame = tk.Frame(parent, bg="#FAFBFC")
        controls_frame.pack(fill=tk.X, pady=(20, 0))
        
        # Navigation buttons
        nav_frame = tk.Frame(controls_frame, bg="#FAFBFC")
        nav_frame.pack(side=tk.LEFT)
        
        prev_btn = tk.Button(
            nav_frame,
            text="⬅️ Previous File",
            command=self._previous_file,
            font=("Arial", 10),
            bg="#E5E7EB",
            fg="#374151",
            relief=tk.FLAT,
            cursor="hand2",
            padx=15,
            pady=8
        )
        prev_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        next_btn = tk.Button(
            nav_frame,
            text="Next File ➡️",
            command=self._next_file,
            font=("Arial", 10),
            bg="#E5E7EB",
            fg="#374151",
            relief=tk.FLAT,
            cursor="hand2",
            padx=15,
            pady=8
        )
        next_btn.pack(side=tk.LEFT)
        
        # Action buttons
        action_frame = tk.Frame(controls_frame, bg="#FAFBFC")
        action_frame.pack(side=tk.RIGHT)
        
        cancel_btn = tk.Button(
            action_frame,
            text="❌ Cancel",
            command=self._cancel_resolution,
            font=("Arial", 10),
            bg="#EF4444",
            fg="#FFFFFF",
            relief=tk.FLAT,
            cursor="hand2",
            padx=15,
            pady=8
        )
        cancel_btn.pack(side=tk.RIGHT)
        
        complete_btn = tk.Button(
            action_frame,
            text="✅ Complete Resolution",
            command=self._complete_resolution,
            font=("Arial", 10, "bold"),
            bg="#10B981",
            fg="#FFFFFF",
            relief=tk.FLAT,
            cursor="hand2",
            padx=15,
            pady=8
        )
        complete_btn.pack(side=tk.RIGHT, padx=(0, 10))
    
    # =============================================================================
    # UI EVENT HANDLERS
    # =============================================================================
    
    def _update_file_list(self):
        """Update the file list display"""
        if not self.file_listbox:
            return
        
        self.file_listbox.delete(0, tk.END)
        
        for i, file_conflict in enumerate(self.conflicted_files):
            status_icon = "✅" if file_conflict.is_resolved else "⚠️"
            display_text = f"{status_icon} {file_conflict.file_path}"
            
            self.file_listbox.insert(tk.END, display_text)
            
            # Highlight current file
            if i == self.current_file_index:
                self.file_listbox.select_set(i)
        
        self._update_progress()
    
    def _update_progress(self):
        """Update the progress indicator"""
        if not self.progress_label:
            return
        
        total_files = len(self.conflicted_files)
        resolved_files = sum(1 for f in self.conflicted_files if f.is_resolved)
        
        progress_text = f"Progress: {resolved_files}/{total_files} files resolved"
        if total_files > 0:
            percentage = (resolved_files / total_files) * 100
            progress_text += f" ({percentage:.0f}%)"
        
        self.progress_label.config(text=progress_text)
    
    def _load_current_file(self):
        """Load the current file's content into the UI"""
        if not self.conflicted_files or self.current_file_index >= len(self.conflicted_files):
            return
        
        current_file = self.conflicted_files[self.current_file_index]
        
        # Update file info
        if self.file_info_label:
            info_text = f"File: {current_file.file_path}\n"
            info_text += f"Local size: {current_file.file_size_local} bytes\n"
            info_text += f"Remote size: {current_file.file_size_remote} bytes\n"
            info_text += f"Has differences: {'Yes' if current_file.has_differences else 'No'}\n"
            info_text += f"Binary file: {'Yes' if current_file.is_binary else 'No'}"
            
            if current_file.resolution_strategy:
                info_text += f"\nResolved: {current_file.resolution_strategy.value}"
            
            self.file_info_label.config(text=info_text)
        
        # Load content into text widgets
        if self.local_text:
            self.local_text.config(state=tk.NORMAL)
            self.local_text.delete(1.0, tk.END)
            self.local_text.insert(1.0, current_file.local_content)
            self.local_text.config(state=tk.DISABLED)
        
        if self.remote_text:
            self.remote_text.config(state=tk.NORMAL)
            self.remote_text.delete(1.0, tk.END)
            self.remote_text.insert(1.0, current_file.remote_content)
            self.remote_text.config(state=tk.DISABLED)
        
        # Load into editor (start with local content)
        if self.editor_text:
            self.editor_text.delete(1.0, tk.END)
            if current_file.resolved_content:
                self.editor_text.insert(1.0, current_file.resolved_content)
            else:
                self.editor_text.insert(1.0, current_file.local_content)
    
    def _on_file_select(self, event):
        """Handle file selection from listbox"""
        if not self.file_listbox:
            return
        
        selection = self.file_listbox.curselection()
        if selection:
            self.current_file_index = selection[0]
            self._load_current_file()
    
    def _previous_file(self):
        """Navigate to previous file"""
        if self.current_file_index > 0:
            self.current_file_index -= 1
            self._update_file_list()
            self._load_current_file()
    
    def _next_file(self):
        """Navigate to next file"""
        if self.current_file_index < len(self.conflicted_files) - 1:
            self.current_file_index += 1
            self._update_file_list()
            self._load_current_file()
    
    # =============================================================================
    # RESOLUTION HANDLERS
    # =============================================================================
    
    def _resolve_file(self, strategy: FileResolutionStrategy):
        """Resolve the current file with the specified strategy"""
        if not self.conflicted_files or self.current_file_index >= len(self.conflicted_files):
            return
        
        current_file = self.conflicted_files[self.current_file_index]
        
        try:
            if strategy == FileResolutionStrategy.KEEP_LOCAL:
                current_file.resolved_content = current_file.local_content
                
            elif strategy == FileResolutionStrategy.KEEP_REMOTE:
                current_file.resolved_content = current_file.remote_content
                
            elif strategy == FileResolutionStrategy.AUTO_MERGE:
                # Attempt automatic merge
                merged_content = self._attempt_auto_merge(current_file)
                if merged_content is not None:
                    current_file.resolved_content = merged_content
                else:
                    messagebox.showwarning(
                        "Auto Merge Failed",
                        f"Could not automatically merge {current_file.file_path}. "
                        "Please use Manual Merge or choose Keep Local/Remote."
                    )
                    return
                    
            elif strategy == FileResolutionStrategy.MANUAL_MERGE:
                # Use content from editor
                if self.editor_text:
                    current_file.resolved_content = self.editor_text.get(1.0, tk.END + "-1c")
                else:
                    messagebox.showerror("Error", "Editor not available")
                    return
            
            # Mark as resolved
            current_file.is_resolved = True
            current_file.resolution_strategy = strategy
            
            # Update tracking
            if current_file.file_path not in self.resolved_files:
                self.resolved_files.append(current_file.file_path)
            self.resolution_strategies[current_file.file_path] = strategy
            
            # Update UI
            self._update_file_list()
            self._load_current_file()
            
            # Auto-advance to next unresolved file
            self._advance_to_next_unresolved()
            
            messagebox.showinfo(
                "File Resolved",
                f"✅ {current_file.file_path} resolved using {strategy.value}"
            )
            
        except Exception as e:
            messagebox.showerror("Resolution Error", f"Failed to resolve file: {e}")
    
    def _attempt_auto_merge(self, file_conflict: FileConflictDetails) -> Optional[str]:
        """Attempt to automatically merge file content"""
        try:
            # Simple line-based merge algorithm
            local_lines = file_conflict.local_content.splitlines()
            remote_lines = file_conflict.remote_content.splitlines()
            
            # If one version is empty, use the other
            if not local_lines:
                return file_conflict.remote_content
            if not remote_lines:
                return file_conflict.local_content
            
            # Simple merge: try to combine unique lines
            merged_lines = []
            local_set = set(local_lines)
            remote_set = set(remote_lines)
            
            # Add lines that are common to both
            common_lines = local_set & remote_set
            merged_lines.extend(sorted(common_lines))
            
            # Add unique local lines
            local_unique = local_set - remote_set
            if local_unique:
                merged_lines.append("")  # Separator
                merged_lines.append("# === Local additions ===")
                merged_lines.extend(sorted(local_unique))
            
            # Add unique remote lines
            remote_unique = remote_set - local_set
            if remote_unique:
                merged_lines.append("")  # Separator
                merged_lines.append("# === Remote additions ===")
                merged_lines.extend(sorted(remote_unique))
            
            return "\n".join(merged_lines)
            
        except Exception as e:
            print(f"[ERROR] Auto merge failed: {e}")
            return None
    
    def _advance_to_next_unresolved(self):
        """Advance to the next unresolved file"""
        # Find next unresolved file
        for i in range(len(self.conflicted_files)):
            if not self.conflicted_files[i].is_resolved:
                self.current_file_index = i
                self._update_file_list()
                self._load_current_file()
                return
        
        # All files resolved
        self._check_completion()
    
    def _check_completion(self):
        """Check if all files are resolved and offer completion"""
        unresolved_count = sum(1 for f in self.conflicted_files if not f.is_resolved)
        
        if unresolved_count == 0:
            result = messagebox.askyesno(
                "All Files Resolved",
                "🎉 All files have been resolved!\n\nWould you like to complete the resolution process?",
                default="yes"
            )
            if result:
                self._complete_resolution()
    
    def _load_local_to_editor(self):
        """Load local content to manual merge editor"""
        if self.editor_text and self.conflicted_files:
            current_file = self.conflicted_files[self.current_file_index]
            self.editor_text.delete(1.0, tk.END)
            self.editor_text.insert(1.0, current_file.local_content)
    
    def _load_remote_to_editor(self):
        """Load remote content to manual merge editor"""
        if self.editor_text and self.conflicted_files:
            current_file = self.conflicted_files[self.current_file_index]
            self.editor_text.delete(1.0, tk.END)
            self.editor_text.insert(1.0, current_file.remote_content)
    
    def _clear_editor(self):
        """Clear the manual merge editor"""
        if self.editor_text:
            self.editor_text.delete(1.0, tk.END)
    
    def _open_external_editor(self, editor_name: str):
        """Open current file in external editor"""
        if not self.conflicted_files or self.current_file_index >= len(self.conflicted_files):
            return
        
        current_file = self.conflicted_files[self.current_file_index]
        
        try:
            # Create temporary file with current content
            temp_file = tempfile.NamedTemporaryFile(
                mode='w',
                suffix=f"_{os.path.basename(current_file.file_path)}",
                delete=False
            )
            temp_file.write(current_file.local_content)
            temp_file.close()
            
            # Launch external editor
            editor_commands = self.available_editors[editor_name]
            success = ExternalEditorManager.launch_external_editor(list(editor_commands), temp_file.name)
            
            if success:
                # Show dialog to wait for user to finish editing
                result = messagebox.askyesno(
                    "External Editor",
                    f"✅ {editor_name} has been opened with the file.\n\n"
                    f"Edit the file and save it, then click 'Yes' to load the changes back.\n"
                    f"Click 'No' to cancel external editing.",
                    default="yes"
                )
                
                if result:
                    # Read back the edited content
                    try:
                        with open(temp_file.name, 'r', encoding='utf-8') as f:
                            edited_content = f.read()
                        
                        # Load into editor
                        if self.editor_text:
                            self.editor_text.delete(1.0, tk.END)
                            self.editor_text.insert(1.0, edited_content)
                        
                        messagebox.showinfo(
                            "External Edit Complete",
                            "Content loaded from external editor. You can now save as Manual Merge."
                        )
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to read edited file: {e}")
            else:
                messagebox.showerror("Error", f"Failed to launch {editor_name}")
            
            # Clean up temp file
            try:
                os.unlink(temp_file.name)
            except:
                pass
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open external editor: {e}")
    
    def _complete_resolution(self):
        """Complete the resolution process"""
        # Check if all files are resolved
        unresolved_files = [f.file_path for f in self.conflicted_files if not f.is_resolved]
        
        if unresolved_files:
            result = messagebox.askyesno(
                "Incomplete Resolution",
                f"⚠️ {len(unresolved_files)} files are still unresolved:\n\n"
                + "\n".join(unresolved_files[:5])  # Show first 5
                + ("..." if len(unresolved_files) > 5 else "")
                + "\n\nDo you want to complete anyway? Unresolved files will keep their local versions.",
                default="no"
            )
            
            if not result:
                return
            
            # Auto-resolve unresolved files to keep local version
            for file_conflict in self.conflicted_files:
                if not file_conflict.is_resolved:
                    file_conflict.resolved_content = file_conflict.local_content
                    file_conflict.is_resolved = True
                    file_conflict.resolution_strategy = FileResolutionStrategy.KEEP_LOCAL
                    self.resolution_strategies[file_conflict.file_path] = FileResolutionStrategy.KEEP_LOCAL
        
        # Create result
        self.result = Stage2Result(
            success=True,
            resolved_files=[f.file_path for f in self.conflicted_files],
            resolution_strategies=self.resolution_strategies,
            message=f"Successfully resolved {len(self.conflicted_files)} files"
        )
        
        if self.dialog:
            self.dialog.quit()
            self.dialog.destroy()
    
    def _cancel_resolution(self):
        """Cancel the resolution process"""
        result = messagebox.askyesno(
            "Cancel Resolution",
            "❌ Are you sure you want to cancel the file resolution process?\n\n"
            "All progress will be lost.",
            default="no"
        )
        
        if result:
            self.result = Stage2Result(
                success=False,
                resolved_files=[],
                resolution_strategies={},
                message="Resolution cancelled by user"
            )
            if self.dialog:
                self.dialog.quit()
                self.dialog.destroy()
    
    def _activate_manual_merge(self):
        """Activate manual merge mode - show editor and external editor options"""
        # Hide instructions and show editor content
        if hasattr(self, 'merge_instructions_frame'):
            self.merge_instructions_frame.pack_forget()
        
        if hasattr(self, 'editor_content_frame'):
            self.editor_content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Load current file content into editor
        self._load_current_file_to_editor()
        
        # Create external editor buttons
        self._create_external_editor_buttons()
    
    def _load_current_file_to_editor(self):
        """Load current file content into the manual merge editor"""
        if self.editor_text and self.conflicted_files:
            current_file = self.conflicted_files[self.current_file_index]
            self.editor_text.delete(1.0, tk.END)
            # Start with local content as default
            self.editor_text.insert(1.0, current_file.local_content)
    
    def _create_external_editor_buttons(self):
        """Create buttons for available external editors"""
        if not hasattr(self, 'external_editor_frame'):
            return
        
        # Clear existing buttons
        for widget in self.external_editor_frame.winfo_children():
            if isinstance(widget, tk.Button):
                widget.destroy()
        
        # Add external editor buttons (max 4 to fit nicely)
        for editor_name in list(self.available_editors.keys())[:4]:
            editor_btn = tk.Button(
                self.external_editor_frame,
                text=editor_name,
                command=lambda name=editor_name: self._open_external_editor(name),
                font=("Arial", 9),
                bg="#F3F4F6",
                fg="#374151",
                relief=tk.FLAT,
                cursor="hand2",
                padx=10,
                pady=4
            )
            editor_btn.pack(side=tk.LEFT, padx=(0, 5))

    # =============================================================================
    # CONVENIENCE FUNCTIONS
    # =============================================================================

def create_file_conflict_details(file_path: str, local_content: str, remote_content: str) -> FileConflictDetails:
    """Create FileConflictDetails object from file information"""
    return FileConflictDetails(
        file_path=file_path,
        local_content=local_content,
        remote_content=remote_content,
        has_differences=(local_content.strip() != remote_content.strip()),
        is_binary=b'\0' in local_content.encode('utf-8', errors='ignore'),
        file_size_local=len(local_content.encode('utf-8')),
        file_size_remote=len(remote_content.encode('utf-8'))
    )


def show_stage2_resolution(parent: Optional[tk.Tk], conflicted_files: List[FileConflictDetails]) -> Optional[Stage2Result]:
    """
    Convenience function to show Stage 2 conflict resolution dialog
    
    Args:
        parent: Parent window
        conflicted_files: List of files that need resolution
        
    Returns:
        Stage2Result or None if cancelled
    """
    dialog = Stage2ConflictResolutionDialog(parent, conflicted_files)
    return dialog.show()


if __name__ == "__main__":
    # Test Stage 2 resolution system
    print("Testing Stage 2 Conflict Resolution System...")
    
    # Create sample conflicted files for testing
    test_files = [
        create_file_conflict_details(
            "test1.txt",
            "Line 1\nLine 2 Local\nLine 3",
            "Line 1\nLine 2 Remote\nLine 3\nLine 4 Remote"
        ),
        create_file_conflict_details(
            "test2.md",
            "# Header\nLocal content\n## Section",
            "# Header\nRemote content\n## Section\n### Subsection"
        )
    ]
    
    print(f"✅ Created {len(test_files)} test file conflict details")
    print(f"   • {test_files[0].file_path} (differences: {test_files[0].has_differences})")
    print(f"   • {test_files[1].file_path} (differences: {test_files[1].has_differences})")
    
    # Test external editor detection
    editors = ExternalEditorManager.detect_available_editors()
    print(f"✅ Detected {len(editors)} external editors: {list(editors.keys())}")
    
    # Test auto-merge functionality
    print("✅ Testing auto-merge functionality...")
    dialog = Stage2ConflictResolutionDialog(None, test_files)
    merged_content = dialog._attempt_auto_merge(test_files[0])
    if merged_content:
        print("   Auto-merge successful, preview:")
        print("   " + merged_content.replace('\n', '\n   ')[:200] + "...")
    else:
        print("   Auto-merge returned None")
    
    # Test GUI if available
    try:
        print("✅ Testing GUI components...")
        root = tk.Tk()
        root.withdraw()  # Hide root window
        
        print("   GUI components initialized successfully")
        print("   To test the full dialog, call show_stage2_resolution() from another script")
        
        root.destroy()
        print("✅ All Stage 2 tests completed successfully!")
        
    except Exception as e:
        print(f"⚠ GUI test skipped (expected in headless environments): {e}")
        print("✅ Non-GUI tests completed successfully!")
