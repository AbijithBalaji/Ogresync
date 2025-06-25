"""
Integration Example: Adding Offline Support to Existing Ogresync

This shows how to integrate the new offline capabilities with your existing
Ogresync.py without modifying the core file.

This approach maintains complete backward compatibility while adding 
powerful offline capabilities.
"""

# Example integration in your main() function:

def integrate_offline_support_example():
    """
    Example showing how to add offline support to existing Ogresync
    without modifying the main file.
    """
    
    # Import your existing Ogresync module
    import Ogresync
    
    try:
        # Import the enhanced auto sync
        from enhanced_auto_sync import create_enhanced_auto_sync, get_offline_integration_status
        
        # Check if offline integration is available
        status = get_offline_integration_status()
        
        if status['integration_ready']:
            print("✅ Offline integration available")
            
            # Create enhanced auto_sync function
            enhanced_auto_sync = create_enhanced_auto_sync(
                original_auto_sync_func=Ogresync.auto_sync,
                vault_path=Ogresync.config_data["VAULT_PATH"],
                config_data=Ogresync.config_data,
                safe_update_log_func=Ogresync.safe_update_log,
                root_window=Ogresync.root,
                is_obsidian_running_func=Ogresync.is_obsidian_running,
                run_command_func=Ogresync.run_command
            )
            
            # Replace the original auto_sync with enhanced version
            Ogresync.auto_sync = enhanced_auto_sync
            
            print("🚀 Offline support activated!")
            
        else:
            print("⚠️ Offline integration not available - missing components")
            print(f"Status: {status}")
            
    except ImportError as e:
        print(f"⚠️ Could not load offline support: {e}")
        print("📝 Continuing with standard online-only mode")


# Alternative approach - modify just a few lines in your existing main():

def main_with_offline_support():
    """
    Modified version of your main() function with offline support.
    
    Only changes:
    1. Import enhanced auto sync
    2. Replace auto_sync function if available
    3. Everything else remains identical
    """
    
    # Your existing imports and setup code here...
    import os
    import time
    import threading
    import ui_elements
    import setup_wizard
    # ... all your existing imports
    
    # NEW: Try to enhance with offline support
    try:
        from enhanced_auto_sync import create_enhanced_auto_sync
        
        # Replace auto_sync with enhanced version if possible
        def create_enhanced_version():
            return create_enhanced_auto_sync(
                original_auto_sync_func=auto_sync,  # Your existing function
                vault_path=config_data["VAULT_PATH"],
                config_data=config_data,
                safe_update_log_func=safe_update_log,
                root_window=root,
                is_obsidian_running_func=is_obsidian_running,
                run_command_func=run_command
            )
        
        print("🚀 Offline support loaded successfully")
        
    except ImportError:
        print("📝 Offline support not available, using standard mode")
        create_enhanced_version = None
    
    # Your existing config loading...
    load_config()
    
    # Your existing setup wizard and dependency initialization...
    # ... all unchanged ...
    
    # The key change - use enhanced auto_sync if available
    if config_data.get("SETUP_DONE", "0") == "1":
        print("DEBUG: Running in sync mode")
        root, log_text, progress_bar = ui_elements.create_minimal_ui(auto_run=False)
        
        def start_sync_after_ui():
            time.sleep(0.2)
            # Use enhanced version if available, otherwise use original
            if create_enhanced_version:
                enhanced_auto_sync = create_enhanced_version()
                enhanced_auto_sync(use_threading=True)
            else:
                auto_sync(use_threading=True)  # Your original function
        
        threading.Thread(target=start_sync_after_ui, daemon=True).start()
        root.mainloop()
    
    else:
        # Setup wizard code remains unchanged
        print("DEBUG: Running setup wizard")
        success, wizard_state = setup_wizard.run_setup_wizard()
        # ... rest unchanged ...


# Configuration-based approach (even simpler):

def simple_config_integration():
    """
    Simplest integration - just check a config flag
    """
    
    # Add to your config_data:
    config_data = {
        "VAULT_PATH": "",
        "OBSIDIAN_PATH": "",
        "GITHUB_REMOTE_URL": "",
        "SETUP_DONE": "0",
        "OFFLINE_MODE_ENABLED": "1"  # NEW: Enable offline support
    }
    
    # In your auto_sync, just add this check at the start:
    def auto_sync_with_offline_check(use_threading=True):
        if config_data.get("OFFLINE_MODE_ENABLED", "0") == "1":
            try:
                from enhanced_auto_sync import create_enhanced_auto_sync
                
                enhanced_func = create_enhanced_auto_sync(
                    original_auto_sync_func=lambda ut: original_auto_sync(ut),
                    vault_path=config_data["VAULT_PATH"],
                    config_data=config_data,
                    safe_update_log_func=safe_update_log,
                    root_window=root,
                    is_obsidian_running_func=is_obsidian_running,
                    run_command_func=run_command
                )
                
                return enhanced_func(use_threading)
                
            except ImportError:
                safe_update_log("⚠️ Offline mode requested but not available")
        
        # Fallback to original
        return original_auto_sync(use_threading)


if __name__ == "__main__":
    print("Offline Integration Examples")
    print("Choose your integration approach:")
    print("1. Full integration (replaces auto_sync)")
    print("2. Modified main() function")
    print("3. Config-based toggle")
    
    integrate_offline_support_example()
