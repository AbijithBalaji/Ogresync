# Ogresync Development Documentation

**⚠️ This document is for advanced developers and maintainers only.**

For general contribution guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Development Environment Setup](#development-environment-setup)
- [Testing Framework](#testing-framework)
- [Build and Packaging](#build-and-packaging)
- [Release Process](#release-process)
- [Advanced Git Operations](#advanced-git-operations)
- [Debugging and Troubleshooting](#debugging-and-troubleshooting)
- [Maintainer Guidelines](#maintainer-guidelines)

## Architecture Overview

### Core System Design

Ogresync follows a modular, dependency-injection architecture designed for reliability and maintainability:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Ogresync.py   │◄──►│ setup_wizard.py  │◄──►│ enhanced_auto_  │
│   (Main App)    │    │ (11-Step Setup)  │    │ sync.py         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ ui_elements.py  │    │ wizard_steps.py  │    │ github_setup.py │
│ (UI Library)    │    │ (Step Functions) │    │ (Git Functions) │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         ▲                       ▲                       ▲
         │               ┌───────┴──────────┐            │
         │               │                  │            │
         ▼               ▼                  ▼            ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Stage1_conflict │    │ stage2_conflict  │    │ backup_manager  │
│ _resolution.py  │    │ _resolution.py   │    │ .py             │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ conflict_resol  │    │ offline_sync_    │    │ remove_config   │
│ ution_integ.py  │    │ manager.py       │    │ .py             │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Dependency Injection Pattern

**Key Innovation**: `wizard_steps.py` and `github_setup.py` use dependency injection to avoid circular imports:

```python
# In wizard_steps.py
def set_dependencies(ui_elements=None, config_data=None, save_config_func=None, 
                    safe_update_log_func=None, run_command_func=None):
    """Inject dependencies from main modules"""
    global _ui_elements, _config_data, _save_config_func
    # Functions originally in Ogresync.py are injected here
```

This allows modular architecture while maintaining access to core functionality.

### Key Design Principles

1. **Dependency Injection**: Functions moved from main files use injection to access core functionality
2. **Modular Refactoring**: Complex functions extracted from `Ogresync.py` and `setup_wizard.py`  
3. **State Management**: Centralized configuration through injection pattern
4. **Error Recovery**: Comprehensive error handling with automatic recovery
5. **Cross-Platform**: Platform-agnostic core with OS-specific adaptations
6. **Git Integration**: Safe, non-destructive git operations with backup systems

### Module Relationships

**Core Modules:**
- `Ogresync.py` - Main application orchestrator, imports all other modules
- `setup_wizard.py` - Complete 11-step setup process with two-stage conflict resolution
- `enhanced_auto_sync.py` - Offline/online sync orchestration
- `offline_sync_manager.py` - Session tracking and offline state management

**Extracted Function Modules (Dependency Injection):**
- `wizard_steps.py` - Step functions extracted from `Ogresync.py` via dependency injection
- `github_setup.py` - Git/GitHub functions extracted from `Ogresync.py` via dependency injection
- `ui_elements.py` - Shared UI components used across all modules

**Conflict Resolution System:**
- `Stage1_conflict_resolution.py` - High-level strategy selection dialog
- `stage2_conflict_resolution.py` - File-by-file conflict resolution
- `conflict_resolution_integration.py` - Integration layer for conflict resolution

**Support Modules:**
- `backup_manager.py` - Automatic backup system with descriptive naming
- `remove_config.py` - Configuration cleanup utilities

### 11-Step Setup Wizard Architecture

The setup wizard (`setup_wizard.py`) orchestrates the complete initial configuration:

```python
class OgresyncSetupWizard:
    """Manages the 11-step setup process with enhanced conflict resolution"""
    
    setup_steps = [
        SetupWizardStep("Obsidian Checkup", "Verify Obsidian installation", "🔍"),
        SetupWizardStep("Git Check", "Verify Git installation", "🔧"),
        SetupWizardStep("Choose Vault", "Select Obsidian vault folder", "📁"),
        SetupWizardStep("Initialize Git", "Setup Git repository in vault", "📋"),
        SetupWizardStep("SSH Key Setup", "Generate or verify SSH key", "🔑"),
        SetupWizardStep("Known Hosts", "Add GitHub to known hosts", "🌐"),
        SetupWizardStep("Test SSH", "Test SSH connection (manual step)", "🔐"),
        SetupWizardStep("GitHub Repository", "Link GitHub repository", "🔗"),
        SetupWizardStep("Repository Sync", "Enhanced two-stage conflict resolution", "⚖️"),
        SetupWizardStep("Final Sync", "Intelligent synchronization", "📥"),
        SetupWizardStep("Complete Setup", "Finalize configuration", "🎉")
    ]
```

**Critical Step 9 - Repository Sync**: This step analyzes repository state and determines appropriate action:
- **Scenario 1**: Both empty → Create README
- **Scenario 2**: Local empty, remote has files → Simple pull
- **Scenario 3**: Local has files, remote empty → Prepare for push
- **Scenario 4**: Both have files → **Trigger two-stage conflict resolution**

This architecture ensures safe repository merging with complete history preservation.

## Development Environment Setup

### Prerequisites for Development

```bash
# Required software
- Python 3.8+ (with tkinter support)
- Git 2.20+
- GitHub account with SSH configured
- VS Code or preferred IDE

# Recommended tools
- pytest for testing
- flake8 for linting
- black for code formatting
```

### Complete Development Setup

```bash
# 1. Clone development branch
git clone -b Development https://github.com/AbijithBalaji/ogresync.git
cd ogresync

# 2. Set up virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install development dependencies
pip install pytest flake8 black

# 5. Verify setup
python Ogresync.py --help
```

### Development Configuration

Create `.vscode/settings.json` for optimal development:
```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/"]
}
```

## Testing Framework

### Test Suite Structure

The test suite contains 30+ comprehensive test files covering:

```
tests/
├── comprehensive_test_suite.py    # Main test orchestrator
├── test_conflict_resolution.py    # Two-stage conflict system
├── test_offline_components.py     # Offline state management
├── test_security_fixes.py         # Security validation
├── test_os_compatibility_fixes.py # Cross-platform testing
└── ...29+ additional test files
```

### Running Tests

```bash
# Full test suite
python tests/comprehensive_test_suite.py

# Specific test categories
python tests/test_conflict_resolution.py
python tests/test_offline_components.py
python tests/test_security_fixes.py

# Using pytest
pytest tests/ -v
pytest tests/test_conflict_resolution.py -v

# Test with coverage
pytest tests/ --cov=. --cov-report=html
```

### Test Categories

1. **Conflict Resolution Tests**: Two-stage system validation
2. **Offline Functionality**: Network interruption handling
3. **Security Tests**: Command injection prevention
4. **Git Operations**: Complex merge scenarios
5. **Cross-Platform**: Windows/Linux compatibility
6. **Edge Cases**: Error recovery and data integrity

### Writing New Tests

Follow this pattern for new tests:
```python
def test_new_feature():
    """
    Test description: What scenario this tests.
    
    Setup: What environment/state is needed
    Execute: What operation is performed
    Verify: What outcome is expected
    """
    # Setup test environment
    test_repo = setup_test_repository()
    
    # Execute the feature
    result = new_feature_function(test_repo)
    
    # Verify results
    assert result.success == True
    assert result.data_integrity == True
    
    # Cleanup
    cleanup_test_repository(test_repo)
```

## Build and Packaging

### PyInstaller Configuration

Development branch contains build scripts for packaging:

```bash
# Windows executable
pyinstaller --onefile --windowed --icon=assets/new_logo_1.ico Ogresync.py

# Linux AppImage
pyinstaller --onefile --icon=assets/new_logo_1.png Ogresync.py
```

### Cross-Platform Considerations

- **Windows**: Handle antivirus false positives
- **Linux**: Support Snap, Flatpak, AppImage installations
- **macOS**: Code signing and notarization (future)

## Release Process

### Maintainer Release Workflow

1. **Development → Main**:
   ```bash
   git checkout main
   git merge Development --no-ff
   git push origin main
   ```

2. **Main → Packaging Branches**:
   ```bash
   # Windows packaging
   git checkout windows-packaging
   git merge main
   # Build executable
   git push origin windows-packaging
   
   # Linux packaging
   git checkout linux-packaging
   git merge main
   # Build AppImage
   git push origin linux-packaging
   ```

3. **GitHub Release**:
   - Tag version: `v1.0.0`
   - Upload executables
   - Update release notes

### Version Management

Follow semantic versioning:
- `MAJOR.MINOR.PATCH` (e.g., 1.2.3)
- Update version in `Ogresync.py` and `README.md`
- Tag releases consistently

### Advanced Git Operations

### Two-Stage Conflict Resolution Architecture

Ogresync implements a sophisticated two-stage conflict resolution system:

#### Stage 1: Strategy Selection (`Stage1_conflict_resolution.py`)
```python
# High-level conflict detection and strategy selection
class ConflictResolutionEngine:
    def analyze_conflicts(self, remote_url):
        """Analyze repository for potential conflicts"""
        
    def apply_strategy(self, strategy, analysis):
        """Apply selected strategy to resolve conflicts"""

# User selects from predefined strategies
strategies = [
    ConflictStrategy.SMART_MERGE,    # Intelligent auto-merge
    ConflictStrategy.KEEP_LOCAL,     # Preserve local with history
    ConflictStrategy.KEEP_REMOTE     # Adopt remote with backup
]
```

#### Stage 2: File-by-File Resolution (`stage2_conflict_resolution.py`)
```python
# Detailed conflict resolution for complex scenarios
for conflicted_file in conflicts:
    resolution_choice = present_file_dialog(file)
    apply_file_resolution(file, resolution_choice)
```

#### Integration Layer (`conflict_resolution_integration.py`)
```python
# Seamless integration with setup wizard and sync operations
def integrate_conflict_resolution_with_setup(setup_context):
    """Called during setup wizard Step 9 when conflicts detected"""
    
def integrate_conflict_resolution_with_sync(sync_context):
    """Called during normal sync operations when conflicts arise"""
```

### Dependency Injection Implementation

The architecture uses dependency injection to break circular imports:

```python
# In Ogresync.py
import wizard_steps
wizard_steps.set_dependencies(
    ui_elements=ui_elements,
    config_data=config_data,
    save_config_func=save_config,
    safe_update_log_func=safe_update_log,
    run_command_func=run_command
)

# In wizard_steps.py  
def find_obsidian_path():
    """Function moved from Ogresync.py, uses injected dependencies"""
    if _ui_elements:
        return _ui_elements.ask_directory_premium(...)
    else:
        return fallback_directory_dialog(...)
```

This pattern allows clean separation while maintaining functionality.

### Git Command Safety

All git operations include comprehensive safety measures through the backup system:

```python
# Before any risky git operation
from backup_manager import OgresyncBackupManager, BackupReason

def safe_git_operation(command, repo_path, reason="sync_operation"):
    # 1. Create automatic backup
    backup_manager = OgresyncBackupManager(repo_path)
    backup_id = backup_manager.create_backup(
        reason=BackupReason.SYNC_OPERATION,
        description=f"Before {command}",
        files_to_backup=None  # Backup all files
    )
    
    # 2. Validate repository state
    validate_repo_integrity(repo_path)
    
    # 3. Execute with comprehensive error handling
    try:
        result = execute_git_command(command, repo_path)
        return result
    except GitError as e:
        # 4. Recovery instructions automatically generated
        recovery_file = backup_manager.create_recovery_instructions(backup_id)
        show_user_recovery_dialog(recovery_file)
        raise e
```

**Key Safety Features:**
- **File-based snapshots** in `.ogresync-backups/` (never synced)
- **Automatic gitignore** management to exclude backups
- **Descriptive backup names** with timestamps and reasons
- **Recovery instructions** automatically generated for users
- **Backup cleanup** based on age, count, and size limits

## Debugging and Troubleshooting

### Logging System

Enable comprehensive logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Common Development Issues

1. **GUI Threading**: Use `threading.Thread` for background operations
2. **Git State**: Always validate repository state before operations
3. **Cross-Platform Paths**: Use `os.path.join()` consistently
4. **Error Recovery**: Implement graceful fallbacks

### Development Tools

Useful debugging utilities:
```bash
# Monitor git operations
git log --oneline --graph -10

# Check repository integrity
git fsck

# Analyze file conflicts
git status --porcelain
```

## Maintainer Guidelines

### Code Review Checklist

- [ ] Code follows PEP 8 standards
- [ ] Tests added for new functionality
- [ ] Documentation updated
- [ ] Cross-platform compatibility verified
- [ ] Security implications reviewed
- [ ] Git operations are safe and non-destructive

### Branch Management

- **Development**: Accept all contributor PRs here
- **Main**: Merge only tested, stable features
- **Packaging**: Platform-specific builds only

### Security Considerations

1. **Command Injection**: Validate all user inputs
2. **File Permissions**: Respect OS security models
3. **Git Operations**: Never force-push without user consent
4. **SSH Keys**: Secure key generation and storage

---

**This document is for maintainers and advanced developers only. Contributors should refer to [CONTRIBUTING.md](CONTRIBUTING.md) for general guidelines.**