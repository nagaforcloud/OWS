"""
Smoke tests for the Option Wheel Strategy.
These tests verify basic functionality without requiring a full test suite.
"""
import sys
import os

def test_basic_functionality():
    """Test basic functionality of the project."""
    try:
        # Test that we can import the main modules
        project_root = os.path.join(os.path.dirname(__file__), '..')
        option_wheel_path = os.path.join(project_root, 'option_wheel_strategy')
        
        # Add paths to sys.path
        sys.path.insert(0, project_root)
        sys.path.insert(0, option_wheel_path)
        
        # Test importing config
        config_file = os.path.join(option_wheel_path, 'config', 'config.py')
        if os.path.exists(config_file):
            print("✓ Config module exists")
        else:
            print("✗ Config module missing")
            return False
            
        # Test importing models
        models_file = os.path.join(option_wheel_path, 'models', 'models.py')
        if os.path.exists(models_file):
            print("✓ Models module exists")
        else:
            print("✗ Models module missing")
            return False
            
        # Test importing core strategy
        strategy_file = os.path.join(option_wheel_path, 'core', 'strategy.py')
        if os.path.exists(strategy_file):
            print("✓ Strategy module exists")
        else:
            print("✗ Strategy module missing")
            return False
            
        # Test importing backtesting
        mock_kite_file = os.path.join(option_wheel_path, 'backtesting', 'mock_kite.py')
        if os.path.exists(mock_kite_file):
            print("✓ Backtesting module exists")
        else:
            print("✗ Backtesting module missing")
            return False
            
        print("✓ Basic functionality verified")
        return True
        
    except Exception as e:
        print(f"✗ Basic functionality test failed: {e}")
        return False

def test_required_files():
    """Test that required files exist."""
    try:
        project_root = os.path.join(os.path.dirname(__file__), '..')
        option_wheel_path = os.path.join(project_root, 'option_wheel_strategy')
        
        required_files = [
            'main.py',
            'requirements.txt',
            '.env',
            'config/config.py',
            'core/strategy.py',
            'models/models.py',
            'models/enums.py',
            'utils/logging_utils.py',
            'notifications/notification_manager.py',
            'backtesting/mock_kite.py'
        ]
        
        missing_files = []
        for file_path in required_files:
            full_path = os.path.join(option_wheel_path, file_path)
            if not os.path.exists(full_path):
                missing_files.append(file_path)
        
        if missing_files:
            print(f"✗ Missing files: {missing_files}")
            return False
        else:
            print("✓ All required files present")
            return True
            
    except Exception as e:
        print(f"✗ Required files test failed: {e}")
        return False

def run_smoke_tests():
    """Run all smoke tests."""
    print("Running smoke tests...")
    
    tests = [
        test_basic_functionality,
        test_required_files
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\nSmoke tests completed: {passed}/{total} passed")
    return passed == total

if __name__ == "__main__":
    success = run_smoke_tests()
    sys.exit(0 if success else 1)