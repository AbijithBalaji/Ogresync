#!/usr/bin/env python3
"""
Test script to verify conflict resolution commit detection
"""

import subprocess

def run_command(cmd, cwd=None):
    """Run a command and return output, error, and return code."""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=30)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), 1

vault_path = "C:/Users/abiji/Test"

# Check recent commits
recent_commits_out, recent_commits_err, recent_commits_rc = run_command("git log --oneline -3", cwd=vault_path)
if recent_commits_rc == 0:
    commit_msgs = recent_commits_out.strip().lower()
    print(f"Recent commit messages:\n{recent_commits_out}")
    print(f"\nLowercase version:\n{commit_msgs}")
    
    # Conflict resolution indicators
    conflict_resolution_indicators = ["resolve conflicts using stage 2", "stage 2 resolution", "conflict resolution", "smart merge"]
    is_conflict_resolution_commit = any(indicator in commit_msgs for indicator in conflict_resolution_indicators)
    
    print(f"\nConflict resolution indicators checked:")
    for indicator in conflict_resolution_indicators:
        found = indicator in commit_msgs
        print(f"  '{indicator}': {found}")
    
    print(f"\nResult: is_conflict_resolution_commit = {is_conflict_resolution_commit}")
    
    # Check unpushed count
    ahead_count_out, ahead_count_err, ahead_count_rc = run_command("git rev-list --count HEAD ^origin/main", cwd=vault_path)
    if ahead_count_rc == 0:
        print(f"\nUnpushed commits: {ahead_count_out}")
    else:
        print(f"\nError checking unpushed commits: {ahead_count_err}")
else:
    print(f"Error getting recent commits: {recent_commits_err}")
