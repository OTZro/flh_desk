#!/usr/bin/env python3
"""
快速測試腳本 - 用來驗證 coordinator.py 的改動是否正確
僅檢查語法和導入，不需要連接真實設備
"""
import sys
import importlib.util

def test_coordinator():
    """測試 coordinator.py 是否有語法錯誤"""
    print("🧪 Testing coordinator.py...")
    
    # Load the module
    spec = importlib.util.spec_from_file_location(
        "coordinator",
        "custom_components/flh_desk/coordinator.py"
    )
    
    if spec is None or spec.loader is None:
        print("❌ Failed to load coordinator.py")
        return False
        
    try:
        coordinator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(coordinator)
        print("✅ coordinator.py loaded successfully")
        
        # Check key classes exist
        assert hasattr(coordinator, 'FLHDeskCoordinator'), "FLHDeskCoordinator class not found"
        assert hasattr(coordinator, 'build_command'), "build_command function not found"
        assert hasattr(coordinator, 'calculate_checksum'), "calculate_checksum function not found"
        print("✅ All expected classes and functions present")
        
        # Check logging methods exist
        klass = coordinator.FLHDeskCoordinator
        assert hasattr(klass, '_notification_handler'), "_notification_handler not found"
        assert hasattr(klass, '_send_command'), "_send_command not found"
        assert hasattr(klass, 'async_connect'), "async_connect not found"
        print("✅ All coordinator methods present")
        
        return True
        
    except SyntaxError as e:
        print(f"❌ Syntax error: {e}")
        return False
    except AssertionError as e:
        print(f"❌ Assertion failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("FLH Desk Coordinator Test")
    print("=" * 60)
    print()
    
    success = test_coordinator()
    
    print()
    print("=" * 60)
    if success:
        print("✅ All tests passed!")
        print()
        print("Next steps:")
        print("1. Copy coordinator.py to Home Assistant")
        print("2. Enable DEBUG logging in configuration.yaml")
        print("3. Reload the integration") 
        print("4. Check logs for detailed BLE communication")
    else:
        print("❌ Tests failed - please fix errors above")
    print("=" * 60)
    
    sys.exit(0 if success else 1)
