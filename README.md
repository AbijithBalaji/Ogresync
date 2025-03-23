# Ogresync

![Ogresync Logo](assets/logo.ico)


**Ogresync** is an open-source synchronization tool that automates syncing your Obsidian vault with GitHub using Git and SSH. Built using Python, it’s a project by **Ogrelix**, a startup focused on creating streamlined, user-centric software tools that simplify digital workflows.

---

## Features

- **One-Time Setup Wizard**  
  Automatically detects Obsidian, configures Git and SSH, and guides you through selecting your vault and linking your GitHub repository.

- **Automatic Synchronization**  
  Detects local changes, pulls remote updates with stash support, launches Obsidian, and upon closing, commits and pushes updates automatically.

- **Intelligent Conflict Resolution**  
  Handles merge conflicts with options to keep local or remote changes, or resolve manually. (Currently under refinement—see Known Issues.)

- **Offline Resilience**  
  Works even without an internet connection, queues local commits, and pushes them automatically when online.

- **Cross-Platform Compatibility**  
  Supports Windows, Linux (AppImage), and macOS (.app). Platform-specific behaviors are handled internally.

- **Community-Centric & Open Source**  
  Contributions, feedback, and ideas are welcome to enhance and expand the project further.

---

## Installation

### Prerequisites

- **Git:** Ensure Git is installed and available in your system PATH.  
  [Download Git](https://git-scm.com/)

- **SSH:** A valid SSH key is required for GitHub synchronization. If absent, Ogresync will assist you in generating one and provide manual instructions if needed.

- **Obsidian:** Install from [obsidian.md](https://obsidian.md/)  

---

### Running from Source

```bash
git clone https://github.com/Ogrelix/Ogresync.git
cd Ogresync
   ```
2. **(Optional) Create a Virtual Environment:**

  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

3. **Install Dependencies:**
  ```bash
  pip install -r requirements.txt
  ```

4. **Run Ogresync:**
  ```bash
  python ogresync.py
  ```

### Packaged Executables
Download ready-to-use binaries from the [Releases](https://github.com/Ogrelix/Ogresync/releases) page:

-   **Windows:** Executable `.exe`

-   **Linux:** AppImage

-   **macOS:** `.app` bundle (coming soon)
  
---

## Usage
### 1\. Initial Setup

-   The wizard helps you choose your Obsidian vault and configures everything, including SSH and GitHub repository setup.

-   If you don't have a GitHub repo, you'll be prompted to create a private one and provide its URL.

-   SSH keys are auto-generated if not found. On Linux/macOS, manual instructions are displayed in case clipboard copy fails.

### 2\. Automatic Synchronization

Once setup is complete, just run **Ogresync** instead of opening Obsidian directly.

-   It pulls any updates from GitHub before opening Obsidian.

-   You edit your notes as usual in Obsidian.

-   After you close Obsidian:

    -   Any changes are automatically committed.

    -   If online, changes are pushed to GitHub.

    -   If offline, they remain committed locally and will be pushed later.

### 3\. Conflict Handling

If the same file is modified on two systems:

-   Conflicts are detected and logged.

-   You will be prompted to resolve using:

    -   Keep Local Changes

    -   Use Remote Changes

    -   Merge Manually

(See Known Issues for current limitations.)

---

## Contributing

We welcome contributions from the community! To keep our codebase clean and facilitate smooth collaboration, please follow these guidelines:

### Branch Structure
- **main**: Contains stable, production-ready code (currently Windows is stable).
- **develop**: The active development branch for new features, bug fixes, and cross-platform improvements. Please branch off `develop` for your work.
  
### How to Contribute
1. Fork this repository.
2. Clone your fork and create a new branch from `develop`:
   ```bash
   git checkout -b feature/your-feature-name develop
3. Implement your changes following our coding standards and ensure tests pass.

4. Commit your changes with clear, descriptive commit messages.

5. Push your branch to your fork and submit a pull request against the `develop` branch.

6. Your pull request will be reviewed by maintainers. Please be responsive to feedback.

For more detailed guidelines, please see our <CONTRIBUTING.md> file.

---

## Known Issues

- **Conflict Dialog Not Triggering Properly:**
The dialog for resolving merge conflicts is not always shown as expected during certain workflows. We are actively working to fix this.

- **Linux and macOS Bugs:**
While basic functionality works, further testing and optimizations are needed. Clipboard features may not work out of the box.

- **Packaging & Shortcuts:**
Native shortcut creation (Start Menu, desktop icons, app directory registration) is not yet implemented.

- **Setup Responsiveness:**
If the user exits dialog boxes prematurely during setup, the main window may become unresponsive. A fallback loop is under development.

---

## Roadmap
- **Enhanced Conflict Resolution UI:**
  Improve the merge conflict dialog and integrate external merge tools.

- **Native Shortcuts & Installers:**
  Develop desktop/start menu shortcuts and native installers for all platforms.

- **Cross-Platform Packaging:**
  Further refine packaging for macOS (.app) and Linux (AppImage) to ensure a seamless user experience.

- **Additional Features:**
  Custom commit messages, scheduled syncs, and more.

---

## License
Ogresync is licensed under the GNU General Public License v3.0 (GPLv3). 
See the LICENSE file for full details.

---

## About Ogrelix
![Ogrelix Logo](assets/ogrelix_logo.png)

**Ogrelix** is an MSME-registered startup based in India, focused on building innovative, simple, and impactful digital tools. While we're not a formal private limited company, our team is passionate about solving real-world problems through open-source and community-driven development. Ogresync is one of our flagship products under active development.

---

Contact
-------

For suggestions, support, or collaboration inquiries:

-   Email: abijith.balaji@gmail.com

-   GitHub Issues: [Open an issue](https://github.com/Ogrelix/Ogresync/issues)

---

### Future Packaging Plans

We aim to release production-ready packages with:

- Installers that add the app to system paths

- Start Menu/Desktop shortcuts

- Cross-platform builds via CI pipelines

Stay tuned for these enhancements in upcoming releases.
