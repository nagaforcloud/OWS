"""
Unit tests for the models module.
"""
import sys
import os
import unittest
import datetime

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'option_wheel_strategy'))

from models.models import Position, Trade
from models.enums import OrderType, ProductType, TransactionType


class TestModels(unittest.TestCase):
    """Test cases for the data models."""

    def test_position_creation(self):
        """Test creation of Position objects."""
        # Test with required parameters only
        position = Position(
            tradingsymbol="TCS24JUL3800CE",
            quantity=150,
            average_price=150.50,
            product="NRML",
            exchange="NSE"
        )
        
        self.assertEqual(position.tradingsymbol, "TCS24JUL3800CE")
        self.assertEqual(position.quantity, 150)
        self.assertEqual(position.average_price, 150.50)
        self.assertEqual(position.product, "NRML")
        self.assertEqual(position.exchange, "NSE")
        self.assertIsNone(position.instrument_token)
        self.assertEqual(position.pnl, 0.0)
        self.assertEqual(position.market_value, 0.0)
        self.assertIsNone(position.timestamp)
        
        # Test with all parameters
        timestamp = datetime.datetime.now()
        position_with_all = Position(
            tradingsymbol="TCS24JUL3800CE",
            quantity=150,
            average_price=150.50,
            product="NRML",
            exchange="NSE",
            instrument_token=123456,
            pnl=1500.0,
            market_value=22575.0,
            timestamp=timestamp
        )
        
        self.assertEqual(position_with_all.tradingsymbol, "TCS24JUL3800CE")
        self.assertEqual(position_with_all.quantity, 150)
        self.assertEqual(position_with_all.average_price, 150.50)
        self.assertEqual(position_with_all.product, "NRML")
        self.assertEqual(position_with_all.exchange, "NSE")
        self.assertEqual(position_with_all.instrument_token, 123456)
        self.assertEqual(position_with_all.pnl, 1500.0)
        self.assertEqual(position_with_all.market_value, 22575.0)
        self.assertEqual(position_with_all.timestamp, timestamp)

    def test_trade_creation(self):
        """Test creation of Trade objects."""
        timestamp = datetime.datetime.now()
        
        # Test with required parameters only
        trade = Trade(
            order_id="ORDER123456",
            tradingsymbol="TCS24JUL3800CE",
            transaction_type="SELL",
            quantity=150,
            price=150.50,
            product="NRML",
            exchange="NSE",
            timestamp=timestamp
        )
        
        self.assertEqual(trade.order_id, "ORDER123456")
        self.assertEqual(trade.tradingsymbol, "TCS24JUL3800CE")
        self.assertEqual(trade.transaction_type, "SELL")
        self.assertEqual(trade.quantity, 150)
        self.assertEqual(trade.price, 150.50)
        self.assertEqual(trade.product, "NRML")
        self.assertEqual(trade.exchange, "NSE")
        self.assertEqual(trade.timestamp, timestamp)
        self.assertEqual(trade.status, "completed")
        self.assertEqual(trade.pnl, 0.0)
        
        # Test with all parameters
        trade_with_all = Trade(
            order_id="ORDER123456",
            tradingsymbol="TCS24JUL3800CE",
            transaction_type="SELL",
            quantity=150,
            price=150.50,
            product="NRML",
            exchange="NSE",
            timestamp=timestamp,
            status="executed",
            pnl=1500.0
        )
        
        self.assertEqual(trade_with_all.order_id, "ORDER123456")
        self.assertEqual(trade_with_all.tradingsymbol, "TCS24JUL3800CE")
        self.assertEqual(trade_with_all.transaction_type, "SELL")
        self.assertEqual(trade_with_all.quantity, 150)
        self.assertEqual(trade_with_all.price, 150.50)
        self.assertEqual(trade_with_all.product, "NRML")
        self.assertEqual(trade_with_all.exchange, "NSE")
        self.assertEqual(trade_with_all.timestamp, timestamp)
        self.assertEqual(trade_with_all.status, "executed")
        self.assertEqual(trade_with_all.pnl, 1500.0)


class TestEnums(unittest.TestCase):
    """Test cases for the enums."""

    def test_order_type_enum(self):
        """Test OrderType enum values."""
        self.assertEqual(OrderType.MARKET.value, "MARKET")
        self.assertEqual(OrderType.LIMIT.value, "LIMIT")
        self.assertEqual(OrderType.SL.value, "SL")
        self.assertEqual(OrderType.SL_M.value, "SL-M")
        
    def test_product_type_enum(self):
        """Test ProductType enum values."""
        self.assertEqual(ProductType.NRML.value, "NRML")
        self.assertEqual(ProductType.CNC.value, "CNC")
        self.assertEqual(ProductType.MIS.value, "MIS")
        
    def test_transaction_type_enum(self):
        """Test TransactionType enum values."""
        self.assertEqual(TransactionType.BUY.value, "BUY")
        self.assertEqual(TransactionType.SELL.value, "SELL")


if __name__ == '__main__':
    unittest.main()