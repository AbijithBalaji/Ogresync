"""
Conflict Resolution Integration with Backup Manager

This module integrates the enhanced conflict resolution system with
the centralized backup manager to ensure safe, non-polluting backups
for all conflict resolution strategies.

Author: Ogresync Development Team
Date: June 2025
"""

import os
from typing import Optional
from backup_manager import OgresyncBackupManager, BackupReason

def create_keep_remote_only_backup(vault_path: str, local_files: Optional[list] = None) -> Optional[str]:
    """
    Create backup before 'Keep Remote Only' strategy
    
    This ensures user's local files are safely backed up before
    being replaced with remote content. Only backs up local files that exist.
    
    Args:
        vault_path: Path to the vault
        local_files: List of local files to backup (only local files)
        
    Returns:
        Backup ID if successful, None if failed
    """
    manager = OgresyncBackupManager(vault_path)
    
    # If specific local files are provided, only backup those
    # Otherwise backup all meaningful local files
    backup_id = manager.create_backup(
        BackupReason.CONFLICT_RESOLUTION,
        "Keep Remote Only - Local files backup before adopting remote content",
        files_to_backup=local_files  # This will be None if not provided, backing up all files
    )
    
    if backup_id:
        file_count = len(local_files) if local_files else "all"
        print(f"✅ Local files backed up before 'Keep Remote Only': {backup_id} ({file_count} files)")
        return backup_id
    else:
        print("❌ Failed to create backup for 'Keep Remote Only' strategy")
        return None

def create_keep_local_only_backup(vault_path: str) -> Optional[str]:
    """
    Create backup before 'Keep Local Only' strategy
    
    This ensures remote content is safely backed up before
    local content overwrites the remote.
    
    Args:
        vault_path: Path to the vault
        
    Returns:
        Backup ID if successful, None if failed
    """
    manager = OgresyncBackupManager(vault_path)
    backup_id = manager.create_backup(
        BackupReason.CONFLICT_RESOLUTION,
        "Keep Local Only - Remote content backup before adopting local content"
    )
    
    if backup_id:
        print(f"✅ Remote content backed up before 'Keep Local Only': {backup_id}")
        return backup_id
    else:
        print("❌ Failed to create backup for 'Keep Local Only' strategy")
        return None

def create_smart_merge_backup(vault_path: str) -> Optional[str]:
    """
    Create backup before 'Smart Merge' strategy
    
    This ensures both local and remote content are backed up
    before the merge operation.
    
    Args:
        vault_path: Path to the vault
        
    Returns:
        Backup ID if successful, None if failed
    """
    manager = OgresyncBackupManager(vault_path)
    backup_id = manager.create_backup(
        BackupReason.CONFLICT_RESOLUTION,
        "Smart Merge - Pre-merge backup of current state"
    )
    
    if backup_id:
        print(f"✅ Pre-merge backup created for 'Smart Merge': {backup_id}")
        return backup_id
    else:
        print("❌ Failed to create backup for 'Smart Merge' strategy")
        return None

def create_sync_mode_backup(vault_path: str, operation: str) -> Optional[str]:
    """
    Create backup during sync mode operations
    
    This ensures sync operations are safe and reversible.
    
    Args:
        vault_path: Path to the vault
        operation: Description of the sync operation
        
    Returns:
        Backup ID if successful, None if failed
    """
    manager = OgresyncBackupManager(vault_path)
    backup_id = manager.create_backup(
        BackupReason.SYNC_OPERATION,
        f"Sync Mode Safety Backup - {operation}"
    )
    
    if backup_id:
        print(f"✅ Sync mode backup created: {backup_id}")
        return backup_id
    else:
        print("❌ Failed to create sync mode backup")
        return None

def cleanup_old_backups(vault_path: str) -> tuple[int, int]:
    """
    Clean up old backups to prevent clutter
    
    Args:
        vault_path: Path to the vault
        
    Returns:
        (number_cleaned, space_freed_mb)
    """
    manager = OgresyncBackupManager(vault_path)
    return manager.cleanup_old_backups()

def list_available_backups(vault_path: str):
    """
    List all available backups for user information
    
    Args:
        vault_path: Path to the vault
    """
    manager = OgresyncBackupManager(vault_path)
    backups = manager.list_backups()
    
    if not backups:
        print("📝 No backups found")
        return
    
    print(f"📋 Found {len(backups)} backup(s):")
    for backup in backups:
        print(f"  • {backup.backup_id}")
        print(f"    Created: {backup.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"    Reason: {backup.reason.value}")
        print(f"    Description: {backup.description}")
        print(f"    Type: {backup.backup_type.value}")
        print()

# Main functions for easy integration
__all__ = [
    'create_keep_remote_only_backup',
    'create_keep_local_only_backup', 
    'create_smart_merge_backup',
    'create_sync_mode_backup',
    'cleanup_old_backups',
    'list_available_backups'
]
