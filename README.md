# Ogresync

<div align="center">
  <img src="assets/new_logo_1_Transparent.png" alt="Ogresync Logo" width="120">
  
  **Professional Obsidian-GitHub Sync Tool**
  
  [![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/AbijithBalaji/ogresync)
  [![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey.svg)](https://github.com/AbijithBalaji/ogresync)
  [![License](https://img.shields.io/badge/license-GPL-green.svg)](LICENSE)
</div>

Ogresync is a professional-grade open source desktop application that seamlessly synchronizes your Obsidian notes across devices. Mimics the Obsidian Sync feature for free by using GitHub. Built with enterprise-level reliability, cross-platform compatibility, and intelligent conflict resolution systems.

## Prerequisites

Before using Ogresync, please ensure you have the following installed:

### Required Software

**1. Obsidian**
- Download from: [https://obsidian.md/download](https://obsidian.md/download)
- Install and run Obsidian
- Create a vault folder where you want to store your notes

**2. Git**
- Download from: [https://git-scm.com/downloads](https://git-scm.com/downloads)
- For new users: Run the setup file and click "Next" until you reach "Setup Completed" for standard Git installation
- Git is required for repository synchronization

## Download & Installation

### Available Platforms

| Platform | Download | Status |
|----------|----------|---------|
| **Windows** | [Download from Releases](../../releases/latest) | Available |
| **Linux** | [Download from Releases](../../releases/latest) | Available |
| **macOS** | `Ogresync.app` | Coming in future updates |

### Installation Steps

**Windows:**
1. Download `ogresync.exe`
2. You may need to allow the file if your antivirus flags it as a threat
3. Run the executable

**Linux:**
1. Download `ogresync.AppImage`
2. Make it executable: `chmod +x ogresync.AppImage`
3. Run: `./ogresync.AppImage`

**Important ⚠️:** Create a **private** GitHub repository if you don't want your notes to be publicly visible.

## How Ogresync Works

Ogresync fundamentally changes how you interact with Obsidian by becoming the central orchestrator for all your note-taking activities. Instead of opening Obsidian directly, you launch Ogresync, which then handles the entire synchronization workflow seamlessly.

### Core Workflow Overview

**This is the heart of Ogresync - understanding this workflow is crucial:**

1. **Launch Ogresync** (not Obsidian) - This is your new workflow
2. **Ogresync performs intelligent pre-sync** - Checks for remote changes, handles conflicts
3. **Ogresync launches Obsidian automatically** - With your vault already synchronized
4. **Edit your notes freely** - Work normally in Obsidian without sync worries
5. **Close Obsidian when finished** - Ogresync detects closure immediately
6. **Ogresync handles post-sync** - Commits your changes, pushes to GitHub, handles any new conflicts

This workflow ensures your vault is always in perfect sync before and after editing, with intelligent conflict resolution at every step.

### Why This Workflow Matters

**Traditional Approach Problems:**
- Opening Obsidian directly can lead to sync conflicts
- Manual git operations are error-prone
- No visibility into sync status during editing
- Conflicts discovered only after making changes

**Ogresync's Solution:**
- **Pre-sync verification** ensures clean starting state
- **Active monitoring** tracks changes during editing
- **Automatic conflict detection** before they become problems
- **Intelligent post-processing** handles any edge cases

**The result:** A worry-free editing experience where synchronization happens invisibly and reliably.

### First-Time Setup

On first launch, Ogresync runs in **Setup Mode** with an 11-step wizard that guides you through:

1. **Obsidian Checkup** - Verify Obsidian installation
2. **Git Check** - Verify Git installation  
3. **Choose Vault** - Select your Obsidian vault folder
4. **Initialize Git** - Setup Git repository in your vault
5. **SSH Key Setup** - Generate or verify SSH key for GitHub
6. **Known Hosts** - Add GitHub to trusted hosts
7. **Test SSH** - Test SSH connection to GitHub
8. **GitHub Repository** - Link your GitHub repository
9. **Repository Sync** - Enhanced two-stage conflict resolution
10. **Final Sync** - Intelligent synchronization with safeguards
11. **Complete Setup** - Finalize configuration

Once setup is complete, a configuration file is stored in OS-specific locations:
- **Windows:** `%APPDATA%\Ogresync\`
- **Linux:** `~/.config/ogresync/`

To run setup again, delete the configuration file and restart the application.

**After Setup - Sync Mode:**
Once setup is complete, Ogresync switches to **Sync Mode** which follows the core workflow described above. Every time you want to use Obsidian, simply launch Ogresync instead.

## Key Features

### Intelligent Synchronization
- Real-time vault monitoring during Obsidian sessions
- Bidirectional sync with GitHub
- Automatic conflict detection and resolution
- Smart merge algorithms with git history preservation

### Two-Stage Conflict Resolution System
- **Stage 1:** High-level strategy selection (Smart Merge, Keep Local, Keep Remote)
- **Stage 2:** File-by-file resolution for complex conflicts
- Automatic local backups created before any changes
- Complete version history preservation through Git
- Rollback capabilities to any previous state
- Graceful handling of concurrent editing scenarios

### Intelligent Offline Support
- **No constant internet required**
- Smart offline state management and session tracking
- Automatic sync when internet becomes available
- Seamless transition between online and offline modes
- Conflict resolution triggered only when transitioning offline-to-online

### Enterprise-Grade Safety
- Comprehensive backup system with descriptive naming
- Data integrity verification
- Extensive edge case handling
- Thoroughly tested for reliability
- Non-destructive operations that preserve git history

## Advanced Technical Features

### Intelligent Workflow Management
- **Pre-sync Phase:** Automatically checks for remote changes before opening Obsidian
- **Session Monitoring:** Tracks remote changes that occur during your editing session
- **Post-sync Phase:** Intelligently handles conflicts that emerge during your session
- **Recovery Operations:** Automatic detection and handling of interrupted sync operations

### Robust Git Integration
- Complex git operations simplified for users without git knowledge
- Intelligent handling of merge conflicts, rebases, and unpushed commits
- Automatic upstream tracking configuration
- Smart detection of recovery scenarios and conflict resolution needs
- Force-push protection with user consent for critical operations

### Cross-Platform Excellence
- Native support for Windows and Linux (macOS coming soon)
- Handles various Obsidian installation methods (native, Snap, Flatpak, AppImage)
- Platform-optimized file operations and process management
- OS-specific configuration storage

## Use Cases

Ogresync is perfect for:

**Individual Users:**
- **Dual-boot systems:** Access your vault from different OS installations
- **Cloud backup:** Secure your notes with Git's powerful version control
- **Version history:** Rollback to any previous version of your notes

**Teams and Collaboration:**
- **Concurrent editing:** Multiple users working on the same vault simultaneously
- **Team documentation:** Collaborative knowledge bases
- **Research groups:** Shared research notes and findings

**Professional Applications:**
- **Company wikis:** Internal documentation management
- **Student collaboration:** Shared study materials
- **Writing projects:** Manuscript backup and version control

## Setup Wizard Guide

The 11-step setup wizard is designed to be user-friendly even without Git knowledge:

### Phase 1: Environment Verification (Steps 1-2)
- **Obsidian Detection:** Automatically finds your Obsidian installation
- **Git Verification:** Ensures Git is properly installed and configured

### Phase 2: Repository Initialization (Steps 3-4)
- **Vault Selection:** Choose your existing vault or create a new one
- **Git Setup:** Initialize repository in your vault and create initial commit

### Phase 3: GitHub Integration (Steps 5-7)
- **SSH Key Generation:** Creates secure SSH keys for GitHub authentication
- **GitHub Setup:** Configures secure connection to GitHub servers
- **Connection Testing:** Verifies everything works properly before proceeding

### Phase 4: Repository Synchronization (Steps 8-11)
- **Repository Linking:** Connects your local vault to GitHub repository
- **Enhanced Conflict Resolution:** Uses two-stage system if both local and remote have content
- **Final Sync:** Completes setup with intelligent synchronization
- **Configuration:** Saves all settings for future sync sessions

**What happens during Repository Sync (Step 9):**

The wizard analyzes your repository state and handles four scenarios:

1. **Both Empty:** Creates initial README and prepares for first sync
2. **Local Empty, Remote Has Files:** Simple pull operation to get remote content
3. **Local Has Files, Remote Empty:** Prepares local files for push to GitHub
4. **Both Have Files:** **Triggers enhanced two-stage conflict resolution**

When both repositories contain files, Ogresync automatically detects conflicts and launches the two-stage resolution system, ensuring safe merging of your content with complete history preservation.

Each step provides clear guidance and error recovery options.

## Core Architecture

Ogresync is built with a modular, dependency-injection architecture:

| Module | Purpose |
|--------|---------|
| `Ogresync.py` | Main application entry point and module orchestration |
| `setup_wizard.py` | Comprehensive 11-step setup wizard with conflict resolution |
| `enhanced_auto_sync.py` | Offline/online sync orchestration |
| `offline_sync_manager.py` | Offline state management and session tracking |
| `Stage1_conflict_resolution.py` | High-level conflict strategy selection |
| `stage2_conflict_resolution.py` | File-by-file conflict resolution |
| `conflict_resolution_integration.py` | Conflict resolution integration layer |
| `backup_manager.py` | File-based backup system with auto-cleanup |
| `ui_elements.py` | Professional UI components library |
| `wizard_steps.py` | Setup step functions (extracted via dependency injection) |
| `github_setup.py` | Git/GitHub functions (extracted via dependency injection) |

## Technical Features

### Advanced Git Logic
- Complex git operations simplified for users
- Intelligent handling of merge conflicts, rebases, and force pushes
- Automatic upstream tracking configuration
- Smart detection of unpushed commits and offline changes

### Robust Error Handling
- Comprehensive edge case detection and handling
- Graceful recovery from network interruptions
- Automatic fallback mechanisms for failed operations
- Detailed logging for troubleshooting

### Cross-Platform Compatibility
- Native support for Windows and Linux
- Handles various Obsidian installation methods (native, Snap, Flatpak, AppImage)
- Platform-optimized file operations and process management

## For Developers

### Running from Source
```bash
git clone https://github.com/AbijithBalaji/ogresync.git
cd ogresync
pip install -r requirements.txt
python Ogresync.py
```

### Development Branch
For full source code, tests, and development documentation:
```bash
git clone -b Development https://github.com/AbijithBalaji/ogresync.git
```

**Note**: You are currently viewing the Development branch which includes:
- Complete test suite (30+ test files)
- Development documentation ([DEVELOPMENT.md](DEVELOPMENT.md))
- Advanced debugging and build tools

## Linux Packaging

Ogresync includes comprehensive Linux packaging support for creating distributable AppImage files:

### Building Linux AppImage

```bash
cd linux-packaging
python build_appimage.py --clean --test
```

**Features:**
- **Cross-distribution compatibility**: Works on Ubuntu, Fedora, openSUSE, Arch, and more
- **GNOME integration**: Proper desktop file and icon handling
- **Self-contained**: No dependencies needed on target system
- **Professional packaging**: Follows Linux packaging standards

**Build options:**
- `--clean`: Clean previous build artifacts
- `--test`: Run verification tests
- `--verbose`: Show detailed build output
- `--arch x86_64`: Specify target architecture

### GNOME Desktop Integration

For better integration with GNOME desktop environment:

```bash
./install-gnome-integration.sh
```

This script:
- Installs desktop file and icons system-wide
- Updates icon cache and desktop database
- Enables launching from Activities overview
- Adds proper taskbar integration

### Build Requirements

| Tool | Purpose | Installation |
|------|---------|-------------|
| **PyInstaller** | Python packaging | `pip install pyinstaller` |
| **appimagetool** | AppImage creation | Auto-downloaded |
| **FUSE** | AppImage execution | `sudo dnf install fuse` |

## System Requirements

| Component | Requirement |
|-----------|-------------|
| **OS** | Windows 10+, Linux (kernel 3.2+) |
| **Memory** | 512 MB RAM minimum |
| **Storage** | 100 MB free space |
| **Dependencies** | Git, Obsidian |

## Security & Privacy

- **Local-first approach:** Your notes remain on your device
- **Encrypted transit:** All GitHub communication uses HTTPS/SSH
- **No telemetry:** No usage data is collected or transmitted
- **Open source:** Complete transparency and auditability
- **Private repositories:** Keep your data secure with private GitHub repos

## Contributing

We welcome contributions from the community! If you'd like to contribute to Ogresync, please check our [Contributing Guide](CONTRIBUTING.md) for detailed information on:
- Development setup
- Code standards
- Pull request process
- Issue reporting guidelines

## Support

- **Documentation:** [Wiki](wiki)
- **Bug Reports:** [Issues](issues)
- **Feature Requests:** [Discussions](discussions)
- **Contact:** abijith.balaji@gmail.com

## Purpose

This project was born out of necessity and passion for both Obsidian and open-source solutions. As a developer who couldn't afford the $9 monthly subscription for Obsidian Sync, I started by creating a simple git-based synchronization script for my personal use case.

What began as a mini-scale solution for syncing my notes between devices quickly evolved into something much larger. As I encountered various edge cases, network interruptions, and collaboration scenarios, I found myself building increasingly sophisticated git logic to handle these challenges.

Today, Ogresync represents months of development, testing, and refinement. It handles complex git operations, provides intelligent conflict resolution, supports offline workflows, and offers the kind of reliability you'd expect from commercial software - all while remaining free and open source.

The goal was simple: make Obsidian synchronization accessible to everyone, regardless of their budget or technical expertise, while providing even more advanced features than traditional sync solutions.

## License

Licensed under the [GPL License](LICENSE) - free for personal and commercial use.

---

<div align="center">
  <strong>Made with dedication by <a href="https://ogrelix.com">Ogrelix Solutions</a></strong>
</div>
