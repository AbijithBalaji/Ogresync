#!/usr/bin/env python3
"""
Analysis of the git checkout quote issue and cross-platform behavior.

This script demonstrates why the extra quotes caused the bug and how it relates
to cross-platform command processing.
"""

import subprocess
import tempfile
import shutil
import os
import platform

def run_command_analysis():
    """Analyze how git processes quotes across different scenarios"""
    print("🔍 Git Checkout Quote Issue Analysis")
    print("=" * 50)
    print(f"🖥️  Platform: {platform.system()}")
    print(f"🐚 Shell: {os.environ.get('SHELL', 'Unknown')}")
    
    # Create a test repository
    test_dir = tempfile.mkdtemp(prefix="quote_analysis_")
    print(f"📁 Test directory: {test_dir}")
    
    try:
        # Set up a simple git repo
        subprocess.run(['git', 'init'], cwd=test_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@test.com'], cwd=test_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=test_dir, capture_output=True)
        
        # Create test files
        test_file = os.path.join(test_dir, "testfile.md")
        space_file = os.path.join(test_dir, "file with spaces.md")
        
        with open(test_file, 'w') as f:
            f.write("# Test File\nOriginal content\n")
        with open(space_file, 'w') as f:
            f.write("# File with Spaces\nOriginal content\n")
            
        subprocess.run(['git', 'add', '.'], cwd=test_dir, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=test_dir, capture_output=True)
        
        # Create a branch and modify files
        subprocess.run(['git', 'checkout', '-b', 'feature'], cwd=test_dir, capture_output=True)
        
        with open(test_file, 'w') as f:
            f.write("# Test File\nModified content\n")
        with open(space_file, 'w') as f:
            f.write("# File with Spaces\nModified content\n")
            
        subprocess.run(['git', 'add', '.'], cwd=test_dir, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Modified'], cwd=test_dir, capture_output=True)
        
        print("\n🧪 Testing different command formats...")
        print("-" * 40)
        
        # Test 1: Correct command (no extra quotes)
        print("\n1. ✅ CORRECT: git checkout master -- testfile.md")
        cmd1 = ['git', 'checkout', 'master', '--', 'testfile.md']
        result1 = subprocess.run(cmd1, cwd=test_dir, capture_output=True, text=True)
        print(f"   Return code: {result1.returncode}")
        if result1.returncode != 0:
            print(f"   Error: {result1.stderr.strip()}")
        else:
            print("   ✅ Success - file checked out correctly")
        
        # Reset file for next test
        subprocess.run(['git', 'checkout', 'feature'], cwd=test_dir, capture_output=True)
        
        # Test 2: Incorrect command (extra quotes around filename)
        print("\n2. ❌ BUGGY: git checkout master -- \"testfile.md\"")
        cmd2 = ['git', 'checkout', 'master', '--', '"testfile.md"']
        result2 = subprocess.run(cmd2, cwd=test_dir, capture_output=True, text=True)
        print(f"   Return code: {result2.returncode}")
        if result2.returncode != 0:
            print(f"   Error: {result2.stderr.strip()}")
            print("   ❌ Failed - git looks for a file literally named '\"testfile.md\"'")
        else:
            print("   Unexpected success")
            
        # Test 3: File with spaces - correct way
        print("\n3. ✅ CORRECT: git checkout master -- \"file with spaces.md\"")
        cmd3 = ['git', 'checkout', 'master', '--', 'file with spaces.md']
        result3 = subprocess.run(cmd3, cwd=test_dir, capture_output=True, text=True)
        print(f"   Return code: {result3.returncode}")
        if result3.returncode != 0:
            print(f"   Error: {result3.stderr.strip()}")
        else:
            print("   ✅ Success - spaced filename handled correctly")
            
        # Reset for next test
        subprocess.run(['git', 'checkout', 'feature'], cwd=test_dir, capture_output=True)
        
        # Test 4: File with spaces - wrong way (double quotes)
        print("\n4. ❌ BUGGY: git checkout master -- '\"file with spaces.md\"'")
        cmd4 = ['git', 'checkout', 'master', '--', '"file with spaces.md"']
        result4 = subprocess.run(cmd4, cwd=test_dir, capture_output=True, text=True)
        print(f"   Return code: {result4.returncode}")
        if result4.returncode != 0:
            print(f"   Error: {result4.stderr.strip()}")
            print("   ❌ Failed - git looks for '\"file with spaces.md\"' (with literal quotes)")
        else:
            print("   Unexpected success")
            
        print("\n🔍 Root Cause Analysis:")
        print("-" * 25)
        print("The issue was NOT platform-specific (Windows vs Linux vs Mac).")
        print("The issue was with how git interprets pathspecs:")
        print()
        print("When using subprocess.run() with a list of arguments:")
        print("✅ ['git', 'checkout', 'branch', '--', 'filename.md']")
        print("   → Git sees: filename.md")
        print()
        print("❌ ['git', 'checkout', 'branch', '--', '\"filename.md\"']")
        print("   → Git sees: \"filename.md\" (literal quotes in filename)")
        print()
        print("Git's pathspec matching is literal - it looks for exactly")
        print("what you specify, including any quote characters.")
        print()
        print("The bug occurred because the code was adding quotes around")
        print("filenames that were already properly escaped for subprocess.run().")
        
        print("\n💡 The Fix:")
        print("-" * 12)
        print("Remove the extra quotes around {missing_file} and {file_path}")
        print("in the f-string construction, because subprocess.run() with")
        print("a list already handles argument separation correctly.")
        
    except Exception as e:
        print(f"❌ Analysis error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        try:
            shutil.rmtree(test_dir)
            print(f"\n🧹 Cleaned up: {test_dir}")
        except:
            pass

if __name__ == "__main__":
    run_command_analysis()
