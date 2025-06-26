# Ogresync Test Suite

This folder contains all test files and debugging utilities for the Ogresync project.

## Test Categories

### Core Functionality Tests
- `test_unpushed_fix.py` - Tests for unpushed commit detection fixes
- `test_upstream_integration.py` - Tests for upstream tracking integration
- `test_conflict_detection.py` - Tests for conflict detection logic

### Offline Sync Tests
- `test_offline_components.py` - Unit tests for offline sync components
- `basic_offline_test.py` - Basic offline functionality tests
- `test_offline_conflict_push_bug.py` - Tests for offline conflict resolution push bug

### Conflict Resolution Tests
- `test_conflict_resolution_push_bug.py` - Tests for conflict resolution push issues
- `test_ogresync_immediate_push_fix.py` - Tests for immediate push after conflict resolution

### Comprehensive Test Suites
- `comprehensive_test_suite.py` - Full integration test suite
- `simple_comprehensive_test.py` - Simplified comprehensive tests
- `focused_strategy_test.py` - Focused testing for specific scenarios
- `advanced_edge_case_test.py` - Advanced edge case testing

### Debugging and Analysis
- `debug_offline_state.py` - Debug offline sync state
- `test_aggressive_cleanup.py` - Test session cleanup functionality
- `verify_backup_refactoring.py` - Verify backup system integrity

### Development Examples
- `enhanced_auto_sync.py` - Enhanced sync implementation examples
- `offline_integration_examples.py` - Examples of offline sync integration

## Running Tests

To run individual tests:
```bash
python tests/test_name.py
```

To run comprehensive tests:
```bash
python tests/comprehensive_test_suite.py
```

## Test Results

Test results and analysis files are automatically generated and stored in this folder when tests are executed.
