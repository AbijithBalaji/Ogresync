"""
Ogresync Backup Management System

This module provides centralized backup management for all Ogresync operations:
- File-based backups with clear naming and documentation
- Automatic cleanup and expiration
- Recovery instructions and restoration
- Prevention of backup pollution in sync operations

Key Principles:
1. Backups are LOCAL ONLY - never synced to remote
2. File-based snapshots in hidden .ogresync-backups/ folder
3. Clear, descriptive folder names for easy identification
4. Automatic cleanup based on age and count
5. User-friendly recovery interface with detailed READMEs

Author: Ogresync Development Team
Date: June 2025
"""

import os
import json
import time
import shutil
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum

class BackupType(Enum):
    """Types of backups supported"""
    FILE_SNAPSHOT = "file_snapshot"     # File-based snapshot (only option)

class BackupReason(Enum):
    """Reasons for creating backups"""
    CONFLICT_RESOLUTION = "conflict_resolution"
    SETUP_SAFETY = "setup_safety" 
    SYNC_OPERATION = "sync_operation"
    USER_REQUESTED = "user_requested"
    AUTO_CLEANUP = "auto_cleanup"

@dataclass
class BackupInfo:
    """Information about a backup"""
    backup_id: str
    backup_type: BackupType
    reason: BackupReason
    created_at: datetime
    description: str
    file_snapshot_path: Optional[str] = None
    files_backed_up: Optional[List[str]] = None
    size_bytes: int = 0
    can_restore: bool = True
    
class OgresyncBackupManager:
    """Centralized backup management for Ogresync"""
    
    def __init__(self, vault_path: str):
        self.vault_path = vault_path
        self.backup_base_dir = os.path.join(vault_path, ".ogresync-backups")
        self.backup_metadata_file = os.path.join(self.backup_base_dir, "backup_registry.json")
        
        # Backup limits and cleanup settings
        self.max_backups_per_type = 10
        self.max_backup_age_days = 30
        self.max_total_backup_size_mb = 500
        
        # Ensure backup infrastructure exists
        self._ensure_backup_infrastructure()
    
    def _ensure_backup_infrastructure(self):
        """Ensure backup directory and gitignore are set up"""
        # Create backup directory
        os.makedirs(self.backup_base_dir, exist_ok=True)
          # Ensure .gitignore excludes our backup directory
        gitignore_path = os.path.join(self.vault_path, ".gitignore")
        gitignore_content = ""
        
        if os.path.exists(gitignore_path):
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                gitignore_content = f.read()
        
        backup_ignore_line = ".ogresync-backups/"
        recovery_ignore_line = "OGRESYNC_RECOVERY_INSTRUCTIONS_*.txt"
        obsidian_ignore_line = ".obsidian/"
        
        if backup_ignore_line not in gitignore_content:
            gitignore_content += f"\n# Ogresync backups (local only)\n{backup_ignore_line}\n"
        
        if recovery_ignore_line not in gitignore_content:
            gitignore_content += f"{recovery_ignore_line}\n"
        
        if obsidian_ignore_line not in gitignore_content:
            gitignore_content += f"\n# Obsidian app settings (personal/local only)\n{obsidian_ignore_line}\n"
        
        with open(gitignore_path, 'w', encoding='utf-8') as f:
            f.write(gitignore_content)
    
    def create_backup(self, reason: BackupReason, description: str, 
                     files_to_backup: Optional[List[str]] = None) -> Optional[str]:
        """
        Create a file-based backup with clear naming and documentation
        
        Args:
            reason: Why the backup is being created
            description: Human-readable description
            files_to_backup: Specific files to backup (None = all meaningful files)
            
        Returns:
            Backup ID if successful, None if failed
        """
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        backup_id = f"backup_{timestamp}_{reason.value}"
        
        try:
            # Create file snapshot backup with improved naming
            snapshot_path = self._create_file_snapshot_backup(backup_id, description, files_to_backup)
            if snapshot_path:
                backup_info = BackupInfo(
                    backup_id=backup_id,
                    backup_type=BackupType.FILE_SNAPSHOT,
                    reason=reason,
                    created_at=datetime.now(),
                    description=description,
                    file_snapshot_path=snapshot_path,
                    files_backed_up=files_to_backup or [],
                    size_bytes=self._calculate_directory_size(snapshot_path)
                )
                self._register_backup(backup_info)
                self._create_recovery_instructions(backup_info)
                return backup_id
            
        except Exception as e:
            print(f"[ERROR] Failed to create backup: {e}")
        
        return None
    
    def _create_file_snapshot_backup(self, backup_id: str, description: str, 
                                   files_to_backup: Optional[List[str]] = None) -> Optional[str]:
        """Create a file-based snapshot backup with improved naming and documentation"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            # Create a more descriptive folder name based on the description
            reason_clean = backup_id.split('_')[-1]  # Extract reason from backup_id
            
            # Create user-friendly folder names based on the description
            if "Keep Remote Only" in description:
                folder_name = f"LOCAL_FILES_before_adopting_remote_{timestamp}"
            elif "Keep Local Only" in description:
                folder_name = f"REMOTE_FILES_before_keeping_local_{timestamp}"
            elif "Smart Merge" in description or "conflict_resolution" in reason_clean:
                folder_name = f"CONFLICT_BACKUP_before_merge_{timestamp}"
            elif "setup" in reason_clean or "Setup" in description:
                folder_name = f"SETUP_SAFETY_backup_{timestamp}"
            else:
                folder_name = f"{reason_clean.upper()}_backup_{timestamp}"
            
            snapshot_dir = os.path.join(self.backup_base_dir, folder_name)
            
            os.makedirs(snapshot_dir, exist_ok=True)
            
            # Create detailed backup manifest and README
            manifest = {
                "backup_info": {
                    "backup_id": backup_id,
                    "created_at": datetime.now().isoformat(),
                    "description": description,
                    "reason": reason_clean,
                    "backup_folder": folder_name
                },
                "files_backed_up": [],
                "backup_summary": {
                    "total_files": 0,
                    "total_size_bytes": 0,
                    "backup_complete": False
                }
            }
            
            total_size = 0
            file_count = 0
            
            if files_to_backup:
                # Backup specific files
                for file_path in files_to_backup:
                    src_path = os.path.join(self.vault_path, file_path)
                    if os.path.exists(src_path):
                        dst_path = os.path.join(snapshot_dir, file_path)
                        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                        shutil.copy2(src_path, dst_path)
                        file_size = os.path.getsize(src_path)
                        manifest["files_backed_up"].append({
                            "file_path": file_path,
                            "size_bytes": file_size,
                            "backed_up_at": datetime.now().isoformat()
                        })
                        total_size += file_size
                        file_count += 1
            else:
                # Backup all meaningful files
                for root, dirs, files in os.walk(self.vault_path):
                    # Skip backup directories and git
                    dirs[:] = [d for d in dirs if d not in {'.git', '.ogresync-backups', '__pycache__'}]
                    
                    for file in files:
                        src_path = os.path.join(root, file)
                        rel_path = os.path.relpath(src_path, self.vault_path)
                        
                        if self._is_meaningful_file(rel_path):
                            dst_path = os.path.join(snapshot_dir, rel_path)
                            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                            shutil.copy2(src_path, dst_path)
                            file_size = os.path.getsize(src_path)
                            manifest["files_backed_up"].append({
                                "file_path": rel_path,
                                "size_bytes": file_size,
                                "backed_up_at": datetime.now().isoformat()
                            })
                            total_size += file_size
                            file_count += 1
            
            # Update summary
            manifest["backup_summary"]["total_files"] = file_count
            manifest["backup_summary"]["total_size_bytes"] = total_size
            manifest["backup_summary"]["backup_complete"] = True
            
            # Save detailed manifest
            manifest_path = os.path.join(snapshot_dir, "backup_manifest.json")
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
            
            # Create user-friendly README
            # Create user-friendly README
            backup_purpose = ""
            if "Keep Remote Only" in description:
                backup_purpose = """
📋 WHAT HAPPENED:
You chose to "Keep Remote Only" during conflict resolution.
This backup contains YOUR LOCAL FILES that were replaced with remote files.

🔍 WHAT'S IN THIS BACKUP:
All your local files exactly as they were before being replaced.
Use this backup to recover any local work you want to keep.
"""
            elif "Keep Local Only" in description:
                backup_purpose = """
📋 WHAT HAPPENED:
You chose to "Keep Local Only" during conflict resolution.
This backup contains the REMOTE FILES that were not adopted.

🔍 WHAT'S IN THIS BACKUP:
All the remote files that were available but not used.
Use this backup to see what was in the remote repository.
"""
            elif "Smart Merge" in description or "conflict" in description.lower():
                backup_purpose = """
📋 WHAT HAPPENED:
A conflict resolution was performed using Smart Merge strategy.
This backup contains files before any changes were made.

🔍 WHAT'S IN THIS BACKUP:
Your files exactly as they were before conflict resolution.
Use this backup to compare or recover specific versions.
"""
            else:
                backup_purpose = """
📋 WHAT HAPPENED:
A backup was created for safety during an Ogresync operation.

🔍 WHAT'S IN THIS BACKUP:
Your files exactly as they were before the operation.
"""

            readme_content = f"""
OGRESYNC BACKUP - {folder_name.split('_', 3)[-1].replace('_', ' ').upper()}
{'=' * 70}

📅 Backup Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📋 Description: {description}
📂 Backup ID: {backup_id}
📊 Files Backed Up: {file_count}
💾 Total Size: {total_size / 1024:.1f} KB
{backup_purpose}

HOW TO RESTORE FILES:
{'-' * 20}
1. Browse the files in this folder - they're organized exactly like your vault
2. Copy any files you want to restore back to your vault
3. You can copy individual files or entire folders
4. Overwrite existing files if you want to restore the old version

FOLDER STRUCTURE:
{'-' * 15}
This backup preserves your exact folder structure.
Each file is in the same relative location as it was in your vault.

SAFETY NOTES:
{'-' * 12}
✅ This backup is LOCAL ONLY - it will NOT be synced to GitHub
✅ Safe to delete this entire folder when you no longer need it
✅ Automatic cleanup will delete this backup after 30 days
✅ You can make copies of files you want to keep permanently

TECHNICAL INFO:
{'-' * 15}
- Backup Type: File Snapshot
- Manifest file: backup_manifest.json (contains detailed file list)
- Original vault path: {self.vault_path}
- Backup folder: {folder_name}

Generated by Ogresync Backup Manager
"""
            
            readme_path = os.path.join(snapshot_dir, "README.txt")
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            
            print(f"✅ File snapshot backup created: {snapshot_dir}")
            print(f"   📊 {file_count} files backed up ({total_size / 1024:.1f} KB)")
            return snapshot_dir
            
        except Exception as e:
            print(f"❌ Error creating file snapshot backup: {e}")
            return None
    
    def _is_meaningful_file(self, file_path: str) -> bool:
        """Check if a file should be backed up"""
        file_name = os.path.basename(file_path)
          # System and temporary files to ignore
        ignored_files = {
            '.gitignore', '.DS_Store', 'Thumbs.db', 'desktop.ini',
            'config.txt', 'ogresync.exe'
        }
        
        ignored_extensions = {
            '.pyc', '.pyo', '.pyd', '.so', '.dll', '.dylib',
            '.tmp', '.temp', '.log', '.cache', '.ico', '.exe'
        }
        
        ignored_patterns = {
            '.git/', '.ogresync-backups/', '__pycache__/', '.vscode/',
            '.idea/', '.vs/', 'node_modules/', 'OGRESYNC_RECOVERY_INSTRUCTIONS',
            '.obsidian/'
        }
        
        if file_name in ignored_files:
            return False
        
        if file_name.startswith('.'):
            return False
        
        _, ext = os.path.splitext(file_name)
        if ext.lower() in ignored_extensions:
            return False
        
        normalized_path = file_path.replace('\\', '/')
        for pattern in ignored_patterns:
            if pattern in normalized_path:
                return False
        
        return True
    
    def _register_backup(self, backup_info: BackupInfo):
        """Register backup in metadata registry"""
        registry = self._load_backup_registry()
        backup_dict = asdict(backup_info)
          # Convert datetime and enums to strings for JSON serialization
        backup_dict['created_at'] = backup_info.created_at.isoformat()
        backup_dict['backup_type'] = backup_info.backup_type.value
        backup_dict['reason'] = backup_info.reason.value
        
        registry[backup_info.backup_id] = backup_dict
        self._save_backup_registry(registry)
    
    def _load_backup_registry(self) -> Dict:
        """Load backup registry from disk"""
        if os.path.exists(self.backup_metadata_file):
            try:
                with open(self.backup_metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save_backup_registry(self, registry: Dict):
        """Save backup registry to disk"""
        try:
            os.makedirs(os.path.dirname(self.backup_metadata_file), exist_ok=True)
            with open(self.backup_metadata_file, 'w', encoding='utf-8') as f:
                json.dump(registry, f, indent=2)
        except Exception as e:
            print(f"❌ Error saving backup registry: {e}")
    
    def _create_recovery_instructions(self, backup_info: BackupInfo):
        """Create user-friendly recovery instructions"""
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        # Create recovery instructions in backup directory, not in the main vault
        backup_dir = os.path.join(self.vault_path, '.ogresync-backups')
        os.makedirs(backup_dir, exist_ok=True)
        instructions_file = os.path.join(backup_dir, f"OGRESYNC_RECOVERY_INSTRUCTIONS_{timestamp}.txt")
        
        instructions = f"""
OGRESYNC RECOVERY INSTRUCTIONS
==============================

Backup Created: {backup_info.created_at.strftime('%Y-%m-%d %H:%M:%S')}
Backup ID: {backup_info.backup_id}
Reason: {backup_info.reason.value}
Description: {backup_info.description}

RECOVERY OPTIONS:
"""
        
        instructions += f"""
📁 FILE SNAPSHOT RECOVERY:
1. Browse backup files:
   Open: {backup_info.file_snapshot_path}
   
2. Restore specific files:
   Copy files from backup folder to your vault
   
3. View backup manifest:
   Open: {os.path.join(backup_info.file_snapshot_path or '', 'backup_manifest.json')}

🗑️ DELETE BACKUP WHEN NO LONGER NEEDED:
   Delete folder: {backup_info.file_snapshot_path}
"""
        
        instructions += f"""

⚠️ IMPORTANT NOTES:
- This backup is LOCAL ONLY and will not be synced to remote
- Backups are automatically cleaned up after {self.max_backup_age_days} days
- You can safely delete this instruction file after reading
- Use 'ogresync backup list' to see all backups

Generated by Ogresync Backup Manager
"""
        
        try:
            with open(instructions_file, 'w', encoding='utf-8') as f:
                f.write(instructions)
            print(f"📋 Recovery instructions saved: {instructions_file}")
        except Exception as e:
            print(f"❌ Error creating recovery instructions: {e}")
    
    def list_backups(self) -> List[BackupInfo]:
        """List all available backups"""
        registry = self._load_backup_registry()
        backups = []
        
        for backup_id, backup_data in registry.items():
            try:
                backup_data['created_at'] = datetime.fromisoformat(backup_data['created_at'])
                backup_data['backup_type'] = BackupType(backup_data['backup_type'])
                backup_data['reason'] = BackupReason(backup_data['reason'])
                backups.append(BackupInfo(**backup_data))
            except Exception as e:
                print(f"❌ Error loading backup {backup_id}: {e}")
        
        return sorted(backups, key=lambda b: b.created_at, reverse=True)
    
    def cleanup_old_backups(self, force: bool = False) -> Tuple[int, int]:
        """
        Clean up old backups based on age and count limits
        
        Returns:
            (cleaned_count, total_space_freed_mb)
        """
        cleaned_count = 0
        space_freed = 0
        
        backups = self.list_backups()
        cutoff_date = datetime.now() - timedelta(days=self.max_backup_age_days)
        
        # Group backups by reason for per-type limits
        backups_by_reason = {}
        for backup in backups:
            if backup.reason not in backups_by_reason:
                backups_by_reason[backup.reason] = []
            backups_by_reason[backup.reason].append(backup)
        
        registry = self._load_backup_registry()
        
        for reason, backup_list in backups_by_reason.items():
            # Sort by date (newest first)
            backup_list.sort(key=lambda b: b.created_at, reverse=True)
            
            for i, backup in enumerate(backup_list):
                should_delete = False
                
                # Delete if too old
                if backup.created_at < cutoff_date:
                    should_delete = True
                    print(f"🕒 Backup {backup.backup_id} is older than {self.max_backup_age_days} days")
                
                # Delete if exceeds count limit (keep newest)
                elif i >= self.max_backups_per_type:
                    should_delete = True
                    print(f"📊 Backup {backup.backup_id} exceeds count limit ({self.max_backups_per_type})")
                
                if should_delete or force:
                    if self._delete_backup(backup):
                        cleaned_count += 1
                        space_freed += backup.size_bytes
                        del registry[backup.backup_id]
        
        self._save_backup_registry(registry)
        return cleaned_count, space_freed // (1024 * 1024)  # Convert to MB
    
    def _delete_backup(self, backup_info: BackupInfo) -> bool:
        """Delete a specific backup"""
        try:
            if backup_info.backup_type == BackupType.FILE_SNAPSHOT and backup_info.file_snapshot_path:
                # Delete snapshot directory
                if os.path.exists(backup_info.file_snapshot_path):
                    shutil.rmtree(backup_info.file_snapshot_path)
                    print(f"🗑️ Deleted snapshot: {backup_info.file_snapshot_path}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error deleting backup {backup_info.backup_id}: {e}")
            return False
    
    def _calculate_directory_size(self, directory: str) -> int:
        """Calculate total size of directory in bytes"""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
        except Exception as e:
            print(f"❌ Error calculating directory size: {e}")
        return total_size


# Convenience functions for easy integration
def create_conflict_resolution_backup(vault_path: str, strategy: str) -> Optional[str]:
    """Create backup before conflict resolution"""
    manager = OgresyncBackupManager(vault_path)
    return manager.create_backup(
        BackupReason.CONFLICT_RESOLUTION,
        f"Before conflict resolution: {strategy} strategy"
    )

def create_setup_safety_backup(vault_path: str, step: str) -> Optional[str]:
    """Create backup during setup for safety"""
    manager = OgresyncBackupManager(vault_path)
    return manager.create_backup(
        BackupReason.SETUP_SAFETY,
        f"Setup safety backup: {step}"
    )

def cleanup_all_backups(vault_path: str) -> Tuple[int, int]:
    """Clean up old backups"""
    manager = OgresyncBackupManager(vault_path)
    return manager.cleanup_old_backups()


if __name__ == "__main__":
    # Test the backup system
    print("Testing Ogresync Backup Manager...")
    
    test_vault = "/tmp/test_vault"
    if not os.path.exists(test_vault):
        os.makedirs(test_vault)
    
    manager = OgresyncBackupManager(test_vault)
    
    # Test backup creation
    backup_id = manager.create_backup(
        BackupReason.CONFLICT_RESOLUTION,
        "Test backup for development"
    )
    
    if backup_id:
        print(f"✅ Test backup created: {backup_id}")
        
        # List backups
        backups = manager.list_backups()
        print(f"✅ Found {len(backups)} backups")
        
        # Test cleanup
        cleaned, space_freed = manager.cleanup_old_backups(force=True)
        print(f"✅ Cleanup completed: {cleaned} backups removed, {space_freed}MB freed")
    else:
        print("❌ Test backup failed")
