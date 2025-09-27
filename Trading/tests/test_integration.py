"""
Integration tests for the option wheel strategy.
"""
import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
import datetime
import pandas as pd

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'option_wheel_strategy'))

from core.strategy import OptionWheelStrategy
from config.config import OptionWheelConfig
from backtesting.mock_kite import MockKiteConnect


class TestOptionWheelIntegration(unittest.TestCase):
    """Integration tests for the OptionWheelStrategy with MockKiteConnect."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a config for testing
        self.config = OptionWheelConfig()
        
        # Create historical data for backtesting
        self.historical_data = {
            'TCS_LTP': {
                '2023-01-01 09:30': 3500.0,
                '2023-01-01 09:35': 3510.0,
                '2023-01-01 09:40': 3495.0
            },
            'OPTION_PREMIUMS': {
                'TCS24JUL3800CE': {
                    '2023-01-01 09:30': 50.0,
                    '2023-01-01 09:35': 52.0,
                    '2023-01-01 09:40': 48.0
                },
                'TCS24JUL3700PE': {
                    '2023-01-01 09:30': 30.0,
                    '2023-01-01 09:35': 28.0,
                    '2023-01-01 09:40': 32.0
                }
            },
            'OPTION_CHAIN_DATA': {
                '2023-01-01 09:30': pd.DataFrame([
                    {
                        'strikePrice': 3700,
                        'expiryDate': datetime.datetime(2024, 7, 25),
                        'PE.delta': 0.20,
                        'CE.delta': 0.80,
                        'PE.openInterest': 1500,
                        'CE.openInterest': 1200,
                        'PE.lastPrice': 30.0,
                        'CE.lastPrice': 40.0
                    },
                    {
                        'strikePrice': 3800,
                        'expiryDate': datetime.datetime(2024, 7, 25),
                        'PE.delta': 0.25,
                        'CE.delta': 0.75,
                        'PE.openInterest': 2000,
                        'CE.openInterest': 1800,
                        'PE.lastPrice': 50.0,
                        'CE.lastPrice': 50.0
                    }
                ])
            }
        }
        
        # Create mock kite client
        self.mock_kite = MockKiteConnect(self.historical_data)
        
        # Create strategy instance
        self.strategy = OptionWheelStrategy(self.config, self.mock_kite)

    def test_complete_strategy_cycle(self):
        """Test a complete strategy cycle with mock data."""
        # Mock the instruments DataFrame
        instruments_data = [
            {"tradingsymbol": "TCS", "exchange": "NSE", "instrument_token": 12345},
            {"tradingsymbol": "TCS24JUL3800CE", "exchange": "NSE", "instrument_token": 67890},
            {"tradingsymbol": "TCS24JUL3700PE", "exchange": "NSE", "instrument_token": 54321}
        ]
        self.strategy.instruments_df = pd.DataFrame(instruments_data)
        
        # Mock the positions method to return no positions initially
        self.mock_kite.positions = Mock(return_value={"net": []})
        
        # Mock LTP to return the underlying price
        self.mock_kite.ltp = Mock(return_value={"NSE:12345": {"last_price": 3500.0}})
        
        # Mock place_order to track calls
        self.mock_kite.place_order = Mock(return_value="MOCK_ORDER_1")
        
        # Execute a strategy cycle
        self.strategy._execute_cycle()
        
        # Verify that LTP was called
        self.mock_kite.ltp.assert_called()
        
        # Verify that positions were checked
        self.mock_kite.positions.assert_called()
        
        # Since we have no positions and are not holding stock, 
        # it should attempt to sell a put
        # The exact call depends on the option selection logic

    def test_short_put_management(self):
        """Test management of a short put position."""
        # Mock the instruments DataFrame
        instruments_data = [
            {"tradingsymbol": "TCS", "exchange": "NSE", "instrument_token": 12345},
            {"tradingsymbol": "TCS24JUL3700PE", "exchange": "NSE", "instrument_token": 54321}
        ]
        self.strategy.instruments_df = pd.DataFrame(instruments_data)
        
        # Mock positions with a short put
        short_put_position = {
            "tradingsymbol": "TCS24JUL3700PE",
            "quantity": -150,  # Short position
            "average_price": 30.0,
            "product": "NRML",
            "exchange": "NSE",
            "instrument_token": 54321
        }
        self.mock_kite.positions = Mock(return_value={"net": [short_put_position]})
        
        # Mock LTP to return a price that hits profit target
        # With entry at 30.0 and 50% profit target, exit at 15.0
        self.mock_kite.ltp = Mock(return_value={
            "NSE:12345": {"last_price": 3500.0},  # Underlying
            "NSE:54321": {"last_price": 15.0}     # Put price at profit target
        })
        
        # Mock place_order to track calls
        self.mock_kite.place_order = Mock(return_value="MOCK_ORDER_CLOSE_PUT")
        
        # Mock get_instrument_token
        self.strategy._get_instrument_token = Mock(return_value=54321)
        
        # Execute a strategy cycle
        self.strategy._execute_cycle()
        
        # Verify that a buy order was placed to close the put
        # (This assumes the put price of 15.0 is <= profit target of 15.0)
        self.mock_kite.place_order.assert_called()

    def test_backtesting_execution(self):
        """Test backtesting execution."""
        # Set simulated time
        test_time = datetime.datetime(2023, 1, 1, 9, 30)
        self.mock_kite.set_simulated_time(test_time)
        
        # Mock instruments DataFrame
        instruments_data = [
            {"tradingsymbol": "TCS", "exchange": "NSE", "instrument_token": 12345}
        ]
        self.strategy.instruments_df = pd.DataFrame(instruments_data)
        
        # Mock positions
        self.mock_kite.positions = Mock(return_value={"net": []})
        
        # Mock LTP
        self.mock_kite.ltp = Mock(return_value={"NSE:12345": {"last_price": 3500.0}})
        
        # Mock place_order
        self.mock_kite.place_order = Mock(return_value="MOCK_ORDER_1")
        
        # Execute cycle
        self.strategy._execute_cycle()
        
        # Verify components were called
        self.assertTrue(self.mock_kite.ltp.called)
        self.assertTrue(self.mock_kite.positions.called)


if __name__ == '__main__':
    unittest.main()