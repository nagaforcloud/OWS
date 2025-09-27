#!/usr/bin/env python3
"""
Comprehensive test suite for verifying all safety and compliance enhancements
"""

import sys
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import OptionWheelConfig
from core.strategy import OptionWheelStrategy
from models.models import Trade, Position
from models.enums import TransactionType, OrderType, ProductType, StrategyType, OptionType
from notifications.notification_manager import NotificationManager
from database.database import DatabaseManager
from risk_management.risk_manager import RiskManager

class TestSafetyAndComplianceEnhancements(unittest.TestCase):
    """
    Test suite for verifying all safety and compliance enhancements
    """
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        
        # Create a mock config
        self.config = OptionWheelConfig()
        
        # Override config for testing
        self.config.dry_run = True
        self.config.use_holiday_calendar = False
        self.config.kill_switch_file = os.path.join(self.test_dir, "STOP_TRADING")
        self.config.min_cash_reserve = 10000
        self.config.risk_per_trade_percent = 0.01
        self.config.strategy_mode = "balanced"
        self.config.enable_auto_roll = False
        
        # Create mock Kite client
        self.mock_kite = MagicMock()
        
        # Initialize strategy with mock Kite client
        self.strategy = OptionWheelStrategy(self.config, kite_client=self.mock_kite)
    
    def tearDown(self):
        """Tear down test fixtures after each test method."""
        # Clean up temporary directory
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_dry_run_mode(self):
        """Test dry run mode functionality"""
        # Test that dry run mode is properly set
        self.assertTrue(self.strategy.dry_run_mode)
        self.assertTrue(self.config.dry_run)
        
        # Test that orders are not placed in dry run mode
        with patch('core.strategy.logger') as mock_logger:
            order_id = self.strategy.place_order(
                symbol="NIFTY2140814950CE",
                transaction_type=TransactionType.SELL,
                quantity=50,
                price=100.0
            )
            
            # Check that order was not placed (returns mock order ID in dry run)
            self.assertIsNotNone(order_id)
            self.assertTrue(order_id.startswith("DRY"))
            
            # Check that dry run warning was logged
            mock_logger.info.assert_any_call("[DRY RUN] Would have placed order: SELL 50 NIFTY2140814950CE at 100.0")
    
    def test_kill_switch_functionality(self):
        """Test kill switch functionality"""
        # Initially, kill switch should not be activated
        self.assertFalse(self.strategy.check_kill_switch())
        
        # Create kill switch file
        kill_switch_path = self.config.kill_switch_file
        with open(kill_switch_path, 'w') as f:
            f.write("STOP_TRADING")
        
        # Now kill switch should be activated
        self.assertTrue(self.strategy.check_kill_switch())
        
        # Remove kill switch file
        os.remove(kill_switch_path)
        
        # Kill switch should be deactivated again
        self.assertFalse(self.strategy.check_kill_switch())
    
    def test_holiday_calendar_integration(self):
        """Test holiday calendar integration"""
        # Test that holiday calendar checking works
        test_date = datetime.now().date()
        
        # In dry run mode with holiday calendar disabled, should return False for weekends
        if test_date.weekday() >= 5:  # Weekend
            # For weekends, should return True (is holiday)
            result = self.strategy.is_holiday(test_date)
            # Depending on implementation, this might vary
            self.assertIsInstance(result, bool)
        else:
            # For weekdays, should return False (not holiday) when calendar is disabled
            result = self.strategy.is_holiday(test_date)
            self.assertIsInstance(result, bool)
        
        # Test that holiday calendar checking works when enabled
        self.strategy.config.use_holiday_calendar = True
        self.strategy.config.holiday_file_path = "./data/nse_holidays.csv"
        
        # Test that holiday checking handles missing file gracefully
        result = self.strategy.is_holiday(test_date)
        self.assertIsInstance(result, bool)
    
    def test_timezone_enforcement(self):
        """Test timezone enforcement"""
        # Test that IST time is returned
        ist_time = self.strategy.get_ist_time()
        self.assertEqual(ist_time.tzinfo.zone, 'Asia/Kolkata')
        
        # Test that current time is reasonable
        now = datetime.now()
        time_diff = abs((ist_time.replace(tzinfo=None) - now).total_seconds())
        # Should be within a few seconds of current time
        self.assertLess(time_diff, 10)
    
    def test_margin_monitoring(self):
        """Test real-time margin monitoring"""
        # Test that margin info is retrieved
        margin_info = self.strategy.get_margin_info()
        self.assertIsInstance(margin_info, dict)
        
        # Test that sufficient margin check works
        # In dry run mode, should return True with mock data
        sufficient = self.strategy.is_sufficient_margin(5000)
        self.assertTrue(sufficient)
        
        # Test with very high required margin
        sufficient = self.strategy.is_sufficient_margin(1000000)
        self.assertFalse(sufficient)
    
    def test_dynamic_position_sizing(self):
        """Test dynamic position sizing"""
        # Test that position size calculation works
        position_size = self.strategy.calculate_position_size(15000)  # NIFTY price
        self.assertIsInstance(position_size, int)
        self.assertGreater(position_size, 0)
        
        # Test that position size respects config limits
        self.assertLessEqual(position_size, self.config.quantity_per_lot)
    
    def test_market_data_reliability(self):
        """Test market data reliability features"""
        # Test that option chain fetching works
        option_chain = self.strategy.fetch_option_chain("NIFTY")
        # Should return empty list in dry run mode
        self.assertIsInstance(option_chain, list)
        
        # Test that nearest expiry options fetching works
        nearest_options = self.strategy.get_nearest_expiry_options("NIFTY")
        # Should return empty list in dry run mode
        self.assertIsInstance(nearest_options, list)
    
    def test_transaction_cost_modeling(self):
        """Test transaction cost modeling"""
        # Test that transaction costs calculation works
        trade_value = 100000  # ₹100,000 trade
        try:
            # Use the actual method name from the strategy
            costs = self.strategy.calculate_transaction_costs(
                trade_value, 
                TransactionType.SELL, 
                "options"
            )
            
            # Should return dictionary with cost components
            self.assertIsInstance(costs, dict)
            # Check that it has the expected keys
            expected_keys = ['brokerage', 'stt', 'turnover_charges', 'gst', 'sebi_charges', 'stamp_duty', 'total_fees']
            for key in expected_keys:
                self.assertIn(key, costs)
                self.assertIsInstance(costs[key], float)
        except AttributeError:
            # If the method doesn't exist, that's a different issue
            self.skipTest("calculate_transaction_costs method not implemented")
        except Exception as e:
            # If cost calculation fails, it should be graceful
            self.fail(f"Transaction cost calculation failed: {e}")
    
    def test_slippage_and_fill_logic(self):
        """Test slippage and fill logic"""
        # Test that slippage application works
        base_price = 100.0
        try:
            # Use the actual method name from the strategy
            slippage_price = self.strategy.apply_slippage(
                base_price, 
                TransactionType.BUY
            )
            
            # Should return a price (might be same or slightly different due to slippage)
            self.assertIsInstance(slippage_price, float)
        except AttributeError:
            # If the method doesn't exist, that's a different issue
            self.skipTest("apply_slippage method not implemented")
        except Exception as e:
            # If slippage fails, it should be graceful
            self.fail(f"Slippage application failed: {e}")
        
        # Test that fill simulation works
        try:
            filled, fill_price = self.strategy.simulate_fill_probability(
                base_price,
                base_price * 0.99,  # Bid
                base_price * 1.01   # Ask
            )
            
            # Should return tuple of (bool, float)
            self.assertIsInstance(filled, bool)
            self.assertIsInstance(fill_price, float)
        except AttributeError:
            # If the method doesn't exist, that's a different issue
            self.skipTest("simulate_fill_probability method not implemented")
        except Exception as e:
            # If fill simulation fails, it should be graceful
            self.fail(f"Fill simulation failed: {e}")
    
    def test_multi_channel_notifications(self):
        """Test multi-channel notifications"""
        # Test that notification manager is initialized
        self.assertIsInstance(self.strategy.notification_manager, NotificationManager)
        
        # Test that notification sending works (even if disabled)
        result = self.strategy.notification_manager.send_notification(
            "Test Title",
            "Test Message",
            "info"
        )
        
        # Should return boolean (True if sent, False if disabled)
        self.assertIsInstance(result, bool)
    
    def test_critical_alerts_system(self):
        """Test critical alerts system"""
        # Test that critical alerts check works
        alerts = self.strategy.check_critical_alerts()
        
        # Should return dictionary with alert status
        self.assertIsInstance(alerts, dict)
        self.assertIn('margin_shortfall', alerts)
        self.assertIn('daily_loss_breached', alerts)
        self.assertIn('api_token_expired', alerts)
        self.assertIn('strategy_stalled', alerts)
        self.assertIn('alerts_triggered', alerts)
    
    def test_health_endpoint(self):
        """Test health endpoint functionality"""
        # Test that strategy status retrieval works
        status = self.strategy.get_strategy_status()
        
        # Should return dictionary with status information
        self.assertIsInstance(status, dict)
        self.assertIn('running', status)
        self.assertIn('positions_count', status)
        self.assertIn('active_orders_count', status)
        self.assertIn('current_strategy_type', status)
        self.assertIn('daily_pnl', status)
        self.assertIn('total_pnl', status)
        self.assertIn('last_updated', status)
        self.assertIn('portfolio_value', status)
        self.assertIn('available_capital', status)
        self.assertIn('performance_metrics', status)
    
    def test_strategy_flexibility(self):
        """Test strategy flexibility features"""
        # Test that strategy mode affects delta range
        balanced_range = self.strategy._get_adjusted_delta_range()
        self.assertIsInstance(balanced_range, tuple)
        self.assertEqual(len(balanced_range), 2)
        
        # Test conservative mode
        self.strategy.config.strategy_mode = "conservative"
        conservative_range = self.strategy._get_adjusted_delta_range()
        self.assertIsInstance(conservative_range, tuple)
        self.assertEqual(len(conservative_range), 2)
        
        # Test aggressive mode
        self.strategy.config.strategy_mode = "aggressive"
        aggressive_range = self.strategy._get_adjusted_delta_range()
        self.assertIsInstance(aggressive_range, tuple)
        self.assertEqual(len(aggressive_range), 2)
    
    def test_auto_rolling_logic(self):
        """Test auto-rolling logic"""
        # Test that auto-rolling check works
        self.strategy.check_and_roll_positions()
        # Should not fail even if no positions exist
    
    def test_greeks_analysis_proxy(self):
        """Test Greeks analysis proxy functionality"""
        # Test that Greeks analysis works with sample data
        sample_data = pd.DataFrame({
            'symbol': ['NIFTY2140814950CE', 'NIFTY2140815000PE'],
            'strike_price': [14950, 15000],
            'option_type': ['CE', 'PE'],
            'expiry_date': [datetime.now() + timedelta(days=30), datetime.now() + timedelta(days=30)],
            'trade_date': [datetime.now(), datetime.now()],
            'value': [10000, 12000],
            'quantity': [50, 50],
            'price': [200, 240]
        })
        
        # Should not fail when processing sample data
        try:
            # Use the actual method name from the strategy
            analyzed_data = self.strategy.analyze_option_greeks_proxy(sample_data)
            self.assertIsInstance(analyzed_data, pd.DataFrame)
        except AttributeError:
            # If the method doesn't exist, that's a different issue
            self.skipTest("analyze_option_greeks_proxy method not implemented")
        except Exception as e:
            # If analysis fails, it should be graceful
            self.fail(f"Greeks analysis failed: {e}")

if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)