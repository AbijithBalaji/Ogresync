# Ogresync Linux Packaging

This directory contains the Linux packaging system for Ogresync, specifically for creating AppImage packages.

## Quick Start

### Prerequisites

- Python 3.8+
- PyInstaller (`pip install pyinstaller`)
- FUSE (for running AppImages)
  - Ubuntu/Debian: `sudo apt install fuse`
  - Fedora: `sudo dnf install fuse`
  - Arch: `sudo pacman -S fuse`

### Building the AppImage

1. **Simple build:**
   ```bash
   ./linux-packaging/build.sh
   ```

2. **Advanced build with options:**
   ```bash
   python3 linux-packaging/build_appimage.py --clean --test --verbose
   ```

3. **Clean build:**
   ```bash
   python3 linux-packaging/build_appimage.py --clean
   ```

## Build Options

- `--clean`: Remove previous build artifacts
- `--test`: Run verification tests after building
- `--verbose`: Enable detailed output during build
- `--arch`: Specify target architecture (default: x86_64)

## Output

The build process creates:

- `linux-packaging/Ogresync-x86_64.AppImage` - The final AppImage
- `linux-packaging/AppDir/` - Temporary build directory
- `dist/` - PyInstaller output directory

## Testing the AppImage

```bash
# Make executable (if not already)
chmod +x linux-packaging/Ogresync-x86_64.AppImage

# Run the application
./linux-packaging/Ogresync-x86_64.AppImage
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
| Console Hiding | Required | Not needed |
| Dependencies | Bundled | Bundled |
| Icon Handling | ICO in EXE | PNG + Desktop file |
| Distribution | Single EXE | Single AppImage |

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
python3 linux-packaging/build_appimage.py --verbose
```

### Manual Testing

```bash
# Extract AppImage contents for inspection
./linux-packaging/Ogresync-x86_64.AppImage --appimage-extract
ls squashfs-root/
```

## Related Files

- `build_appimage.py` - Main build script
- `build.sh` - Simple shell wrapper
- `Ogresync-linux.spec` - PyInstaller spec file (auto-generated)
- `README.md` - This documentation

## Contributing

When making changes to the Linux packaging:

1. Test on multiple distributions
2. Verify AppImage portability
3. Update documentation
4. Consider impact on Windows packaging

---

*This packaging system is designed to complement the existing Windows packaging while providing Linux users with a native, portable installation option.*
