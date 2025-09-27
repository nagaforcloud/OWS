"""
Configuration module for the Option Wheel Strategy.
"""
import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class OptionWheelConfig:
    """
    Configuration parameters for the Option Wheel Strategy.
    Sensitive data (API_KEY, API_SECRET, ACCESS_TOKEN) are loaded from environment variables.
    Default values are provided for development/testing if environment variables are not set.
    """
    # API Credentials
    api_key: str = field(default_factory=lambda: os.getenv("KITE_API_KEY", "YOUR_KITE_API_KEY_DEFAULT"))
    api_secret: str = field(default_factory=lambda: os.getenv("KITE_API_SECRET", "YOUR_KITE_API_SECRET_DEFAULT"))
    access_token: str = field(default_factory=lambda: os.getenv("KITE_ACCESS_TOKEN", "YOUR_KITE_ACCESS_TOKEN_DEFAULT"))
    
    # Trading Parameters
    symbol: str = os.getenv("SYMBOL", "TCS")
    quantity_per_lot: int = int(os.getenv("QUANTITY_PER_LOT", 150))
    profit_target_percentage: float = float(os.getenv("PROFIT_TARGET_PERCENTAGE", 0.50))
    loss_limit_percentage: float = float(os.getenv("LOSS_LIMIT_PERCENTAGE", 1.00))
    otm_delta_range_low: float = float(os.getenv("OTM_DELTA_RANGE_LOW", 0.15))
    otm_delta_range_high: float = float(os.getenv("OTM_DELTA_RANGE_HIGH", 0.25))
    min_open_interest: int = int(os.getenv("MIN_OPEN_INTEREST", 1000))
    
    # Strategy Timing
    strategy_run_interval_seconds: int = int(os.getenv("STRATEGY_RUN_INTERVAL_SECONDS", 300))
    market_open_hour: int = int(os.getenv("MARKET_OPEN_HOUR", 9))
    market_open_minute: int = int(os.getenv("MARKET_OPEN_MINUTE", 15))
    market_close_hour: int = int(os.getenv("MARKET_CLOSE_HOUR", 15))
    market_close_minute: int = int(os.getenv("MARKET_CLOSE_MINUTE", 30))
    
    # Risk Management
    max_concurrent_positions: int = int(os.getenv("MAX_CONCURRENT_POSITIONS", 5))
    max_daily_loss_limit: float = float(os.getenv("MAX_DAILY_LOSS_LIMIT", 5000.0))
    max_portfolio_risk: float = float(os.getenv("MAX_PORTFOLIO_RISK", 0.02))  # 2% of portfolio
    
    # Notification Settings
    enable_notifications: bool = os.getenv("ENABLE_NOTIFICATIONS", "false").lower() == "true"
    notification_webhook_url: str = os.getenv("NOTIFICATION_WEBHOOK_URL", "")
    
    # Data Settings
    use_nse_api: bool = os.getenv("USE_NSE_API", "true").lower() == "true"
    data_refresh_interval: int = int(os.getenv("DATA_REFRESH_INTERVAL", 60))