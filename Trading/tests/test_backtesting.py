"""
Unit tests for the backtesting module.
"""
import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
import datetime
import pandas as pd

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'option_wheel_strategy'))

from backtesting.mock_kite import MockKiteConnect


class TestMockKiteConnect(unittest.TestCase):
    """Test cases for the MockKiteConnect class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
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
            'OPTION_CHAIN_DATA': {}
        }
        
        self.mock_kite = MockKiteConnect(self.historical_data)

    def test_initialization(self):
        """Test MockKiteConnect initialization."""
        self.assertEqual(self.mock_kite.historical_data, self.historical_data)
        self.assertEqual(self.mock_kite.simulated_positions, [])
        self.assertEqual(self.mock_kite.simulated_orders, [])
        self.assertEqual(self.mock_kite.current_simulated_time, datetime.datetime(2023, 1, 1, 9, 30, 0))
        
        # Test constants
        self.assertEqual(self.mock_kite.EXCHANGE_NSE, "NSE")
        self.assertEqual(self.mock_kite.PRODUCT_NRML, "NRML")
        self.assertEqual(self.mock_kite.PRODUCT_CNC, "CNC")
        self.assertEqual(self.mock_kite.TRANSACTION_TYPE_BUY, "BUY")
        self.assertEqual(self.mock_kite.TRANSACTION_TYPE_SELL, "SELL")
        self.assertEqual(self.mock_kite.ORDER_TYPE_MARKET, "MARKET")

    def test_set_simulated_time(self):
        """Test setting simulated time."""
        new_time = datetime.datetime(2023, 1, 2, 10, 0, 0)
        self.mock_kite.set_simulated_time(new_time)
        self.assertEqual(self.mock_kite.current_simulated_time, new_time)

    def test_ltp(self):
        """Test LTP retrieval."""
        # Test equity LTP
        result = self.mock_kite.ltp(["NSE:TCS"])
        self.assertIn("NSE:TCS", result)
        self.assertEqual(result["NSE:TCS"]["last_price"], 3500.0)
        
        # Test option LTP
        result = self.mock_kite.ltp(["NSE:67890"])  # Assuming 67890 is TCS24JUL3800CE token
        self.assertIn("NSE:67890", result)
        self.assertEqual(result["NSE:67890"]["last_price"], 50.0)
        
        # Test missing data (should return 0.0)
        result = self.mock_kite.ltp(["NSE:NONEXISTENT"])
        self.assertIn("NSE:NONEXISTENT", result)
        self.assertEqual(result["NSE:NONEXISTENT"]["last_price"], 0.0)

    def test_positions(self):
        """Test positions retrieval."""
        # Test with empty positions
        result = self.mock_kite.positions()
        self.assertIn("net", result)
        self.assertEqual(result["net"], [])
        
        # Test with some positions
        self.mock_kite.simulated_positions = [
            {
                "tradingsymbol": "TCS24JUL3800CE",
                "quantity": -150,
                "average_price": 50.0,
                "product": "NRML",
                "exchange": "NSE",
                "instrument_token": 67890
            }
        ]
        result = self.mock_kite.positions()
        self.assertEqual(result["net"], self.mock_kite.simulated_positions)

    def test_place_order(self):
        """Test order placement."""
        # Test sell order (creates new short position)
        order_id = self.mock_kite.place_order(
            tradingsymbol="TCS24JUL3800CE",
            exchange="NSE",
            transaction_type="SELL",
            quantity=150,
            order_type="MARKET",
            product="NRML",
            instrument_token=67890
        )
        
        self.assertTrue(order_id.startswith("MOCK_ORDER_"))
        self.assertEqual(len(self.mock_kite.simulated_orders), 1)
        self.assertEqual(len(self.mock_kite.simulated_positions), 1)
        
        # Verify the position
        position = self.mock_kite.simulated_positions[0]
        self.assertEqual(position["tradingsymbol"], "TCS24JUL3800CE")
        self.assertEqual(position["quantity"], -150)  # Negative for short
        self.assertEqual(position["product"], "NRML")
        self.assertEqual(position["exchange"], "NSE")
        
        # Test buy order (closes existing position)
        order_id2 = self.mock_kite.place_order(
            tradingsymbol="TCS24JUL3800CE",
            exchange="NSE",
            transaction_type="BUY",
            quantity=150,
            order_type="MARKET",
            product="NRML",
            instrument_token=67890
        )
        
        # Position should be removed when netted out to zero
        self.assertEqual(len(self.mock_kite.simulated_positions), 0)
        self.assertEqual(len(self.mock_kite.simulated_orders), 2)

    def test_instruments(self):
        """Test instruments listing."""
        instruments = self.mock_kite.instruments()
        self.assertIsInstance(instruments, list)
        self.assertGreater(len(instruments), 0)
        
        # Check that it contains equity and option instruments
        equity_found = False
        option_found = False
        
        for instrument in instruments:
            if instrument["instrument_type"] == "EQ":
                equity_found = True
            elif instrument["instrument_type"] in ["CE", "PE"]:
                option_found = True
                
        self.assertTrue(equity_found)
        self.assertTrue(option_found)


if __name__ == '__main__':
    unittest.main()