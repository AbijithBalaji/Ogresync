# Contributing to Ogresync

Thank you for your interest in contributing to Ogresync! This document provides comprehensive guidelines for contributing to our Git synchronization tool with advanced conflict resolution capabilities.

## Table of Contents

- [Overview](#overview)
- [Repository Structure & Branching Strategy](#repository-structure--branching-strategy)
- [Getting Started](#getting-started)
- [Development Process](#development-process)
- [Testing](#testing)
- [Code Standards](#code-standards)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)
- [Community Guidelines](#community-guidelines)

## Overview

Ogresync is a professional Git synchronization tool designed for cross-platform use, featuring a sophisticated two-stage conflict resolution system. We welcome contributions from developers of all skill levels.

**Important**: All contributors must work exclusively on the `development` branch. The `main` branch and packaging branches are maintained by project maintainers only.

## Repository Structure & Branching Strategy

### Branch Hierarchy
- **`development`** - Active development branch where all contributions are made
- **`main`** - Stable, user-ready code for distribution (maintainer-only)
- **`windows-packaging`** - Windows executable packaging (maintainer-only)
- **`linux-packaging`** - Linux executable packaging (maintainer-only)

### Contributor Workflow
1. **Contributors** work exclusively on feature branches from `development`
2. **Maintainers** merge approved PRs from `development` → `main`
3. **Maintainers** handle packaging: `main` → platform-specific branches → releases

### Key Directories

**Development Branch (Current):**
- `/` - Core application modules and configuration
- `/tests/` - Comprehensive test suite (30+ test files) ✅ **Available Here**
- `/assets/` - Application icons and branding
- `/build/` - Build artifacts (excluded from repository)

**Main Branch:**
- Contains only production-ready code without tests
- Used for user downloads and GitHub Releases

*Note: You're currently on the development branch with full access to tests and development tools.*

## Getting Started

### Prerequisites
- Python 3.8+
- Git 2.20+
- GitHub account with SSH key configured

### Development Setup
1. **Fork the repository** on GitHub
2. **Clone your fork and switch to development**:
   ```bash
   git clone git@github.com:YOUR_USERNAME/ogresync.git
   cd ogresync
   git checkout Development  # This branch has tests and dev tools
   ```
3. **Set up the development environment**:
   ```bash
   # Create virtual environment (recommended)
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Install development dependencies
   pip install pytest flake8 black
   ```
4. **Add upstream remote**:
   ```bash
   git remote add upstream git@github.com:AbijithBalaji/ogresync.git
   ```
5. **Verify setup**:
   ```bash
   # Test the application
   python Ogresync.py --help
   
   # Run tests to ensure everything works
   python tests/comprehensive_test_suite.py
   ```

### Verify Installation
```bash
python Ogresync.py --help
```
You should see the application help menu.

## Development Process

### Creating a Feature Branch
Always branch from the latest `development`:
```bash
git checkout development
git pull upstream development
git checkout -b feature/descriptive-name
```

### Branch Naming Conventions
- **Features**: `feature/add-batch-processing`
- **Bug fixes**: `fix/conflict-resolution-memory-leak`
- **Documentation**: `docs/update-setup-guide`
- **Tests**: `test/improve-offline-coverage`

### Making Changes
1. **Keep changes focused** - One feature/fix per branch
2. **Write tests** for new functionality
3. **Update documentation** as needed
4. **Follow code standards** (see below)

### Commit Messages
Use clear, descriptive commit messages:
```bash
# Good
git commit -m "Add batch processing for multiple repository sync"
git commit -m "Fix memory leak in conflict resolution stage 2"

# Avoid
git commit -m "fix stuff"
git commit -m "WIP"
```

## Testing

Ogresync has a comprehensive test suite with 30+ test files covering various scenarios. **You are currently on the development branch which includes the full test suite.**

### Running Tests
```bash
# Run all tests
python -m pytest tests/

# Run the comprehensive test suite
python tests/comprehensive_test_suite.py

# Run specific test categories
python tests/test_conflict_resolution.py
python tests/test_offline_components.py
python tests/test_security_fixes.py
```

### Key Test Areas
- **Conflict Resolution**: Two-stage merge and resolution system
- **Offline Functionality**: Repository sync without network access
- **Cross-platform Compatibility**: Windows, Linux, macOS support
- **Security**: Command injection prevention and input validation
- **Edge Cases**: Complex merge scenarios and error handling

### Writing Tests
When adding new features:
1. **Add unit tests** for individual functions
2. **Add integration tests** for feature workflows
3. **Test cross-platform compatibility** where applicable
4. **Include edge cases** and error conditions

Example test structure:
```python
def test_new_feature():
    """Test description explaining the scenario."""
    # Setup
    test_data = setup_test_repository()
    
    # Execute
    result = your_new_function(test_data)
    
    # Verify
    assert result.success == True
    assert result.conflicts_resolved == expected_count
```

## Code Standards

### Python Standards
- **PEP 8 compliance** - Use `flake8` or `black` for formatting
- **Type hints** where appropriate
- **Docstrings** for all public functions and classes
- **Error handling** with specific exception types

### Code Organization
- **Modular design** - Keep functions focused and reusable
- **Clear variable names** - Avoid abbreviations
- **Comments** for complex logic, especially in conflict resolution
- **Constants** in UPPER_CASE

### Example Code Style
```python
def resolve_merge_conflicts(repository_path: str, strategy: str = "smart") -> ConflictResolution:
    """
    Resolve merge conflicts using the specified strategy.
    
    Args:
        repository_path: Absolute path to the Git repository
        strategy: Conflict resolution strategy ('smart', 'manual', 'auto')
    
    Returns:
        ConflictResolution object with resolution status and details
    
    Raises:
        RepositoryError: If repository path is invalid
        ConflictResolutionError: If conflicts cannot be resolved
    """
    if not os.path.exists(repository_path):
        raise RepositoryError(f"Repository not found: {repository_path}")
    
    # Implementation here...
    return ConflictResolution(success=True, method=strategy)
```

### UI and User Experience
- **Consistent terminology** across all interfaces
- **Clear error messages** with actionable guidance
- **Cross-platform compatibility** considerations
- **Professional appearance** in GUI elements

## Pull Request Process

### Before Submitting
1. **Sync with upstream**:
   ```bash
   git checkout development
   git pull upstream development
   git checkout your-feature-branch
   git rebase development
   ```
2. **Run the full test suite**:
   ```bash
   python -m pytest tests/
   ```
3. **Ensure code quality**:
   ```bash
   flake8 *.py
   ```

### PR Requirements
- **Target branch**: Always target `development`
- **Clear title**: Descriptive summary of changes
- **Detailed description**: What, why, and how
- **Link related issues**: Use "Fixes #123" or "Relates to #456"
- **Test coverage**: Include tests for new functionality
- **Documentation**: Update relevant docs

### PR Template
```markdown
## Description
Brief description of changes and motivation.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] Added tests for new functionality
- [ ] Tested on multiple platforms (if applicable)

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Changes are backwards compatible
```

### Review Process
1. **Automated checks** must pass (CI/CD if configured)
2. **Maintainer review** - May request changes or clarification
3. **Address feedback** promptly and professionally
4. **Final approval** required before merge

## Issue Reporting

### Bug Reports
Use the bug report template with:
- **Environment**: OS, Python version, Git version
- **Steps to reproduce**: Detailed, step-by-step instructions
- **Expected behavior**: What should happen
- **Actual behavior**: What actually happens
- **Logs**: Include relevant error messages or logs
- **Screenshots**: If applicable for UI issues

### Feature Requests
Include:
- **Use case**: Why this feature is needed
- **Proposed solution**: How it might work
- **Alternatives considered**: Other approaches you've thought about
- **Implementation details**: Any technical considerations

### Security Issues
**Do not** open public issues for security vulnerabilities. Instead:
1. Email maintainers directly
2. Provide detailed reproduction steps
3. Allow reasonable time for response and fix

## Community Guidelines

### Code of Conduct
- **Be respectful** and professional in all interactions
- **Constructive feedback** - Focus on code, not individuals
- **Inclusive language** - Welcome contributors from all backgrounds
- **Help others** - Share knowledge and assist newcomers

### Communication Channels
- **GitHub Issues**: Bug reports, feature requests, general questions
- **Pull Requests**: Code review discussions
- **Discussions**: Design decisions, architectural questions

### Recognition
Contributors are recognized through:
- **Commit history** preservation
- **Release notes** acknowledgment
- **Community appreciation** for significant contributions

## Questions?

- **New to contributing?** Start with issues labeled "good first issue"
- **Need clarification?** Open a discussion or comment on relevant issues
- **Technical questions?** Reference the codebase - it's well-documented
- **Stuck?** Don't hesitate to ask for help

Thank you for contributing to Ogresync! Your efforts help make Git synchronization better for everyone.

---

**Advanced Developers**: See [DEVELOPMENT.md](DEVELOPMENT.md) for technical architecture, build processes, and maintainer guidelines.
