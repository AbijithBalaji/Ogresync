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
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Dict, List, Tuple, Optional, Any, Set
import difflib

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

def run_git_command(command: str, cwd: str = None) -> Tuple[str, str, int]:
    """Run a git command and return output, error, and return code."""
    try:
        process = subprocess.run(
            command.split(),
            cwd=cwd,
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
                    analysis.conflicted_files.append(conflict_info)
                    analysis.different_files.append(file_path)
                else:
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
        
        # Get files from remote main branch
        out, err, rc = run_git_command("git ls-tree -r --name-only origin/main", cwd=vault_path)
        if rc == 0 and out.strip():
            return [f.strip() for f in out.strip().split('\n') if f.strip()]
    except Exception:
        pass
    return []

def files_differ(vault_path: str, file_path: str) -> bool:
    """Check if a file differs between local and remote versions."""
    try:
        # Compare local file with remote version
        out, err, rc = run_git_command(f"git diff HEAD origin/main -- {file_path}", cwd=vault_path)
        return rc == 0 and out.strip() != ""
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
            out, err, rc = run_git_command(f"git show origin/main:{file_path}", cwd=vault_path)
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
        self.dialog = None
        
    def show(self) -> Optional[str]:
        """Show the dialog and return user's choice."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Conflict Resolution - Strategy Selection")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        self.dialog.resizable(True, True)
        
        # Set dialog size - increased height to prevent truncation
        self.dialog.update_idletasks()
        width, height = 750, 700
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
        self.dialog.minsize(600, 500)  # Set minimum size to prevent shrinking too small
        
        self._create_widgets()
        
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
        
        self.dialog.configure(bg=bg_primary)
        
        # Main container with scrollable frame
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
            details_text = f"Files with conflicts: {', '.join([f.file_path for f in self.analysis.conflicted_files[:3]])}"
            if len(self.analysis.conflicted_files) > 3:
                details_text += f" and {len(self.analysis.conflicted_files) - 3} more..."
            
            details_label = tk.Label(
                summary_inner,
                text=details_text,
                font=("Arial", 9),
                bg=bg_card,
                fg=text_secondary,
                wraplength=650,
                justify=tk.LEFT
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
        self.dialog.destroy()
    
    def _cancel(self):
        """Cancel the dialog."""
        self.result = None
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
        self.dialog = None
        
    def show(self) -> Dict[str, str]:
        """Show the dialog and return resolution choices for each file."""
        if not self.conflicted_files:
            return {}
        
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Conflict Resolution - File by File")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        self.dialog.resizable(True, True)
        
        # Set dialog size - improved sizing
        self.dialog.update_idletasks()
        width, height = 950, 750
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
        self.dialog.minsize(850, 650)
        
        self._create_widgets()
        self._load_current_file()
        
        # Wait for user response
        self.parent.wait_window(self.dialog)
        return self.results
    
    def _create_widgets(self):
        """Create the dialog widgets."""
        bg_primary = "#FAFBFC"
        bg_card = "#FFFFFF"
        
        self.dialog.configure(bg=bg_primary)
        
        # Main container
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
            borderwidth=1
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
            borderwidth=1
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
            borderwidth=1
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
        
        # Create button grid
        button_grid = tk.Frame(action_inner, bg=bg_card)
        button_grid.pack(fill=tk.X)
        
        # Row 1: Auto merge and Manual merge
        row1 = tk.Frame(button_grid, bg=bg_card)
        row1.pack(fill=tk.X, pady=(0, 8))
        
        auto_merge_btn = tk.Button(
            row1,
            text="🔄 Auto Merge",
            command=lambda: self._resolve_file("auto_merge"),
            font=("Arial", 10, "bold"),
            bg=accent_color,
            fg="#FFFFFF",
            relief=tk.FLAT,
            cursor="hand2",
            padx=15,
            pady=8
        )
        auto_merge_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        manual_merge_btn = tk.Button(
            row1,
            text="✏️ Manual Merge",
            command=lambda: self._resolve_file("manual_merge"),
            font=("Arial", 10),
            bg=warning_color,
            fg="#FFFFFF",
            relief=tk.FLAT,
            cursor="hand2",
            padx=15,
            pady=8
        )
        manual_merge_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # Row 2: Keep local and Keep remote
        row2 = tk.Frame(button_grid, bg=bg_card)
        row2.pack(fill=tk.X)
        
        keep_local_btn = tk.Button(
            row2,
            text="📁 Keep Local",
            command=lambda: self._resolve_file("keep_local"),
            font=("Arial", 10),
            bg=bg_card,
            fg=accent_color,
            relief=tk.SOLID,
            borderwidth=1,
            cursor="hand2",
            padx=15,
            pady=8
        )
        keep_local_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        keep_remote_btn = tk.Button(
            row2,
            text="🌐 Keep Remote",
            command=lambda: self._resolve_file("keep_remote"),
            font=("Arial", 10),
            bg=bg_card,
            fg=accent_color,
            relief=tk.SOLID,
            borderwidth=1,
            cursor="hand2",
            padx=15,
            pady=8
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
        
        # Update text widgets
        self.local_text.delete(1.0, tk.END)
        self.local_text.insert(1.0, local_content if local_content else "[File not found locally]")
        
        self.remote_text.delete(1.0, tk.END)
        self.remote_text.insert(1.0, remote_content if remote_content else "[File not found in remote]")
        
        # Generate diff
        diff_content = self._generate_diff(local_content, remote_content, current_file.file_path)
        self.diff_text.delete(1.0, tk.END)
        self.diff_text.insert(1.0, diff_content)
        
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
        self.results[current_file.file_path] = resolution
        
        # Handle manual merge immediately
        if resolution == "manual_merge":
            self._open_manual_merge(current_file)
        
        # Move to next file if available
        if self.current_file_index < len(self.conflicted_files) - 1:
            self.current_file_index += 1
            self._load_current_file()
        else:
            # All files resolved
            self._finish_resolution()
    
    def _open_manual_merge(self, file_info: FileConflictInfo):
        """Open the file in external editor for manual merge."""
        try:
            file_path = os.path.join(self.vault_path, file_info.file_path)
            
            # Determine the appropriate editor/program to open the file
            if sys.platform.startswith('win'):
                os.startfile(file_path)
            elif sys.platform.startswith('darwin'):
                subprocess.run(['open', file_path])
            else:
                # Linux - try common editors
                editors = ['code', 'gedit', 'nano', 'vim', 'emacs']
                for editor in editors:
                    try:
                        subprocess.run([editor, file_path], check=True)
                        break
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        continue
                else:
                    # Fallback to xdg-open
                    subprocess.run(['xdg-open', file_path])
            
            messagebox.showinfo(
                "Manual Merge",
                f"The file '{file_info.file_path}' has been opened in your default editor.\n\n"
                "Please resolve the conflicts manually and save the file.\n"
                "Click OK when you're done editing."
            )
        except Exception as e:
            messagebox.showerror(
                "Error Opening File",
                f"Could not open file for manual editing:\n{e}\n\n"
                "Please open the file manually in your preferred editor."
            )
    
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
        
        self.dialog.destroy()
    
    def _cancel(self):
        """Cancel the resolution process."""
        if messagebox.askyesno("Cancel Resolution", "Are you sure you want to cancel the conflict resolution?"):
            self.results = {}
            self.dialog.destroy()

# =============================================================================
# MAIN CONFLICT RESOLUTION ORCHESTRATOR
# =============================================================================

class ConflictResolver:
    """Main class that orchestrates the two-stage conflict resolution process."""
    
    def __init__(self, vault_path: str, parent_window=None):
        self.vault_path = vault_path
        self.parent_window = parent_window
    
    def resolve_conflicts(self, conflict_type: str = None) -> Dict[str, Any]:
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
            # Analyze conflicts
            analysis = analyze_repository_conflicts(self.vault_path)
            
            if not analysis.has_conflicts:
                return {
                    'success': True,
                    'strategy': 'no_conflicts',
                    'file_resolutions': {},
                    'message': 'No conflicts detected'
                }
            
            # Stage 1: High-level strategy selection
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
    """Apply keep local strategy - overwrite remote with local files."""
    try:
        # Commit all local changes
        run_git_command("git add -A", cwd=vault_path)
        _, _, rc = run_git_command('git commit -m "Keep local files - conflict resolution"', cwd=vault_path)
        if rc != 0:
            # Might be nothing to commit
            pass
        
        # Force push to overwrite remote
        _, err, rc = run_git_command("git push origin main --force", cwd=vault_path)
        if rc != 0:
            print(f"Error force pushing: {err}")
            return False
        
        return True
    except Exception as e:
        print(f"Error in keep local strategy: {e}")
        return False

def _apply_keep_remote_strategy(vault_path: str) -> bool:
    """Apply keep remote strategy - overwrite local with remote files."""
    try:
        # Reset local branch to remote
        _, err, rc = run_git_command("git fetch origin", cwd=vault_path)
        if rc != 0:
            print(f"Error fetching: {err}")
            return False
        
        _, err, rc = run_git_command("git reset --hard origin/main", cwd=vault_path)
        if rc != 0:
            print(f"Error resetting to remote: {err}")
            return False
        
        return True
    except Exception as e:
        print(f"Error in keep remote strategy: {e}")
        return False

def _apply_smart_merge_strategy(vault_path: str, file_resolutions: Dict[str, str]) -> bool:
    """Apply smart merge strategy with individual file resolutions."""
    try:
        # First, handle non-conflicting files by doing a normal merge
        # This will automatically merge files that don't conflict
        _, _, rc = run_git_command("git merge origin/main --no-commit", cwd=vault_path)
        
        # Now handle individual file resolutions
        for file_path, resolution in file_resolutions.items():
            if resolution == 'keep_local':
                run_git_command(f"git checkout --ours -- {file_path}", cwd=vault_path)
            elif resolution == 'keep_remote':
                run_git_command(f"git checkout --theirs -- {file_path}", cwd=vault_path)
            elif resolution == 'auto_merge':
                # Try automatic merge for this file
                _, _, rc = run_git_command(f"git merge-file -p {file_path} {file_path} {file_path}", cwd=vault_path)
                # If auto merge fails, default to keep local
                if rc != 0:
                    run_git_command(f"git checkout --ours -- {file_path}", cwd=vault_path)
            elif resolution == 'manual_merge':
                # Manual merge was already handled in the UI
                # Just ensure the file is staged
                run_git_command(f"git add {file_path}", cwd=vault_path)
        
        # Stage all resolved files
        run_git_command("git add -A", cwd=vault_path)
        
        # Commit the merge
        _, err, rc = run_git_command('git commit -m "Smart merge - conflict resolution"', cwd=vault_path)
        if rc != 0:
            print(f"Error committing merge: {err}")
            return False
        
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

def show_conflict_resolution_dialog(parent_window, conflict_files_text: str) -> str:
    """
    Backward compatibility function for existing conflict resolution dialog.
    Returns simple choice: 'ours', 'theirs', or 'manual'
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
