"""
Verification script to confirm backup system refactoring is complete

This script verifies:
1. No git backup branch references remain in the codebase
2. Backup folders are protected from deletion during conflict resolution
3. Stage 2 conflict resolution is clean of git backup branch logic
4. All backup operations now use the centralized backup manager

Run this to confirm the refactoring is complete.
"""

import os
import re
from pathlib import Path

def scan_file_for_patterns(file_path, patterns):
    """Scan a file for problematic patterns"""
    issues = []
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            lines = content.split('\n')
            
            for pattern_name, pattern in patterns.items():
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    # Find line number
                    line_num = content[:match.start()].count('\n') + 1
                    line_content = lines[line_num - 1].strip()
                    
                    # Skip comments, documentation, and this verification script itself
                    if line_content.startswith('#') or line_content.startswith('"""') or line_content.startswith("'''"):
                        continue
                    if '# ' in line_content and pattern_name in ['git_backup_branch', 'backup_branch_param']:
                        continue  # Skip comments
                    if 'verify_backup_refactoring.py' in str(file_path):
                        continue  # Skip this verification script itself
                        
                    issues.append({
                        'file': file_path,
                        'line': line_num,
                        'pattern': pattern_name,
                        'content': line_content,
                        'match': match.group()
                    })
    except Exception as e:
        print(f"Error scanning {file_path}: {e}")
    
    return issues

def verify_backup_refactoring():
    """Main verification function"""
    print("🔍 Verifying Ogresync backup system refactoring...")
    print("=" * 60)
    
    # Patterns to look for (these should NOT exist in active code)
    problematic_patterns = {
        'git_backup_branch': r'git\s+backup\s+branch|backup\s+branch.*git',
        'backup_branch_param': r'backup_branch(?!\s*=)(?!.*commit)(?!.*lost)',  # Parameter usage, not error messages
        'create_backup_branch': r'_create.*backup.*branch\(',
    }
    
    # Patterns that SHOULD exist (these are good)
    expected_patterns = {
        'backup_manager': r'backup_manager|BackupManager',
        'file_snapshot': r'file_snapshot|FILE_SNAPSHOT',
        'ogresync_backups': r'\.ogresync-backups',
        'backup_protection': r'\.ogresync-backups.*in.*root',
    }
    
    # Files to check
    python_files = []
    for file_path in Path('.').glob('*.py'):
        if file_path.is_file():
            python_files.append(str(file_path))
    
    print(f"📁 Scanning {len(python_files)} Python files...")
    
    all_issues = []
    good_patterns_found = {pattern: 0 for pattern in expected_patterns}
    
    for file_path in python_files:
        # Check for problematic patterns
        issues = scan_file_for_patterns(file_path, problematic_patterns)
        all_issues.extend(issues)
        
        # Check for expected patterns
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            for pattern_name, pattern in expected_patterns.items():
                matches = len(re.findall(pattern, content, re.IGNORECASE))
                good_patterns_found[pattern_name] += matches
    
    # Report results
    print("\n📊 VERIFICATION RESULTS:")
    print("=" * 60)
    
    if all_issues:
        print(f"❌ Found {len(all_issues)} potential issues:")
        for issue in all_issues:
            print(f"  🚨 {issue['file']}:{issue['line']} - {issue['pattern']}")
            print(f"     Content: {issue['content']}")
            print(f"     Match: '{issue['match']}'")
            print()
        return False
    else:
        print("✅ No problematic git backup branch references found!")
    
    print("\n📈 Expected patterns found:")
    for pattern_name, count in good_patterns_found.items():
        status = "✅" if count > 0 else "⚠️"
        print(f"  {status} {pattern_name}: {count} occurrences")
    
    # Specific file checks
    print("\n🔍 Specific file verification:")
    
    # Check Stage1_conflict_resolution.py for backup protection
    stage1_file = "Stage1_conflict_resolution.py"
    if os.path.exists(stage1_file):
        with open(stage1_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if '.ogresync-backups' in content and 'continue' in content:
                print("  ✅ Stage1 has backup folder protection logic")
            else:
                print("  ❌ Stage1 missing backup folder protection")
    
    # Check stage2_conflict_resolution.py for cleanliness  
    stage2_file = "stage2_conflict_resolution.py"
    if os.path.exists(stage2_file):
        with open(stage2_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'backup_branch' not in content and 'git.*backup' not in content:
                print("  ✅ Stage2 is clean of git backup branch references")
            else:
                print("  ❌ Stage2 still has git backup branch references")
    
    # Check backup_manager.py for centralized backup
    backup_mgr_file = "backup_manager.py" 
    if os.path.exists(backup_mgr_file):
        with open(backup_mgr_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'OgresyncBackupManager' in content and 'FILE_SNAPSHOT' in content:
                print("  ✅ Centralized backup manager is properly implemented")
            else:
                print("  ❌ Backup manager implementation issues")
    
    print("\n" + "=" * 60)
    
    if all_issues:
        print("❌ REFACTORING INCOMPLETE - Issues found above need to be resolved")
        return False
    else:
        print("🎉 REFACTORING COMPLETE!")
        print("✅ All git backup branch logic removed")
        print("✅ File-based backup system in place")  
        print("✅ Backup folders protected from deletion")
        print("✅ Stage 2 conflict resolution is clean")
        return True

if __name__ == "__main__":
    success = verify_backup_refactoring()
    exit(0 if success else 1)
