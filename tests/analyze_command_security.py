#!/usr/bin/env python3
"""
Analysis and fixes for command construction issues in the Ogresync codebase.

This script identifies and documents potential security and reliability issues
with git command construction using f-strings.
"""

import os
import subprocess
import tempfile
import shutil

def analyze_command_construction_issues():
    """Analyze and demonstrate command construction issues found in the codebase"""
    print("🔍 Command Construction Security Analysis")
    print("=" * 50)
    
    print("\n📋 Issues Found:")
    print("-" * 20)
    
    print("\n1. ❌ ISSUE: Unsafe commit message handling")
    print("   Location: Stage1_conflict_resolution.py lines 628, 630, 1337")
    print("   Problem: Commit messages inserted directly into shell commands")
    print("   Risk: Command injection if message contains quotes or special chars")
    
    # Demonstrate the issue
    print("\n🧪 Demonstrating the problem:")
    
    unsafe_message = 'Important fix" && echo "INJECTED COMMAND" && echo "'
    
    # Show what the current code would create
    windows_cmd = f'git commit -m "{unsafe_message}"'
    linux_cmd = f"git commit -m '{unsafe_message}'"
    
    print(f"   Unsafe Windows command: {windows_cmd}")
    print(f"   Unsafe Linux command: {linux_cmd}")
    print("   ❌ This could execute arbitrary commands!")
    
    print("\n2. ❌ ISSUE: Unsafe merge message handling")
    print("   Location: Stage1_conflict_resolution.py lines 677, 679")
    print("   Problem: Merge messages inserted directly into shell commands")
    print("   Risk: Same command injection vulnerability")
    
    # Show merge message issue
    unsafe_merge_msg = 'Merge branch" && rm -rf / && echo "'
    windows_merge_cmd = f'git merge origin/main --no-ff --allow-unrelated-histories -m "{unsafe_merge_msg}"'
    print(f"   Unsafe merge command: {windows_merge_cmd}")
    print("   ❌ Extremely dangerous!")
    
    print("\n✅ SOLUTIONS:")
    print("-" * 15)
    
    print("\n1. Use subprocess with argument lists instead of shell commands")
    print("2. Properly escape/sanitize user-controlled input")
    print("3. Use git's --file option for complex messages")
    print("4. Validate and sanitize commit messages before use")
    
    print("\n🔧 Recommended fixes:")
    print("   - Replace shell=True with proper argument lists")
    print("   - Use shlex.quote() for dynamic values")
    print("   - Write messages to temporary files for complex cases")
    
    return True

def demonstrate_safe_alternatives():
    """Demonstrate safe ways to construct git commands"""
    print("\n🛡️ Safe Command Construction Examples")
    print("=" * 45)
    
    # Create a test repository
    test_dir = tempfile.mkdtemp(prefix="safe_command_test_")
    print(f"📁 Test directory: {test_dir}")
    
    try:
        # Initialize git repo
        subprocess.run(['git', 'init'], cwd=test_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@test.com'], cwd=test_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=test_dir, capture_output=True)
        
        # Create a test file
        test_file = os.path.join(test_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("Test content")
        
        subprocess.run(['git', 'add', '.'], cwd=test_dir, capture_output=True)
        
        print("\n1. ✅ SAFE: Using subprocess with argument lists")
        
        # Safe commit with potentially dangerous message
        dangerous_message = 'Fix issue with "quotes" and && special chars'
        
        # Method 1: Argument list (safest)
        result1 = subprocess.run([
            'git', 'commit', '-m', dangerous_message
        ], cwd=test_dir, capture_output=True, text=True)
        
        if result1.returncode == 0:
            print(f"   ✅ Safe method 1 (arg list): SUCCESS")
            print(f"   Message handled: {dangerous_message}")
        else:
            print(f"   ❌ Failed: {result1.stderr}")
        
        print("\n2. ✅ SAFE: Using temporary files for complex messages")
        
        # Method 2: Temporary file for very complex messages
        complex_message = """Multi-line commit message
        With "quotes" and 'apostrophes'
        And $(dangerous) && commands
        
        This is much safer!"""
        
        # Write message to temporary file
        msg_file = os.path.join(test_dir, "commit_msg.tmp")
        with open(msg_file, 'w', encoding='utf-8') as f:
            f.write(complex_message)
        
        # Create another change to commit
        with open(test_file, 'a') as f:
            f.write("\nMore content")
        subprocess.run(['git', 'add', '.'], cwd=test_dir, capture_output=True)
        
        result2 = subprocess.run([
            'git', 'commit', '--file', msg_file
        ], cwd=test_dir, capture_output=True, text=True)
        
        if result2.returncode == 0:
            print(f"   ✅ Safe method 2 (temp file): SUCCESS")
            print(f"   Complex message handled safely")
        else:
            print(f"   ❌ Failed: {result2.stderr}")
        
        # Clean up temp file
        os.remove(msg_file)
        
        print("\n3. ✅ SAFE: Input validation and sanitization")
        
        def sanitize_commit_message(message):
            """Sanitize commit message for safe use"""
            # Remove dangerous characters and limit length
            import re
            # Replace dangerous patterns
            sanitized = re.sub(r'[`$();&|<>]', '', message)
            # Limit length
            sanitized = sanitized[:500]
            # Escape quotes properly
            sanitized = sanitized.replace('"', '\\"').replace("'", "\\'")
            return sanitized.strip()
        
        unsafe_input = 'Commit with $(dangerous) && commands'
        safe_message = sanitize_commit_message(unsafe_input)
        
        print(f"   Original: {unsafe_input}")
        print(f"   Sanitized: {safe_message}")
        print("   ✅ Safe to use in commands")
        
    except Exception as e:
        print(f"❌ Demo error: {e}")
    
    finally:
        try:
            shutil.rmtree(test_dir)
            print(f"\n🧹 Cleaned up: {test_dir}")
        except:
            pass

if __name__ == "__main__":
    analyze_command_construction_issues()
    demonstrate_safe_alternatives()
    
    print("\n🎯 SUMMARY:")
    print("=" * 15)
    print("The main security issues found are:")
    print("1. Direct insertion of user-controlled strings into shell commands")
    print("2. Platform-specific quote handling that's inconsistent")
    print("3. No input validation for commit/merge messages")
    print("\nThese should be fixed by using subprocess argument lists")
    print("and proper input sanitization.")
