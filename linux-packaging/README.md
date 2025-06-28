# Ogresync Linux Packaging

This directory contains the Linux packaging infrastructure for building distributable AppImage files of Ogresync.

## Overview

The Linux packaging system provides:
- **Cross-distribution compatibility** through AppImage format
- **Professional packaging** following Linux desktop standards
- **Self-contained executables** with all dependencies included
- **Automated build process** with dependency checking
- **Quality assurance** through verification testing
- **Clean separation** from Windows packaging infrastructure

## Quick Start

### Prerequisites

```bash
# Install PyInstaller (if not already installed)
pip install pyinstaller

# On Fedora (for FUSE support)
sudo dnf install fuse

# On Ubuntu/Debian
sudo apt install fuse
```

### Building

From the repository root:

```bash
# Clean build (recommended)
cd linux-packaging
python build_appimage.py --clean --test

# Quick rebuild
python build_appimage.py

# Verbose output for debugging
python build_appimage.py --clean --verbose
```

## Usage

```bash
# Make executable (if not already)
chmod +x linux-packaging/Ogresync-x86_64.AppImage

# Run the application
./linux-packaging/Ogresync-x86_64.AppImage

# Or run directly from the linux-packaging directory
cd linux-packaging
./Ogresync-x86_64.AppImage
```

## Distribution

The resulting AppImage is a single executable file that can be distributed to users. It includes all dependencies and works on most Linux distributions.

## Architecture

### AppImage Structure

```
AppDir/
├── AppRun                 # Main execution script
├── ogresync.desktop      # Desktop integration file
├── ogresync.png          # Application icon
└── usr/
    └── bin/
        └── ogresync      # Main executable (from PyInstaller)
```

### Build Process

1. **Dependency Check**: Verify Python, PyInstaller, and FUSE
2. **Tool Download**: Download appimagetool if not available
3. **PyInstaller Build**: Create standalone executable
4. **AppDir Creation**: Set up AppImage directory structure
5. **AppImage Assembly**: Use appimagetool to create final AppImage
6. **Verification**: Test the AppImage functionality

## Comparison with Windows Packaging

| Feature | Windows | Linux |
|---------|---------|--------|
| Package Format | Standalone EXE | AppImage |
| Branch | `windows-packaging` | `linux-packaging` |
| Build Tool | PyInstaller + custom scripts | PyInstaller + AppImage tools |
| Console Hiding | Required (`packaging_utils.py`) | Not needed |
| Dependencies | Bundled in EXE | Bundled in AppImage |
| Icon Handling | ICO embedded in EXE | PNG + Desktop file |
| Distribution | Single EXE file | Single AppImage file |
| Platform Utils | `packaging_utils.py` | `linux_packaging_utils.py` |

## Future Enhancements

1. **Flatpak Package**: For better desktop integration
2. **Snap Package**: For Ubuntu users
3. **Auto-update**: Built-in update mechanism
4. **Code Signing**: For security verification
5. **Multi-arch**: ARM64 support

## Troubleshooting

### Common Issues

1. **FUSE not found**: Install FUSE package for your distribution
2. **AppImage won't run**: Check file permissions (`chmod +x`)
3. **Large file size**: Consider excluding unnecessary dependencies
4. **Missing dependencies**: Check PyInstaller hidden imports

### Debug Mode

```bash
# From repository root
cd linux-packaging
python build_appimage.py --verbose

# Or using the shell wrapper
./build.sh --verbose
```

### Manual Testing

```bash
# Extract AppImage contents for inspection
./linux-packaging/Ogresync-x86_64.AppImage --appimage-extract
ls squashfs-root/
```

## Related Files

- `build_appimage.py` - Main build script with full automation
- `linux_packaging_utils.py` - Linux-specific packaging utilities
- `build.sh` - Simple shell wrapper for build script
- `test_linux_packaging.py` - Linux packaging verification tests
- `README.md` - This documentation
- `.gitignore` - Linux packaging build artifacts exclusions

**Note**: PyInstaller spec files are auto-generated during build process.

## Contributing

When making changes to the Linux packaging:

1. **Test on multiple distributions** (Ubuntu, Fedora, openSUSE, etc.)
2. **Verify AppImage portability** across different Linux versions
3. **Update documentation** to reflect any changes
4. **Test build process** with clean environment
5. **Consider cross-platform compatibility** with Windows packaging

### Development Workflow

1. Work on the `Development` branch for testing new features
2. Packaging changes should be made in the `linux-packaging` branch
3. Ensure changes don't conflict with `windows-packaging` branch
4. Test thoroughly before merging

### Branch Structure

- **`main`**: Clean, user-ready code (no development files)
- **`Development`**: Full development environment with tests
- **`linux-packaging`**: Linux-specific packaging (this branch)
- **`windows-packaging`**: Windows-specific packaging

---

*This packaging system is designed to complement the existing Windows packaging while providing Linux users with a native, portable installation option. The clean branch structure ensures platform-specific code remains separated and maintainable.*
