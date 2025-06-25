#!/usr/bin/env python3
"""
Test script to verify that upstream tracking doesn't interfere with Ogresync workflow.
Tests the critical sync scenarios with tracking enabled.
"""

import os
import shutil
import tempfile
import subprocess
import time

def run_command(cmd, cwd=None, capture_output=False):
    """Run a command and return output, error, and return code."""
    try:
        if capture_output:
            result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=30)
            return result.stdout.strip(), result.stderr.strip(), result.returncode
        else:
            result = subprocess.run(cmd, shell=True, cwd=cwd, timeout=30)
            return "", "", result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timed out", 1
    except Exception as e:
        return "", str(e), 1

class UpstreamTrackingTester:
    def __init__(self):
        self.temp_dir: str = ""
        self.local_repo: str = ""
        self.remote_repo: str = ""
        
    def setup_test_repos(self):
        """Set up local and remote test repositories."""
        print("Setting up test repositories...")
        
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp(prefix="ogresync_upstream_test_")
        print(f"Test directory: {self.temp_dir}")
        
        # Create remote (bare) repository
        self.remote_repo = os.path.join(self.temp_dir, "remote.git")
        os.makedirs(self.remote_repo)
        run_command("git init --bare", cwd=self.remote_repo)
        
        # Create local repository
        self.local_repo = os.path.join(self.temp_dir, "local")
        os.makedirs(self.local_repo)
        run_command("git init", cwd=self.local_repo)
        run_command("git config user.email 'test@example.com'", cwd=self.local_repo)
        run_command("git config user.name 'Test User'", cwd=self.local_repo)
        run_command(f"git remote add origin {self.remote_repo}", cwd=self.local_repo)
        
        # Create initial file and commit
        with open(os.path.join(self.local_repo, "README.md"), "w") as f:
            f.write("# Test Repository\n")
        
        run_command("git add README.md", cwd=self.local_repo)
        run_command("git commit -m 'Initial commit'", cwd=self.local_repo)
        
        print("✅ Test repositories set up successfully")
        
    def test_push_with_upstream(self):
        """Test pushing with -u flag sets upstream tracking."""
        print("\nTest 1: Push with upstream tracking...")
        
        # Push with -u flag
        out, err, rc = run_command("git push -u origin main", cwd=self.local_repo, capture_output=True)
        if rc != 0:
            print(f"❌ Push failed: {err}")
            return False
            
        # Check if upstream is set
        upstream_out, upstream_err, upstream_rc = run_command("git rev-parse --abbrev-ref main@{upstream}", cwd=self.local_repo, capture_output=True)
        if upstream_rc == 0 and upstream_out == "origin/main":
            print("✅ Upstream tracking correctly set to origin/main")
        else:
            print(f"❌ Upstream tracking not set correctly: {upstream_out}, error: {upstream_err}")
            return False
            
        return True
        
    def test_unpushed_commit_detection(self):
        """Test that unpushed commit detection works correctly with upstream tracking."""
        print("\nTest 2: Unpushed commit detection with tracking...")
        
        # Check initial unpushed commits (should be 0)
        out, err, rc = run_command("git rev-list --count HEAD ^origin/main", cwd=self.local_repo, capture_output=True)
        if rc == 0 and out == "0":
            print("✅ Correctly reports 0 unpushed commits after push")
        else:
            print(f"❌ Incorrect unpushed count after push: {out}, error: {err}")
            return False
            
        # Add a new commit
        with open(os.path.join(self.local_repo, "test.txt"), "w") as f:
            f.write("Test content\n")
        run_command("git add test.txt", cwd=self.local_repo)
        run_command("git commit -m 'Add test file'", cwd=self.local_repo)
        
        # Check unpushed commits (should be 1)
        out, err, rc = run_command("git rev-list --count HEAD ^origin/main", cwd=self.local_repo, capture_output=True)
        if rc == 0 and out == "1":
            print("✅ Correctly reports 1 unpushed commit after new commit")
        else:
            print(f"❌ Incorrect unpushed count after new commit: {out}, error: {err}")
            return False
            
        return True
        
    def test_pull_with_tracking(self):
        """Test that pull operations work correctly with upstream tracking."""
        print("\nTest 3: Pull operations with tracking...")
        
        # Create a clone to simulate remote changes
        clone_repo = os.path.join(self.temp_dir, "clone")
        run_command(f"git clone {self.remote_repo} {clone_repo}", cwd=self.temp_dir)
        
        # Make a change in the clone
        with open(os.path.join(clone_repo, "remote_file.txt"), "w") as f:
            f.write("Remote content\n")
        run_command("git add remote_file.txt", cwd=clone_repo)
        run_command("git commit -m 'Add remote file'", cwd=clone_repo)
        run_command("git push origin main", cwd=clone_repo)
        
        # Fetch and check if we can see the remote changes
        run_command("git fetch origin", cwd=self.local_repo)
        out, err, rc = run_command("git log --oneline origin/main", cwd=self.local_repo, capture_output=True)
        if "Add remote file" in out:
            print("✅ Remote changes visible after fetch")
        else:
            print(f"❌ Remote changes not visible: {out}")
            return False
            
        # Pull the changes
        out, err, rc = run_command("git pull origin main", cwd=self.local_repo, capture_output=True)
        if rc == 0:
            print("✅ Pull operation successful")
        else:
            print(f"❌ Pull failed: {err}")
            return False
            
        # Verify the file exists
        if os.path.exists(os.path.join(self.local_repo, "remote_file.txt")):
            print("✅ Remote file pulled successfully")
            return True
        else:
            print("❌ Remote file not found after pull")
            return False
            
    def test_force_push_scenarios(self):
        """Test force push scenarios with upstream tracking."""
        print("\nTest 4: Force push scenarios...")
        
        # Make conflicting changes in local
        with open(os.path.join(self.local_repo, "conflict_file.txt"), "w") as f:
            f.write("Local version\n")
        run_command("git add conflict_file.txt", cwd=self.local_repo)
        run_command("git commit -m 'Local conflicting change'", cwd=self.local_repo)
        
        # Test regular push (should fail due to non-fast-forward)
        out, err, rc = run_command("git push origin main", cwd=self.local_repo, capture_output=True)
        if rc != 0 and ("non-fast-forward" in err or "rejected" in err or "fetch first" in err):
            print("✅ Regular push correctly rejected for non-fast-forward")
        else:
            print(f"❌ Expected push rejection, but got rc={rc}, err={err}")
            return False
            
        # Test force push with lease
        out, err, rc = run_command("git push --force-with-lease origin main", cwd=self.local_repo, capture_output=True)
        if rc == 0:
            print("✅ Force push with lease successful")
        else:
            print(f"❌ Force push with lease failed: {err}")
            return False
            
        return True
        
    def run_all_tests(self):
        """Run all upstream tracking tests."""
        print("Starting Upstream Tracking Integration Tests")
        print("=" * 50)
        
        try:
            self.setup_test_repos()
            
            tests = [
                self.test_push_with_upstream,
                self.test_unpushed_commit_detection,
                self.test_pull_with_tracking,
                self.test_force_push_scenarios
            ]
            
            passed = 0
            total = len(tests)
            
            for test in tests:
                if test():
                    passed += 1
                else:
                    print("❌ Test failed!")
                    
            print("\n" + "=" * 50)
            print(f"Test Results: {passed}/{total} tests passed")
            
            if passed == total:
                print("🎉 All upstream tracking integration tests PASSED!")
                return True
            else:
                print("💥 Some tests FAILED!")
                return False
                
        except Exception as e:
            print(f"❌ Test suite failed with exception: {e}")
            return False
        finally:
            self.cleanup()
            
    def cleanup(self):
        """Clean up test files."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                print(f"✅ Cleaned up test directory: {self.temp_dir}")
            except Exception as e:
                print(f"⚠️ Could not clean up {self.temp_dir}: {e}")

if __name__ == "__main__":
    tester = UpstreamTrackingTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)
