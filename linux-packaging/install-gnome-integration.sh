#!/bin/bash
# Ogresync AppImage GNOME Integration Script
# This script helps integrate the Ogresync AppImage with GNOME desktop

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APPIMAGE_PATH="$SCRIPT_DIR/Ogresync-x86_64.AppImage"
USER_APPLICATIONS_DIR="$HOME/.local/share/applications"
USER_ICONS_DIR="$HOME/.local/share/icons/hicolor"

echo "🔧 Ogresync GNOME Integration"
echo "================================"

# Check if AppImage exists
if [ ! -f "$APPIMAGE_PATH" ]; then
    echo "❌ AppImage not found at: $APPIMAGE_PATH"
    exit 1
fi

echo "✅ Found AppImage at: $APPIMAGE_PATH"

# Make AppImage executable
chmod +x "$APPIMAGE_PATH"

# Create directories
mkdir -p "$USER_APPLICATIONS_DIR"
mkdir -p "$USER_ICONS_DIR"/{16x16,32x32,48x48,64x64,128x128,256x256,512x512}/apps

# Extract icon from AppImage
echo "📄 Extracting and installing desktop file..."

# Create desktop file with absolute path
cat > "$USER_APPLICATIONS_DIR/ogresync.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Ogresync
GenericName=Obsidian Sync Alternative
Comment=Git-based vault synchronization for Obsidian
Exec=$APPIMAGE_PATH
Icon=ogresync
Categories=Office;Utility;
Keywords=obsidian;sync;git;vault;notes;markdown;
Terminal=false
StartupWMClass=Ogresync
StartupNotify=true
NoDisplay=false
EOF

echo "🎨 Installing icon files..."

# Extract icon from AppImage and install to user directory
if command -v unzip >/dev/null 2>&1; then
    # Try to extract icon from AppImage
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR"
    
    # Extract AppImage
    "$APPIMAGE_PATH" --appimage-extract >/dev/null 2>&1 || true
    
    if [ -f "squashfs-root/ogresync.png" ]; then
        # Copy icon to all standard sizes
        for size in 16x16 32x32 48x48 64x64 128x128 256x256 512x512; do
            cp "squashfs-root/ogresync.png" "$USER_ICONS_DIR/$size/apps/ogresync.png"
        done
        echo "✅ Icons installed successfully"
    else
        echo "⚠️  Could not extract icon from AppImage"
    fi
    
    # Cleanup
    cd "$SCRIPT_DIR"
    rm -rf "$TEMP_DIR"
else
    echo "⚠️  unzip not found, cannot extract icon"
fi

# Update icon cache
echo "🔄 Updating icon cache..."
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "$USER_ICONS_DIR" 2>/dev/null || true
    echo "✅ Icon cache updated"
else
    echo "⚠️  gtk-update-icon-cache not found"
fi

# Update desktop database
echo "🔄 Updating desktop database..."
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$USER_APPLICATIONS_DIR" 2>/dev/null || true
    echo "✅ Desktop database updated"
else
    echo "⚠️  update-desktop-database not found"
fi

echo ""
echo "🎉 Integration complete!"
echo ""
echo "📋 What was done:"
echo "   • AppImage made executable"
echo "   • Desktop file installed to: $USER_APPLICATIONS_DIR/ogresync.desktop"
echo "   • Icons installed to user icon directory"
echo "   • Icon cache and desktop database updated"
echo ""
echo "🚀 You should now be able to:"
echo "   • Find Ogresync in your application menu"
echo "   • See the proper icon in GNOME"
echo "   • Launch Ogresync from the Activities overview"
echo ""
echo "💡 If the icon still doesn't appear, try:"
echo "   • Log out and log back in"
echo "   • Run: gsettings reset org.gnome.desktop.interface icon-theme"
echo "   • Restart GNOME Shell: Alt+F2, type 'r', press Enter"
