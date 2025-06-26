# Ogresync

<div align="center">
  <img src="assets/new_logo_1_Transparent.png" alt="Ogresync Logo" width="120">
  
  **Professional Obsidian-GitHub Sync Tool**
  
  [![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/yourusername/ogresync)
  [![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)](https://github.com/yourusername/ogresync)
  [![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
</div>

Ogresync is a professional-grade desktop application that seamlessly synchronizes your Obsidian notes with GitHub repositories. Built with enterprise-level reliability, cross-platform compatibility, and intelligent conflict resolution.

## 🚀 Quick Start

### Download & Install

Choose your platform:

| Platform | Download | Requirements |
|----------|----------|--------------|
| **Windows** | [`ogresync.exe`](releases/latest) | Windows 10/11 |
| **Linux** | [`ogresync.AppImage`](releases/latest) | Any modern Linux distribution |
| **macOS** | [`Ogresync.app`](releases/latest) | macOS 10.14+ |

### First Launch

1. **Download** the appropriate executable for your platform
2. **Run** Ogresync - the setup wizard will guide you through:
   - 📁 Obsidian vault location
   - 🔗 GitHub repository connection
   - 🔐 Authentication setup
   - ⚙️ Sync preferences
3. **Start syncing** your notes automatically!

## ✨ Key Features

### 🔄 **Intelligent Synchronization**
- Real-time vault monitoring
- Bidirectional sync with GitHub
- Automatic conflict detection and resolution
- Smart merge algorithms

### 🛡️ **Enterprise-Grade Safety**
- Automatic backup creation before any changes
- Complete version history preservation
- Rollback capabilities
- Data integrity verification

### 🌍 **Cross-Platform Excellence**
- Native Windows, Linux, and macOS support
- Consistent user experience across platforms
- Platform-optimized file handling

### 🧠 **Smart Conflict Resolution**
- AI-powered merge suggestions
- Interactive conflict resolution interface
- Manual override capabilities
- Conflict history tracking

## 🔧 Advanced Usage

### Command Line Interface
```bash
# Run from source (developers)
python Ogresync.py

# Run with enhanced offline support
python enhanced_auto_sync.py

# Debug mode (development branch)
python Ogresync.py --debug
```

### Configuration
Ogresync stores configuration in platform-appropriate locations:
- **Windows**: `%APPDATA%\Ogresync\`
- **Linux**: `~/.config/ogresync/`
- **macOS**: `~/Library/Application Support/Ogresync/`

## 🏢 Professional Use

Ogresync is designed for:
- **Teams** collaborating on documentation
- **Researchers** sharing knowledge bases
- **Companies** managing internal wikis
- **Students** synchronizing study notes
- **Writers** backing up manuscripts

## 🛠️ For Developers

### Core Architecture
Ogresync is built with a modular architecture:

| Module | Purpose |
|--------|---------|
| `Ogresync.py` | Main application entry point |
| `enhanced_auto_sync.py` | **Offline/online sync orchestration** |
| `offline_sync_manager.py` | **Offline state management** |
| `conflict_resolution_integration.py` | Smart conflict resolution |
| `setup_wizard.py` | Initial configuration wizard |
| `backup_manager.py` | Automatic backup system |

### Running from Source
```bash
git clone https://github.com/yourusername/ogresync.git
cd ogresync
pip install -r requirements.txt
python Ogresync.py
```

### Development Branch
For full source code, tests, and development documentation:
```bash
git clone -b development https://github.com/yourusername/ogresync.git
```

## 📋 System Requirements

| Component | Requirement |
|-----------|-------------|
| **OS** | Windows 10+, Linux (kernel 3.2+), macOS 10.14+ |
| **Memory** | 512 MB RAM minimum |
| **Storage** | 100 MB free space |
| **Network** | Internet connection for GitHub sync |
| **Dependencies** | Git (auto-installed if needed) |

## 🔒 Security & Privacy

- **Local-first**: Your notes remain on your device
- **Encrypted transit**: All GitHub communication uses HTTPS/SSH
- **No telemetry**: No usage data collected
- **Open source**: Full transparency

## 📞 Support

- 📚 **Documentation**: [Wiki](wiki)
- 🐛 **Bug Reports**: [Issues](issues)
- 💡 **Feature Requests**: [Discussions](discussions)
- 📧 **Contact**: support@ogrelix.com

## 🤝 Contributing

We welcome contributions from the community! See our [Contributing Guide](CONTRIBUTING.md) for details.

## 📄 License

Licensed under the [MIT License](LICENSE) - free for personal and commercial use.

---

<div align="center">
  <strong>Made with ❤️ by <a href="https://ogrelix.com">Ogrelix Solutions</a></strong>
</div>
