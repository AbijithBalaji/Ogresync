# Ogresync Windows Packaging Guide

This document describes the Windows packaging process for Ogresync, including solutions for common packaging issues.

## Overview

The Ogresync Windows packaging system addresses several critical issues:

1. **Subprocess Console Windows**: Prevents command prompt windows from flashing during git operations
2. **Unicode Character Compatibility**: Safely handles special characters in packaged applications  
3. **Asset Bundling**: Properly includes icons and resources in the executable
4. **Dependency Management**: Ensures all required modules are included
5. **Path Resolution**: Handles file paths correctly in both development and packaged modes

## Files Created for Packaging

### Core Packaging Files

- `packaging_utils.py` - Utilities for handling packaging issues
- `Ogresync.spec` - PyInstaller specification file  
- `build_exe_enhanced.py` - Enhanced build script with verification
- `build.bat` - Simple batch file for Windows users

### Key Changes Made

#### 1. Subprocess Window Hiding

Modified all subprocess calls in:
- `Ogresync.py` (main run_command function)
- `wizard_steps.py` (fallback run_command)
- `github_setup.py` (git command execution)

**Solution**: Added STARTUPINFO configuration for Windows:

```python
# Determine if we're running as a packaged executable
is_packaged = getattr(sys, 'frozen', False)

# On Windows, hide console windows when packaged
startupinfo = None
if platform.system() == "Windows" and is_packaged:
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE

result = subprocess.run(
    command,
    # ... other parameters ...
    startupinfo=startupinfo
)
```

#### 2. Unicode Character Safety

Created `SafeUnicodeChars` class in `packaging_utils.py`:

```python
class SafeUnicodeChars:
    CHECK_MARK = safe_unicode_char("✅", "[OK]")
    CROSS_MARK = safe_unicode_char("❌", "[FAIL]")  
    WARNING = safe_unicode_char("⚠️", "[WARN]")
    # ... more characters with ASCII fallbacks
```

#### 3. Resource Path Resolution

Added `get_resource_path()` function:

```python
def get_resource_path(relative_path: str) -> str:
    if is_packaged_app():
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)
```

## Build Process

### Option 1: Enhanced Build Script (Recommended)

```bash
python build_exe_enhanced.py --clean
```

### Option 2: Simple Batch File

```bash
build.bat
```

### Option 3: Direct PyInstaller

```bash
pyinstaller Ogresync.spec
```

## Build Output

The build process creates:

- `dist/Ogresync.exe` - Main executable (~14MB)
- `dist/assets/` - Bundled application assets
- `dist/run_ogresync.bat` - Convenience batch file
- `dist/README_EXECUTABLE.md` - User documentation

## Testing the Executable

### Basic Test
```bash
# Start the application
dist\Ogresync.exe
```

### Troubleshooting Test
```bash
# Run with batch file for easier error reporting
dist\run_ogresync.bat
```

## Common Issues and Solutions

### Issue 1: Console Windows Flashing
**Cause**: subprocess calls without proper Windows configuration
**Solution**: Use `startupinfo` parameter with `SW_HIDE` flag

### Issue 2: Unicode Characters Causing Crashes
**Cause**: Special characters not supported in packaged environment
**Solution**: Use `SafeUnicodeChars` with ASCII fallbacks

### Issue 3: "File Not Found" Errors for Assets
**Cause**: Incorrect path resolution in packaged mode
**Solution**: Use `get_resource_path()` for all asset access

### Issue 4: Import Errors in Packaged Mode
**Cause**: PyInstaller missing hidden imports
**Solution**: Add modules to `hiddenimports` in spec file

### Issue 5: Large Executable Size
**Current Size**: ~14MB (acceptable)
**If too large**: Add more exclusions to spec file

## Distribution

### Single File Distribution
The executable is completely standalone - just distribute `Ogresync.exe`

### Package Distribution
For better user experience, distribute the entire `dist/` folder containing:
- `Ogresync.exe`
- `assets/`
- `run_ogresync.bat`
- `README_EXECUTABLE.md`

## Development vs Packaged Mode

The application detects its mode using:

```python
def is_packaged_app() -> bool:
    return getattr(sys, 'frozen', False)
```

This allows different behavior in development vs packaged modes:
- Development: Full console output, detailed error messages
- Packaged: Hidden console windows, user-friendly error handling

## Future Improvements

1. **Code Signing**: Add digital signature for Windows SmartScreen compatibility
2. **Installer Creation**: Use NSIS or Inno Setup for professional installer
3. **Auto-updater**: Implement automatic update checking
4. **Performance**: Further optimize startup time and memory usage

## Build Environment Requirements

- Python 3.8+
- PyInstaller 6.0+
- All dependencies from requirements.txt
- Windows 10/11 for testing

## Version Control

This packaging work is maintained in the `windows-packaging` branch to:
- Keep packaging changes separate from main development
- Allow easy testing and refinement
- Enable rollback if issues occur
- Maintain clean main branch for development

## Maintenance

When updating the application:

1. Make changes in main branch
2. Merge to `windows-packaging` branch  
3. Test the build process
4. Update this documentation if needed
5. Create new release with updated executable

---

**Note**: This packaging system ensures the Windows executable works identically to the Python script while providing a much better user experience.
