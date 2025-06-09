import tkinter as tk
from tkinter import ttk, scrolledtext
import tkinter.font as tkfont
import sys

# --- Font Handling ---
# Initialize FONT_FAMILY_PRIMARY later, after root window exists
FONT_FAMILY_PRIMARY = "TkDefaultFont"  # Default fallback, will be updated
FONT_SIZE_NORMAL = 10
FONT_SIZE_LARGE = 12
FONT_WEIGHT_BOLD = "bold"

def get_default_font_family():
    """Suggests a decent default font based on the OS.
    This function should be called AFTER a Tk root window has been initialized.
    """
    if sys.platform == "win32":
        return "Segoe UI"
    elif sys.platform == "darwin":  # macOS
        available_fonts = tkfont.families()
        if "San Francisco" in available_fonts:  # Unlikely to be listed this way
            return "San Francisco"
        if "Helvetica Neue" in available_fonts:
            return "Helvetica Neue"
        return "TkDefaultFont"  # Fallback to Tkinter's default for macOS
    else:  # Linux and other
        available_fonts = tkfont.families()
        for font_name in ["Noto Sans", "Cantarell", "Roboto", "DejaVu Sans", "Liberation Sans"]:
            if font_name in available_fonts:
                return font_name
        return "TkDefaultFont"  # Fallback for Linux/other

def init_font_config():
    """Initializes font configuration, specifically FONT_FAMILY_PRIMARY.
    Must be called after the Tk root window is created.
    """
    global FONT_FAMILY_PRIMARY
    FONT_FAMILY_PRIMARY = get_default_font_family()

# --- Styling ---
def setup_styles():
    """Configures ttk styles for a more modern look."""
    # FONT_FAMILY_PRIMARY is now assumed to be initialized by init_font_config()
    style = ttk.Style()
    
    available_themes = style.theme_names()
    # Prefer 'clam', 'alt', or 'vista' (on Windows) for a cleaner look than 'default' or 'classic'
    preferred_themes = ['clam', 'alt']
    if sys.platform == "win32":
        preferred_themes.insert(0, 'vista') # 'vista' often looks good on Windows

    selected_theme = None
    for theme in preferred_themes:
        if theme in available_themes:
            selected_theme = theme
            break
    if not selected_theme:
        selected_theme = style.theme_use() # Use current or default if preferred not found

    try:
        style.theme_use(selected_theme)
    except tk.TclError:
        print(f"Warning: Theme '{selected_theme}' not available or failed to apply. Using fallback.")
        # Fallback to a known safe theme if the selected one fails
        if 'default' in available_themes:
            style.theme_use('default')

    # General widget styling
    style.configure("TFrame", background="#ECECEC") # Light gray background for frames
    style.configure("TLabel", font=(FONT_FAMILY_PRIMARY, FONT_SIZE_NORMAL), background="#ECECEC")
    style.configure("TButton", font=(FONT_FAMILY_PRIMARY, FONT_SIZE_NORMAL, FONT_WEIGHT_BOLD), padding=(10, 5))
    style.configure("Header.TLabel", font=(FONT_FAMILY_PRIMARY, FONT_SIZE_LARGE, FONT_WEIGHT_BOLD), background="#ECECEC")
    style.configure("LabelFrame.TLabel", font=(FONT_FAMILY_PRIMARY, FONT_SIZE_NORMAL, FONT_WEIGHT_BOLD), background="#ECECEC")
    style.configure("TProgressbar", thickness=20)
    
    # Style for ScrolledText (though it's a tk widget, its frame can be styled)
    # The actual text area font is set directly on the widget.

# --- Main Application Window ---
def create_main_window():
    """Creates and returns the main application window and its core widgets."""
    root = tk.Tk()
    root.title("Ogresync")
    root.geometry("700x500") # Default size, can be adjusted
    root.configure(bg="#ECECEC")

    init_font_config() # Initialize fonts after root window exists, before setup_styles

    setup_styles() # Apply ttk styles

    main_frame = ttk.Frame(root, padding="10 10 10 10")
    main_frame.pack(expand=True, fill=tk.BOTH)

    # Log area
    log_frame = ttk.LabelFrame(main_frame, text="Activity Log", padding="10 10 10 10")
    log_frame.pack(pady=10, padx=5, fill=tk.BOTH, expand=True)
    
    log_text_widget = scrolledtext.ScrolledText(
        log_frame, 
        wrap=tk.WORD, 
        height=15, 
        state='disabled',
        font=(FONT_FAMILY_PRIMARY, FONT_SIZE_NORMAL),
        relief=tk.SOLID, # Use tk relief for ScrolledText
        borderwidth=1
    )
    log_text_widget.pack(expand=True, fill=tk.BOTH)

    # Progress bar
    progress_bar_widget = ttk.Progressbar(main_frame, orient="horizontal", length=300, mode="determinate")
    progress_bar_widget.pack(pady=(10, 5), padx=5, fill=tk.X)

    # Placeholder for control buttons (to be added in Ogresync.py or here if complex)
    # control_button_frame = ttk.Frame(main_frame)
    # control_button_frame.pack(pady=5, fill=tk.X, anchor='s')
    # Example:
    # sync_btn = ttk.Button(control_button_frame, text="Start Sync")
    # sync_btn.pack(side=tk.RIGHT, padx=5)
    # setup_btn = ttk.Button(control_button_frame, text="Run Setup")
    # setup_btn.pack(side=tk.RIGHT, padx=5)


    return root, log_text_widget, progress_bar_widget

# --- Conflict Resolution Dialog ---
def create_conflict_resolution_dialog(parent_window, conflict_files_text):
    """Creates and shows a themed modal dialog for merge conflict resolution."""
    top = tk.Toplevel(parent_window)
    top.title("Merge Conflict Detected")
    top.transient(parent_window) # Associate with parent
    top.grab_set() # Make modal
    top.resizable(False, False)
    top.configure(bg="#ECECEC")

    # Apply styles to Toplevel if necessary (often inherited or use a new Style object)
    # style = ttk.Style(top) 
    # style.theme_use(ttk.Style().theme_use()) # Inherit theme

    dialog_frame = ttk.Frame(top, padding="15 15 15 15")
    dialog_frame.pack(expand=True, fill=tk.BOTH)
    
    message_text = (f"Merge conflict detected in the following file(s):\\n{conflict_files_text}\\n\\n"
                    "How would you like to resolve these conflicts?\\n"
                    "• Keep Local Changes (your version)\\n"
                    "• Keep Remote Changes (GitHub version)\\n"
                    "• Merge Manually (resolve conflicts in your editor)")
    
    label = ttk.Label(dialog_frame, text=message_text, justify="left", wraplength=400)
    label.pack(pady=(0, 15))

    resolution = {"choice": None} # Use a dictionary to pass choice out

    def set_choice(choice):
        resolution["choice"] = choice
        top.destroy()

    btn_frame = ttk.Frame(dialog_frame)
    btn_frame.pack(pady=10)

    btn_local = ttk.Button(btn_frame, text="Keep Local Changes", command=lambda: set_choice("ours"))
    btn_remote = ttk.Button(btn_frame, text="Keep Remote Changes", command=lambda: set_choice("theirs"))
    btn_manual = ttk.Button(btn_frame, text="Merge Manually", command=lambda: set_choice("manual"))
    
    btn_local.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
    btn_remote.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
    btn_manual.grid(row=0, column=2, padx=5, pady=5, sticky="ew")
    
    btn_frame.grid_columnconfigure(0, weight=1)
    btn_frame.grid_columnconfigure(1, weight=1)
    btn_frame.grid_columnconfigure(2, weight=1)

    # Center the dialog
    top.update_idletasks()
    parent_x = parent_window.winfo_x()
    parent_y = parent_window.winfo_y()
    parent_width = parent_window.winfo_width()
    parent_height = parent_window.winfo_height()
    dialog_width = top.winfo_width()
    dialog_height = top.winfo_height()
    x = parent_x + (parent_width // 2) - (dialog_width // 2)
    y = parent_y + (parent_height // 2) - (dialog_height // 2)
    top.geometry(f'+{x}+{y}')

    parent_window.wait_window(top) # Wait for dialog to close
    return resolution["choice"]

# --- Minimal UI for Auto-Sync ---
def create_minimal_ui(auto_run=False):
    """Creates a minimal UI window for auto-sync mode with modern styling."""
    root = tk.Tk()
    root.title("Ogresync" if auto_run else "Ogresync Setup")
    root.geometry("500x350")
    root.configure(bg="#ECECEC")
    
    # Set icon with error handling
    try:
        import sys
        import os
        if hasattr(sys, "_MEIPASS"):
            icon_path = os.path.join(sys._MEIPASS, "assets", "logo.png")
        else:
            icon_path = os.path.join("assets", "logo.png")
        
        if os.path.exists(icon_path):
            img = tk.PhotoImage(file=icon_path)
            root.iconphoto(True, img)
    except Exception:
        pass  # Use default icon if loading fails
    
    init_font_config()  # Initialize fonts after root window exists
    setup_styles()  # Apply ttk styles
    
    main_frame = ttk.Frame(root, padding="15 15 15 15")
    main_frame.pack(expand=True, fill=tk.BOTH)
    
    # Title label
    title_text = "Auto-Sync Active" if auto_run else "Ogresync Ready"
    title_label = ttk.Label(main_frame, text=title_text, style="Header.TLabel")
    title_label.pack(pady=(0, 10))
    
    # Log area
    log_frame = ttk.LabelFrame(main_frame, text="Activity Log", padding="10 10 10 10")
    log_frame.pack(pady=5, fill=tk.BOTH, expand=True)
    
    log_text_widget = scrolledtext.ScrolledText(
        log_frame,
        wrap=tk.WORD,
        height=12,
        state='disabled',
        font=(FONT_FAMILY_PRIMARY, FONT_SIZE_NORMAL),
        relief=tk.SOLID,
        borderwidth=1
    )
    log_text_widget.pack(expand=True, fill=tk.BOTH)
    
    # Progress bar
    progress_bar_widget = ttk.Progressbar(main_frame, orient="horizontal", length=400, mode="determinate")
    progress_bar_widget.pack(pady=(10, 5), fill=tk.X)
    
    return root, log_text_widget, progress_bar_widget

# --- Wizard UI for Setup ---
def create_wizard_ui():
    """Creates a larger UI with wizard-related buttons for setup mode."""
    root = tk.Tk()
    root.title("Ogresync Setup")
    root.geometry("600x500")
    root.configure(bg="#ECECEC")
    
    # Set icon with error handling
    try:
        import sys
        import os
        if hasattr(sys, "_MEIPASS"):
            icon_path = os.path.join(sys._MEIPASS, "assets", "logo.png")
        else:
            icon_path = os.path.join("assets", "logo.png")
        
        if os.path.exists(icon_path):
            img = tk.PhotoImage(file=icon_path)
            root.iconphoto(True, img)
    except Exception:
        pass  # Use default icon if loading fails
    
    init_font_config()  # Initialize fonts after root window exists
    setup_styles()  # Apply ttk styles
    
    main_frame = ttk.Frame(root, padding="20 20 20 20")
    main_frame.pack(expand=True, fill=tk.BOTH)
    
    # Header
    header_label = ttk.Label(main_frame, text="Ogresync First-Time Setup", style="Header.TLabel")
    header_label.pack(pady=(0, 15))
    
    # Log area
    log_frame = ttk.LabelFrame(main_frame, text="Setup Progress", padding="10 10 10 10")
    log_frame.pack(pady=5, fill=tk.BOTH, expand=True)
    
    log_text_widget = scrolledtext.ScrolledText(
        log_frame,
        wrap=tk.WORD,
        height=12,
        font=(FONT_FAMILY_PRIMARY, FONT_SIZE_NORMAL),
        relief=tk.SOLID,
        borderwidth=1
    )
    log_text_widget.pack(expand=True, fill=tk.BOTH)
    
    # Progress bar
    progress_bar_widget = ttk.Progressbar(main_frame, orient="horizontal", length=500, mode="determinate")
    progress_bar_widget.pack(pady=(10, 15), fill=tk.X)
    
    # Button frame for SSH operations
    btn_frame = ttk.Frame(main_frame)
    btn_frame.pack(pady=10, fill=tk.X)
    
    # Note: The actual button commands will be passed from the main file
    # These buttons will be created but commands assigned later
    ssh_buttons_frame = ttk.Frame(btn_frame)
    ssh_buttons_frame.pack(pady=5)
    
    # Create button placeholders that will have commands assigned later
    gen_btn = ttk.Button(ssh_buttons_frame, text="Generate SSH Key")
    gen_btn.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
    
    copy_btn = ttk.Button(ssh_buttons_frame, text="Copy SSH Key")
    copy_btn.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
    
    test_ssh_btn = ttk.Button(ssh_buttons_frame, text="Re-test SSH")
    test_ssh_btn.grid(row=0, column=2, padx=10, pady=5, sticky="ew")
    
    # Configure grid weights for equal button sizing
    ssh_buttons_frame.grid_columnconfigure(0, weight=1)
    ssh_buttons_frame.grid_columnconfigure(1, weight=1)
    ssh_buttons_frame.grid_columnconfigure(2, weight=1)
    
    # Exit button
    exit_btn = ttk.Button(btn_frame, text="Exit", width=15)
    exit_btn.pack(pady=(10, 0))
    
    # Return everything including button references for command assignment
    return root, log_text_widget, progress_bar_widget, gen_btn, copy_btn, test_ssh_btn, exit_btn

# --- Helper for simple dialogs (optional, can be expanded) ---
# You can also wrap standard dialogs if you want to ensure consistent styling/behavior
# from tkinter import simpledialog, messagebox

# def ask_string_dialog(parent, title, prompt):
#     # Potentially customize simpledialog here if possible, or use a custom Toplevel
#     return simpledialog.askstring(title, prompt, parent=parent)

# def show_info_message(title, message):
#     messagebox.showinfo(title, message)

# def show_error_message(title, message):
#     messagebox.showerror(title, message)
