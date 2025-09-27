"""
Unit tests for the configuration module.
"""
import os
import sys
import unittest
from unittest.mock import patch

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'option_wheel_strategy'))

from config.config import OptionWheelConfig


class TestOptionWheelConfig(unittest.TestCase):
    """Test cases for the OptionWheelConfig class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Clear environment variables that might affect tests
        env_vars_to_clear = [
            'KITE_API_KEY', 'KITE_API_SECRET', 'KITE_ACCESS_TOKEN',
            'SYMBOL', 'QUANTITY_PER_LOT', 'PROFIT_TARGET_PERCENTAGE',
            'LOSS_LIMIT_PERCENTAGE', 'OTM_DELTA_RANGE_LOW', 'OTM_DELTA_RANGE_HIGH',
            'MIN_OPEN_INTEREST', 'STRATEGY_RUN_INTERVAL_SECONDS',
            'MARKET_OPEN_HOUR', 'MARKET_OPEN_MINUTE',
            'MARKET_CLOSE_HOUR', 'MARKET_CLOSE_MINUTE',
            'MAX_CONCURRENT_POSITIONS', 'MAX_DAILY_LOSS_LIMIT',
            'MAX_PORTFOLIO_RISK', 'ENABLE_NOTIFICATIONS',
            'NOTIFICATION_WEBHOOK_URL', 'USE_NSE_API', 'DATA_REFRESH_INTERVAL'
        ]
        for var in env_vars_to_clear:
            if var in os.environ:
                del os.environ[var]

    def test_default_values(self):
        """Test that default values are correctly set when no environment variables are present."""
        config = OptionWheelConfig()
        
        # Test API credentials defaults
        self.assertEqual(config.api_key, "YOUR_KITE_API_KEY_DEFAULT")
        self.assertEqual(config.api_secret, "YOUR_KITE_API_SECRET_DEFAULT")
        self.assertEqual(config.access_token, "YOUR_KITE_ACCESS_TOKEN_DEFAULT")
        
        # Test trading parameters defaults
        self.assertEqual(config.symbol, "TCS")
        self.assertEqual(config.quantity_per_lot, 150)
        self.assertEqual(config.profit_target_percentage, 0.50)
        self.assertEqual(config.loss_limit_percentage, 1.00)
        self.assertEqual(config.otm_delta_range_low, 0.15)
        self.assertEqual(config.otm_delta_range_high, 0.25)
        self.assertEqual(config.min_open_interest, 1000)
        
        # Test strategy timing defaults
        self.assertEqual(config.strategy_run_interval_seconds, 300)
        self.assertEqual(config.market_open_hour, 9)
        self.assertEqual(config.market_open_minute, 15)
        self.assertEqual(config.market_close_hour, 15)
        self.assertEqual(config.market_close_minute, 30)
        
        # Test risk management defaults
        self.assertEqual(config.max_concurrent_positions, 5)
        self.assertEqual(config.max_daily_loss_limit, 5000.0)
        self.assertEqual(config.max_portfolio_risk, 0.02)
        
        # Test notification settings defaults
        self.assertFalse(config.enable_notifications)
        self.assertEqual(config.notification_webhook_url, "")
        
        # Test data settings defaults
        self.assertTrue(config.use_nse_api)
        self.assertEqual(config.data_refresh_interval, 60)

    @patch.dict(os.environ, {
        'KITE_API_KEY': 'test_api_key',
        'KITE_API_SECRET': 'test_api_secret',
        'KITE_ACCESS_TOKEN': 'test_access_token',
        'SYMBOL': 'TEST',
        'QUANTITY_PER_LOT': '100',
        'PROFIT_TARGET_PERCENTAGE': '0.30',
        'LOSS_LIMIT_PERCENTAGE': '0.75',
        'OTM_DELTA_RANGE_LOW': '0.10',
        'OTM_DELTA_RANGE_HIGH': '0.30',
        'MIN_OPEN_INTEREST': '500',
        'STRATEGY_RUN_INTERVAL_SECONDS': '600',
        'MARKET_OPEN_HOUR': '10',
        'MARKET_OPEN_MINUTE': '0',
        'MARKET_CLOSE_HOUR': '16',
        'MARKET_CLOSE_MINUTE': '0',
        'MAX_CONCURRENT_POSITIONS': '10',
        'MAX_DAILY_LOSS_LIMIT': '10000.0',
        'MAX_PORTFOLIO_RISK': '0.05',
        'ENABLE_NOTIFICATIONS': 'true',
        'NOTIFICATION_WEBHOOK_URL': 'https://test.webhook.com',
        'USE_NSE_API': 'false',
        'DATA_REFRESH_INTERVAL': '120'
    })
    def test_environment_variable_loading(self):
        """Test that configuration correctly loads from environment variables."""
        config = OptionWheelConfig()
        
        # Test API credentials from environment
        self.assertEqual(config.api_key, 'test_api_key')
        self.assertEqual(config.api_secret, 'test_api_secret')
        self.assertEqual(config.access_token, 'test_access_token')
        
        # Test trading parameters from environment
        self.assertEqual(config.symbol, 'TEST')
        self.assertEqual(config.quantity_per_lot, 100)
        self.assertEqual(config.profit_target_percentage, 0.30)
        self.assertEqual(config.loss_limit_percentage, 0.75)
        self.assertEqual(config.otm_delta_range_low, 0.10)
        self.assertEqual(config.otm_delta_range_high, 0.30)
        self.assertEqual(config.min_open_interest, 500)
        
        # Test strategy timing from environment
        self.assertEqual(config.strategy_run_interval_seconds, 600)
        self.assertEqual(config.market_open_hour, 10)
        self.assertEqual(config.market_open_minute, 0)
        self.assertEqual(config.market_close_hour, 16)
        self.assertEqual(config.market_close_minute, 0)
        
        # Test risk management from environment
        self.assertEqual(config.max_concurrent_positions, 10)
        self.assertEqual(config.max_daily_loss_limit, 10000.0)
        self.assertEqual(config.max_portfolio_risk, 0.05)
        
        # Test notification settings from environment
        self.assertTrue(config.enable_notifications)
        self.assertEqual(config.notification_webhook_url, 'https://test.webhook.com')
        
        # Test data settings from environment
        self.assertFalse(config.use_nse_api)
        self.assertEqual(config.data_refresh_interval, 120)

    def test_type_conversion(self):
        """Test that string environment variables are correctly converted to appropriate types."""
        # Set environment variables with string values that need conversion
        env_vars = {
            'QUANTITY_PER_LOT': '200',
            'PROFIT_TARGET_PERCENTAGE': '0.40',
            'LOSS_LIMIT_PERCENTAGE': '0.80',
            'OTM_DELTA_RANGE_LOW': '0.20',
            'OTM_DELTA_RANGE_HIGH': '0.40',
            'MIN_OPEN_INTEREST': '1500',
            'STRATEGY_RUN_INTERVAL_SECONDS': '900',
            'MARKET_OPEN_HOUR': '8',
            'MARKET_OPEN_MINUTE': '30',
            'MARKET_CLOSE_HOUR': '17',
            'MARKET_CLOSE_MINUTE': '45',
            'MAX_CONCURRENT_POSITIONS': '8',
            'MAX_DAILY_LOSS_LIMIT': '7500.50',
            'MAX_PORTFOLIO_RISK': '0.03',
            'ENABLE_NOTIFICATIONS': 'true',
            'USE_NSE_API': 'false',
            'DATA_REFRESH_INTERVAL': '180'
        }
        
        with patch.dict(os.environ, env_vars):
            config = OptionWheelConfig()
            
            # Test integer conversions
            self.assertIsInstance(config.quantity_per_lot, int)
            self.assertEqual(config.quantity_per_lot, 200)
            
            self.assertIsInstance(config.strategy_run_interval_seconds, int)
            self.assertEqual(config.strategy_run_interval_seconds, 900)
            
            self.assertIsInstance(config.market_open_hour, int)
            self.assertEqual(config.market_open_hour, 8)
            
            self.assertIsInstance(config.market_open_minute, int)
            self.assertEqual(config.market_open_minute, 30)
            
            self.assertIsInstance(config.market_close_hour, int)
            self.assertEqual(config.market_close_hour, 17)
            
            self.assertIsInstance(config.market_close_minute, int)
            self.assertEqual(config.market_close_minute, 45)
            
            self.assertIsInstance(config.max_concurrent_positions, int)
            self.assertEqual(config.max_concurrent_positions, 8)
            
            self.assertIsInstance(config.min_open_interest, int)
            self.assertEqual(config.min_open_interest, 1500)
            
            self.assertIsInstance(config.data_refresh_interval, int)
            self.assertEqual(config.data_refresh_interval, 180)
            
            # Test float conversions
            self.assertIsInstance(config.profit_target_percentage, float)
            self.assertEqual(config.profit_target_percentage, 0.40)
            
            self.assertIsInstance(config.loss_limit_percentage, float)
            self.assertEqual(config.loss_limit_percentage, 0.80)
            
            self.assertIsInstance(config.otm_delta_range_low, float)
            self.assertEqual(config.otm_delta_range_low, 0.20)
            
            self.assertIsInstance(config.otm_delta_range_high, float)
            self.assertEqual(config.otm_delta_range_high, 0.40)
            
            self.assertIsInstance(config.max_daily_loss_limit, float)
            self.assertEqual(config.max_daily_loss_limit, 7500.50)
            
            self.assertIsInstance(config.max_portfolio_risk, float)
            self.assertEqual(config.max_portfolio_risk, 0.03)
            
            # Test boolean conversions
            self.assertIsInstance(config.enable_notifications, bool)
            self.assertTrue(config.enable_notifications)
            
            self.assertIsInstance(config.use_nse_api, bool)
            self.assertFalse(config.use_nse_api)


if __name__ == '__main__':
    unittest.main()