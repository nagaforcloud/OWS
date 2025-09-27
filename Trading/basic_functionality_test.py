#!/usr/bin/env python3

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_basic_functionality():
    """Test basic functionality of the enhanced trading bot"""
    print("=" * 60)
    print("BASIC FUNCTIONALITY TEST")
    print("=" * 60)
    
    # Test 1: Import core modules
    try:
        from config.config import OptionWheelConfig
        print("✅ Config module imports successfully")
    except Exception as e:
        print(f"❌ Config module import failed: {e}")
        return False
    
    try:
        from core.strategy import OptionWheelStrategy
        print("✅ Strategy module imports successfully")
    except Exception as e:
        print(f"❌ Strategy module import failed: {e}")
        return False
    
    try:
        from notifications.notification_manager import NotificationManager
        print("✅ Notification manager imports successfully")
    except Exception as e:
        print(f"❌ Notification manager import failed: {e}")
        return False
    
    try:
        from database.database import DatabaseManager
        print("✅ Database manager imports successfully")
    except Exception as e:
        print(f"❌ Database manager import failed: {e}")
        return False
    
    try:
        from risk_management.risk_manager import RiskManager
        print("✅ Risk manager imports successfully")
    except Exception as e:
        print(f"❌ Risk manager import failed: {e}")
        return False
    
    # Test 2: Configuration loading
    try:
        config = OptionWheelConfig()
        print("✅ Configuration loads successfully")
        print(f"   - Dry run mode: {config.dry_run}")
        print(f"   - Kill switch file: {config.kill_switch_file}")
        print(f"   - Strategy mode: {config.strategy_mode}")
        print(f"   - Risk per trade: {config.risk_per_trade_percent:.2%}")
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        return False
    
    # Test 3: Strategy initialization
    try:
        strategy = OptionWheelStrategy(config)
        print("✅ Strategy initializes successfully")
        print(f"   - Dry run mode: {strategy.dry_run_mode}")
        print(f"   - Kill switch file: {strategy.kill_switch_file}")
    except Exception as e:
        print(f"❌ Strategy initialization failed: {e}")
        return False
    
    # Test 4: Safety features
    try:
        # Test kill switch check
        kill_switch_status = strategy.check_kill_switch()
        print(f"✅ Kill switch check works: {kill_switch_status}")
        
        # Test IST time
        ist_time = strategy.get_ist_time()
        print(f"✅ IST time works: {ist_time}")
        
        # Test margin info
        margin_info = strategy.get_margin_info()
        print(f"✅ Margin info works: {bool(margin_info)}")
        
        # Test sufficient margin
        is_sufficient = strategy.is_sufficient_margin(1000)
        print(f"✅ Sufficient margin check works: {is_sufficient}")
        
        # Test position sizing
        position_size = strategy.calculate_position_size(15000)
        print(f"✅ Position sizing works: {position_size}")
    except Exception as e:
        print(f"❌ Safety features test failed: {e}")
        return False
    
    # Test 5: Notification manager
    try:
        notification_manager = NotificationManager()
        print("✅ Notification manager works")
        print(f"   - Enabled: {notification_manager.enabled}")
        print(f"   - Type: {notification_manager.notification_type}")
    except Exception as e:
        print(f"❌ Notification manager test failed: {e}")
        return False
    
    # Test 6: Database manager
    try:
        db_manager = DatabaseManager()
        print("✅ Database manager works")
        print(f"   - DB path: {db_manager.db_path}")
    except Exception as e:
        print(f"❌ Database manager test failed: {e}")
        return False
    
    # Test 7: Risk manager
    try:
        risk_manager = RiskManager(config)
        print("✅ Risk manager works")
        print(f"   - Max daily loss: ₹{risk_manager.config.max_daily_loss_limit:,.2f}")
        print(f"   - Max positions: {risk_manager.config.max_concurrent_positions}")
    except Exception as e:
        print(f"❌ Risk manager test failed: {e}")
        return False
    
    # Test 8: Backtesting functionality
    try:
        from backtesting.nifty_backtesting import NiftyBacktestingStrategy
        backtester = NiftyBacktestingStrategy(config)
        print("✅ Backtesting strategy works")
    except Exception as e:
        print(f"❌ Backtesting strategy test failed: {e}")
        return False
    
    # Test 9: Dashboard functionality
    try:
        from dashboard.dashboard import Dashboard
        dashboard = Dashboard()
        print("✅ Dashboard works")
    except Exception as e:
        print(f"❌ Dashboard test failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("ALL BASIC FUNCTIONALITY TESTS PASSED")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = test_basic_functionality()
    sys.exit(0 if success else 1)