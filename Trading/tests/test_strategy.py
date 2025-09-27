"""
Unit tests for the strategy module.
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
from models.models import Position, Trade


class TestOptionWheelStrategy(unittest.TestCase):
    """Test cases for the OptionWheelStrategy class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a minimal config for testing
        self.config = OptionWheelConfig()
        
        # Create a mock kite client
        self.mock_kite = Mock()
        self.mock_kite.EXCHANGE_NSE = "NSE"
        self.mock_kite.PRODUCT_NRML = "NRML"
        self.mock_kite.PRODUCT_CNC = "CNC"
        self.mock_kite.TRANSACTION_TYPE_BUY = "BUY"
        self.mock_kite.TRANSACTION_TYPE_SELL = "SELL"
        self.mock_kite.ORDER_TYPE_MARKET = "MARKET"
        
        # Create strategy instance
        self.strategy = OptionWheelStrategy(self.config, self.mock_kite)

    def test_initialization(self):
        """Test strategy initialization."""
        # Test that the strategy is created with the correct config
        self.assertEqual(self.strategy.config, self.config)
        self.assertEqual(self.strategy.kite, self.mock_kite)
        self.assertIsNotNone(self.strategy.logger)
        self.assertTrue(self.strategy.is_running)
        self.assertEqual(self.strategy.daily_pnl, 0.0)
        self.assertEqual(self.strategy.positions_history, [])
        self.assertEqual(self.strategy.trades_history, [])

    def test_get_instrument_token(self):
        """Test instrument token lookup."""
        # Create a mock instruments DataFrame
        instruments_data = [
            {"tradingsymbol": "TCS", "exchange": "NSE", "instrument_token": 12345},
            {"tradingsymbol": "TCS24JUL3800CE", "exchange": "NSE", "instrument_token": 67890},
            {"tradingsymbol": "TCS24JUL3700PE", "exchange": "NSE", "instrument_token": 54321}
        ]
        self.strategy.instruments_df = pd.DataFrame(instruments_data)
        
        # Test successful lookup
        token = self.strategy._get_instrument_token("TCS", "NSE")
        self.assertEqual(token, 12345)
        
        # Test unsuccessful lookup
        token = self.strategy._get_instrument_token("NONEXISTENT", "NSE")
        self.assertIsNone(token)
        
        # Test with empty DataFrame
        self.strategy.instruments_df = pd.DataFrame()
        token = self.strategy._get_instrument_token("TCS", "NSE")
        self.assertIsNone(token)

    def test_get_current_ltp(self):
        """Test current LTP retrieval."""
        # Mock the kite.ltp method
        self.mock_kite.ltp.return_value = {"NSE:12345": {"last_price": 3500.50}}
        
        # Test successful LTP retrieval
        ltp = self.strategy._get_current_ltp(12345, "TCS")
        self.assertEqual(ltp, 3500.50)
        self.mock_kite.ltp.assert_called_once_with(["NSE:12345"])
        
        # Test unsuccessful LTP retrieval
        self.mock_kite.ltp.return_value = {}
        ltp = self.strategy._get_current_ltp(99999, "NONEXISTENT")
        self.assertIsNone(ltp)

    def test_place_order(self):
        """Test order placement."""
        # Mock the kite.place_order method
        self.mock_kite.place_order.return_value = "ORDER123456"
        
        # Test successful order placement
        order_id = self.strategy._place_order(
            tradingsymbol="TCS24JUL3800CE",
            instrument_token=67890,
            transaction_type="SELL",
            quantity=150,
            order_type="MARKET",
            product="NRML"
        )
        
        self.assertEqual(order_id, "ORDER123456")
        self.mock_kite.place_order.assert_called_once_with(
            tradingsymbol="TCS24JUL3800CE",
            exchange="NSE",
            transaction_type="SELL",
            quantity=150,
            order_type="MARKET",
            product="NRML",
            instrument_token=67890
        )
        
        # Verify that a trade was added to history
        self.assertEqual(len(self.strategy.trades_history), 1)
        trade = self.strategy.trades_history[0]
        self.assertEqual(trade.order_id, "ORDER123456")
        self.assertEqual(trade.tradingsymbol, "TCS24JUL3800CE")
        self.assertEqual(trade.transaction_type, "SELL")
        self.assertEqual(trade.quantity, 150)
        self.assertEqual(trade.product, "NRML")
        self.assertEqual(trade.exchange, "NSE")

    def test_is_market_open(self):
        """Test market open detection."""
        # Test with mock kite (should always return True for backtesting)
        with patch('isinstance', return_value=True):
            self.assertTrue(self.strategy._is_market_open())
        
        # For a more complete test, we would need to mock datetime.datetime.now()
        # and test various scenarios, but that's beyond the scope of this example

    def test_calculate_position_pnl(self):
        """Test position P&L calculation."""
        # Mock the kite.ltp method
        self.mock_kite.ltp.return_value = {"NSE:12345": {"last_price": 3600.0}}
        
        # Create a mock position
        position = {
            "tradingsymbol": "TCS",
            "instrument_token": 12345,
            "average_price": 3500.0,
            "quantity": 150
        }
        
        # Test P&L calculation
        pnl = self.strategy._calculate_position_pnl(position)
        expected_pnl = (3600.0 - 3500.0) * 150  # (current - avg) * quantity
        self.assertEqual(pnl, expected_pnl)
        
        # Test with missing instrument token
        position_no_token = {
            "tradingsymbol": "TCS",
            "average_price": 3500.0,
            "quantity": 150
        }
        pnl = self.strategy._calculate_position_pnl(position_no_token)
        self.assertEqual(pnl, 0.0)

    def test_get_best_strikes(self):
        """Test best strike selection."""
        # Create mock options chain data
        options_data = [
            {
                "strikePrice": 3700,
                "expiryDate": datetime.datetime(2024, 7, 25),
                "PE.delta": 0.20,
                "CE.delta": 0.80,
                "PE.openInterest": 1500,
                "CE.openInterest": 1200
            },
            {
                "strikePrice": 3800,
                "expiryDate": datetime.datetime(2024, 7, 25),
                "PE.delta": 0.25,
                "CE.delta": 0.75,
                "PE.openInterest": 2000,
                "CE.openInterest": 1800
            },
            {
                "strikePrice": 3900,
                "expiryDate": datetime.datetime(2024, 7, 25),
                "PE.delta": 0.30,
                "CE.delta": 0.70,
                "PE.openInterest": 1000,
                "CE.openInterest": 2500
            }
        ]
        option_chain = pd.DataFrame(options_data)
        
        # Mock instrument token lookup
        self.strategy._get_instrument_token = Mock(return_value=67890)
        
        # Test with current price of 3800 (at the money)
        best_put, best_call = self.strategy._get_best_strikes(option_chain, 3800.0)
        
        # With the default config (delta 0.15-0.25), the best put should be strike 3700
        # With the default config (delta 0.15-0.25), the best call should be none (all > 0.25)
        self.assertIsNotNone(best_put)
        self.assertEqual(best_put["strikePrice"], 3700)
        # Note: best_call might be None or might be strike 3800 depending on exact filtering
        
        # Verify that instrument tokens were added
        self.assertIn("instrument_token", best_put)
        self.assertIn("tradingsymbol", best_put)


if __name__ == '__main__':
    unittest.main()