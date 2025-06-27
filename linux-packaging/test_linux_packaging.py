#!/usr/bin/env python3
"""
Test script for Linux packaging system

This script tests various components of the Linux packaging system
to ensure everything works correctly before building the AppImage.

Usage:
    python3 linux-packaging/test_linux_packaging.py [--verbose]
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Add the linux-packaging directory to Python path
linux_packaging_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, linux_packaging_dir)

try:
    from linux_packaging_utils import *
    LINUX_UTILS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import linux_packaging_utils: {e}")
    print("Some tests may be skipped.")
    LINUX_UTILS_AVAILABLE = False


class LinuxPackagingTester:
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.test_results = []
    
    def log(self, message, is_error=False):
        """Log a message"""
        prefix = "[ERROR]" if is_error else "[INFO]"
        print(f"{prefix} {message}")
        if self.verbose or is_error:
            sys.stdout.flush()
    
    def run_test(self, test_name, test_func):
        """Run a test and record the result"""
        self.log(f"Running test: {test_name}")
        try:
            result = test_func()
            self.test_results.append((test_name, True, None))
            self.log(f"✓ {test_name} passed")
            return True
        except Exception as e:
            self.test_results.append((test_name, False, str(e)))
            self.log(f"✗ {test_name} failed: {e}", is_error=True)
            return False
    
    def test_system_detection(self):
        """Test system detection functions"""
        if not LINUX_UTILS_AVAILABLE:
            raise Exception("Linux utils not available")
            
        assert is_linux(), "Should detect Linux system"
        
        distro = get_linux_distro()
        assert isinstance(distro, dict), "Should return dictionary"
        assert "name" in distro, "Should have distro name"
        
        desktop = get_desktop_environment()
        assert isinstance(desktop, str), "Should return string"
        
        self.log(f"Detected distro: {distro['name']}")
        self.log(f"Detected desktop: {desktop}")
        
        return True
    
    def test_path_resolution(self):
        """Test path resolution functions"""
        if not LINUX_UTILS_AVAILABLE:
            raise Exception("Linux utils not available")
            
        # Test config directory
        config_dir = get_linux_config_directory()
        assert os.path.exists(config_dir), "Config directory should be created"
        
        # Test data directory
        data_dir = get_linux_data_directory()
        assert os.path.exists(data_dir), "Data directory should be created"
        
        # Test resource path resolution
        resource_path = get_linux_resource_path("assets/new_logo_1.png")
        assert isinstance(resource_path, str), "Should return string path"
        
        self.log(f"Config dir: {config_dir}")
        self.log(f"Data dir: {data_dir}")
        self.log(f"Resource path: {resource_path}")
        
        return True
    
    def test_desktop_integration(self):
        """Test desktop integration functions"""
        if not LINUX_UTILS_AVAILABLE:
            raise Exception("Linux utils not available")
            
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test desktop file creation
            desktop_file = os.path.join(temp_dir, "test.desktop")
            
            # Mock the desktop directory for testing
            original_expanduser = os.path.expanduser
            def mock_expanduser(path):
                if path.startswith("~/.local/share/applications"):
                    return path.replace("~/.local/share/applications", temp_dir)
                return original_expanduser(path)
            
            os.path.expanduser = mock_expanduser
            
            try:
                # This would normally create in ~/.local/share/applications
                # but our mock redirects it to temp_dir
                result = create_desktop_file(
                    "TestApp",
                    "/usr/bin/testapp",
                    "testapp",
                    "Test application"
                )
                
                assert os.path.exists(result), "Desktop file should be created"
                
                # Read and verify content
                with open(result, 'r') as f:
                    content = f.read()
                    assert "Name=TestApp" in content, "Should contain app name"
                    assert "Exec=/usr/bin/testapp" in content, "Should contain exec path"
                
                self.log(f"Desktop file created at: {result}")
                
            finally:
                os.path.expanduser = original_expanduser
        
        return True
    
    def test_subprocess_handling(self):
        """Test subprocess execution"""
        if not LINUX_UTILS_AVAILABLE:
            raise Exception("Linux utils not available")
            
        # Test basic command
        result = run_subprocess_safe(
            ["echo", "test"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, "Echo command should succeed"
        assert "test" in result.stdout, "Should capture output"
        
        return True
    
    def test_file_manager_detection(self):
        """Test file manager detection"""
        if not LINUX_UTILS_AVAILABLE:
            raise Exception("Linux utils not available")
            
        file_manager = get_file_manager_command()
        
        if file_manager:
            self.log(f"Detected file manager: {file_manager}")
        else:
            self.log("No file manager detected (this is okay)")
        
        # This test always passes as not having a file manager is acceptable
        return True
    
    def test_system_requirements(self):
        """Test system requirements gathering"""
        if not LINUX_UTILS_AVAILABLE:
            raise Exception("Linux utils not available")
            
        requirements = get_system_requirements()
        
        required_keys = [
            "os", "architecture", "python_version", 
            "distro", "desktop_environment", "fuse_available"
        ]
        
        for key in required_keys:
            assert key in requirements, f"Should have {key} in requirements"
        
        assert requirements["os"] == "Linux", "Should detect Linux OS"
        
        self.log("System requirements:")
        for key, value in requirements.items():
            self.log(f"  {key}: {value}")
        
        return True
    
    def test_fuse_detection(self):
        """Test FUSE availability detection"""
        if not LINUX_UTILS_AVAILABLE:
            raise Exception("Linux utils not available")
            
        fuse_available = check_fuse_available()
        
        self.log(f"FUSE available: {fuse_available}")
        
        if not fuse_available:
            self.log("FUSE not available - AppImages may not work")
        
        # This test always passes as FUSE might not be installed
        return True
    
    def run_all_tests(self):
        """Run all tests"""
        print("=" * 60)
        print("Linux Packaging System Test Suite")
        print("=" * 60)
        
        tests = [
            ("System Detection", self.test_system_detection),
            ("Path Resolution", self.test_path_resolution),
            ("Desktop Integration", self.test_desktop_integration),
            ("Subprocess Handling", self.test_subprocess_handling),
            ("File Manager Detection", self.test_file_manager_detection),
            ("System Requirements", self.test_system_requirements),
            ("FUSE Detection", self.test_fuse_detection),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            if self.run_test(test_name, test_func):
                passed += 1
            else:
                failed += 1
        
        print("\n" + "=" * 60)
        print("Test Results Summary")
        print("=" * 60)
        
        for test_name, success, error in self.test_results:
            status = "PASS" if success else "FAIL"
            print(f"{status:4} {test_name}")
            if error and self.verbose:
                print(f"     Error: {error}")
        
        print(f"\nTotal: {len(tests)} tests")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        
        if failed > 0:
            print("\nSome tests failed. Check the errors above.")
            return False
        else:
            print("\nAll tests passed! Linux packaging system is ready.")
            return True


def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Linux packaging system')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    
    args = parser.parse_args()
    
    tester = LinuxPackagingTester(verbose=args.verbose)
    success = tester.run_all_tests()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
