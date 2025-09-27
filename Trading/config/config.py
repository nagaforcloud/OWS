from dataclasses import dataclass
from dotenv import load_dotenv
import os
from typing import Optional
import logging

# Load environment variables
load_dotenv()

@dataclass
class OptionWheelConfig:
    """
    Configuration class for the Options Wheel Strategy
    """
    # API Credentials
    api_key: str = os.getenv('KITE_API_KEY', '')
    api_secret: str = os.getenv('KITE_API_SECRET', '')
    access_token: str = os.getenv('KITE_ACCESS_TOKEN', '')
    
    # Trading Parameters
    symbol: str = os.getenv('SYMBOL', 'TCS')
    quantity_per_lot: int = int(os.getenv('QUANTITY_PER_LOT', '150'))
    profit_target_percentage: float = float(os.getenv('PROFIT_TARGET_PERCENTAGE', '0.50'))
    loss_limit_percentage: float = float(os.getenv('LOSS_LIMIT_PERCENTAGE', '1.00'))
    
    # Delta Range
    otm_delta_range_low: float = float(os.getenv('OTM_DELTA_RANGE_LOW', '0.15'))
    otm_delta_range_high: float = float(os.getenv('OTM_DELTA_RANGE_HIGH', '0.25'))
    
    # Open Interest
    min_open_interest: int = int(os.getenv('MIN_OPEN_INTEREST', '1000'))
    
    # Strategy Timing
    strategy_run_interval_seconds: int = int(os.getenv('STRATEGY_RUN_INTERVAL_SECONDS', '300'))
    market_open_hour: int = int(os.getenv('MARKET_OPEN_HOUR', '9'))
    market_open_minute: int = int(os.getenv('MARKET_OPEN_MINUTE', '9'))
    market_close_hour: int = int(os.getenv('MARKET_CLOSE_HOUR', '15'))
    market_close_minute: int = int(os.getenv('MARKET_CLOSE_MINUTE', '30'))
    
    # Risk Management
    max_concurrent_positions: int = int(os.getenv('MAX_CONCURRENT_POSITIONS', '5'))
    max_daily_loss_limit: float = float(os.getenv('MAX_DAILY_LOSS_LIMIT', '5000.0'))
    max_portfolio_risk: float = float(os.getenv('MAX_PORTFOLIO_RISK', '0.02'))
    
    # Notification Settings
    enable_notifications: bool = os.getenv('ENABLE_NOTIFICATIONS', 'false').lower() == 'true'
    notification_webhook_url: str = os.getenv('NOTIFICATION_WEBHOOK_URL', '')
    
    # Data Settings
    use_nse_api: bool = os.getenv('USE_NSE_API', 'true').lower() == 'true'
    data_refresh_interval: int = int(os.getenv('DATA_REFRESH_INTERVAL', '60'))
    use_nifty: bool = os.getenv('USE_NIFTY', 'false').lower() == 'true'
    
    # Safety & Compliance Settings
    dry_run: bool = os.getenv('DRY_RUN', 'false').lower() == 'true'
    use_holiday_calendar: bool = os.getenv('USE_HOLIDAY_CALENDAR', 'false').lower() == 'true'
    holiday_file_path: str = os.getenv('HOLIDAY_FILE_PATH', './data/nse_holidays.csv')
    strategy_mode: str = os.getenv('STRATEGY_MODE', 'balanced')  # conservative, balanced, aggressive
    risk_per_trade_percent: float = float(os.getenv('RISK_PER_TRADE_PERCENT', '0.01'))
    min_cash_reserve: float = float(os.getenv('MIN_CASH_RESERVE', '10000'))
    enable_auto_roll: bool = os.getenv('ENABLE_AUTO_ROLL', 'false').lower() == 'true'
    kill_switch_file: str = os.getenv('KILL_SWITCH_FILE', 'STOP_TRADING')
    
    def __post_init__(self):
        """Validate configuration parameters after initialization"""
        self._validate_config()

    def _validate_config(self):
        """Validate configuration parameters"""
        errors = []
        
        # Validate API credentials
        if not self.api_key:
            errors.append("API Key is required")
        if not self.api_secret:
            errors.append("API Secret is required")
        
        # Validate trading parameters
        if self.quantity_per_lot <= 0:
            errors.append("Quantity per lot must be positive")
        
        if not (0 < self.profit_target_percentage <= 1):
            errors.append("Profit target percentage must be between 0 and 1")
        
        if not (0 < self.loss_limit_percentage <= 1):
            errors.append("Loss limit percentage must be between 0 and 1")
        
        # Validate delta range
        if not (0 < self.otm_delta_range_low < self.otm_delta_range_high < 1):
            errors.append("Delta range must satisfy 0 < low < high < 1")
        
        # Validate open interest
        if self.min_open_interest <= 0:
            errors.append("Minimum open interest must be positive")
        
        # Validate strategy timing
        if self.strategy_run_interval_seconds <= 0:
            errors.append("Strategy run interval must be positive")
        
        if not (0 <= self.market_open_hour <= 23):
            errors.append("Market open hour must be between 0 and 23")
        
        if not (0 <= self.market_open_minute <= 59):
            errors.append("Market open minute must be between 0 and 59")
            
        if not (0 <= self.market_close_hour <= 23):
            errors.append("Market close hour must be between 0 and 23")
        
        if not (0 <= self.market_close_minute <= 59):
            errors.append("Market close minute must be between 0 and 59")
        
        # Validate risk management
        if self.max_concurrent_positions <= 0:
            errors.append("Max concurrent positions must be positive")
        
        if self.max_daily_loss_limit < 0:
            errors.append("Max daily loss limit must be non-negative")
        
        if not (0 <= self.max_portfolio_risk <= 1):
            errors.append("Max portfolio risk must be between 0 and 1")
        
        # Validate data settings
        if self.data_refresh_interval <= 0:
            errors.append("Data refresh interval must be positive")
        
        # Validate strategy mode
        valid_modes = ['conservative', 'balanced', 'aggressive']
        if self.strategy_mode.lower() not in valid_modes:
            errors.append(f"Strategy mode must be one of: {', '.join(valid_modes)}")
        
        # Validate risk per trade percent
        if not (0 < self.risk_per_trade_percent <= 0.1):
            errors.append("Risk per trade percent must be between 0 and 0.1 (10%)")
        
        if errors:
            error_msg = "Configuration validation failed:\\n" + "\\n".join(errors)
            logging.error(error_msg)
            raise ValueError(error_msg)

    @property
    def market_open_time(self):
        """Get market open time as a formatted string"""
        return f"{self.market_open_hour:02d}:{self.market_open_minute:02d}"
    
    @property
    def market_close_time(self):
        """Get market close time as a formatted string"""
        return f"{self.market_close_hour:02d}:{self.market_close_minute:02d}"

    def __post_init__(self):
        """Validate configuration parameters after initialization"""
        self._validate_config()

    def _validate_config(self):
        """Validate configuration parameters"""
        errors = []
        
        # Validate API credentials
        if not self.api_key:
            errors.append("API Key is required")
        if not self.api_secret:
            errors.append("API Secret is required")
        
        # Validate trading parameters
        if self.quantity_per_lot <= 0:
            errors.append("Quantity per lot must be positive")
        
        if not (0 < self.profit_target_percentage <= 1):
            errors.append("Profit target percentage must be between 0 and 1")
        
        if not (0 < self.loss_limit_percentage <= 1):
            errors.append("Loss limit percentage must be between 0 and 1")
        
        # Validate delta range
        if not (0 < self.otm_delta_range_low < self.otm_delta_range_high < 1):
            errors.append("Delta range must satisfy 0 < low < high < 1")
        
        # Validate open interest
        if self.min_open_interest <= 0:
            errors.append("Minimum open interest must be positive")
        
        # Validate strategy timing
        if self.strategy_run_interval_seconds <= 0:
            errors.append("Strategy run interval must be positive")
        
        if not (0 <= self.market_open_hour <= 23):
            errors.append("Market open hour must be between 0 and 23")
        
        if not (0 <= self.market_open_minute <= 59):
            errors.append("Market open minute must be between 0 and 59")
            
        if not (0 <= self.market_close_hour <= 23):
            errors.append("Market close hour must be between 0 and 23")
        
        if not (0 <= self.market_close_minute <= 59):
            errors.append("Market close minute must be between 0 and 59")
        
        # Validate risk management
        if self.max_concurrent_positions <= 0:
            errors.append("Max concurrent positions must be positive")
        
        if self.max_daily_loss_limit < 0:
            errors.append("Max daily loss limit must be non-negative")
        
        if not (0 <= self.max_portfolio_risk <= 1):
            errors.append("Max portfolio risk must be between 0 and 1")
        
        # Validate data settings
        if self.data_refresh_interval <= 0:
            errors.append("Data refresh interval must be positive")
        
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(errors)
            logging.error(error_msg)
            raise ValueError(error_msg)

    @property
    def market_open_time(self):
        """Get market open time as a formatted string"""
        return f"{self.market_open_hour:02d}:{self.market_open_minute:02d}"
    
    @property
    def market_close_time(self):
        """Get market close time as a formatted string"""
        return f"{self.market_close_hour:02d}:{self.market_close_minute:02d}"

# Global config instance
config = OptionWheelConfig()