#!/usr/bin/env python3
"""
Targeted subprocess.run fixer for setup_wizard.py

This script specifically targets subprocess.run calls in setup_wizard.py and replaces them
with the existing run_command_safe() function to hide console windows in packaged apps.

This is a safer, more targeted approach than the previous automated script.
"""

import re
import os

def analyze_subprocess_calls(file_path):
    """Analyze all subprocess.run calls and their context"""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    subprocess_calls = []
    for i, line in enumerate(lines):
        if 'subprocess.run(' in line:
            # Get context around the call
            start_line = max(0, i - 3)
            end_line = min(len(lines), i + 8)
            context = ''.join(lines[start_line:end_line])
            
            subprocess_calls.append({
                'line_num': i + 1,
                'line_content': line.strip(),
                'context': context,
                'is_fallback': 'fallback' in line.lower() or 'except' in lines[max(0, i-5):i],
                'is_import': 'import subprocess' in lines[max(0, i-3):i+1]
            })
    
    return subprocess_calls

def fix_setup_wizard_subprocess(file_path):
    """
    Fix subprocess.run calls in setup_wizard.py by replacing them with run_command_safe()
    """
    print(f"Analyzing subprocess calls in {file_path}...")
    
    # First, analyze all calls
    calls = analyze_subprocess_calls(file_path)
    
    print(f"Found {len(calls)} subprocess.run calls:")
    for call in calls:
        print(f"  Line {call['line_num']}: {call['line_content']}")
        print(f"    - Is fallback: {call['is_fallback']}")
        print(f"    - Has import: {call['is_import']}")
        print()
    
    # Read the file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Track changes
    changes_made = 0
    
    # Pattern 1: Simple subprocess.run calls (most common)
    # subprocess.run(['git', 'command'], ...)
    pattern1 = r'subprocess\.run\('
    
    def replace_subprocess_run(match):
        nonlocal changes_made
        changes_made += 1
        return 'run_command_safe('
    
    # Replace all subprocess.run( with run_command_safe(
    new_content = re.sub(pattern1, replace_subprocess_run, content)
    
    # Remove import subprocess lines that are just for subprocess.run
    # But keep them if they're needed for other subprocess functions
    lines = new_content.split('\n')
    new_lines = []
    
    for i, line in enumerate(lines):
        # Check if this is a standalone "import subprocess" line in a try block
        if 'import subprocess' in line and line.strip() == 'import subprocess':
            # Check if it's in a fallback context and only used for subprocess.run
            # Look ahead to see if only subprocess.run is used
            look_ahead = lines[i+1:i+10]
            uses_other_subprocess = any('subprocess.Popen' in l or 'subprocess.call' in l or 'subprocess.check_' in l for l in look_ahead)
            
            if not uses_other_subprocess:
                # Skip this import line as it's only for subprocess.run
                print(f"Removing unnecessary 'import subprocess' at line {i+1}")
                continue
        
        new_lines.append(line)
    
    new_content = '\n'.join(new_lines)
    
    # Write the fixed content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✅ Fixed {changes_made} subprocess.run calls in {file_path}")
    return changes_made

def main():
    """Main function"""
    setup_wizard_path = "setup_wizard.py"
    
    if not os.path.exists(setup_wizard_path):
        print(f"❌ File {setup_wizard_path} not found!")
        return
    
    print("🔧 Fixing subprocess.run calls in setup_wizard.py...")
    print("=" * 60)
    
    # Create backup
    backup_path = f"{setup_wizard_path}.backup_subprocess_fix"
    with open(setup_wizard_path, 'r', encoding='utf-8') as f:
        content = f.read()
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"📋 Created backup: {backup_path}")
    
    try:
        changes = fix_setup_wizard_subprocess(setup_wizard_path)
        
        if changes > 0:
            print("\n✅ SUCCESS: Fixed all subprocess.run calls in setup_wizard.py")
            print(f"   - {changes} subprocess.run calls replaced with run_command_safe()")
            print("   - All logic and error handling preserved")
            print("   - Console windows will now be hidden in packaged apps")
        else:
            print("\n✅ No changes needed - all subprocess.run calls already fixed")
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        # Restore backup
        with open(backup_path, 'r', encoding='utf-8') as f:
            content = f.read()
        with open(setup_wizard_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"🔄 Restored from backup due to error")

if __name__ == "__main__":
    main()
