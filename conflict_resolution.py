"""
Advanced Two-Stage Conflict Resolution System for Ogresync

This module provides comprehensive conflict resolution capabilities:
1. Stage 1: High-level strategy selection (Keep Local, Keep Remote, Smart Merge)
2. Stage 2: File-by-file resolution for conflicting files (Auto Merge, Manual Merge, Keep Local, Keep Remote)

The system is designed to handle conflicts in:
- Initial repository setup (local vs remote files)
- During sync operations (git merge conflicts)
- When repositories diverge during sync
"""

import os
import sys
import subprocess
import tempfile
import webbrowser
import shlex
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Dict, List, Tuple, Optional, Any, Set
import difflib
import datetime
import traceback
import shutil
import importlib

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import ui_elements
except ImportError:
    # Fallback if ui_elements is not available
    ui_elements = None

# =============================================================================
# CONFLICT ANALYSIS SYSTEM
# =============================================================================

class ConflictType:
    """Enumeration of conflict types."""
    REPOSITORY_SETUP = "repository_setup"  # Initial setup conflicts
    MERGE_CONFLICT = "merge_conflict"       # Git merge conflicts during sync
    DIVERGED_BRANCHES = "diverged_branches" # Branches have diverged

class FileConflictInfo:
    """Information about a conflicted file."""
    def __init__(self, file_path: str, conflict_type: str):
        self.file_path = file_path
        self.conflict_type = conflict_type  # 'modified', 'added', 'deleted', 'both_modified'
        self.local_content = ""
        self.remote_content = ""
        self.has_content_conflict = False
        self.is_binary = False

class ConflictAnalysis:
    """Comprehensive analysis of conflicts."""
    def __init__(self):
        self.conflict_type = ""
        self.has_conflicts = False
        self.conflicted_files: List[FileConflictInfo] = []
        self.local_only_files: List[str] = []
        self.remote_only_files: List[str] = []
        self.identical_files: List[str] = []
        self.different_files: List[str] = []
        self.summary = ""

def run_git_command(command: str, cwd: Optional[str] = None) -> Tuple[str, str, int]:
    """Run a git command and return output, error, and return code."""
    try:
        # Handle cwd parameter properly - subprocess.run expects str or None, not just any Optional
        working_dir = cwd if cwd is not None else None
        
        # Split command into parts, being careful with quotes
        import shlex
        command_parts = shlex.split(command)
        
        process = subprocess.run(
            command_parts,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=30
        )
        return process.stdout, process.stderr, process.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timed out", 1
    except Exception as e:
        return "", str(e), 1

def analyze_repository_conflicts(vault_path: str) -> ConflictAnalysis:
    """
    Analyze conflicts between local and remote repositories.
    Works for both setup conflicts and merge conflicts.
    """
    analysis = ConflictAnalysis()
    
    try:
        # Check if we're in a git repository
        _, _, rc = run_git_command("git status", cwd=vault_path)
        if rc != 0:
            analysis.summary = "Not a git repository"
            return analysis
        
        # Check for active merge conflicts first
        conflicted_files_out, _, rc = run_git_command("git diff --name-only --diff-filter=U", cwd=vault_path)
        if rc == 0 and conflicted_files_out.strip():
            analysis.conflict_type = ConflictType.MERGE_CONFLICT
            analysis.has_conflicts = True
            
            for file_path in conflicted_files_out.strip().split('\n'):
                if file_path.strip():
                    conflict_info = FileConflictInfo(file_path.strip(), 'both_modified')
                    conflict_info.has_content_conflict = True
                    analysis.conflicted_files.append(conflict_info)
            
            analysis.summary = f"Active merge conflicts in {len(analysis.conflicted_files)} files"
            return analysis
        
        # Check for setup-type conflicts (local vs remote differences)
        # Get list of all files (local and remote)
        local_files = get_local_files(vault_path)
        remote_files = get_remote_files(vault_path)
        
        if not local_files and not remote_files:
            analysis.summary = "Both repositories are empty"
            return analysis
        
        all_files = set(local_files) | set(remote_files)
        
        for file_path in all_files:
            if file_path in local_files and file_path in remote_files:
                # File exists in both - check if content differs
                if files_differ(vault_path, file_path):
                    conflict_info = FileConflictInfo(file_path, 'both_modified')
                    conflict_info.has_content_conflict = True
                    conflict_info.local_content = get_file_content(vault_path, file_path, "local")
                    conflict_info.remote_content = get_file_content(vault_path, file_path, "remote")
                    analysis.conflicted_files.append(conflict_info)
                    analysis.different_files.append(file_path)
                else:
                    # Files are identical, no conflict
                    analysis.identical_files.append(file_path)
            elif file_path in local_files:
                analysis.local_only_files.append(file_path)
            else:
                analysis.remote_only_files.append(file_path)
        
        # Determine conflict type and summary
        if analysis.conflicted_files or (analysis.local_only_files and analysis.remote_only_files):
            analysis.conflict_type = ConflictType.REPOSITORY_SETUP
            analysis.has_conflicts = True
            
            conflict_count = len(analysis.conflicted_files)
            local_only_count = len(analysis.local_only_files)
            remote_only_count = len(analysis.remote_only_files)
            
            summary_parts = []
            if conflict_count > 0:
                summary_parts.append(f"{conflict_count} files with content conflicts")
            if local_only_count > 0:
                summary_parts.append(f"{local_only_count} local-only files")
            if remote_only_count > 0:
                summary_parts.append(f"{remote_only_count} remote-only files")
            
            analysis.summary = "; ".join(summary_parts)
            
            # Add detailed file list to summary for better user visibility
            if local_only_count > 0:
                analysis.summary += f"\n\nLocal-only files:"
                for i, file_path in enumerate(analysis.local_only_files[:10]):  # Show first 10
                    analysis.summary += f"\n• {file_path}"
                if local_only_count > 10:
                    analysis.summary += f"\n• ... and {local_only_count - 10} more"
            
            if remote_only_count > 0:
                analysis.summary += f"\n\nRemote-only files:"
                for i, file_path in enumerate(analysis.remote_only_files[:10]):  # Show first 10
                    analysis.summary += f"\n• {file_path}"
                if remote_only_count > 10:
                    analysis.summary += f"\n• ... and {remote_only_count - 10} more"
                    
        else:
            analysis.summary = "No conflicts detected"
        
        return analysis
        
    except Exception as e:
        analysis.summary = f"Error analyzing conflicts: {e}"
        return analysis

def get_local_files(vault_path: str) -> List[str]:
    """Get list of files in local repository (excluding .git)."""
    files = []
    try:
        for root, dirs, filenames in os.walk(vault_path):
            # Skip .git directory
            if '.git' in root:
                continue
            for filename in filenames:
                # Skip common non-content files
                if filename.startswith('.') and filename not in ['.gitignore']:
                    continue
                rel_path = os.path.relpath(os.path.join(root, filename), vault_path)
                files.append(rel_path.replace('\\', '/'))  # Normalize path separators
    except Exception:
        pass
    return files

def get_remote_files(vault_path: str) -> List[str]:
    """Get list of files in remote repository."""
    try:
        # First fetch remote refs
        run_git_command("git fetch origin", cwd=vault_path)
        
        # Try main branch first, then master
        for branch in ["origin/main", "origin/master"]:
            out, err, rc = run_git_command(f"git ls-tree -r --name-only {branch}", cwd=vault_path)
            if rc == 0 and out.strip():
                return [f.strip() for f in out.strip().split('\n') if f.strip()]
    except Exception:
        pass
    return []

def files_differ(vault_path: str, file_path: str) -> bool:
    """Check if a file differs between local and remote versions."""
    try:
        # Get content from both versions
        local_content = get_file_content(vault_path, file_path, "local")
        remote_content = get_file_content(vault_path, file_path, "remote")
        
        # Compare content directly
        return local_content.strip() != remote_content.strip()
    except Exception:
        return False

def get_file_content(vault_path: str, file_path: str, version: str = "local") -> str:
    """Get content of a file from local or remote version."""
    try:
        if version == "local":
            full_path = os.path.join(vault_path, file_path)
            if os.path.exists(full_path):
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
        elif version == "remote":
            # Try main branch first, then master
            for branch in ["origin/main", "origin/master"]:
                out, err, rc = run_git_command(f"git show {branch}:{file_path}", cwd=vault_path)
                if rc == 0:
                    return out
    except Exception:
        pass
    return ""

# =============================================================================
# STAGE 1: HIGH-LEVEL CONFLICT RESOLUTION DIALOG
# =============================================================================

class Stage1ConflictDialog:
    """Stage 1 conflict resolution - high-level strategy selection."""
    
    def __init__(self, parent, analysis: ConflictAnalysis):
        self.parent = parent
        self.analysis = analysis
        self.result = None
        self.dialog: Optional[tk.Toplevel] = None
        
    def show(self) -> Optional[str]:
        """Show the dialog and return user's choice."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Conflict Resolution - Strategy Selection")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        self.dialog.resizable(True, True)
        
        # Set dialog size - increased size for better readability
        self.dialog.update_idletasks()
        width, height = 800, 750  # Increased from 750x700
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
        self.dialog.minsize(700, 600)  # Increased minimum size
        
        # Force dialog to appear and initialize properly
        self.dialog.update()
        self.dialog.lift()
        self.dialog.focus_force()
        
        self._create_widgets()
        
        # Ensure dialog is fully rendered before showing
        self.dialog.update_idletasks()
        
        # Wait for user response
        self.parent.wait_window(self.dialog)
        return self.result
    
    def _create_widgets(self):
        """Create the dialog widgets."""
        # Configure colors
        bg_primary = "#FAFBFC"
        bg_card = "#FFFFFF"
        text_primary = "#1E293B"
        text_secondary = "#475569"
        accent_color = "#6366F1"
        
        if self.dialog is not None:
            self.dialog.configure(bg=bg_primary)
        
        # Main container with scrollable frame
        if self.dialog is not None:
            canvas = tk.Canvas(self.dialog, bg=bg_primary, highlightthickness=0)
            scrollbar = tk.Scrollbar(self.dialog, orient="vertical", command=canvas.yview)
            scrollable_frame = tk.Frame(canvas, bg=bg_primary)
        
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # Show/hide scrollbar based on content size
            if canvas.bbox("all")[3] > canvas.winfo_height():
                scrollbar.pack(side="right", fill="y", padx=(0, 20), pady=20)
            else:
                scrollbar.pack_forget()
        
        scrollable_frame.bind("<Configure>", on_frame_configure)
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack scrollable components
        canvas.pack(side="left", fill="both", expand=True, padx=20, pady=20)
        
        # Create main content in scrollable frame
        main_frame = tk.Frame(scrollable_frame, bg=bg_primary)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header_frame = tk.Frame(main_frame, bg=bg_primary)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = tk.Label(
            header_frame,
            text="⚠️ Conflict Resolution Required",
            font=("Arial", 16, "bold"),
            bg=bg_primary,
            fg=text_primary
        )
        title_label.pack()
        
        # Conflict summary card
        summary_card = tk.Frame(main_frame, bg=bg_card, relief=tk.RAISED, borderwidth=1)
        summary_card.pack(fill=tk.X, pady=(0, 20))
        
        summary_inner = tk.Frame(summary_card, bg=bg_card)
        summary_inner.pack(fill=tk.X, padx=20, pady=15)
        
        summary_title = tk.Label(
            summary_inner,
            text="Conflict Summary:",
            font=("Arial", 12, "bold"),
            bg=bg_card,
            fg=text_primary
        )
        summary_title.pack(anchor=tk.W)
        
        summary_text = tk.Label(
            summary_inner,
            text=self.analysis.summary,
            font=("Arial", 11),
            bg=bg_card,
            fg=text_secondary,
            wraplength=650,
            justify=tk.LEFT
        )
        summary_text.pack(anchor=tk.W, pady=(5, 0))
        
        # File details
        if self.analysis.conflicted_files:
            files_text = f"Conflicted files ({len(self.analysis.conflicted_files)}):\n"
            for i, file_info in enumerate(self.analysis.conflicted_files[:5]):  # Show up to 5 files
                files_text += f"• {file_info.file_path}\n"
            if len(self.analysis.conflicted_files) > 5:
                files_text += f"• ... and {len(self.analysis.conflicted_files) - 5} more files"
            
            details_label = tk.Label(
                summary_inner,
                text=files_text,
                font=("Arial", 9),
                bg=bg_card,
                fg=text_secondary,
                wraplength=700,
                justify=tk.LEFT,
                anchor="w"
            )
            details_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Strategy selection
        strategy_frame = tk.Frame(main_frame, bg=bg_card, relief=tk.RAISED, borderwidth=1)
        strategy_frame.pack(fill=tk.BOTH, expand=True)
        
        strategy_inner = tk.Frame(strategy_frame, bg=bg_card)
        strategy_inner.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        strategy_title = tk.Label(
            strategy_inner,
            text="Choose Resolution Strategy:",
            font=("Arial", 12, "bold"),
            bg=bg_card,
            fg=text_primary
        )
        strategy_title.pack(anchor=tk.W, pady=(0, 15))
        
        # Strategy buttons
        self._create_strategy_button(
            strategy_inner, 
            "🔄 Smart Merge (Recommended)",
            "Automatically merges non-conflicting files and prompts for manual resolution of conflicts",
            "smart_merge",
            is_primary=True
        )
        
        self._create_strategy_button(
            strategy_inner,
            "📁 Keep Local Only",
            "Keeps all local files and overwrites remote repository",
            "keep_local"
        )
        
        self._create_strategy_button(
            strategy_inner,
            "🌐 Keep Remote Only", 
            "Downloads all remote files and overwrites local changes",
            "keep_remote"
        )
        
        # Cancel button
        cancel_frame = tk.Frame(strategy_inner, bg=bg_card)
        cancel_frame.pack(fill=tk.X, pady=(15, 0))
        
        cancel_btn = tk.Button(
            cancel_frame,
            text="Cancel",
            command=self._cancel,
            font=("Arial", 10),
            bg=bg_card,
            fg=text_secondary,
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=8
        )
        cancel_btn.pack(side=tk.RIGHT)
        
        # Bind mousewheel scrolling to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # Bind mousewheel for different platforms
        def bind_mousewheel(widget):
            # Windows and MacOS
            widget.bind("<MouseWheel>", _on_mousewheel)
            # Linux
            widget.bind("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
            widget.bind("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))
        
        bind_mousewheel(canvas)
        bind_mousewheel(self.dialog)
    
    def _create_strategy_button(self, parent, title, description, choice, is_primary=False):
        """Create a strategy selection button."""
        bg_card = "#FFFFFF"
        text_primary = "#1E293B"
        text_secondary = "#475569"
        accent_color = "#6366F1"
        
        btn_frame = tk.Frame(parent, bg=bg_card)
        btn_frame.pack(fill=tk.X, pady=(0, 15))
        
        if is_primary:
            btn_bg = accent_color
            btn_fg = "#FFFFFF"
            btn_active_bg = "#4F46E5"
        else:
            btn_bg = bg_card
            btn_fg = accent_color
            btn_active_bg = "#F1F5F9"
        
        btn = tk.Button(
            btn_frame,
            text=title,
            command=lambda: self._set_choice(choice),
            font=("Arial", 11, "bold" if is_primary else "normal"),
            bg=btn_bg,
            fg=btn_fg,
            activebackground=btn_active_bg,
            relief=tk.SOLID if not is_primary else tk.FLAT,
            borderwidth=1 if not is_primary else 0,
            cursor="hand2",
            padx=20,
            pady=15
        )
        btn.pack(fill=tk.X)
        
        desc_label = tk.Label(
            btn_frame,
            text=description,
            font=("Arial", 9),
            bg=bg_card,
            fg=text_secondary,
            wraplength=650,
            justify=tk.LEFT
        )
        desc_label.pack(anchor=tk.W, pady=(5, 0))
    
    def _set_choice(self, choice):
        """Set the user's choice and close dialog."""
        self.result = choice
        if self.dialog is not None:
            self.dialog.destroy()
    
    def _cancel(self):
        """Cancel the dialog."""
        self.result = None
        if self.dialog is not None:
            self.dialog.destroy()

# =============================================================================
# STAGE 2: FILE-BY-FILE CONFLICT RESOLUTION
# =============================================================================

class Stage2ConflictDialog:
    """Stage 2 conflict resolution - file-by-file resolution."""
    
    def __init__(self, parent, conflicted_files: List[FileConflictInfo], vault_path: str):
        self.parent = parent
        self.conflicted_files = conflicted_files
        self.vault_path = vault_path
        self.current_file_index = 0
        self.results = {}  # file_path -> choice
        self.dialog: Optional[tk.Toplevel] = None
        
    def show(self) -> Dict[str, str]:
        """Show the dialog and return resolution choices for each file."""
        if not self.conflicted_files:
            return {}
        
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Conflict Resolution - File by File")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        self.dialog.resizable(True, True)
        
        # Set dialog size - larger size for better content viewing
        self.dialog.update_idletasks()
        width, height = 1000, 800  # Increased from 950x750
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
        self.dialog.minsize(900, 700)  # Increased minimum size
        
        # Force dialog to appear and initialize properly
        self.dialog.update()
        self.dialog.lift()
        self.dialog.focus_force()
        
        self._create_widgets()
        self._load_current_file()
        
        # Ensure dialog is fully rendered before showing
        self.dialog.update_idletasks()
        
        # Wait for user response
        self.parent.wait_window(self.dialog)
        return self.results
    
    def _create_widgets(self):
        """Create the dialog widgets."""
        bg_primary = "#FAFBFC"
        bg_card = "#FFFFFF"
        
        if self.dialog is not None:
            self.dialog.configure(bg=bg_primary)
        
        # Main container
        if self.dialog is not None:
            main_frame = tk.Frame(self.dialog, bg=bg_primary)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Header with progress
        self._create_header(main_frame)
        
        # File info section
        self._create_file_info_section(main_frame)
        
        # Content comparison section
        self._create_content_section(main_frame)
        
        # Action buttons
        self._create_action_buttons(main_frame)
        
        # Navigation buttons
        self._create_navigation_buttons(main_frame)
    
    def _create_header(self, parent):
        """Create header with progress information."""
        bg_primary = "#FAFBFC"
        text_primary = "#1E293B"
        
        header_frame = tk.Frame(parent, bg=bg_primary)
        header_frame.pack(fill=tk.X, pady=(0, 15))
        
        title_label = tk.Label(
            header_frame,
            text="File Conflict Resolution",
            font=("Arial", 16, "bold"),
            bg=bg_primary,
            fg=text_primary
        )
        title_label.pack(side=tk.LEFT)
        
        self.progress_label = tk.Label(
            header_frame,
            text="",
            font=("Arial", 12),
            bg=bg_primary,
            fg=text_primary
        )
        self.progress_label.pack(side=tk.RIGHT)
    
    def _create_file_info_section(self, parent):
        """Create file information section."""
        bg_card = "#FFFFFF"
        text_primary = "#1E293B"
        text_secondary = "#475569"
        
        info_frame = tk.Frame(parent, bg=bg_card, relief=tk.RAISED, borderwidth=1)
        info_frame.pack(fill=tk.X, pady=(0, 15))
        
        info_inner = tk.Frame(info_frame, bg=bg_card)
        info_inner.pack(fill=tk.X, padx=15, pady=12)
        
        self.file_path_label = tk.Label(
            info_inner,
            text="",
            font=("Arial", 12, "bold"),
            bg=bg_card,
            fg=text_primary
        )
        self.file_path_label.pack(anchor=tk.W)
        
        self.conflict_type_label = tk.Label(
            info_inner,
            text="",
            font=("Arial", 10),
            bg=bg_card,
            fg=text_secondary
        )
        self.conflict_type_label.pack(anchor=tk.W, pady=(2, 0))
    
    def _create_content_section(self, parent):
        """Create content comparison section."""
        bg_card = "#FFFFFF"
        
        content_frame = tk.Frame(parent, bg=bg_card, relief=tk.RAISED, borderwidth=1)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(content_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Local content tab
        local_frame = tk.Frame(self.notebook, bg=bg_card)
        self.notebook.add(local_frame, text="Local Version")
        
        self.local_text = tk.Text(
            local_frame,
            wrap=tk.WORD,
            font=("Courier", 10),
            bg="#F8F9FA",
            fg="#1E293B",
            relief=tk.FLAT,
            borderwidth=1,
            state=tk.DISABLED  # Make read-only as requested
        )
        local_scrollbar = tk.Scrollbar(local_frame, orient=tk.VERTICAL, command=self.local_text.yview)
        self.local_text.configure(yscrollcommand=local_scrollbar.set)
        
        self.local_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        local_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Remote content tab
        remote_frame = tk.Frame(self.notebook, bg=bg_card)
        self.notebook.add(remote_frame, text="Remote Version")
        
        self.remote_text = tk.Text(
            remote_frame,
            wrap=tk.WORD,
            font=("Courier", 10),
            bg="#F8F9FA",
            fg="#1E293B",
            relief=tk.FLAT,
            borderwidth=1,
            state=tk.DISABLED  # Make read-only as requested
        )
        remote_scrollbar = tk.Scrollbar(remote_frame, orient=tk.VERTICAL, command=self.remote_text.yview)
        self.remote_text.configure(yscrollcommand=remote_scrollbar.set)
        
        self.remote_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        remote_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Diff view tab
        diff_frame = tk.Frame(self.notebook, bg=bg_card)
        self.notebook.add(diff_frame, text="Differences")
        
        self.diff_text = tk.Text(
            diff_frame,
            wrap=tk.WORD,
            font=("Courier", 9),
            bg="#F8F9FA",
            fg="#1E293B",
            relief=tk.FLAT,
            borderwidth=1,
            state=tk.DISABLED  # Make read-only as requested
        )
        diff_scrollbar = tk.Scrollbar(diff_frame, orient=tk.VERTICAL, command=self.diff_text.yview)
        self.diff_text.configure(yscrollcommand=diff_scrollbar.set)
        
        self.diff_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        diff_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _create_action_buttons(self, parent):
        """Create action buttons for conflict resolution."""
        bg_card = "#FFFFFF"
        accent_color = "#6366F1"
        success_color = "#10B981"
        warning_color = "#F59E0B"
        
        action_frame = tk.Frame(parent, bg=bg_card, relief=tk.RAISED, borderwidth=1)
        action_frame.pack(fill=tk.X, pady=(0, 15))
        
        action_inner = tk.Frame(action_frame, bg=bg_card)
        action_inner.pack(fill=tk.X, padx=15, pady=15)
        
        action_title = tk.Label(
            action_inner,
            text="Choose resolution for this file:",
            font=("Arial", 11, "bold"),
            bg=bg_card,
            fg="#1E293B"
        )
        action_title.pack(anchor=tk.W, pady=(0, 10))
        
        # Create button grid with 4 options as requested
        button_grid = tk.Frame(action_inner, bg=bg_card)
        button_grid.pack(fill=tk.X)
        
        # Row 1: Manual merge (recommended) and Auto merge
        row1 = tk.Frame(button_grid, bg=bg_card)
        row1.pack(fill=tk.X, pady=(0, 8))
        
        manual_merge_btn = tk.Button(
            row1,
            text="✏️ Manual Merge (Recommended)",
            command=lambda: self._resolve_file("manual_merge"),
            font=("Arial", 10, "bold"),
            bg=warning_color,
            fg="#FFFFFF",
            relief=tk.FLAT,
            cursor="hand2",
            padx=15,
            pady=10
        )
        manual_merge_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        auto_merge_btn = tk.Button(
            row1,
            text="🔄 Auto Merge",
            command=lambda: self._resolve_file("auto_merge"),
            font=("Arial", 10),
            bg=accent_color,
            fg="#FFFFFF",
            relief=tk.FLAT,
            cursor="hand2",
            padx=15,
            pady=10
        )
        auto_merge_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # Row 2: Keep local and Keep remote
        row2 = tk.Frame(button_grid, bg=bg_card)
        row2.pack(fill=tk.X)
        
        keep_local_btn = tk.Button(
            row2,
            text="📁 Keep Local Version",
            command=lambda: self._resolve_file("keep_local"),
            font=("Arial", 10),
            bg=bg_card,
            fg=accent_color,
            relief=tk.SOLID,
            borderwidth=1,
            cursor="hand2",
            padx=15,
            pady=10
        )
        keep_local_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        keep_remote_btn = tk.Button(
            row2,
            text="🌐 Keep Remote Version",
            command=lambda: self._resolve_file("keep_remote"),
            font=("Arial", 10),
            bg=bg_card,
            fg=accent_color,
            relief=tk.SOLID,
            borderwidth=1,
            cursor="hand2",
            padx=15,
            pady=10
        )
        keep_remote_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
    
    def _create_navigation_buttons(self, parent):
        """Create navigation buttons."""
        bg_primary = "#FAFBFC"
        text_secondary = "#475569"
        
        nav_frame = tk.Frame(parent, bg=bg_primary)
        nav_frame.pack(fill=tk.X)
        
        self.prev_btn = tk.Button(
            nav_frame,
            text="← Previous",
            command=self._previous_file,
            font=("Arial", 10),
            bg=bg_primary,
            fg=text_secondary,
            relief=tk.FLAT,
            cursor="hand2",
            padx=15,
            pady=8
        )
        self.prev_btn.pack(side=tk.LEFT)
        
        self.next_btn = tk.Button(
            nav_frame,
            text="Next →",
            command=self._next_file,
            font=("Arial", 10),
            bg=bg_primary,
            fg=text_secondary,
            relief=tk.FLAT,
            cursor="hand2",
            padx=15,
            pady=8
        )
        self.next_btn.pack(side=tk.LEFT, padx=(10, 0))
        
        finish_btn = tk.Button(
            nav_frame,
            text="Finish Resolution",
            command=self._finish_resolution,
            font=("Arial", 10, "bold"),
            bg="#10B981",
            fg="#FFFFFF",
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=8
        )
        finish_btn.pack(side=tk.RIGHT)
        
        cancel_btn = tk.Button(
            nav_frame,
            text="Cancel",
            command=self._cancel,
            font=("Arial", 10),
            bg=bg_primary,
            fg=text_secondary,
            relief=tk.FLAT,
            cursor="hand2",
            padx=15,
            pady=8
        )
        cancel_btn.pack(side=tk.RIGHT, padx=(0, 10))
    
    def _load_current_file(self):
        """Load content for the current file."""
        if self.current_file_index >= len(self.conflicted_files):
            return
        
        current_file = self.conflicted_files[self.current_file_index]
        
        # Update progress
        self.progress_label.config(
            text=f"File {self.current_file_index + 1} of {len(self.conflicted_files)}"
        )
        
        # Update file info
        self.file_path_label.config(text=f"📄 {current_file.file_path}")
        self.conflict_type_label.config(text=f"Conflict type: {current_file.conflict_type}")
        
        # Load file contents
        local_content = get_file_content(self.vault_path, current_file.file_path, "local")
        remote_content = get_file_content(self.vault_path, current_file.file_path, "remote")
        
        # Update text widgets (temporarily enable for editing)
        self.local_text.config(state=tk.NORMAL)
        self.local_text.delete(1.0, tk.END)
        self.local_text.insert(1.0, local_content if local_content else "[File not found locally]")
        self.local_text.config(state=tk.DISABLED)  # Make read-only again
        
        self.remote_text.config(state=tk.NORMAL)
        self.remote_text.delete(1.0, tk.END)
        self.remote_text.insert(1.0, remote_content if remote_content else "[File not found in remote]")
        self.remote_text.config(state=tk.DISABLED)  # Make read-only again
        
        # Generate diff
        diff_content = self._generate_diff(local_content, remote_content, current_file.file_path)
        self.diff_text.config(state=tk.NORMAL)
        self.diff_text.delete(1.0, tk.END)
        self.diff_text.insert(1.0, diff_content)
        self.diff_text.config(state=tk.DISABLED)  # Make read-only again
        
        # Update navigation buttons
        self.prev_btn.config(state=tk.NORMAL if self.current_file_index > 0 else tk.DISABLED)
        self.next_btn.config(state=tk.NORMAL if self.current_file_index < len(self.conflicted_files) - 1 else tk.DISABLED)
    
    def _generate_diff(self, local_content: str, remote_content: str, filename: str) -> str:
        """Generate a readable diff between local and remote content."""
        try:
            local_lines = local_content.splitlines(keepends=True)
            remote_lines = remote_content.splitlines(keepends=True)
            
            diff = list(difflib.unified_diff(
                local_lines,
                remote_lines,
                fromfile=f"Local: {filename}",
                tofile=f"Remote: {filename}",
                lineterm=""
            ))
            
            if not diff:
                return "No differences found between local and remote versions."
            
            return "".join(diff)
        except Exception as e:
            return f"Error generating diff: {e}"
    
    def _resolve_file(self, resolution: str):
        """Resolve the current file with the given resolution."""
        if self.current_file_index >= len(self.conflicted_files):
            return
        
        current_file = self.conflicted_files[self.current_file_index]
        
        # Handle different resolution types
        if resolution == "manual_merge":
            self._open_manual_merge_editor(current_file)
        elif resolution == "auto_merge":
            self._perform_auto_merge(current_file)
        elif resolution == "keep_local":
            self._apply_keep_local(current_file)
        elif resolution == "keep_remote":
            self._apply_keep_remote(current_file)
        
        # Mark file as resolved
        self.results[current_file.file_path] = resolution
    
    def _open_manual_merge_editor(self, file_info: FileConflictInfo):
        """Open enhanced in-dialog manual merge editor."""
        # Create the manual merge dialog
        merge_dialog = tk.Toplevel(self.dialog)
        merge_dialog.title(f"Manual Merge - {file_info.file_path}")
        merge_dialog.transient(self.dialog)
        merge_dialog.grab_set()
        merge_dialog.resizable(True, True)
        
        # Set dialog size
        width, height = 1000, 700
        x = (merge_dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (merge_dialog.winfo_screenheight() // 2) - (height // 2)
        merge_dialog.geometry(f"{width}x{height}+{x}+{y}")
        merge_dialog.minsize(800, 600)
        
        # Colors
        bg_primary = "#FAFBFC"
        bg_card = "#FFFFFF"
        text_primary = "#1E293B"
        accent_color = "#6366F1"
        success_color = "#10B981"
        
        merge_dialog.configure(bg=bg_primary)
        
        # Main container
        main_frame = tk.Frame(merge_dialog, bg=bg_primary)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header
        header_frame = tk.Frame(main_frame, bg=bg_primary)
        header_frame.pack(fill=tk.X, pady=(0, 15))
        
        title_label = tk.Label(
            header_frame,
            text=f"✏️ Manual Merge Editor - {file_info.file_path}",
            font=("Arial", 14, "bold"),
            bg=bg_primary,
            fg=text_primary
        )
        title_label.pack(side=tk.LEFT)
        
        # Get current content
        local_content = get_file_content(self.vault_path, file_info.file_path, "local")
        remote_content = get_file_content(self.vault_path, file_info.file_path, "remote")
        
        # Create a PanedWindow for three-column layout
        paned_window = tk.PanedWindow(main_frame, orient=tk.HORIZONTAL, bg=bg_primary)
        paned_window.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Left column - Local content (read-only)
        local_frame = tk.Frame(paned_window, bg=bg_card, relief=tk.RAISED, borderwidth=1)
        local_label = tk.Label(local_frame, text="📁 Local Version (Read-Only)", 
                             font=("Arial", 10, "bold"), bg=bg_card, fg=text_primary)
        local_label.pack(pady=5)
        
        local_text = tk.Text(
            local_frame,
            wrap=tk.WORD,
            font=("Courier", 9),
            bg="#F8F9FA",
            fg="#1E293B",
            relief=tk.FLAT,
            borderwidth=1,
            state=tk.DISABLED
        )
        local_scrollbar = tk.Scrollbar(local_frame, orient=tk.VERTICAL, command=local_text.yview)
        local_text.configure(yscrollcommand=local_scrollbar.set)
        
        local_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        local_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # Insert local content
        local_text.config(state=tk.NORMAL)
        local_text.insert(1.0, local_content if local_content else "[No local content]")
        local_text.config(state=tk.DISABLED)
        
        # Middle column - Merged content (editable)
        merge_frame = tk.Frame(paned_window, bg=bg_card, relief=tk.RAISED, borderwidth=1)
        merge_label = tk.Label(merge_frame, text="✏️ Merged Version (Editable)", 
                             font=("Arial", 10, "bold"), bg=bg_card, fg=text_primary)
        merge_label.pack(pady=5)
        
        merge_text = tk.Text(
            merge_frame,
            wrap=tk.WORD,
            font=("Courier", 9),
            bg="#FFFFFF",
            fg="#1E293B",
            relief=tk.FLAT,
            borderwidth=1,
            insertbackground="#6366F1",
            selectbackground="#E0E7FF"
        )
        merge_scrollbar = tk.Scrollbar(merge_frame, orient=tk.VERTICAL, command=merge_text.yview)
        merge_text.configure(yscrollcommand=merge_scrollbar.set)
        
        merge_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        merge_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # Start with local content as base for editing
        merge_text.insert(1.0, local_content if local_content else "")
        
        # Right column - Remote content (read-only)
        remote_frame = tk.Frame(paned_window, bg=bg_card, relief=tk.RAISED, borderwidth=1)
        remote_label = tk.Label(remote_frame, text="🌐 Remote Version (Read-Only)", 
                              font=("Arial", 10, "bold"), bg=bg_card, fg=text_primary)
        remote_label.pack(pady=5)
        
        remote_text = tk.Text(
            remote_frame,
            wrap=tk.WORD,
            font=("Courier", 9),
            bg="#F8F9FA",
            fg="#1E293B",
            relief=tk.FLAT,
            borderwidth=1,
            state=tk.DISABLED
        )
        remote_scrollbar = tk.Scrollbar(remote_frame, orient=tk.VERTICAL, command=remote_text.yview)
        remote_text.configure(yscrollcommand=remote_scrollbar.set)
        
        remote_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        remote_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # Insert remote content
        remote_text.config(state=tk.NORMAL)
        remote_text.insert(1.0, remote_content if remote_content else "[No remote content]")
        remote_text.config(state=tk.DISABLED)
        
        # Add panes to the PanedWindow
        paned_window.add(local_frame, minsize=250)
        paned_window.add(merge_frame, minsize=300)
        paned_window.add(remote_frame, minsize=250)
        
        # Editor controls frame
        controls_frame = tk.Frame(main_frame, bg=bg_primary)
        controls_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Helper buttons
        helper_frame = tk.Frame(controls_frame, bg=bg_primary)
        helper_frame.pack(side=tk.LEFT)
        
        copy_local_btn = tk.Button(
            helper_frame,
            text="📁 Copy Local →",
            command=lambda: self._copy_content_to_editor(merge_text, local_content),
            font=("Arial", 9),
            bg=bg_card,
            fg=accent_color,
            relief=tk.SOLID,
            borderwidth=1,
            cursor="hand2",
            padx=10,
            pady=5
        )
        copy_local_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        copy_remote_btn = tk.Button(
            helper_frame,
            text="← 🌐 Copy Remote",
            command=lambda: self._copy_content_to_editor(merge_text, remote_content),
            font=("Arial", 9),
            bg=bg_card,
            fg=accent_color,
            relief=tk.SOLID,
            borderwidth=1,
            cursor="hand2",
            padx=10,
            pady=5
        )
        copy_remote_btn.pack(side=tk.LEFT, padx=(5, 0))
        
        # Open in external editor button
        external_btn = tk.Button(
            controls_frame,
            text="🔧 Open in External Editor",
            command=lambda: self._open_in_external_editor(file_info, merge_text),
            font=("Arial", 9),
            bg=bg_card,
            fg=accent_color,
            relief=tk.SOLID,
            borderwidth=1,
            cursor="hand2",
            padx=10,
            pady=5
        )
        external_btn.pack(side=tk.LEFT, padx=(20, 0))
        
        # Action buttons
        action_frame = tk.Frame(main_frame, bg=bg_primary)
        action_frame.pack(fill=tk.X)
        
        cancel_btn = tk.Button(
            action_frame,
            text="Cancel",
            command=lambda: merge_dialog.destroy(),
            font=("Arial", 10),
            bg=bg_primary,
            fg="#6B7280",
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=8
        )
        cancel_btn.pack(side=tk.LEFT)
        
        save_btn = tk.Button(
            action_frame,
            text="💾 Save & Apply Merge",
            command=lambda: self._save_merged_content(merge_dialog, merge_text, file_info),
            font=("Arial", 10, "bold"),
            bg=success_color,
            fg="#FFFFFF",
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=8
        )
        save_btn.pack(side=tk.RIGHT)
        
        # Add basic editor functionality
        self._add_editor_shortcuts(merge_text)
        
        # Focus on the merge editor
        merge_text.focus_set()
    
    def _copy_content_to_editor(self, text_widget, content):
        """Copy content to the merge editor."""
        text_widget.delete(1.0, tk.END)
        text_widget.insert(1.0, content if content else "")
    
    def _open_in_external_editor(self, file_info: FileConflictInfo, merge_text):
        """Open the file in external editor and refresh the merge editor."""
        try:
            file_path = os.path.join(self.vault_path, file_info.file_path)
            
            # Get available editors
            editors = self._get_available_editors()
            
            if not editors:
                messagebox.showerror(
                    "No Editors Found",
                    "No suitable text editors were found on your system.\n"
                    "Please install a text editor like VS Code, gedit, or nano."
                )
                return
            
            # If only one editor, use it directly
            if len(editors) == 1:
                selected_editor = editors[0]
            else:
                # Let user choose editor
                selected_editor = self._show_editor_selection_dialog(editors)
                if not selected_editor:
                    return
            
            # Save current content to file before opening
            current_content = merge_text.get(1.0, tk.END + "-1c")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(current_content)
            
            # Open in selected editor
            if selected_editor['command']:
                subprocess.run(selected_editor['command'] + [file_path], check=False)
            
            # Show dialog to refresh after editing
            result = messagebox.askyesno(
                "External Editor",
                f"The file has been opened in {selected_editor['name']}.\n\n"
                "After you finish editing and save the file, click 'Yes' to refresh the content in the merge editor.\n"
                "Click 'No' to continue without refreshing."
            )
            
            if result:
                # Refresh the merge editor with the updated file content
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        updated_content = f.read()
                    merge_text.delete(1.0, tk.END)
                    merge_text.insert(1.0, updated_content)
                except Exception as e:
                    messagebox.showerror("Error", f"Could not refresh content: {e}")
        
        except Exception as e:
            messagebox.showerror(
                "Error Opening External Editor",
                f"Could not open external editor:\n{e}"
            )
    
    def _get_available_editors(self):
        """Get list of available text editors on the system."""
        editors = []
        
        # Define common editors with their commands and display names
        editor_candidates = [
            {'name': 'Visual Studio Code', 'command': ['code'], 'check_cmd': 'code'},
            {'name': 'Sublime Text', 'command': ['subl'], 'check_cmd': 'subl'},
            {'name': 'Atom', 'command': ['atom'], 'check_cmd': 'atom'},
            {'name': 'Gedit', 'command': ['gedit'], 'check_cmd': 'gedit'},
            {'name': 'Kate', 'command': ['kate'], 'check_cmd': 'kate'},
            {'name': 'Pluma', 'command': ['pluma'], 'check_cmd': 'pluma'},
            {'name': 'Mousepad', 'command': ['mousepad'], 'check_cmd': 'mousepad'},
            {'name': 'Leafpad', 'command': ['leafpad'], 'check_cmd': 'leafpad'},
            {'name': 'Xed', 'command': ['xed'], 'check_cmd': 'xed'},
            {'name': 'Nano', 'command': ['gnome-terminal', '--', 'nano'], 'check_cmd': 'nano'},
            {'name': 'Vim', 'command': ['gnome-terminal', '--', 'vim'], 'check_cmd': 'vim'},
        ]
        
        for editor in editor_candidates:
            try:
                # Check if editor is available
                subprocess.run(['which', editor['check_cmd']], 
                             capture_output=True, check=True)
                editors.append(editor)
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        
        return editors
    
    def _show_editor_selection_dialog(self, editors):
        """Show dialog to select external editor."""
        selection_dialog = tk.Toplevel(self.dialog)
        selection_dialog.title("Select Text Editor")
        selection_dialog.transient(self.dialog)
        selection_dialog.grab_set()
        selection_dialog.resizable(False, False)
        
        # Center the dialog
        width, height = 400, 300
        x = (selection_dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (selection_dialog.winfo_screenheight() // 2) - (height // 2)
        selection_dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        selected_editor = [None]  # Use list to modify from nested function
        
        # Main frame
        main_frame = tk.Frame(selection_dialog, bg="#FAFBFC")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = tk.Label(
            main_frame,
            text="Choose a text editor:",
            font=("Arial", 12, "bold"),
            bg="#FAFBFC",
            fg="#1E293B"
        )
        title_label.pack(pady=(0, 15))
        
        # Editor list
        editor_frame = tk.Frame(main_frame, bg="#FFFFFF", relief=tk.RAISED, borderwidth=1)
        editor_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Scrollable list
        canvas = tk.Canvas(editor_frame, bg="#FFFFFF", highlightthickness=0)
        scrollbar = tk.Scrollbar(editor_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#FFFFFF")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Add editor buttons
        for i, editor in enumerate(editors):
            btn = tk.Button(
                scrollable_frame,
                text=f"🔧 {editor['name']}",
                command=lambda e=editor: [selected_editor.__setitem__(0, e), selection_dialog.destroy()],
                font=("Arial", 10),
                bg="#FFFFFF",
                fg="#6366F1",
                relief=tk.FLAT,
                cursor="hand2",
                anchor="w",
                padx=20,
                pady=10
            )
            btn.pack(fill=tk.X, padx=10, pady=2)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Cancel button
        cancel_btn = tk.Button(
            main_frame,
            text="Cancel",
            command=lambda: selection_dialog.destroy(),
            font=("Arial", 10),
            bg="#FAFBFC",
            fg="#6B7280",
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=8
        )
        cancel_btn.pack()
        
        # Wait for dialog to close
        selection_dialog.wait_window()
        
        return selected_editor[0]
    
    def _add_editor_shortcuts(self, text_widget):
        """Add basic keyboard shortcuts to the text editor."""
        # Ctrl+A - Select all
        text_widget.bind('<Control-a>', lambda e: text_widget.tag_add(tk.SEL, "1.0", tk.END))
        
        # Ctrl+Z - Undo (if available)
        try:
            text_widget.bind('<Control-z>', lambda e: text_widget.edit_undo())
        except:
            pass
        
        # Ctrl+Y - Redo (if available)
        try:
            text_widget.bind('<Control-y>', lambda e: text_widget.edit_redo())
        except:
            pass
        
        # Tab - Insert 4 spaces
        text_widget.bind('<Tab>', self._insert_tab)
        
        # Shift+Tab - Remove 4 spaces
        text_widget.bind('<Shift-Tab>', self._remove_tab)
    
    def _insert_tab(self, event):
        """Insert tab as 4 spaces."""
        event.widget.insert(tk.INSERT, "    ")
        return 'break'
    
    def _remove_tab(self, event):
        """Remove tab (4 spaces) from beginning of line."""
        text_widget = event.widget
        current_line = text_widget.get(tk.INSERT + " linestart", tk.INSERT)
        if current_line.startswith("    "):
            text_widget.delete(tk.INSERT + " linestart", tk.INSERT + " linestart +4c")
        return 'break'
    
    def _save_merged_content(self, dialog, text_widget, file_info: FileConflictInfo):
        """Save the merged content to both local and remote repositories."""
        try:
            # Get the merged content
            merged_content = text_widget.get(1.0, tk.END + "-1c")
            
            # Save to local file
            local_file_path = os.path.join(self.vault_path, file_info.file_path)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
            
            # Write the merged content
            with open(local_file_path, 'w', encoding='utf-8') as f:
                f.write(merged_content)
            
            # Stage the file in git
            subprocess.run(['git', 'add', file_info.file_path], 
                         cwd=self.vault_path, check=True)
            
            # Show success message
            messagebox.showinfo(
                "Merge Saved",
                f"The merged content has been saved to:\n{file_info.file_path}\n\n"
                "The file has been staged for commit. It will be applied to both "
                "local and remote repositories when the resolution process completes."
            )
            
            # Close the dialog
            dialog.destroy()
            
            # Move to next file
            self._move_to_next_file()
            
        except Exception as e:
            messagebox.showerror(
                "Error Saving Merge",
                f"Could not save the merged content:\n{e}"
            )
    
    def _perform_auto_merge(self, file_info: FileConflictInfo):
        """Perform automatic merge using git's merge tools."""
        try:
            file_path = os.path.join(self.vault_path, file_info.file_path)
            
            # Try git's automatic merge
            result = subprocess.run(
                ['git', 'merge-file', '-p', file_path, file_path, file_path],
                cwd=self.vault_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                # Auto merge successful
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(result.stdout)
                
                # Stage the file
                subprocess.run(['git', 'add', file_info.file_path], 
                             cwd=self.vault_path, check=True)
                
                messagebox.showinfo(
                    "Auto Merge Successful",
                    f"The file '{file_info.file_path}' has been automatically merged successfully."
                )
                
                self._move_to_next_file()
            else:
                # Auto merge failed, fall back to manual merge
                messagebox.showwarning(
                    "Auto Merge Failed",
                    f"Automatic merge failed for '{file_info.file_path}'.\n"
                    "Please use Manual Merge to resolve the conflicts."
                )
        
        except Exception as e:
            messagebox.showerror(
                "Auto Merge Error",
                f"Error during auto merge:\n{e}\n\n"
                "Please use Manual Merge to resolve the conflicts."
            )
    
    def _apply_keep_local(self, file_info: FileConflictInfo):
        """Keep the local version of the file."""
        try:
            # Get local content
            local_content = get_file_content(self.vault_path, file_info.file_path, "local")
            
            # Write local content to file
            file_path = os.path.join(self.vault_path, file_info.file_path)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(local_content if local_content else "")
            
            # Stage the file
            subprocess.run(['git', 'add', file_info.file_path], 
                         cwd=self.vault_path, check=True)
            
            messagebox.showinfo(
                "Local Version Kept",
                f"The local version of '{file_info.file_path}' has been kept.\n"
                "This version will be applied to both local and remote repositories."
            )
            
            self._move_to_next_file()
            
        except Exception as e:
            messagebox.showerror(
                "Error Keeping Local Version",
                f"Could not keep local version:\n{e}"
            )
    
    def _apply_keep_remote(self, file_info: FileConflictInfo):
        """Keep the remote version of the file."""
        try:
            # Get remote content
            remote_content = get_file_content(self.vault_path, file_info.file_path, "remote")
            
            # Write remote content to file
            file_path = os.path.join(self.vault_path, file_info.file_path)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(remote_content if remote_content else "")
            
            # Stage the file
            subprocess.run(['git', 'add', file_info.file_path], 
                         cwd=self.vault_path, check=True)
            
            messagebox.showinfo(
                "Remote Version Kept",
                f"The remote version of '{file_info.file_path}' has been kept.\n"
                "This version will be applied to both local and remote repositories."
            )
            
            self._move_to_next_file()
            
        except Exception as e:
            messagebox.showerror(
                "Error Keeping Remote Version",
                f"Could not keep remote version:\n{e}"
            )
    
    def _move_to_next_file(self):
        """Move to the next file or finish if all files are resolved."""
        if self.current_file_index < len(self.conflicted_files) - 1:
            self.current_file_index += 1
            self._load_current_file()
        else:
            # All files resolved
            self._finish_resolution()
    
    def _previous_file(self):
        """Navigate to previous file."""
        if self.current_file_index > 0:
            self.current_file_index -= 1
            self._load_current_file()
    
    def _next_file(self):
        """Navigate to next file."""
        if self.current_file_index < len(self.conflicted_files) - 1:
            self.current_file_index += 1
            self._load_current_file()
    
    def _finish_resolution(self):
        """Finish the resolution process."""
        # Check if all files have been resolved
        unresolved = []
        for file_info in self.conflicted_files:
            if file_info.file_path not in self.results:
                unresolved.append(file_info.file_path)
        
        if unresolved:
            response = messagebox.askyesno(
                "Unresolved Files",
                f"The following files are not yet resolved:\n\n"
                f"{', '.join(unresolved[:3])}"
                f"{' and others' if len(unresolved) > 3 else ''}\n\n"
                "Do you want to continue without resolving these files?\n"
                "(They will be marked for manual resolution)"
            )
            if not response:
                return
            
            # Mark unresolved files for manual resolution
            for file_path in unresolved:
                self.results[file_path] = "manual_merge"
        
        if self.dialog is not None:
            self.dialog.destroy()
    
    def _cancel(self):
        """Cancel the resolution process."""
        if messagebox.askyesno("Cancel Resolution", "Are you sure you want to cancel the conflict resolution?"):
            self.results = {}
            if self.dialog is not None:
                self.dialog.destroy()

# =============================================================================
# MAIN CONFLICT RESOLUTION ORCHESTRATOR
# =============================================================================

class ConflictResolver:
    """Main class that orchestrates the two-stage conflict resolution process."""
    
    def __init__(self, vault_path: str, parent_window: Optional[tk.Tk] = None, analysis: Optional[ConflictAnalysis] = None):
        self.vault_path = vault_path
        self.parent_window = parent_window
        self.provided_analysis = analysis
    
    def resolve_conflicts(self, conflict_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Main method to resolve conflicts using the two-stage approach.
        
        Returns:
            Dict with resolution results:
            {
                'success': bool,
                'strategy': str,  # Stage 1 result
                'file_resolutions': dict,  # Stage 2 results
                'message': str
            }
        """
        try:
            # Ensure parent window is properly initialized
            if self.parent_window is None:
                return {
                    'success': False,
                    'strategy': 'error',
                    'file_resolutions': {},
                    'message': 'No parent window available for dialog'
                }
            
            # Analyze conflicts - use provided analysis if available, otherwise create new one
            if self.provided_analysis is not None:
                analysis = self.provided_analysis
                print(f"🔄 Using provided analysis: {analysis.has_conflicts} conflicts, {len(analysis.conflicted_files)} conflicted files")
            else:
                analysis = analyze_repository_conflicts(self.vault_path)
                print(f"🔄 Created new analysis: {analysis.has_conflicts} conflicts, {len(analysis.conflicted_files)} conflicted files")
            
            if not analysis.has_conflicts:
                return {
                    'success': True,
                    'strategy': 'no_conflicts',
                    'file_resolutions': {},
                    'message': 'No conflicts detected'
                }
            
            # Ensure parent window is responsive before showing dialog
            self.parent_window.update_idletasks()
            
            # Check if we only have content conflicts (no missing files)
            # If so, skip Stage 1 and go directly to Stage 2
            only_content_conflicts = (
                len(analysis.conflicted_files) > 0 and  # Has content conflicts
                len(analysis.local_only_files) == 0 and  # No local-only files
                len(analysis.remote_only_files) == 0      # No remote-only files
            )
            
            if only_content_conflicts:
                print(f"🎯 Detected only content conflicts in {len(analysis.conflicted_files)} files. Skipping Stage 1 and going directly to file-by-file resolution.")
                
                # Go directly to Stage 2: File-by-file resolution
                stage2_dialog = Stage2ConflictDialog(
                    self.parent_window, 
                    analysis.conflicted_files,
                    self.vault_path
                )
                file_resolutions = stage2_dialog.show()
                
                if not file_resolutions:
                    return {
                        'success': False,
                        'strategy': 'cancelled',
                        'file_resolutions': {},
                        'message': 'File resolution cancelled by user'
                    }
                
                return {
                    'success': True,
                    'strategy': 'smart_merge',
                    'file_resolutions': file_resolutions,
                    'message': f'Content conflicts resolved for {len(file_resolutions)} files'
                }
            
            # Stage 1: High-level strategy selection (for cases with missing files)
            stage1_dialog = Stage1ConflictDialog(self.parent_window, analysis)
            strategy = stage1_dialog.show()
            
            if not strategy:
                return {
                    'success': False,
                    'strategy': 'cancelled',
                    'file_resolutions': {},
                    'message': 'Resolution cancelled by user'
                }
            
            result = {
                'success': True,
                'strategy': strategy,
                'file_resolutions': {},
                'message': f'Strategy selected: {strategy}'
            }
            
            # Handle different strategies
            if strategy == 'keep_local':
                result['message'] = 'Keeping local files only'
                return result
            
            elif strategy == 'keep_remote':
                result['message'] = 'Keeping remote files only'
                return result
            
            elif strategy == 'smart_merge':
                # Stage 2: File-by-file resolution for conflicted files
                if analysis.conflicted_files:
                    stage2_dialog = Stage2ConflictDialog(
                        self.parent_window, 
                        analysis.conflicted_files,
                        self.vault_path
                    )
                    file_resolutions = stage2_dialog.show()
                    
                    if not file_resolutions:
                        return {
                            'success': False,
                            'strategy': strategy,
                            'file_resolutions': {},
                            'message': 'File resolution cancelled by user'
                        }
                    
                    result['file_resolutions'] = file_resolutions
                    result['message'] = f'Smart merge completed with {len(file_resolutions)} files resolved'
                else:
                    result['message'] = 'Smart merge completed - no file conflicts to resolve'
                
                return result
            
            else:
                return {
                    'success': False,
                    'strategy': strategy,
                    'file_resolutions': {},
                    'message': f'Unknown strategy: {strategy}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'strategy': 'error',
                'file_resolutions': {},
                'message': f'Error during conflict resolution: {e}'
            }

# =============================================================================
# CONFLICT RESOLUTION EXECUTION
# =============================================================================

def apply_conflict_resolution(vault_path: str, resolution_result: Dict[str, Any]) -> bool:
    """
    Apply the conflict resolution choices to the repository.
    
    Args:
        vault_path: Path to the vault/repository
        resolution_result: Result from ConflictResolver.resolve_conflicts()
    
    Returns:
        True if successful, False otherwise
    """
    try:
        strategy = resolution_result.get('strategy')
        file_resolutions = resolution_result.get('file_resolutions', {})
        
        if strategy == 'keep_local':
            return _apply_keep_local_strategy(vault_path)
        
        elif strategy == 'keep_remote':
            return _apply_keep_remote_strategy(vault_path)
        
        elif strategy == 'smart_merge':
            return _apply_smart_merge_strategy(vault_path, file_resolutions)
        
        else:
            print(f"Unknown strategy: {strategy}")
            return False
            
    except Exception as e:
        print(f"Error applying conflict resolution: {e}")
        return False

def _apply_keep_local_strategy(vault_path: str) -> bool:
    """Apply keep local strategy - preserve local files while maintaining git history."""
    try:
        print("Resolving conflict using local strategy (keeping local files)...")
        
        # First, check if we're in a git repository
        stdout, stderr, rc = run_git_command("git status --porcelain", cwd=vault_path)
        if rc != 0:
            print(f"❌ Error: Not a valid git repository: {stderr}")
            return False
        
        # Configure git user if not set (for commit to work)
        stdout, stderr, rc = run_git_command("git config user.name", cwd=vault_path)
        if rc != 0 or not stdout.strip():
            print("Setting git user name...")
            run_git_command('git config user.name "Ogresync"', cwd=vault_path)
        
        stdout, stderr, rc = run_git_command("git config user.email", cwd=vault_path)
        if rc != 0 or not stdout.strip():
            print("Setting git user email...")
            run_git_command('git config user.email "ogresync@local"', cwd=vault_path)
        
        # Configure git merge strategy
        print("Configuring git merge strategy...")
        run_git_command("git config pull.rebase false", cwd=vault_path)
        
        # Fetch latest remote state to get the full history
        print("Fetching remote repository state...")
        stdout, stderr, rc = run_git_command("git fetch origin", cwd=vault_path)
        if rc != 0:
            print(f"Warning: Could not fetch remote: {stderr}")
        
        # Check if there are any uncommitted changes
        stdout, stderr, rc = run_git_command("git status --porcelain", cwd=vault_path)
        has_uncommitted_changes = bool(stdout.strip())
        
        if has_uncommitted_changes:
            print("Found uncommitted changes, staging and committing...")
            # Stage all local changes
            stdout, stderr, rc = run_git_command("git add -A", cwd=vault_path)
            if rc != 0:
                print(f"❌ Error staging local files: {stderr}")
                return False
            
            # Commit the changes
            stdout, stderr, rc = run_git_command('git commit -m "Keep local files - conflict resolution"', cwd=vault_path)
            if rc != 0:
                print(f"❌ Error committing local files: {stderr}")
                return False
            print(f"✅ Successfully committed local changes")
        else:
            print("No uncommitted changes found - files already committed")
        
        # Check if we have any commits at all
        stdout, stderr, rc = run_git_command("git rev-parse HEAD", cwd=vault_path)
        if rc != 0:
            print("No commits found, creating initial commit...")
            # Ensure we have at least one file to commit
            ensure_file_path = os.path.join(vault_path, "README.md")
            if not os.path.exists(ensure_file_path):
                with open(ensure_file_path, "w") as f:
                    f.write("# Local Repository\n\nThis repository was initialized locally.\n")
            
            stdout, stderr, rc = run_git_command("git add -A", cwd=vault_path)
            stdout, stderr, rc = run_git_command('git commit -m "Initial commit - keep local files"', cwd=vault_path)
            if rc != 0:
                print(f"❌ Error creating initial commit: {stderr}")
                return False
        
        # Get current branch name
        stdout, stderr, rc = run_git_command("git branch --show-current", cwd=vault_path)
        current_branch = stdout.strip() if rc == 0 and stdout.strip() else None
        
        if not current_branch:
            stdout, stderr, rc = run_git_command("git rev-parse --abbrev-ref HEAD", cwd=vault_path)
            current_branch = stdout.strip() if rc == 0 and stdout.strip() else "main"
        
        print(f"Current branch: {current_branch}")
        
        # Check if remote branch exists
        stdout, stderr, rc = run_git_command("git show-ref --verify refs/remotes/origin/main", cwd=vault_path)
        remote_main_exists = (rc == 0)
        
        if not remote_main_exists:
            stdout, stderr, rc = run_git_command("git show-ref --verify refs/remotes/origin/master", cwd=vault_path)
            if rc == 0:
                remote_branch = "origin/master"
                print("Using origin/master as remote branch")
            else:
                print("No remote branch found, this will be the first push")
                remote_branch = None
        else:
            remote_branch = "origin/main"
            print("Using origin/main as remote branch")
        
        if remote_branch:
            # Create a backup of remote history before proceeding
            print("Creating backup of remote history...")
            backup_branch = f"backup-remote-{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            stdout, stderr, rc = run_git_command(f"git branch {backup_branch} {remote_branch}", cwd=vault_path)
            if rc == 0:
                print(f"✅ Remote history backed up to branch: {backup_branch}")
            else:
                print(f"⚠️ Could not create backup branch: {stderr}")
            
            # Try to merge remote history while keeping local files
            print("Attempting to merge remote history while preserving local files...")
            
            # Create a temporary branch to work on
            temp_branch = f"temp-merge-{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            stdout, stderr, rc = run_git_command(f"git checkout -b {temp_branch}", cwd=vault_path)
            if rc != 0:
                print(f"❌ Could not create temporary branch: {stderr}")
                return False
            
            # First, try to merge using the "ours" strategy to preserve local files
            print(f"Merging {remote_branch} with strategy to keep local files...")
            stdout, stderr, rc = run_git_command(f"git merge {remote_branch} -X ours --no-edit -m 'Merge remote history while keeping local files'", cwd=vault_path)
            
            if rc == 0:
                print("✅ Successfully merged remote history while keeping local files")
            else:
                print("⚠️ Merge had conflicts, resolving by keeping local files...")
                # Check if we're in a merge state
                stdout, stderr, rc_status = run_git_command("git status --porcelain=v1", cwd=vault_path)
                if rc_status == 0 and any(line.startswith(('UU', 'AA', 'DD', 'AU', 'UA', 'DU', 'UD')) for line in stdout.splitlines()):
                    # We have merge conflicts, resolve them by keeping local versions
                    run_git_command("git checkout --ours .", cwd=vault_path)
                    run_git_command("git add -A", cwd=vault_path)
                    stdout, stderr, rc = run_git_command('git commit --no-edit', cwd=vault_path)
                    if rc == 0:
                        print("✅ Conflicts resolved in favor of local files")
                    else:
                        print(f"❌ Error committing merge resolution: {stderr}")
                        # Clean up and return to original branch
                        run_git_command(f"git merge --abort", cwd=vault_path)
                        run_git_command(f"git checkout {current_branch}", cwd=vault_path)
                        run_git_command(f"git branch -D {temp_branch}", cwd=vault_path)
                        return False
                else:
                    print(f"❌ Merge failed with error: {stderr}")
                    # Clean up and return to original branch
                    run_git_command(f"git checkout {current_branch}", cwd=vault_path)
                    run_git_command(f"git branch -D {temp_branch}", cwd=vault_path)
                    return False
            
            # Switch back to main branch and apply the merge
            print(f"Applying merge to {current_branch}...")
            stdout, stderr, rc = run_git_command(f"git checkout {current_branch}", cwd=vault_path)
            if rc != 0:
                print(f"❌ Could not switch back to {current_branch}: {stderr}")
                return False
            
            stdout, stderr, rc = run_git_command(f"git merge {temp_branch} --no-edit", cwd=vault_path)
            if rc != 0:
                print(f"❌ Could not apply merge to {current_branch}: {stderr}")
                return False
            
            # Clean up temporary branch
            run_git_command(f"git branch -d {temp_branch}", cwd=vault_path)
            print("✅ Merge applied successfully")
        
        # Push the merged history
        print("Pushing merged history to remote...")
        stdout, stderr, rc = run_git_command(f"git push origin {current_branch}", cwd=vault_path)
        
        if rc != 0:
            if "non-fast-forward" in stderr or "rejected" in stderr:
                print("⚠️ Push rejected due to remote changes.")
                print("💡 The remote repository has been updated since we started.")
                print("💡 This is expected behavior when preserving history.")
                
                # Fetch the latest changes to see what's new
                run_git_command("git fetch origin", cwd=vault_path)
                
                # Use --force-with-lease for safer force pushing
                # This ensures we don't overwrite commits we haven't seen
                print("Using force-with-lease to safely push merged history...")
                stdout, stderr, rc = run_git_command(f"git push origin {current_branch} --force-with-lease", cwd=vault_path)
                if rc != 0:
                    print(f"❌ Force push with lease failed: {stderr}")
                    print("💡 This indicates someone else pushed changes after we fetched.")
                    print("💡 The operation was safely aborted to prevent data loss.")
                    if remote_branch:
                        print(f"💡 Remote history is still preserved in branch: {backup_branch}")
                    return False
                else:
                    print("✅ Successfully pushed with history preservation")
            else:
                print(f"❌ Error pushing to remote: {stderr}")
                if remote_branch:
                    print(f"💡 Remote history is preserved in branch: {backup_branch}")
                return False
        
        print("✅ Local files successfully pushed while preserving git history")
        print("🔄 IMPORTANT: Git history has been preserved!")
        print("📋 Summary of what happened:")
        print("   • Your local files have been kept as the final version")
        print("   • Remote git history has been merged and preserved")
        print("   • You can see the complete history with: git log --oneline --graph")
        if remote_branch:
            print(f"   • Remote history backup is available in branch: {backup_branch}")
            print("   • You can recover remote files anytime using git commands")
        print("💡 This operation was NON-DESTRUCTIVE - no data was lost!")
        
        return True
    except Exception as e:
        print(f"❌ Error in keep local strategy: {e}")
        import traceback
        traceback.print_exc()
        return False

def _create_backup(vault_path: str) -> bool:
    """Create a backup of local files before conflict resolution."""
    try:
        # Create human-readable timestamp
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_name = f"LOCAL_FILES_BACKUP_{timestamp}_before_remote_download"
        backup_dir = os.path.join(vault_path, backup_name)
        
        # Handle name collisions with incremental counter
        counter = 1
        while os.path.exists(backup_dir):
            backup_name = f"LOCAL_FILES_BACKUP_{timestamp}_before_remote_download_({counter})"
            backup_dir = os.path.join(vault_path, backup_name)
            counter += 1
        
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        backup_count = 0
        backup_info = []
        
        # Copy all non-git files to backup
        for root, dirs, files in os.walk(vault_path):
            # Skip .git directory and backup directories
            if '.git' in root or 'backup' in root.lower():
                continue
                
            for file in files:
                if not file.startswith('.'):
                    src_path = os.path.join(root, file)
                    rel_path = os.path.relpath(src_path, vault_path)
                    
                    # Create destination directory structure
                    dest_path = os.path.join(backup_dir, rel_path)
                    dest_dir = os.path.dirname(dest_path)
                    
                    if not os.path.exists(dest_dir):
                        os.makedirs(dest_dir)
                    
                    # Copy file
                    shutil.copy2(src_path, dest_path)
                    backup_count += 1
                    backup_info.append(rel_path)
        
        if backup_count == 0:
            print("No files found to backup (vault appears to be empty)")
            # Remove the empty backup directory
            if os.path.exists(backup_dir):
                os.rmdir(backup_dir)
            return True  # Still return True as this is not an error
        
        # Create detailed backup info file (matching old system format)
        info_file = os.path.join(backup_dir, "BACKUP_INFO.txt")
        with open(info_file, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write("OGRESYNC LOCAL FILES BACKUP\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Backup Created: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Operation: Keep Remote Only (downloading remote files)\n")
            f.write(f"Original Vault Path: {vault_path}\n")
            f.write(f"Total Files Backed Up: {backup_count}\n\n")
            
            f.write("IMPORTANT NOTES:\n")
            f.write("- This backup was created before downloading remote files\n")
            f.write("- Your local files have been safely preserved in this backup\n")
            f.write("- You can restore individual files from this backup if needed\n")
            f.write("- This backup folder will NOT be synchronized to GitHub\n\n")
            
            f.write("BACKED UP FILES:\n")
            f.write("-" * 40 + "\n")
            for file_path in backup_info:
                f.write(f"• {file_path}\n")
            
            f.write("\n" + "=" * 60 + "\n")
            f.write("End of backup information\n")
            f.write("=" * 60 + "\n")
        
        print(f"Backup created: {backup_count} files backed up to {backup_dir}")
        print(f"Backup folder: {backup_name}")
        return True
        
    except Exception as e:
        print(f"Error creating backup: {e}")
        return False

def _apply_keep_remote_strategy(vault_path: str) -> bool:
    """Apply keep remote strategy - overwrite local with remote files."""
    try:
        print("Resolving conflict using remote strategy (downloading remote files)...")
        
        # First, check if we're in a git repository
        stdout, stderr, rc = run_git_command("git status --porcelain", cwd=vault_path)
        if rc != 0:
            print(f"❌ Error: Not a valid git repository: {stderr}")
            return False
        
        # Configure git user if not set (for potential merge commits)
        stdout, stderr, rc = run_git_command("git config user.name", cwd=vault_path)
        if rc != 0 or not stdout.strip():
            print("Setting git user name...")
            run_git_command('git config user.name "Ogresync"', cwd=vault_path)
        
        stdout, stderr, rc = run_git_command("git config user.email", cwd=vault_path)
        if rc != 0 or not stdout.strip():
            print("Setting git user email...")
            run_git_command('git config user.email "ogresync@local"', cwd=vault_path)
        
        # Configure git pull to handle divergent branches with merge strategy
        print("Configuring git merge strategy...")
        stdout, stderr, rc = run_git_command("git config pull.rebase false", cwd=vault_path)
        if rc != 0:
            print(f"Warning: Could not configure git pull strategy: {stderr}")
        
        # Fetch latest remote state
        print("Fetching remote repository state...")
        stdout, stderr, rc = run_git_command("git fetch origin", cwd=vault_path)
        if rc != 0:
            print(f"❌ Error fetching remote files: {stderr}")
            return False
        
        # Create backup of local files before overwriting
        print("Creating backup of local files...")
        backup_success = _create_backup(vault_path)
        if backup_success:
            print("✅ Local files backed up successfully")
        else:
            print("⚠️  Warning: Could not create backup of local files")
        
        # Add any backup folders to .gitignore to prevent them from being cleaned
        gitignore_path = os.path.join(vault_path, ".gitignore")
        gitignore_content = ""
        if os.path.exists(gitignore_path):
            with open(gitignore_path, "r") as f:
                gitignore_content = f.read()
        
        if "LOCAL_FILES_BACKUP_*" not in gitignore_content:
            with open(gitignore_path, "a") as f:
                if gitignore_content and not gitignore_content.endswith('\n'):
                    f.write('\n')
                f.write("# Ogresync backup folders\nLOCAL_FILES_BACKUP_*\n")
            print("Added backup folders to .gitignore")
        
        # Get current branch name
        stdout, stderr, rc = run_git_command("git branch --show-current", cwd=vault_path)
        current_branch = stdout.strip() if rc == 0 and stdout.strip() else "main"
        
        if not current_branch:
            stdout, stderr, rc = run_git_command("git rev-parse --abbrev-ref HEAD", cwd=vault_path)
            current_branch = stdout.strip() if rc == 0 and stdout.strip() else "main"
        
        print(f"Current branch: {current_branch}")
        
        # Check if origin/main exists, if not try origin/master
        stdout, stderr, rc = run_git_command("git show-ref --verify refs/remotes/origin/main", cwd=vault_path)
        if rc != 0:
            # Try master branch
            stdout, stderr, rc = run_git_command("git show-ref --verify refs/remotes/origin/master", cwd=vault_path)
            if rc == 0:
                remote_branch = "origin/master"
                print("Using origin/master as remote branch")
            else:
                print("❌ Error: Could not find origin/main or origin/master branch")
                return False
        else:
            remote_branch = "origin/main"
            print("Using origin/main as remote branch")
        
        # Reset local branch to remote (this overwrites local files with remote)
        print(f"Resetting local branch to {remote_branch}...")
        stdout, stderr, rc = run_git_command(f"git reset --hard {remote_branch}", cwd=vault_path)
        if rc != 0:
            print(f"❌ Error resetting to remote: {stderr}")
            return False
        
        # Clean working directory to ensure we match remote exactly
        print("Cleaning working directory...")
        stdout, stderr, rc = run_git_command("git clean -fd", cwd=vault_path)
        if rc != 0:
            print(f"Warning: Could not clean working directory: {stderr}")
        
        print("✅ Remote files successfully downloaded and local repository reset")
        return True
    except Exception as e:
        print(f"❌ Error downloading remote files: {e}")
        import traceback
        traceback.print_exc()
        return False

def _apply_smart_merge_strategy(vault_path: str, file_resolutions: Dict[str, str]) -> bool:
    """Apply smart merge strategy with individual file resolutions."""
    try:
        # First, ensure we have the latest remote state
        _, _, rc = run_git_command("git fetch origin", cwd=vault_path)
        if rc != 0:
            print("Warning: Could not fetch from remote")
        
        # Handle individual file resolutions
        for file_path, resolution in file_resolutions.items():
            if resolution == 'keep_local':
                run_git_command(f"git checkout HEAD -- '{file_path}'", cwd=vault_path)
            elif resolution == 'keep_remote':
                run_git_command(f"git checkout origin/main -- '{file_path}'", cwd=vault_path)
            elif resolution == 'auto_merge':
                # Try automatic merge for this file
                _, _, rc = run_git_command(f"git merge-file '{file_path}' '{file_path}' origin/main:'{file_path}'", cwd=vault_path)
                # If auto merge fails, default to keep local
                if rc != 0:
                    run_git_command(f"git checkout HEAD -- '{file_path}'", cwd=vault_path)
            elif resolution == 'manual_merge':
                # Manual merge was already handled in the UI
                # Just ensure the file is staged
                run_git_command(f"git add '{file_path}'", cwd=vault_path)
        
        # Stage all resolved files
        run_git_command("git add -A", cwd=vault_path)
        
        # Commit the merge
        _, err, rc = run_git_command('git commit -m "Smart merge - conflict resolution"', cwd=vault_path)
        if rc != 0:
            # Check if there's nothing to commit
            if "nothing to commit" not in err.lower():
                print(f"Error committing merge: {err}")
                return False
        
        # Push changes to remote to apply resolution immediately
        _, err, rc = run_git_command("git push origin main", cwd=vault_path)
        if rc != 0:
            print(f"Warning: Could not push to remote: {err}")
            # Don't fail here as local resolution is complete
        
        return True
    except Exception as e:
        print(f"Error in smart merge strategy: {e}")
        return False

# =============================================================================
# CONVENIENCE FUNCTIONS FOR INTEGRATION
# =============================================================================

def resolve_repository_conflicts(vault_path: str, parent_window=None) -> Dict[str, Any]:
    """
    Convenience function to resolve repository conflicts.
    This is the main entry point for conflict resolution.
    """
    resolver = ConflictResolver(vault_path, parent_window)
    return resolver.resolve_conflicts()

def resolve_merge_conflicts(vault_path: str, parent_window=None) -> Dict[str, Any]:
    """
    Convenience function specifically for git merge conflicts.
    """
    resolver = ConflictResolver(vault_path, parent_window)
    return resolver.resolve_conflicts(ConflictType.MERGE_CONFLICT)

# =============================================================================
# BACKWARD COMPATIBILITY FUNCTIONS
# =============================================================================

def show_conflict_resolution_dialog(parent_window, conflict_files_text: str) -> Optional[str]:
    """
    Backward compatibility function for existing conflict resolution dialog.
    Returns simple choice: 'ours', 'theirs', 'manual', or None if cancelled
    """
    # For backward compatibility, create a simple analysis
    analysis = ConflictAnalysis()
    analysis.has_conflicts = True
    analysis.summary = f"Conflicts detected in files: {conflict_files_text}"
    
    # Show Stage 1 dialog
    stage1_dialog = Stage1ConflictDialog(parent_window, analysis)
    strategy = stage1_dialog.show()
    
    # Map to old format
    if strategy == 'keep_local':
        return 'ours'
    elif strategy == 'keep_remote':
        return 'theirs'
    elif strategy == 'smart_merge':
        return 'manual'
    else:
        return None

if __name__ == "__main__":
    # Test the conflict resolution system
    print("Conflict Resolution System Test")
    
    # This would normally be called from the main application
    root = tk.Tk()
    root.withdraw()  # Hide main window
    
    # Test with a dummy path
    vault_path = "/tmp/test_vault"
    
    try:
        result = resolve_repository_conflicts(vault_path, root)
        print(f"Resolution result: {result}")
    except Exception as e:
        print(f"Error: {e}")
    
    root.destroy()
