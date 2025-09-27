#!/usr/bin/env python3
"""
Health check script for the Options Wheel Strategy Trading Bot
This script verifies that all components can be imported and basic functionality works
"""
import sys
import os

# Add the Trading directory to the Python path to handle relative imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from config.config import OptionWheelConfig
from models.models import Trade, Position, OptionContract
from models.enums import TransactionType, OrderType, ProductType, OptionType, ExchangeType
from utils.logging_utils import get_logger
from database.database import DatabaseManager
from risk_management.risk_manager import RiskManager
from notifications.notification_manager import NotificationManager
from datetime import datetime

def health_check():
    print("=" * 60)
    print("OPTIONS WHEEL STRATEGY - HEALTH CHECK")
    print("=" * 60)
    
    # Test configuration
    print("✓ Testing Configuration...")
    config = OptionWheelConfig()
    print(f"  - Symbol: {config.symbol}")
    print(f"  - Quantity per lot: {config.quantity_per_lot}")
    print(f"  - Profit target: {config.profit_target_percentage:.2%}")
    print(f"  - Loss limit: {config.loss_limit_percentage:.2%}")
    
    # Test enums
    print("✓ Testing Enums...")
    print(f"  - Transaction types: {list(TransactionType)}")
    print(f"  - Order types: {list(OrderType)}")
    print(f"  - Product types: {list(ProductType)}")
    
    # Test models
    print("✓ Testing Models...")
    sample_trade = Trade(
        order_id="TEST001",
        symbol="NIFTY22000PE",
        exchange="NFO",
        instrument_token=12345,
        transaction_type=TransactionType.SELL,
        order_type=OrderType.MARKET,
        product=ProductType.MIS,
        quantity=50,
        price=120.50
    )
    print(f"  - Created sample trade: {sample_trade.order_id}")
    print(f"  - Trade total value: {sample_trade.total_value()}")
    
    sample_position = Position(
        symbol="NIFTY22000PE",
        exchange="NFO",
        instrument_token=12345,
        product=ProductType.MIS,
        quantity=-50,
        average_price=120.0,
        last_price=115.0
    )
    print(f"  - Created sample position: {sample_position.symbol}")
    print(f"  - Position P&L: {sample_position.pnl()}")
    
    sample_option = OptionContract(
        symbol="NIFTY22000PE23DEC",
        instrument_token=12345,
        exchange=ExchangeType.NFO,
        option_type=OptionType.PUT,
        strike_price=22000.0,
        expiry_date=datetime.now(),
        last_price=120.50,
        open_interest=100000,
        volume=50000,
        oi_day_high=105000,
        oi_day_low=95000,
        bid_price=120.0,
        ask_price=120.5,
        underlying_value=22050.0
    )
    print(f"  - Created sample option: {sample_option.symbol}")
    print(f"  - Option intrinsic value: {sample_option.intrinsic_value(22050.0)}")
    
    # Test logging
    print("✓ Testing Logging...")
    logger = get_logger(__name__)
    logger.info("Health check logging test passed")
    print("  - Logger created and test message logged")
    
    # Test database (in-memory)
    print("✓ Testing Database...")
    db = DatabaseManager(db_path=":memory:")  # Use in-memory DB for testing
    success = db.save_trade(sample_trade)
    print(f"  - Database connection: {'✓' if success else '✗'}")
    
    # Test risk management
    print("✓ Testing Risk Management...")
    risk_manager = RiskManager(config)
    should_place, issues = risk_manager.should_place_order("NIFTY", 50, 120.0, 100000.0)
    print(f"  - Risk check passed: {should_place}")
    print(f"  - Risk issues: {len(issues)}")
    
    # Test notifications (disabled)
    print("✓ Testing Notifications...")
    notification_manager = NotificationManager()
    notification_result = notification_manager.send_notification("Test", "Health check notification", "info")
    print(f"  - Notification enabled: {notification_manager.enabled}")
    print(f"  - Notification sent: {notification_result}")
    
    print("=" * 60)
    print("HEALTH CHECK COMPLETED SUCCESSFULLY!")
    print("All components imported and basic functionality verified.")
    print("=" * 60)

if __name__ == "__main__":
    health_check()