import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import tkinter.font as tkfont
import sys
import os
from typing import Optional, Callable, Dict, Any, Union

# =============================================================================
# PREMIUM UI DESIGN SYSTEM - MODERN & SCALABLE
# =============================================================================

# --- Enhanced Color Palette ---
class Colors:
    # Premium Brand Colors - Modern gradient-friendly palette
    PRIMARY = "#6366F1"        # Indigo - Premium, professional
    PRIMARY_HOVER = "#4F46E5"  # Darker indigo for hover
    PRIMARY_ACTIVE = "#4338CA" # Even darker for active state
    PRIMARY_LIGHT = "#A5B4FC"  # Light indigo for accents
    PRIMARY_GHOST = "#E0E7FF" # Light indigo instead of transparent
    
    # Semantic Colors
    SUCCESS = "#10B981"        # Emerald green
    SUCCESS_HOVER = "#059669"  # Darker emerald
    SUCCESS_LIGHT = "#A7F3D0"  # Light emerald
    
    WARNING = "#F59E0B"        # Amber
    WARNING_HOVER = "#D97706"  # Darker amber
    WARNING_LIGHT = "#FDE68A"  # Light amber
    
    ERROR = "#EF4444"          # Red
    ERROR_HOVER = "#DC2626"    # Darker red
    ERROR_LIGHT = "#FECACA"    # Light red
    
    INFO = "#3B82F6"          # Blue
    INFO_HOVER = "#2563EB"    # Darker blue
    INFO_LIGHT = "#BFDBFE"    # Light blue
    
    # Premium Background System
    BG_PRIMARY = "#FAFBFC"     # Primary background - slightly off-white
    BG_SECONDARY = "#F7F9FB"   # Secondary background
    BG_TERTIARY = "#F1F4F7"    # Tertiary background
    BG_CARD = "#FFFFFF"        # Card backgrounds
    BG_ELEVATED = "#FFFFFF"    # Elevated surfaces
    
    # Glass/Blur Effects (simulated with lighter colors)
    GLASS_PRIMARY = "#F8F9FA"   # Light gray instead of transparent white
    GLASS_SECONDARY = "#F1F3F4" # Slightly darker gray
    
    # Premium Surface Colors
    SURFACE_DEFAULT = "#FFFFFF"
    SURFACE_HOVER = "#F8FAFC"
    SURFACE_ACTIVE = "#F1F5F9"
    SURFACE_DISABLED = "#F8FAFC"
    
    # Professional Text Hierarchy
    TEXT_PRIMARY = "#1E293B"   # Very dark slate
    TEXT_SECONDARY = "#475569" # Medium slate
    TEXT_TERTIARY = "#64748B"  # Light slate
    TEXT_MUTED = "#94A3B8"     # Very light slate
    TEXT_INVERSE = "#FFFFFF"   # White text
    TEXT_ACCENT = "#6366F1"    # Brand color text
    
    # Sophisticated Border System
    BORDER_SUBTLE = "#F1F5F9"  # Very light borders
    BORDER_DEFAULT = "#E2E8F0" # Default borders
    BORDER_STRONG = "#CBD5E1"  # Strong borders
    BORDER_ACCENT = "#6366F1"  # Accent borders
    
    # Professional Shadow System (using gray colors since tkinter doesn't support alpha)
    SHADOW_SM = "#F1F5F9"      # Very light gray
    SHADOW_MD = "#E2E8F0"      # Light gray
    SHADOW_LG = "#CBD5E1"      # Medium gray
    SHADOW_XL = "#94A3B8"      # Darker gray
    
    # Gradient Colors for Premium Effects
    GRADIENT_PRIMARY = ["#6366F1", "#8B5CF6"]   # Indigo to purple
    GRADIENT_SUCCESS = ["#10B981", "#059669"]   # Emerald gradient
    GRADIENT_SUNSET = ["#F59E0B", "#EF4444"]    # Warm gradient
    GRADIENT_OCEAN = ["#06B6D4", "#3B82F6"]     # Cool gradient

# --- Professional Typography System ---
class Typography:
    # Premium Font Stack
    PRIMARY_FONT = "Inter"     # Primary UI font
    HEADING_FONT = "SF Pro Display" # For headings (fallback to primary)
    MONO_FONT = "SF Mono"      # Monospace font
    
    # Comprehensive Size Scale
    XXS = 9   # Tiny text
    XS = 10   # Extra small
    SM = 11   # Small
    BASE = 12 # Base size
    MD = 13   # Medium
    LG = 14   # Large
    XL = 16   # Extra large
    XXL = 18  # Double extra large
    XXXL = 20 # Triple extra large
    H4 = 22   # Heading 4
    H3 = 24   # Heading 3
    H2 = 28   # Heading 2
    H1 = 32   # Heading 1
    DISPLAY = 36 # Display text
    
    # Professional Font Weights (tkinter-compatible)
    THIN = "normal"
    EXTRALIGHT = "normal"
    LIGHT = "normal"
    NORMAL = "normal"
    MEDIUM = "normal"
    SEMIBOLD = "bold"
    BOLD = "bold"
    EXTRABOLD = "bold"
    BLACK = "bold"

# --- Advanced Spacing System ---
class Spacing:
    # Micro spacing
    XXS = 2
    XS = 4
    SM = 6
    # Standard spacing
    MD = 8
    LG = 12
    XL = 16
    XXL = 20
    XXXL = 24
    # Large spacing
    GIANT = 32
    HUGE = 40
    MASSIVE = 48
    
    # Component-specific spacing
    BUTTON_PADDING_X = 16
    BUTTON_PADDING_Y = 8
    CARD_PADDING = 20
    SECTION_MARGIN = 24
    
# --- Animation & Effects System ---
class Effects:
    # Timing functions
    FAST = 150     # Quick interactions
    NORMAL = 250   # Standard transitions
    SLOW = 350     # Deliberate animations
    
    # Easing curves (for future CSS-like transitions)
    EASE_IN = "ease-in"
    EASE_OUT = "ease-out"
    EASE_IN_OUT = "ease-in-out"
    
    # Shadow definitions
    SHADOW_NONE = "none"
    SHADOW_SM = "0 1px 2px rgba(0, 0, 0, 0.05)"
    SHADOW_MD = "0 4px 6px rgba(0, 0, 0, 0.1)"
    SHADOW_LG = "0 10px 15px rgba(0, 0, 0, 0.1)"
    SHADOW_XL = "0 20px 25px rgba(0, 0, 0, 0.15)"
    
    # Border radius for modern rounded corners
    RADIUS_NONE = 0
    RADIUS_SM = 3
    RADIUS_MD = 6
    RADIUS_LG = 8
    RADIUS_XL = 12
    RADIUS_FULL = 9999

# --- Icon System (Unicode/Text-based for cross-platform compatibility) ---
class Icons:
    # Navigation
    ARROW_LEFT = "←"
    ARROW_RIGHT = "→"
    ARROW_UP = "↑" 
    ARROW_DOWN = "↓"
    
    # Actions
    PLAY = "▶"
    PAUSE = "⏸"
    STOP = "⏹"
    REFRESH = "↻"
    DOWNLOAD = "⬇"
    UPLOAD = "⬆"
    SYNC = "⟲"
    
    # Status
    SUCCESS = "✓"
    ERROR = "✗"
    WARNING = "⚠"
    INFO = "ℹ"
    
    # Files & Folders
    FOLDER = "📁"
    FILE = "📄"
    GEAR = "⚙"
    KEY = "🔑"
    LINK = "🔗"
    
    # Security & Tools
    SECURITY = "🔒"
    COPY = "📋"
    
    # Interface
    MENU = "☰"
    CLOSE = "✕"
    MINIMIZE = "−"
    MAXIMIZE = "□"

# =============================================================================
# ADVANCED UI COMPONENT SYSTEM
# =============================================================================

# Global font configuration
FONT_FAMILY_PRIMARY = "TkDefaultFont"
FONT_FAMILY_MONO = "TkFixedFont"

def get_premium_font_family():
    """Gets the best available font for a premium look."""
    try:
        available_fonts = tkfont.families()
        
        # Premium font preferences by platform
        if sys.platform == "win32":
            preferred = ["Segoe UI Variable", "Segoe UI", "Calibri"]
        elif sys.platform == "darwin":  # macOS
            preferred = ["SF Pro Display", "Helvetica Neue", "Lucida Grande"]
        else:  # Linux
            preferred = ["Inter", "Roboto", "Noto Sans", "Ubuntu", "Cantarell", "DejaVu Sans"]
        
        for font in preferred:
            if font in available_fonts:
                return font
                
        return "TkDefaultFont"
    except Exception:
        return "TkDefaultFont"

def get_premium_mono_font():
    """Gets the best available monospace font."""
    try:
        available_fonts = tkfont.families()
        
        if sys.platform == "win32":
            preferred = ["Consolas", "Courier New"]
        elif sys.platform == "darwin":
            preferred = ["SF Mono", "Menlo", "Monaco"]
        else:
            preferred = ["JetBrains Mono", "Fira Code", "Ubuntu Mono", "DejaVu Sans Mono"]
            
        for font in preferred:
            if font in available_fonts:
                return font
                
        return "TkFixedFont"
    except Exception:
        return "TkFixedFont"

def init_font_config():
    """Initializes premium font configuration."""
    global FONT_FAMILY_PRIMARY, FONT_FAMILY_MONO
    FONT_FAMILY_PRIMARY = get_premium_font_family()
    FONT_FAMILY_MONO = get_premium_mono_font()

# =============================================================================
# PREMIUM COMPONENT LIBRARY
# =============================================================================

class PremiumButton:
    """Enhanced button component with hover effects and styling options."""
    
    @staticmethod
    def create_primary(parent, text, command=None, icon=None, size="md"):
        """Creates a primary button with premium styling."""
        btn_frame = tk.Frame(parent, bg=Colors.BG_PRIMARY)
        
        # Size configurations
        sizes = {
            "sm": {"font_size": Typography.SM, "pad_x": 12, "pad_y": 6, "min_width": 60},
            "md": {"font_size": Typography.MD, "pad_x": 16, "pad_y": 8, "min_width": 80},
            "lg": {"font_size": Typography.LG, "pad_x": 20, "pad_y": 10, "min_width": 100}
        }
        
        size_config = sizes.get(size, sizes["md"])
        
        # Create button text with optional icon
        button_text = f"{icon} {text}" if icon else text
        
        btn = tk.Button(
            btn_frame,
            text=button_text,
            command=command,
            font=(FONT_FAMILY_PRIMARY, size_config["font_size"], Typography.MEDIUM),
            bg=Colors.PRIMARY,
            fg=Colors.TEXT_INVERSE,
            activebackground=Colors.PRIMARY_HOVER,
            activeforeground=Colors.TEXT_INVERSE,
            relief=tk.FLAT,
            borderwidth=0,
            cursor="hand2",
            padx=size_config["pad_x"],
            pady=size_config["pad_y"],
            width=10,  # Set minimum width in characters
            height=2   # Set minimum height in text lines
        )
        
        # Add hover effects
        def on_enter(e):
            btn.config(bg=Colors.PRIMARY_HOVER)
        
        def on_leave(e):
            btn.config(bg=Colors.PRIMARY)
            
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        btn.pack(fill=tk.BOTH, expand=True)
        
        # Store the actual button widget in the frame for easy access
        btn_frame.button = btn
        return btn_frame
    
    @staticmethod
    def create_secondary(parent, text, command=None, icon=None, size="md"):
        """Creates a secondary button with outline styling."""
        btn_frame = tk.Frame(parent, bg=Colors.BG_PRIMARY)
        
        sizes = {
            "sm": {"font_size": Typography.SM, "pad_x": 12, "pad_y": 6, "min_width": 60},
            "md": {"font_size": Typography.MD, "pad_x": 16, "pad_y": 8, "min_width": 80},
            "lg": {"font_size": Typography.LG, "pad_x": 20, "pad_y": 10, "min_width": 100}
        }
        
        size_config = sizes.get(size, sizes["md"])
        button_text = f"{icon} {text}" if icon else text
        
        btn = tk.Button(
            btn_frame,
            text=button_text,
            command=command,
            font=(FONT_FAMILY_PRIMARY, size_config["font_size"], Typography.MEDIUM),
            bg=Colors.BG_CARD,
            fg=Colors.TEXT_ACCENT,
            activebackground=Colors.SURFACE_HOVER,
            activeforeground=Colors.PRIMARY_HOVER,
            relief=tk.SOLID,
            borderwidth=1,
            cursor="hand2",
            padx=size_config["pad_x"],
            pady=size_config["pad_y"],
            width=10,  # Set minimum width in characters
            height=2   # Set minimum height in text lines
        )
        
        def on_enter(e):
            btn.config(bg=Colors.SURFACE_HOVER, fg=Colors.PRIMARY_HOVER, relief=tk.SOLID)
        
        def on_leave(e):
            btn.config(bg=Colors.BG_CARD, fg=Colors.TEXT_ACCENT, relief=tk.SOLID)
            
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        btn.pack(fill=tk.BOTH, expand=True)
        
        # Store the actual button widget in the frame for easy access
        btn_frame.button = btn
        return btn_frame
    
    @staticmethod
    def create_danger(parent, text, command=None, icon=None, size="md"):
        """Creates a danger button with error styling."""
        btn_frame = tk.Frame(parent, bg=Colors.BG_PRIMARY)
        
        sizes = {
            "sm": {"font_size": Typography.SM, "pad_x": 12, "pad_y": 6},
            "md": {"font_size": Typography.MD, "pad_x": 16, "pad_y": 8},
            "lg": {"font_size": Typography.LG, "pad_x": 20, "pad_y": 10}
        }
        
        size_config = sizes.get(size, sizes["md"])
        button_text = f"{icon} {text}" if icon else text
        
        btn = tk.Button(
            btn_frame,
            text=button_text,
            command=command,
            font=(FONT_FAMILY_PRIMARY, size_config["font_size"], Typography.MEDIUM),
            bg=Colors.ERROR,
            fg=Colors.TEXT_INVERSE,
            activebackground=Colors.ERROR_HOVER,
            activeforeground=Colors.TEXT_INVERSE,
            relief=tk.FLAT,
            borderwidth=0,
            cursor="hand2",
            padx=size_config["pad_x"],
            pady=size_config["pad_y"]
        )
        
        def on_enter(e):
            btn.config(bg=Colors.ERROR_HOVER)
        
        def on_leave(e):
            btn.config(bg=Colors.ERROR)
            
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        btn.pack(fill=tk.BOTH, expand=True)
        
        btn_frame.button = btn
        return btn_frame
    
    @staticmethod
    def create_success(parent, text, command=None, icon=None, size="md"):
        """Creates a success button with success styling."""
        btn_frame = tk.Frame(parent, bg=Colors.BG_PRIMARY)
        
        sizes = {
            "sm": {"font_size": Typography.SM, "pad_x": 12, "pad_y": 6},
            "md": {"font_size": Typography.MD, "pad_x": 16, "pad_y": 8},
            "lg": {"font_size": Typography.LG, "pad_x": 20, "pad_y": 10}
        }
        
        size_config = sizes.get(size, sizes["md"])
        button_text = f"{icon} {text}" if icon else text
        
        btn = tk.Button(
            btn_frame,
            text=button_text,
            command=command,
            font=(FONT_FAMILY_PRIMARY, size_config["font_size"], Typography.MEDIUM),
            bg=Colors.SUCCESS,
            fg=Colors.TEXT_INVERSE,
            activebackground=Colors.SUCCESS_HOVER,
            activeforeground=Colors.TEXT_INVERSE,
            relief=tk.FLAT,
            borderwidth=0,
            cursor="hand2",
            padx=size_config["pad_x"],
            pady=size_config["pad_y"]
        )
        
        def on_enter(e):
            btn.config(bg=Colors.SUCCESS_HOVER)
        
        def on_leave(e):
            btn.config(bg=Colors.SUCCESS)
            
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        btn.pack(fill=tk.BOTH, expand=True)
        
        btn_frame.button = btn
        return btn_frame
    
    @staticmethod
    def create_warning(parent, text, command=None, icon=None, size="md"):
        """Creates a warning button with warning styling."""
        btn_frame = tk.Frame(parent, bg=Colors.BG_PRIMARY)
        
        sizes = {
            "sm": {"font_size": Typography.SM, "pad_x": 12, "pad_y": 6},
            "md": {"font_size": Typography.MD, "pad_x": 16, "pad_y": 8},
            "lg": {"font_size": Typography.LG, "pad_x": 20, "pad_y": 10}
        }
        
        size_config = sizes.get(size, sizes["md"])
        button_text = f"{icon} {text}" if icon else text
        
        btn = tk.Button(
            btn_frame,
            text=button_text,
            command=command,
            font=(FONT_FAMILY_PRIMARY, size_config["font_size"], Typography.MEDIUM),
            bg=Colors.WARNING,
            fg=Colors.TEXT_INVERSE,
            activebackground=Colors.WARNING_HOVER,
            activeforeground=Colors.TEXT_INVERSE,
            relief=tk.FLAT,
            borderwidth=0,
            cursor="hand2",
            padx=size_config["pad_x"],
            pady=size_config["pad_y"]
        )
        
        def on_enter(e):
            btn.config(bg=Colors.WARNING_HOVER)
        
        def on_leave(e):
            btn.config(bg=Colors.WARNING)
            
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        btn.pack(fill=tk.BOTH, expand=True)
        
        btn_frame.button = btn
        return btn_frame

class PremiumCard:
    """Card component with elevated styling and shadows."""
    
    @staticmethod
    def create(parent, title=None, padding=Spacing.CARD_PADDING):
        """Creates a premium card container."""
        # Outer frame for shadow effect (simulation)
        shadow_frame = tk.Frame(parent, bg=Colors.SHADOW_MD, height=2)
        shadow_frame.pack(fill=tk.X, padx=(2, 0), pady=(2, 0))
        
        # Main card frame
        card_frame = tk.Frame(
            parent,
            bg=Colors.BG_CARD,
            relief=tk.FLAT,
            borderwidth=1
        )
        card_frame.pack(fill=tk.BOTH, expand=True, padx=(0, 2), pady=(0, 2))
        
        # Inner content frame with padding
        content_frame = tk.Frame(card_frame, bg=Colors.BG_CARD)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=padding, pady=padding)
        
        # Optional title
        if title:
            title_label = tk.Label(
                content_frame,
                text=title,
                font=(FONT_FAMILY_PRIMARY, Typography.LG, Typography.SEMIBOLD),
                bg=Colors.BG_CARD,
                fg=Colors.TEXT_PRIMARY
            )
            title_label.pack(anchor=tk.W, pady=(0, Spacing.MD))
        
        return content_frame

class PremiumDialog:
    """Enhanced dialog system with modern styling."""
    
    @staticmethod
    def create_base(parent, title, width=400, height=300):
        """Creates a base dialog with premium styling."""
        dialog = tk.Toplevel(parent)
        dialog.title(title)
        dialog.transient(parent)
        dialog.grab_set()
        dialog.resizable(False, False)
        dialog.configure(bg=Colors.BG_PRIMARY)
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # Main container with padding
        main_frame = tk.Frame(dialog, bg=Colors.BG_PRIMARY)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=Spacing.XL, pady=Spacing.XL)
        
        return dialog, main_frame

# --- Premium Styling System ---
def setup_premium_styles():
    """Configures advanced TTK styles for premium appearance."""
    style = ttk.Style()
    
    # Select the best available theme
    available_themes = style.theme_names()
    preferred_themes = ['vista', 'clam', 'alt', 'default']
    
    selected_theme = None
    for theme in preferred_themes:
        if theme in available_themes:
            selected_theme = theme
            break
    
    if selected_theme:
        try:
            style.theme_use(selected_theme)
        except tk.TclError:
            style.theme_use('default')
    
    # Premium Frame Styling
    style.configure(
        "Premium.TFrame",
        background=Colors.BG_CARD,
        relief="flat",
        borderwidth=0
    )
    
    style.configure(
        "Card.TFrame", 
        background=Colors.BG_CARD,
        relief="solid",
        borderwidth=1,
        lightcolor=Colors.BORDER_SUBTLE,
        darkcolor=Colors.BORDER_SUBTLE
    )
    
    # Premium Label Styling
    style.configure(
        "Premium.TLabel",
        font=(FONT_FAMILY_PRIMARY, Typography.BASE, Typography.NORMAL),
        background=Colors.BG_CARD,
        foreground=Colors.TEXT_PRIMARY
    )
    
    style.configure(
        "Heading.TLabel",
        font=(FONT_FAMILY_PRIMARY, Typography.XL, Typography.SEMIBOLD),
        background=Colors.BG_CARD,
        foreground=Colors.TEXT_PRIMARY
    )
    
    style.configure(
        "Title.TLabel",
        font=(FONT_FAMILY_PRIMARY, Typography.XXL, Typography.BOLD),
        background=Colors.BG_CARD,
        foreground=Colors.TEXT_PRIMARY
    )
    
    style.configure(
        "Subtitle.TLabel",
        font=(FONT_FAMILY_PRIMARY, Typography.LG, Typography.MEDIUM),
        background=Colors.BG_CARD,
        foreground=Colors.TEXT_SECONDARY
    )
    
    style.configure(
        "Caption.TLabel",
        font=(FONT_FAMILY_PRIMARY, Typography.SM, Typography.NORMAL),
        background=Colors.BG_CARD,
        foreground=Colors.TEXT_MUTED
    )
    
    # Premium Button Styling
    style.configure(
        "Premium.TButton",
        font=(FONT_FAMILY_PRIMARY, Typography.MD, Typography.MEDIUM),
        padding=(Spacing.BUTTON_PADDING_X, Spacing.BUTTON_PADDING_Y),
        background=Colors.PRIMARY,
        foreground=Colors.TEXT_INVERSE,
        borderwidth=0,
        focuscolor="none"
    )
    
    style.map(
        "Premium.TButton",
        background=[
            ("active", Colors.PRIMARY_HOVER),
            ("pressed", Colors.PRIMARY_ACTIVE)
        ],
        foreground=[
            ("active", Colors.TEXT_INVERSE),
            ("pressed", Colors.TEXT_INVERSE)
        ]
    )
    
    # Success Button
    style.configure(
        "Success.TButton",
        font=(FONT_FAMILY_PRIMARY, Typography.MD, Typography.MEDIUM),
        padding=(Spacing.BUTTON_PADDING_X, Spacing.BUTTON_PADDING_Y),
        background=Colors.SUCCESS,
        foreground=Colors.TEXT_INVERSE,
        borderwidth=0,
        focuscolor="none"
    )
    
    style.map(
        "Success.TButton",
        background=[("active", Colors.SUCCESS_HOVER)]
    )
    
    # Secondary/Outline Button
    style.configure(
        "Secondary.TButton",
        font=(FONT_FAMILY_PRIMARY, Typography.MD, Typography.MEDIUM),
        padding=(Spacing.BUTTON_PADDING_X, Spacing.BUTTON_PADDING_Y),
        background=Colors.BG_CARD,
        foreground=Colors.TEXT_ACCENT,
        borderwidth=1,
        relief="solid",
        focuscolor="none"
    )
    
    style.map(
        "Secondary.TButton",
        background=[
            ("active", Colors.SURFACE_HOVER),
            ("pressed", Colors.SURFACE_ACTIVE)
        ]
    )
    
    # Danger Button
    style.configure(
        "Danger.TButton",
        font=(FONT_FAMILY_PRIMARY, Typography.MD, Typography.MEDIUM),
        padding=(Spacing.BUTTON_PADDING_X, Spacing.BUTTON_PADDING_Y),
        background=Colors.ERROR,
        foreground=Colors.TEXT_INVERSE,
        borderwidth=0,
        focuscolor="none"
    )
    
    style.map(
        "Danger.TButton",
        background=[("active", Colors.ERROR_HOVER)]
    )
    
    # Premium LabelFrame
    style.configure(
        "Premium.TLabelframe",
        background=Colors.BG_CARD,
        borderwidth=1,
        relief="solid",
        lightcolor=Colors.BORDER_DEFAULT,
        darkcolor=Colors.BORDER_DEFAULT
    )
    
    style.configure(
        "Premium.TLabelframe.Label",
        font=(FONT_FAMILY_PRIMARY, Typography.MD, Typography.SEMIBOLD),
        background=Colors.BG_CARD,
        foreground=Colors.TEXT_PRIMARY
    )
    
    # Premium Progressbar
    style.configure(
        "Premium.Horizontal.TProgressbar",
        background=Colors.PRIMARY,
        troughcolor=Colors.BG_TERTIARY,
        borderwidth=0,
        lightcolor=Colors.PRIMARY,
        darkcolor=Colors.PRIMARY
    )

# =============================================================================
# ENHANCED WINDOW CREATION FUNCTIONS
# =============================================================================

def create_premium_main_window():
    """Creates the main application window with premium styling."""
    root = tk.Tk()
    root.title("Ogresync")
    root.geometry("800x600")
    root.configure(bg=Colors.BG_PRIMARY)
    root.minsize(600, 400)
    
    # Set window icon
    try:
        if hasattr(sys, "_MEIPASS"):
            icon_path = os.path.join(sys._MEIPASS, "assets", "logo.png")
        else:
            icon_path = os.path.join("assets", "logo.png")
        
        if os.path.exists(icon_path):
            img = tk.PhotoImage(file=icon_path)
            root.iconphoto(True, img)
    except Exception:
        pass
    
    # Initialize fonts and styles
    init_font_config()
    setup_premium_styles()
    
    # Create main container with premium styling
    main_container = tk.Frame(root, bg=Colors.BG_PRIMARY)
    main_container.pack(fill=tk.BOTH, expand=True, padx=Spacing.XL, pady=Spacing.LG)
    
    # Header section with title and subtitle
    header_frame = tk.Frame(main_container, bg=Colors.BG_PRIMARY)
    header_frame.pack(fill=tk.X, pady=(0, Spacing.XL))
    
    # App title
    title_label = tk.Label(
        header_frame,
        text="Ogresync",
        font=(FONT_FAMILY_PRIMARY, Typography.H2, Typography.BOLD),
        bg=Colors.BG_PRIMARY,
        fg=Colors.TEXT_PRIMARY
    )
    title_label.pack(anchor=tk.W)
    
    # Subtitle
    subtitle_label = tk.Label(
        header_frame,
        text="Obsidian Vault Synchronization",
        font=(FONT_FAMILY_PRIMARY, Typography.MD, Typography.NORMAL),
        bg=Colors.BG_PRIMARY,
        fg=Colors.TEXT_SECONDARY
    )
    subtitle_label.pack(anchor=tk.W, pady=(2, 0))
    
    # Main content area using PremiumCard
    content_card = PremiumCard.create(main_container, padding=Spacing.XL)
    
    # Activity log section
    log_header = tk.Label(
        content_card,
        text=f"{Icons.FILE} Activity Log",
        font=(FONT_FAMILY_PRIMARY, Typography.LG, Typography.SEMIBOLD),
        bg=Colors.BG_CARD,
        fg=Colors.TEXT_PRIMARY
    )
    log_header.pack(anchor=tk.W, pady=(0, Spacing.SM))
    
    # Log text widget with premium styling
    log_frame = tk.Frame(content_card, bg=Colors.BG_CARD)
    log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, Spacing.LG))
    
    log_text_widget = scrolledtext.ScrolledText(
        log_frame,
        wrap=tk.WORD,
        height=15,
        state='disabled',
        font=(FONT_FAMILY_MONO, Typography.SM),
        bg=Colors.BG_SECONDARY,
        fg=Colors.TEXT_PRIMARY,
        insertbackground=Colors.TEXT_PRIMARY,
        selectbackground=Colors.PRIMARY_LIGHT,
        selectforeground=Colors.TEXT_PRIMARY,
        relief=tk.FLAT,
        borderwidth=1,
        highlightthickness=1,
        highlightcolor=Colors.BORDER_ACCENT,
        highlightbackground=Colors.BORDER_DEFAULT
    )
    log_text_widget.pack(fill=tk.BOTH, expand=True)
    
    # Progress section
    progress_header = tk.Label(
        content_card,
        text=f"{Icons.SYNC} Progress",
        font=(FONT_FAMILY_PRIMARY, Typography.MD, Typography.MEDIUM),
        bg=Colors.BG_CARD,
        fg=Colors.TEXT_PRIMARY
    )
    progress_header.pack(anchor=tk.W, pady=(0, Spacing.XS))
    
    # Progress bar with premium styling
    progress_frame = tk.Frame(content_card, bg=Colors.BG_CARD)
    progress_frame.pack(fill=tk.X, pady=(0, Spacing.SM))
    
    progress_bar_widget = ttk.Progressbar(
        progress_frame,
        style="Premium.Horizontal.TProgressbar",
        orient="horizontal",
        length=400,
        mode="determinate"
    )
    progress_bar_widget.pack(fill=tk.X)
    
    return root, log_text_widget, progress_bar_widget

# Enhanced conflict resolution dialog with premium styling
def create_premium_conflict_dialog(parent_window, conflict_files_text):
    """Creates a beautifully styled conflict resolution dialog."""
    dialog, main_frame = PremiumDialog.create_base(
        parent_window, 
        "Merge Conflict Detected", 
        width=500, 
        height=350
    )
    
    # Header with icon and title
    header_frame = tk.Frame(main_frame, bg=Colors.BG_PRIMARY)
    header_frame.pack(fill=tk.X, pady=(0, Spacing.LG))
    
    # Warning icon and title
    title_frame = tk.Frame(header_frame, bg=Colors.BG_PRIMARY)
    title_frame.pack(fill=tk.X)
    
    icon_label = tk.Label(
        title_frame,
        text=Icons.WARNING,
        font=(FONT_FAMILY_PRIMARY, Typography.H3),
        bg=Colors.BG_PRIMARY,
        fg=Colors.WARNING
    )
    icon_label.pack(side=tk.LEFT, padx=(0, Spacing.SM))
    
    title_label = tk.Label(
        title_frame,
        text="Merge Conflict Detected",
        font=(FONT_FAMILY_PRIMARY, Typography.XL, Typography.SEMIBOLD),
        bg=Colors.BG_PRIMARY,
        fg=Colors.TEXT_PRIMARY
    )
    title_label.pack(side=tk.LEFT, anchor=tk.W)
    
    # Content card
    content_card = PremiumCard.create(main_frame, padding=Spacing.LG)
    
    # Message text
    message_text = (
        f"Conflicts were found in the following files:\n\n"
        f"{conflict_files_text}\n\n"
        f"Please choose how you'd like to resolve these conflicts:"
    )
    
    message_label = tk.Label(
        content_card,
        text=message_text,
        font=(FONT_FAMILY_PRIMARY, Typography.MD),
        bg=Colors.BG_CARD,
        fg=Colors.TEXT_SECONDARY,
        justify=tk.LEFT,
        wraplength=420
    )
    message_label.pack(pady=(0, Spacing.LG), anchor=tk.W)
    
    # Resolution choice storage
    resolution = {"choice": None}
    
    def set_choice(choice):
        resolution["choice"] = choice
        dialog.destroy()
    
    # Action buttons with premium styling
    button_frame = tk.Frame(content_card, bg=Colors.BG_CARD)
    button_frame.pack(fill=tk.X, pady=(Spacing.MD, 0))
    
    # Create premium buttons
    btn_local = PremiumButton.create_secondary(
        button_frame, 
        "Keep Local", 
        lambda: set_choice("ours"),
        Icons.DOWNLOAD
    )
    btn_local.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, Spacing.SM))
    
    btn_remote = PremiumButton.create_secondary(
        button_frame,
        "Keep Remote", 
        lambda: set_choice("theirs"),
        Icons.UPLOAD
    )
    btn_remote.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(Spacing.SM, Spacing.SM))
    
    btn_manual = PremiumButton.create_primary(
        button_frame,
        "Merge Manually",
        lambda: set_choice("manual"),
        Icons.GEAR
    )
    btn_manual.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(Spacing.SM, 0))
    
    # Wait for user choice
    parent_window.wait_window(dialog)
    return resolution["choice"]

# Enhanced minimal UI for auto-sync with premium styling
def create_premium_minimal_ui(auto_run=False):
    """Creates a minimal UI with premium styling for auto-sync mode."""
    root = tk.Tk()
    root.title("Ogresync")
    root.geometry("600x400")
    root.configure(bg=Colors.BG_PRIMARY)
    root.resizable(False, False)
    
    # Set icon
    try:
        if hasattr(sys, "_MEIPASS"):
            icon_path = os.path.join(sys._MEIPASS, "assets", "logo.png")
        else:
            icon_path = os.path.join("assets", "logo.png")
        
        if os.path.exists(icon_path):
            img = tk.PhotoImage(file=icon_path)
            root.iconphoto(True, img)
    except Exception:
        pass  # Icon loading failed, continue without icon
    
    # Main content area
    main_frame = tk.Frame(root, bg=Colors.BG_PRIMARY)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=Spacing.LG, pady=Spacing.LG)
    
    # Header
    header_frame = tk.Frame(main_frame, bg=Colors.BG_PRIMARY)
    header_frame.pack(fill=tk.X, pady=(0, Spacing.LG))
    
    title_label = tk.Label(
        header_frame,
        text="🔄 Ogresync Auto-Sync",
        font=(FONT_FAMILY_PRIMARY, Typography.H1, Typography.BOLD),
        bg=Colors.BG_PRIMARY,
        fg=Colors.PRIMARY
    )
    title_label.pack()
    
    # Progress section
    progress_frame = tk.Frame(main_frame, bg=Colors.BG_PRIMARY)
    progress_frame.pack(fill=tk.X, pady=(0, Spacing.LG))
    
    progress_label = tk.Label(
        progress_frame,
        text="Sync Progress:",
        font=(FONT_FAMILY_PRIMARY, Typography.SM, Typography.BOLD),
        bg=Colors.BG_PRIMARY,
        fg=Colors.TEXT_PRIMARY
    )
    progress_label.pack(anchor=tk.W)
    
    progress_bar = ttk.Progressbar(
        progress_frame,
        mode='determinate',
        length=400,
        style="Premium.Horizontal.TProgressbar"
    )
    progress_bar.pack(fill=tk.X, pady=(Spacing.SM, 0))
    
    # Log area
    log_frame = tk.Frame(main_frame, bg=Colors.BG_PRIMARY)
    log_frame.pack(fill=tk.BOTH, expand=True)
    
    log_label = tk.Label(
        log_frame,
        text="Sync Log:",
        font=(FONT_FAMILY_PRIMARY, Typography.SM, Typography.BOLD),
        bg=Colors.BG_PRIMARY,
        fg=Colors.TEXT_PRIMARY
    )
    log_label.pack(anchor=tk.W)
    
    log_text = scrolledtext.ScrolledText(
        log_frame,
        height=12,
        font=(FONT_FAMILY_MONO, Typography.SM),
        bg=Colors.BG_CARD,
        fg=Colors.TEXT_PRIMARY,
        relief=tk.FLAT,
        borderwidth=1,
        highlightthickness=1,
        highlightcolor=Colors.BORDER_ACCENT,
        highlightbackground=Colors.BORDER_DEFAULT,
        insertbackground=Colors.PRIMARY,
        selectbackground=Colors.PRIMARY_LIGHT,
        selectforeground=Colors.TEXT_PRIMARY,
        state='disabled'
    )
    log_text.pack(fill=tk.BOTH, expand=True, pady=(Spacing.SM, 0))
    
    return root, log_text, progress_bar

# Enhanced wizard UI for setup with premium styling
def create_premium_wizard_ui():
    """Creates a premium setup wizard interface."""
    root = tk.Tk()
    root.title("Ogresync Setup")
    root.geometry("700x550")
    root.configure(bg=Colors.BG_PRIMARY)
    root.resizable(True, False)
    root.minsize(600, 500)
    
    # Set icon
    try:
        if hasattr(sys, "_MEIPASS"):
            icon_path = os.path.join(sys._MEIPASS, "assets", "logo.png")
        else:
            icon_path = os.path.join("assets", "logo.png")
        
        if os.path.exists(icon_path):
            img = tk.PhotoImage(file=icon_path)
            root.iconphoto(True, img)
    except Exception:
        pass  # Icon loading failed, continue without icon
    
    # Main content area with premium styling
    main_frame = tk.Frame(root, bg=Colors.BG_PRIMARY)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=Spacing.LG, pady=Spacing.LG)
    
    # Header
    header_frame = tk.Frame(main_frame, bg=Colors.BG_PRIMARY)
    header_frame.pack(fill=tk.X, pady=(0, Spacing.LG))
    
    title_label = tk.Label(
        header_frame,
        text="🔄 Ogresync Setup Wizard",
        font=(FONT_FAMILY_PRIMARY, Typography.H1, Typography.BOLD),
        bg=Colors.BG_PRIMARY,
        fg=Colors.PRIMARY
    )
    title_label.pack()
    
    subtitle_label = tk.Label(
        header_frame,
        text="Set up your Obsidian vault synchronization with GitHub",
        font=(FONT_FAMILY_PRIMARY, Typography.MD),
        bg=Colors.BG_PRIMARY,
        fg=Colors.TEXT_SECONDARY
    )
    subtitle_label.pack(pady=(Spacing.SM, 0))
    
    # Progress section
    progress_frame = tk.Frame(main_frame, bg=Colors.BG_PRIMARY)
    progress_frame.pack(fill=tk.X, pady=(0, Spacing.LG))
    
    progress_label = tk.Label(
        progress_frame,
        text="Setup Progress:",
        font=(FONT_FAMILY_PRIMARY, Typography.SM, Typography.BOLD),
        bg=Colors.BG_PRIMARY,
        fg=Colors.TEXT_PRIMARY
    )
    progress_label.pack(anchor=tk.W)
    
    progress_bar = ttk.Progressbar(
        progress_frame,
        mode='determinate',
        length=400,
        style="Premium.Horizontal.TProgressbar"
    )
    progress_bar.pack(fill=tk.X, pady=(Spacing.SM, 0))
    
    # Log area
    log_frame = tk.Frame(main_frame, bg=Colors.BG_PRIMARY)
    log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, Spacing.LG))
    
    log_label = tk.Label(
        log_frame,
        text="Setup Log:",
        font=(FONT_FAMILY_PRIMARY, Typography.SM, Typography.BOLD),
        bg=Colors.BG_PRIMARY,
        fg=Colors.TEXT_PRIMARY
    )
    log_label.pack(anchor=tk.W)
    
    log_text = scrolledtext.ScrolledText(
        log_frame,
        height=12,
        font=(FONT_FAMILY_MONO, Typography.SM),
        bg=Colors.BG_CARD,
        fg=Colors.TEXT_PRIMARY,
        relief=tk.FLAT,
        borderwidth=1,
        highlightthickness=1,
        highlightcolor=Colors.BORDER_ACCENT,
        highlightbackground=Colors.BORDER_DEFAULT,
        insertbackground=Colors.PRIMARY,
        selectbackground=Colors.PRIMARY_LIGHT,
        selectforeground=Colors.TEXT_PRIMARY,
        state='disabled'
    )
    log_text.pack(fill=tk.BOTH, expand=True, pady=(Spacing.SM, 0))
    
    # Control buttons
    button_frame = tk.Frame(main_frame, bg=Colors.BG_PRIMARY)
    button_frame.pack(fill=tk.X)
    
    # SSH key generation button
    gen_btn = PremiumButton.create_secondary(
        button_frame,
        "Generate SSH Key",
        None,  # Command will be set later
        icon=Icons.SECURITY,
        size="md"
    )
    gen_btn.pack(side=tk.LEFT, padx=(0, Spacing.SM))
    
    # Copy SSH key button
    copy_btn = PremiumButton.create_secondary(
        button_frame,
        "Copy SSH Key",
        None,  # Command will be set later
        icon=Icons.COPY,
        size="md"
    )
    copy_btn.pack(side=tk.LEFT, padx=(0, Spacing.SM))
    
    # Test SSH button
    test_ssh_btn = PremiumButton.create_primary(
        button_frame,
        "Test SSH Connection",
        None,  # Command will be set later
        icon=Icons.SUCCESS,
        size="md"
    )
    test_ssh_btn.pack(side=tk.LEFT, padx=(0, Spacing.SM))
    
    # Exit button
    exit_btn = PremiumButton.create_danger(
        button_frame,
        "Exit",
        None,  # Command will be set later
        size="md"
    )
    exit_btn.pack(side=tk.RIGHT)
    
    return root, log_text, progress_bar, gen_btn, copy_btn, test_ssh_btn, exit_btn

# =============================================================================
# ENHANCED DIALOG SYSTEM
# =============================================================================

def show_premium_info(title, message, parent=None):
    """Show an info message with premium styling."""
    dialog, main_frame = PremiumDialog.create_base(parent, title, 450, 300) # Increased height from 250
    
    # Icon and message
    content_frame = tk.Frame(main_frame, bg=Colors.BG_PRIMARY)
    content_frame.pack(fill=tk.BOTH, expand=True, pady=Spacing.LG)
    
    # Info icon
    icon_label = tk.Label(
        content_frame,
        text=Icons.INFO,
        font=(FONT_FAMILY_PRIMARY, Typography.H1),
        bg=Colors.BG_PRIMARY,
        fg=Colors.INFO
    )
    icon_label.pack(pady=(0, Spacing.MD))
    
    # Message
    message_label = tk.Label(
        content_frame,
        text=message,
        font=(FONT_FAMILY_PRIMARY, Typography.MD),
        bg=Colors.BG_PRIMARY,
        fg=Colors.TEXT_PRIMARY,
        wraplength=380,
        justify=tk.CENTER
    )
    message_label.pack(pady=(0, Spacing.LG))
    
    # OK button
    ok_btn = PremiumButton.create_primary(
        content_frame,
        "OK",
        lambda: dialog.destroy(),
        size="md"
    )
    ok_btn.pack(pady=Spacing.SM) # Added pady
    
    dialog.wait_window()
    return True

def show_premium_error(title, message, parent=None):
    """Show an error message with premium styling."""
    dialog, main_frame = PremiumDialog.create_base(parent, title, 450, 300) # Increased height from 250
    
    content_frame = tk.Frame(main_frame, bg=Colors.BG_PRIMARY)
    content_frame.pack(fill=tk.BOTH, expand=True, pady=Spacing.LG)
    
    # Error icon
    icon_label = tk.Label(
        content_frame,
        text=Icons.ERROR,
        font=(FONT_FAMILY_PRIMARY, Typography.H1),
        bg=Colors.BG_PRIMARY,
        fg=Colors.ERROR
    )
    icon_label.pack(pady=(0, Spacing.MD))
    
    # Message
    message_label = tk.Label(
        content_frame,
        text=message,
        font=(FONT_FAMILY_PRIMARY, Typography.MD),
        bg=Colors.BG_PRIMARY,
        fg=Colors.TEXT_PRIMARY,
        wraplength=380,
        justify=tk.CENTER
    )
    message_label.pack(pady=(0, Spacing.LG))
    
    # OK button
    ok_btn = PremiumButton.create_primary(
        content_frame,
        "OK",
        lambda: dialog.destroy(),
        size="md"
    )
    ok_btn.pack(pady=Spacing.SM) # Added pady
    
    dialog.wait_window()
    return True

def ask_premium_yes_no(title, message, parent=None):
    """Ask a yes/no question with premium styling."""
    dialog, main_frame = PremiumDialog.create_base(parent, title, 500, 350)
    
    result = {"answer": False}
    
    # Content frame with proper spacing
    content_frame = tk.Frame(main_frame, bg=Colors.BG_PRIMARY)
    content_frame.pack(fill=tk.BOTH, expand=True, padx=Spacing.LG, pady=Spacing.LG)
    
    # Question icon
    icon_label = tk.Label(
        content_frame,
        text="❓",
        font=(FONT_FAMILY_PRIMARY, Typography.H1, Typography.BOLD),
        bg=Colors.BG_PRIMARY,
        fg=Colors.INFO
    )
    icon_label.pack(pady=(0, Spacing.MD))
    
    # Message
    message_label = tk.Label(
        content_frame,
        text=message,
        font=(FONT_FAMILY_PRIMARY, Typography.MD),
        bg=Colors.BG_PRIMARY,
        fg=Colors.TEXT_PRIMARY,
        wraplength=400,
        justify=tk.CENTER
    )
    message_label.pack(pady=(0, Spacing.XL))
    
    # Button container with fixed dimensions
    button_container = tk.Frame(content_frame, bg=Colors.BG_PRIMARY, height=60)
    button_container.pack(fill=tk.X, side=tk.BOTTOM)
    button_container.pack_propagate(False)
    
    # Center the button area within the container
    button_frame = tk.Frame(button_container, bg=Colors.BG_PRIMARY)
    button_frame.pack(expand=True)
    
    def yes_clicked():
        result["answer"] = True
        dialog.destroy()
    
    def no_clicked():
        result["answer"] = False
        dialog.destroy()
    
    # Create buttons with guaranteed minimum size and explicit dimensions
    yes_btn = tk.Button(
        button_frame,
        text="Yes",
        command=yes_clicked,
        font=(FONT_FAMILY_PRIMARY, Typography.MD, Typography.MEDIUM),
        bg=Colors.PRIMARY,
        fg=Colors.TEXT_INVERSE,
        activebackground=Colors.PRIMARY_HOVER,
        activeforeground=Colors.TEXT_INVERSE,
        relief=tk.FLAT,
        borderwidth=0,
        cursor="hand2",
        width=10,  # Increased width
        height=2   # Increased height
    )
    yes_btn.pack(side=tk.LEFT, padx=(0, Spacing.LG), pady=Spacing.MD, ipadx=10, ipady=5)
    
    no_btn = tk.Button(
        button_frame,
        text="No",
        command=no_clicked,
        font=(FONT_FAMILY_PRIMARY, Typography.MD, Typography.MEDIUM),
        bg=Colors.BG_CARD,
        fg=Colors.TEXT_ACCENT,
        activebackground=Colors.SURFACE_HOVER,
        activeforeground=Colors.PRIMARY_HOVER,
        relief=tk.SOLID,
        borderwidth=1,
        cursor="hand2",
        width=10,  # Increased width
        height=2   # Increased height
    )
    no_btn.pack(side=tk.LEFT, pady=Spacing.MD, ipadx=10, ipady=5)
    
    # Add hover effects
    def yes_enter(e):
        yes_btn.config(bg=Colors.PRIMARY_HOVER)
    def yes_leave(e):
        yes_btn.config(bg=Colors.PRIMARY)
    
    def no_enter(e):
        no_btn.config(bg=Colors.SURFACE_HOVER, fg=Colors.PRIMARY_HOVER)
    def no_leave(e):
        no_btn.config(bg=Colors.BG_CARD, fg=Colors.TEXT_ACCENT)
    
    yes_btn.bind("<Enter>", yes_enter)
    yes_btn.bind("<Leave>", yes_leave)
    no_btn.bind("<Enter>", no_enter)
    no_btn.bind("<Leave>", no_leave)
    
    # Focus and keyboard support
    yes_btn.focus_set()
    dialog.bind('<Return>', lambda e: yes_clicked())
    dialog.bind('<Escape>', lambda e: no_clicked())
    
    dialog.wait_window()
    return result["answer"]

def ask_premium_string(title, prompt, initial_value="", parent=None, icon=None): # Added icon parameter
    """Ask for string input with premium styling."""
    dialog, main_frame = PremiumDialog.create_base(parent, title, 500, 300)
    
    result = {"value": None}
    
    content_frame = tk.Frame(main_frame, bg=Colors.BG_PRIMARY)
    content_frame.pack(fill=tk.BOTH, expand=True, pady=Spacing.LG)
    
    # Input icon
    icon_label = tk.Label(
        content_frame,
        text=icon if icon else "📝",  # Use provided icon or default
        font=(FONT_FAMILY_PRIMARY, Typography.H2),
        bg=Colors.BG_PRIMARY,
        fg=Colors.PRIMARY
    )
    icon_label.pack(pady=(0, Spacing.MD))
    
    # Prompt message
    prompt_label = tk.Label(
        content_frame,
        text=prompt,
        font=(FONT_FAMILY_PRIMARY, Typography.MD),
        bg=Colors.BG_PRIMARY,
        fg=Colors.TEXT_PRIMARY,
        wraplength=420,
        justify=tk.CENTER
    )
    prompt_label.pack(pady=(0, Spacing.LG))
    
    # Text input with premium styling
    input_frame = tk.Frame(content_frame, bg=Colors.BG_PRIMARY)
    input_frame.pack(fill=tk.X, pady=(0, Spacing.LG))
    
    entry_var = tk.StringVar(value=initial_value)
    entry = tk.Entry(
        input_frame,
        textvariable=entry_var,
        font=(FONT_FAMILY_PRIMARY, Typography.MD),
        bg=Colors.BG_CARD,
        fg=Colors.TEXT_PRIMARY,
        relief=tk.FLAT,
        borderwidth=2,
        highlightthickness=2,
        highlightcolor=Colors.BORDER_ACCENT,
        highlightbackground=Colors.BORDER_DEFAULT,
        insertbackground=Colors.PRIMARY,
        selectbackground=Colors.PRIMARY_LIGHT,
        selectforeground=Colors.TEXT_PRIMARY
    )
    entry.pack(fill=tk.X, ipady=8, padx=Spacing.MD)
    entry.focus_set()
    entry.select_range(0, tk.END)
    
    # Button frame
    button_frame = tk.Frame(content_frame, bg=Colors.BG_PRIMARY)
    button_frame.pack(pady=(Spacing.MD, 0))
    
    def submit():
        result["value"] = entry_var.get().strip()
        dialog.destroy()
    
    def cancel():
        result["value"] = None
        dialog.destroy()
    
    # Bind Enter key to submit
    def on_enter(event):
        submit()
    
    dialog.bind('<Return>', on_enter)
    dialog.bind('<KP_Enter>', on_enter)
    
    # Create buttons
    ok_btn = PremiumButton.create_primary(
        button_frame,
        "OK",
        submit,
        icon=Icons.SUCCESS,
        size="md"
    )
    ok_btn.pack(side=tk.LEFT, padx=(0, Spacing.SM))
    
    cancel_btn = PremiumButton.create_secondary(
        button_frame,
        "Cancel",
        cancel,
        size="md"
    )
    cancel_btn.pack(side=tk.LEFT)
    
    dialog.wait_window()
    return result["value"]

# =============================================================================
# BACKWARD COMPATIBILITY WRAPPERS
# =============================================================================

# Legacy function wrappers for backward compatibility
def create_main_window():
    """Legacy wrapper for create_premium_main_window."""
    return create_premium_main_window()

def create_conflict_resolution_dialog(parent_window, conflict_files_text):
    """Legacy wrapper for create_premium_conflict_dialog."""
    return create_premium_conflict_dialog(parent_window, conflict_files_text)

def create_minimal_ui(auto_run=False):
    """Legacy wrapper for create_premium_minimal_ui."""
    return create_premium_minimal_ui(auto_run)

def create_wizard_ui():
    """Legacy wrapper for create_premium_wizard_ui."""
    return create_premium_wizard_ui()

def show_info_message(title, message, parent=None):
    """Legacy wrapper for show_premium_info."""
    return show_premium_info(title, message, parent)

def show_error_message(title, message, parent=None):
    """Legacy wrapper for show_premium_error."""
    return show_premium_error(title, message, parent)

def ask_yes_no(title, message, parent=None):
    """Legacy wrapper for ask_premium_yes_no."""
    return ask_premium_yes_no(title, message, parent)

def ask_string_dialog(title, prompt, initial_value="", parent=None, icon=None): # Added icon parameter
    """Legacy wrapper for ask_premium_string."""
    return ask_premium_string(title, prompt, initial_value, parent, icon) # Pass icon

def ask_file_dialog(title, filetypes=None, parent=None):
    """Open file selection dialog (fallback to tkinter)."""
    from tkinter import filedialog
    if filetypes is None:
        filetypes = [("All files", "*.*")]
    return filedialog.askopenfilename(title=title, parent=parent, filetypes=filetypes)

def ask_directory_dialog(title, parent=None):
    """Open directory selection dialog (fallback to tkinter)."""
    from tkinter import filedialog
    return filedialog.askdirectory(title=title, parent=parent)

# Enhanced repository conflict resolution dialog
def create_repository_conflict_dialog(parent_window, message, analysis):
    """Creates a dialog for resolving repository content conflicts during setup."""
    # Create the dialog window
    dialog = tk.Toplevel(parent_window)
    dialog.title("Repository Content Conflict")
    dialog.transient(parent_window)
    dialog.grab_set()
    dialog.resizable(False, False)
    dialog.configure(bg="#FAFBFC")
    
    # Center the dialog
    dialog.update_idletasks()
    width, height = 650, 550
    x = (dialog.winfo_screenwidth() // 2) - (width // 2)
    y = (dialog.winfo_screenheight() // 2) - (height // 2)
    dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    # Main container
    main_frame = tk.Frame(dialog, bg="#FAFBFC")
    main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    # Header with icon and title
    header_frame = tk.Frame(main_frame, bg="#FAFBFC")
    header_frame.pack(fill=tk.X, pady=(0, 20))
    
    title_label = tk.Label(
        header_frame,
        text="⚠️ Repository Content Conflict",
        font=("Arial", 16, "bold"),
        bg="#FAFBFC",
        fg="#1E293B"
    )
    title_label.pack()
    
    # Content area
    content_frame = tk.Frame(main_frame, bg="#FFFFFF", relief=tk.RAISED, borderwidth=1)
    content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
    
    # Padding inside content
    inner_frame = tk.Frame(content_frame, bg="#FFFFFF")
    inner_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    # Message
    message_label = tk.Label(
        inner_frame,
        text=message,
        font=("Arial", 12),
        bg="#FFFFFF",
        fg="#475569",
        wraplength=580,
        justify=tk.LEFT
    )
    message_label.pack(pady=(0, 20))
    
    # File details
    if analysis["local_files"]:
        local_label = tk.Label(
            inner_frame,
            text=f"📁 Local files ({len(analysis['local_files'])} items):",
            font=("Arial", 10, "bold"),
            bg="#FFFFFF",
            fg="#1E293B"
        )
        local_label.pack(anchor=tk.W)
        
        local_preview = analysis["local_files"][:3]
        preview_text = ", ".join(local_preview)
        if len(analysis["local_files"]) > 3:
            preview_text += f" and {len(analysis['local_files']) - 3} more..."
        
        local_files_label = tk.Label(
            inner_frame,
            text=preview_text,
            font=("Arial", 9),
            bg="#FFFFFF",
            fg="#64748B",
            wraplength=580,
            justify=tk.LEFT
        )
        local_files_label.pack(anchor=tk.W, pady=(2, 10))
    
    if analysis["remote_files"]:
        remote_label = tk.Label(
            inner_frame,
            text=f"🌐 Remote files ({len(analysis['remote_files'])} items):",
            font=("Arial", 10, "bold"),
            bg="#FFFFFF",
            fg="#1E293B"
        )
        remote_label.pack(anchor=tk.W)
        
        remote_preview = analysis["remote_files"][:3]
        preview_text = ", ".join(remote_preview)
        if len(analysis["remote_files"]) > 3:
            preview_text += f" and {len(analysis['remote_files']) - 3} more..."
        
        remote_files_label = tk.Label(
            inner_frame,
            text=preview_text,
            font=("Arial", 9),
            bg="#FFFFFF",
            fg="#64748B",
            wraplength=580,
            justify=tk.LEFT
        )
        remote_files_label.pack(anchor=tk.W, pady=(2, 0))
    
    # Choice storage
    choice = {"value": None}
    
    def set_choice(selected_choice):
        choice["value"] = selected_choice
        dialog.destroy()
    
    # Button area
    button_frame = tk.Frame(inner_frame, bg="#FFFFFF")
    button_frame.pack(fill=tk.X, pady=(20, 0))
    
    # Button 1: Smart Merge (Recommended)
    merge_btn = tk.Button(
        button_frame,
        text="🔄 Smart Merge (Recommended)",
        command=lambda: set_choice("merge"),
        font=("Arial", 11, "bold"),
        bg="#6366F1",
        fg="#FFFFFF",
        activebackground="#4F46E5",
        activeforeground="#FFFFFF",
        relief=tk.FLAT,
        borderwidth=0,
        cursor="hand2",
        padx=20,
        pady=12
    )
    merge_btn.pack(fill=tk.X, pady=(0, 5))
    
    merge_desc = tk.Label(
        button_frame,
        text="Combines both local and remote files. Conflicts will be marked for manual review.",
        font=("Arial", 9),
        bg="#FFFFFF",
        fg="#64748B",
        wraplength=580
    )
    merge_desc.pack(anchor=tk.W, pady=(2, 15))
    
    # Button 2: Keep Local Files Only
    local_btn = tk.Button(
        button_frame,
        text="📁 Keep Local Files Only",
        command=lambda: set_choice("local"),
        font=("Arial", 11),
        bg="#FFFFFF",
        fg="#6366F1",
        activebackground="#F1F5F9",
        activeforeground="#4F46E5",
        relief=tk.SOLID,
        borderwidth=1,
        cursor="hand2",
        padx=20,
        pady=12
    )
    local_btn.pack(fill=tk.X, pady=(0, 5))
    
    local_desc = tk.Label(
        button_frame,
        text="Overwrites remote repository with your local files.",
        font=("Arial", 9),
        bg="#FFFFFF",
        fg="#64748B",
        wraplength=580
    )
    local_desc.pack(anchor=tk.W, pady=(2, 15))
    
    # Button 3: Use Remote Files Only
    remote_btn = tk.Button(
        button_frame,
        text="🌐 Use Remote Files Only", 
        command=lambda: set_choice("remote"),
        font=("Arial", 11),
        bg="#FFFFFF",
        fg="#6366F1",
        activebackground="#F1F5F9",
        activeforeground="#4F46E5",
        relief=tk.SOLID,
        borderwidth=1,
        cursor="hand2",
        padx=20,
        pady=12
    )
    remote_btn.pack(fill=tk.X, pady=(0, 5))
    
    remote_desc = tk.Label(
        button_frame,
        text="Downloads remote files and backs up your local files.",
        font=("Arial", 9),
        bg="#FFFFFF",
        fg="#64748B",
        wraplength=580
    )
    remote_desc.pack(anchor=tk.W)
    
    # Wait for user choice
    parent_window.wait_window(dialog)
    return choice["value"]

# Enhanced dialog for handling missing vault directories with recovery options
def create_vault_recovery_dialog(parent_window, missing_vault_path):
    """Creates a dialog for handling missing vault directories."""
    # Create the dialog window
    dialog = tk.Toplevel(parent_window)
    dialog.title("Vault Directory Not Found")
    dialog.transient(parent_window)
    dialog.grab_set()
    dialog.resizable(False, False)
    dialog.configure(bg="#FAFBFC")
    
    # Center the dialog
    dialog.update_idletasks()
    width, height = 600, 450
    x = (dialog.winfo_screenwidth() // 2) - (width // 2)
    y = (dialog.winfo_screenheight() // 2) - (height // 2)
    dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    # Main container
    main_frame = tk.Frame(dialog, bg="#FAFBFC")
    main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    # Header with icon and title
    header_frame = tk.Frame(main_frame, bg="#FAFBFC")
    header_frame.pack(fill=tk.X, pady=(0, 20))
    
    title_label = tk.Label(
        header_frame,
        text="⚠️ Vault Directory Missing",
        font=("Arial", 16, "bold"),
        bg="#FAFBFC",
        fg="#DC2626"
    )
    title_label.pack()
    
    # Content area
    content_frame = tk.Frame(main_frame, bg="#FFFFFF", relief=tk.RAISED, borderwidth=1)
    content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
    
    # Padding inside content
    inner_frame = tk.Frame(content_frame, bg="#FFFFFF")
    inner_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    # Message
    message_text = (
        f"The configured vault directory cannot be found:\n\n"
        f"📁 {missing_vault_path}\n\n"
        f"This might have happened if the directory was moved, deleted, or renamed.\n"
        f"Please choose how you'd like to proceed:"
    )
    
    message_label = tk.Label(
        inner_frame,
        text=message_text,
        font=("Arial", 12),
        bg="#FFFFFF",
        fg="#475569",
        wraplength=520,
        justify=tk.LEFT
    )
    message_label.pack(pady=(0, 20))
    
    # Choice storage
    choice = {"value": None}
    
    def set_choice(selected_choice):
        choice["value"] = selected_choice
        dialog.destroy()
    
    # Button area
    button_frame = tk.Frame(inner_frame, bg="#FFFFFF")
    button_frame.pack(fill=tk.X, pady=(20, 0))
    
    # Button 1: Recreate Directory (Recommended)
    recreate_btn = tk.Button(
        button_frame,
        text="🔄 Recreate Directory (Recommended)",
        command=lambda: set_choice("recreate"),
        font=("Arial", 11, "bold"),
        bg="#059669",
        fg="#FFFFFF",
        activebackground="#047857",
        activeforeground="#FFFFFF",
        relief=tk.FLAT,
        borderwidth=0,
        cursor="hand2",
        padx=20,
        pady=12
    )
    recreate_btn.pack(fill=tk.X, pady=(0, 5))
    
    recreate_desc = tk.Label(
        button_frame,
        text="Creates the vault directory at the original location and downloads remote files.",
        font=("Arial", 9),
        bg="#FFFFFF",
        fg="#64748B",
        wraplength=520
    )
    recreate_desc.pack(anchor=tk.W, pady=(2, 15))
    
    # Button 2: Select New Directory
    select_btn = tk.Button(
        button_frame,
        text="📁 Choose Different Directory",
        command=lambda: set_choice("select_new"),
        font=("Arial", 11),
        bg="#FFFFFF",
        fg="#6366F1",
        activebackground="#F1F5F9",
        activeforeground="#4F46E5",
        relief=tk.SOLID,
        borderwidth=1,
        cursor="hand2",
        padx=20,
        pady=12
    )
    select_btn.pack(fill=tk.X, pady=(0, 5))
    
    select_desc = tk.Label(
        button_frame,
        text="Browse and select a different directory to use as your vault.",
        font=("Arial", 9),
        bg="#FFFFFF",
        fg="#64748B",
        wraplength=520
    )
    select_desc.pack(anchor=tk.W, pady=(2, 15))
    
    # Button 3: Run Setup Again
    setup_btn = tk.Button(
        button_frame,
        text="⚙️ Run Setup Wizard Again",
        command=lambda: set_choice("setup"),
        font=("Arial", 11),
        bg="#FFFFFF",
        fg="#6366F1",
        activebackground="#F1F5F9",
        activeforeground="#4F46E5",
        relief=tk.SOLID,
        borderwidth=1,
        cursor="hand2",
        padx=20,
        pady=12
    )
    setup_btn.pack(fill=tk.X, pady=(0, 5))
    
    setup_desc = tk.Label(
        button_frame,
        text="Start the complete setup process from the beginning.",
        font=("Arial", 9),
        bg="#FFFFFF",
        fg="#64748B",
        wraplength=520
    )
    setup_desc.pack(anchor=tk.W)
    
    # Wait for user choice
    parent_window.wait_window(dialog)
    return choice["value"]
