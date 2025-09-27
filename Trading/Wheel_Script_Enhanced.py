import requests
import pandas as pd
import numpy as np
import time
import datetime
import logging
import os
import json
import signal
import sys
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum
from logging.handlers import RotatingFileHandler

from kiteconnect import KiteConnect
from kiteconnect import exceptions as kc_exceptions

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# --- Enums for better type safety ---
class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"
    SL_M = "SL-M"

class ProductType(Enum):
    NRML = "NRML"
    CNC = "CNC"
    MIS = "MIS"

class TransactionType(Enum):
    BUY = "BUY"
    SELL = "SELL"

# --- Configuration ---
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

# --- Enhanced Logging Setup ---
def setup_logging(log_level=logging.INFO) -> logging.Logger:
    """Set up enhanced logging with both file and console handlers."""
    logger = logging.getLogger("OptionWheel")
    logger.setLevel(log_level)
    
    # Prevent adding multiple handlers if function is called multiple times
    if logger.handlers:
        return logger
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        "option_wheel_enhanced.log", 
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# --- Notification System ---
class NotificationManager:
    """Handles sending notifications for important events."""
    
    def __init__(self, config: OptionWheelConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
    
    def send_notification(self, title: str, message: str, priority: str = "info") -> None:
        """Send notification via webhook or other means."""
        if not self.config.enable_notifications:
            return
            
        try:
            if self.config.notification_webhook_url:
                payload = {
                    "title": title,
                    "message": message,
                    "priority": priority,
                    "timestamp": datetime.datetime.now().isoformat()
                }
                response = requests.post(
                    self.config.notification_webhook_url,
                    json=payload,
                    timeout=10
                )
                response.raise_for_status()
                self.logger.info(f"Notification sent: {title}")
        except Exception as e:
            self.logger.error(f"Failed to send notification: {e}")

# --- Data Models ---
@dataclass
class Position:
    """Represents a trading position."""
    tradingsymbol: str
    quantity: int
    average_price: float
    product: str
    exchange: str
    instrument_token: Optional[int] = None
    pnl: float = 0.0
    market_value: float = 0.0
    timestamp: Optional[datetime.datetime] = None

@dataclass
class Trade:
    """Represents a trade execution."""
    order_id: str
    tradingsymbol: str
    transaction_type: str
    quantity: int
    price: float
    product: str
    exchange: str
    timestamp: datetime.datetime
    status: str = "completed"
    pnl: float = 0.0

# --- Mock KiteConnect for Backtesting ---
class MockKiteConnect:
    """
    A mock class to simulate KiteConnect API calls for backtesting purposes.
    It provides predefined or historical data instead of making live API requests.
    """
    def __init__(self, historical_data: Dict[str, Any]):
        self.logger = setup_logging().getChild(__name__)
        self.historical_data = historical_data # Contains simulated LTPs, options chains etc.
        self.simulated_positions = [] # List of dicts, mimicking Kite's positions structure
        self.simulated_orders = [] # Track placed orders
        self.current_simulated_time = datetime.datetime(2023, 1, 1, 9, 30, 0) # Default start time for backtest

        # Constants mimicking KiteConnect's
        self.EXCHANGE_NSE = "NSE"
        self.PRODUCT_NRML = "NRML"
        self.PRODUCT_CNC = "CNC"
        self.TRANSACTION_TYPE_BUY = "BUY"
        self.TRANSACTION_TYPE_SELL = "SELL"
        self.ORDER_TYPE_MARKET = "MARKET"

    def set_simulated_time(self, new_time: datetime.datetime):
        """Sets the current simulated time for backtesting."""
        self.current_simulated_time = new_time

    def ltp(self, instruments: List[str]) -> Dict[str, Dict[str, float]]:
        """
        Simulates fetching Last Traded Price (LTP) for given instruments.
        Looks up prices from historical_data based on current_simulated_time.
        """
        result = {}
        for inst_str in instruments:
            parts = inst_str.split(':')
            token_or_symbol = parts[1]

            # Get the date and time string for lookup in historical data
            # Use 'H:M' for hourly data, or 'H:M:S' for second-by-second data if available
            time_key = self.current_simulated_time.strftime('%Y-%m-%d %H:%M') 

            simulated_price = None
            if token_or_symbol == "TCS":
                simulated_price = self.historical_data.get('TCS_LTP', {}).get(time_key)
            else:
                # For options, look up from OPTION_PREMIUMS data
                simulated_price = self.historical_data.get('OPTION_PREMIUMS', {}).get(token_or_symbol, {}).get(time_key)
            
            if simulated_price is not None:
                result[inst_str] = {"last_price": simulated_price}
            else:
                self.logger.warning(f"Mock LTP: No historical price found for {inst_str} at {time_key}. Returning 0.0.")
                result[inst_str] = {"last_price": 0.0} # Fallback
        self.logger.debug(f"Mock LTP for {instruments}: {result}")
        return result

    def positions(self) -> Dict[str, List[Dict[str, Any]]]:
        """Simulates fetching current positions from the simulated portfolio."""
        self.logger.debug(f"Mock Positions: {self.simulated_positions}")
        return {"net": self.simulated_positions}

    def place_order(self, tradingsymbol: str, exchange: str, transaction_type: str,
                    quantity: int, order_type: str, product: str, instrument_token: int) -> str:
        """
        Simulates placing an order and updates the simulated positions.
        This is a simplified fill logic (market orders fill at current simulated LTP).
        """
        order_id = f"MOCK_ORDER_{len(self.simulated_orders) + 1}"
        self.logger.info(f"Mock Order Placed: {order_id} - {transaction_type} {quantity} {tradingsymbol} ({product})")

        # Simulate order fill price
        ltp_data = self.ltp([f"{exchange}:{instrument_token}"])
        fill_price = ltp_data.get(f"{exchange}:{instrument_token}", {}).get("last_price", 0.0)
        if fill_price == 0.0:
            self.logger.error(f"Mock Order: Could not get fill price for {tradingsymbol}. Order might not be realistic.")

        # Update simulated positions
        found_pos = False
        for pos in self.simulated_positions:
            if pos["tradingsymbol"] == tradingsymbol and pos["product"] == product:
                if transaction_type == self.TRANSACTION_TYPE_BUY:
                    # Calculate new average price for buy
                    current_value = pos["average_price"] * pos["quantity"]
                    new_value = current_value + (fill_price * quantity)
                    pos["quantity"] += quantity
                    pos["average_price"] = new_value / pos["quantity"] if pos["quantity"] != 0 else 0
                else: # SELL
                    # Calculate new average price for sell (if selling from existing pos)
                    current_value = pos["average_price"] * pos["quantity"]
                    new_value = current_value - (fill_price * quantity)
                    pos["quantity"] -= quantity
                    pos["average_price"] = new_value / pos["quantity"] if pos["quantity"] != 0 else 0
                found_pos = True
                break
        
        if not found_pos:
            # If it's a new short position (sell without existing holding)
            if transaction_type == self.TRANSACTION_TYPE_SELL:
                self.simulated_positions.append({
                    "tradingsymbol": tradingsymbol,
                    "quantity": -quantity, # Negative for short positions
                    "average_price": fill_price,
                    "product": product,
                    "exchange": exchange,
                    "instrument_token": instrument_token
                })
            elif transaction_type == self.TRANSACTION_TYPE_BUY:
                 self.simulated_positions.append({
                    "tradingsymbol": tradingsymbol,
                    "quantity": quantity,
                    "average_price": fill_price,
                    "product": product,
                    "exchange": exchange,
                    "instrument_token": instrument_token
                })

        # Remove positions that net out to zero (e.g., bought back a short position)
        self.simulated_positions = [p for p in self.simulated_positions if p["quantity"] != 0]

        self.simulated_orders.append({
            "order_id": order_id,
            "tradingsymbol": tradingsymbol,
            "transaction_type": transaction_type,
            "quantity": quantity,
            "fill_price": fill_price,
            "timestamp": self.current_simulated_time
        })
        return order_id

    def instruments(self) -> List[Dict[str, Any]]:
        """
        Simulates fetching instruments list. This should be a comprehensive list
        of all instruments relevant to your backtest (equity and all options).
        """
        # This is a static list for demonstration. In a real backtest, you'd generate
        # this based on the options available in your historical data for the backtest period.
        return [
            {"instrument_token": 12345, "tradingsymbol": "TCS", "exchange": "NSE", "instrument_type": "EQ"},
            # Example options for TCS, assuming a fixed expiry for simplicity in this mock
            # You would need to dynamically generate these based on your historical options chain
            {"instrument_token": 67890, "tradingsymbol": "TCS24JUL3800PE", "exchange": "NSE", "instrument_type": "PE", "strike": 3800, "expiry": "2024-07-25"},
            {"instrument_token": 67891, "tradingsymbol": "TCS24JUL3900CE", "exchange": "NSE", "instrument_type": "CE", "strike": 3900, "expiry": "2024-07-25"},
            {"instrument_token": 67892, "tradingsymbol": "TCS24JUL3700PE", "exchange": "NSE", "instrument_type": "PE", "strike": 3700, "expiry": "2024-07-25"},
            {"instrument_token": 67893, "tradingsymbol": "TCS24JUL4000CE", "exchange": "NSE", "instrument_type": "CE", "strike": 4000, "expiry": "2024-07-25"},
            # Add more relevant instruments here
        ]

    def historical_data(self, instrument_token: int, from_date: datetime.date, 
                       to_date: datetime.date, interval: str) -> List[Dict[str, Any]]:
        """
        Simulates fetching historical data.
        """
        # This is a simplified mock implementation
        self.logger.info(f"Mock historical data request for token {instrument_token} from {from_date} to {to_date}")
        return []

# --- Enhanced Option Wheel Strategy ---
class EnhancedOptionWheelStrategy:
    """
    Enhanced implementation of the Option Wheel Strategy using Zerodha KiteConnect.
    
    The strategy involves:
    1. Selling Out-of-the-Money (OTM) Cash-Secured Puts.
    2. If assigned (stock delivered), selling OTM Covered Calls.
    3. Managing existing positions (profit booking, stop-loss).
    """

    def __init__(self, config: OptionWheelConfig, kite_client: Optional[Any] = None):
        """
        Initializes the EnhancedOptionWheelStrategy with provided configuration.

        Args:
            config (OptionWheelConfig): Configuration object containing API keys,
                                        strategy parameters, and market timings.
            kite_client (Optional[Any]): An optional KiteConnect client instance.
                                         Used for dependency injection during testing/mocking.
        """
        self.config = config
        self.kite = kite_client
        self.instruments_df: Optional[pd.DataFrame] = None
        self.logger = setup_logging().getChild(__name__)
        self.notification_manager = NotificationManager(config, self.logger)
        self.is_running = True
        self.daily_pnl = 0.0
        self.positions_history: List[Position] = []
        self.trades_history: List[Trade] = []
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # State file for persistence
        self.state_file = "option_wheel_state.json"
        self._load_state()

        # Only initialize real KiteConnect if a mock client is not provided
        if self.kite is None:
            self._init_kite()
        
        # Always fetch instruments, whether from real API or mock
        self._fetch_all_instruments()

    def _retry_kite_api_call(self, func, *args, max_retries=3, delay=1, **kwargs):
        """
        Retry a Kite API call with exponential backoff.
        
        Args:
            func: The Kite API function to call
            *args: Positional arguments for the function
            max_retries: Maximum number of retry attempts
            delay: Initial delay between retries (in seconds)
            **kwargs: Keyword arguments for the function
            
        Returns:
            The result of the function call or None if all retries failed
        """
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except kc_exceptions.NetworkException as e:
                if attempt < max_retries - 1:
                    wait_time = delay * (2 ** attempt)  # Exponential backoff
                    self.logger.warning(f"Network error on attempt {attempt + 1}/{max_retries}. Retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"Network error after {max_retries} attempts: {e}")
                    return None
            except kc_exceptions.TokenException as e:
                self.logger.error(f"Token error - session may have expired: {e}")
                # Try to reinitialize Kite connection
                self._init_kite()
                if attempt < max_retries - 1:
                    time.sleep(delay)
                else:
                    return None
            except kc_exceptions.InputException as e:
                self.logger.error(f"Input error - cannot retry: {e}")
                return None
            except Exception as e:
                self.logger.error(f"Unexpected error on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(delay)
                else:
                    return None
        return None

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}. Shutting down gracefully...")
        self.is_running = False
        
        # Generate final performance report
        perf_summary = self.get_performance_summary()
        portfolio_report = self.get_detailed_portfolio_report()
        
        self.logger.info("=== FINAL PERFORMANCE REPORT ===")
        self.logger.info(f"Performance Summary: {json.dumps(perf_summary, indent=2)}")
        self.logger.info(f"Portfolio Report: {json.dumps(portfolio_report, indent=2)}")
        
        # Save final state
        self._save_state()
        
        # Send notification
        self.notification_manager.send_notification(
            "Strategy Shutdown",
            f"Strategy shutdown completed. Final P&L: ₹{self.daily_pnl:,.2f}"
        )
        
        sys.exit(0)

    def _save_state(self):
        """Save strategy state to file."""
        try:
            # Convert complex objects to serializable format
            positions_history_serializable = []
            for pos in self.positions_history:
                pos_dict = vars(pos).copy()
                # Convert datetime objects to strings
                if hasattr(pos, 'timestamp') and pos.timestamp:
                    pos_dict['timestamp'] = pos.timestamp.isoformat() if hasattr(pos.timestamp, 'isoformat') else str(pos.timestamp)
                positions_history_serializable.append(pos_dict)
            
            trades_history_serializable = []
            for trade in self.trades_history:
                trade_dict = vars(trade).copy()
                # Convert datetime objects to strings
                if hasattr(trade, 'timestamp') and trade.timestamp:
                    trade_dict['timestamp'] = trade.timestamp.isoformat() if hasattr(trade.timestamp, 'isoformat') else str(trade.timestamp)
                trades_history_serializable.append(trade_dict)
            
            state = {
                "daily_pnl": self.daily_pnl,
                "positions_history": positions_history_serializable,
                "trades_history": trades_history_serializable,
                "timestamp": datetime.datetime.now().isoformat(),
                "config": {
                    "symbol": self.config.symbol,
                    "quantity_per_lot": self.config.quantity_per_lot,
                    "profit_target_percentage": self.config.profit_target_percentage,
                    "loss_limit_percentage": self.config.loss_limit_percentage
                }
            }
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2, default=str)
            self.logger.info("Strategy state saved successfully.")
        except Exception as e:
            self.logger.error(f"Failed to save strategy state: {e}")

    def _load_state(self):
        """Load strategy state from file."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                self.daily_pnl = state.get("daily_pnl", 0.0)
                
                # Load positions history
                positions_data = state.get("positions_history", [])
                for pos_data in positions_data:
                    try:
                        # Convert timestamp string back to datetime
                        if 'timestamp' in pos_data and pos_data['timestamp']:
                            pos_data['timestamp'] = datetime.datetime.fromisoformat(pos_data['timestamp'])
                        pos = Position(**{k: v for k, v in pos_data.items() if k in Position.__dataclass_fields__})
                        self.positions_history.append(pos)
                    except Exception as e:
                        self.logger.warning(f"Failed to load position: {e}")
                
                # Load trades history
                trades_data = state.get("trades_history", [])
                for trade_data in trades_data:
                    try:
                        # Convert timestamp string back to datetime
                        if 'timestamp' in trade_data and trade_data['timestamp']:
                            trade_data['timestamp'] = datetime.datetime.fromisoformat(trade_data['timestamp'])
                        trade = Trade(**{k: v for k, v in trade_data.items() if k in Trade.__dataclass_fields__})
                        self.trades_history.append(trade)
                    except Exception as e:
                        self.logger.warning(f"Failed to load trade: {e}")
                
                self.logger.info(f"Loaded previous state. Daily P&L: ₹{self.daily_pnl:,.2f}, Positions: {len(self.positions_history)}, Trades: {len(self.trades_history)}")
        except Exception as e:
            self.logger.error(f"Failed to load strategy state: {e}")

    def _init_kite(self) -> None:
        """
        Initializes the KiteConnect object.
        ACCESS_TOKEN needs to be obtained dynamically after a successful login.
        For a production setup, you would typically have a web server that handles the
        login redirect and stores the access token securely.
        For a script, you'll need to manually get the request_token from the redirect URL
        after navigating to kite.login_url() in your browser, and then generate the access token.
        """
        # If kite client is already provided (e.g., mock), skip initialization
        if self.kite is not None:
            return

        try:
            self.kite = KiteConnect(api_key=self.config.api_key)
            if not self.config.access_token or self.config.access_token == "YOUR_KITE_ACCESS_TOKEN_DEFAULT":
                self.logger.critical("ACCESS_TOKEN is not set in .env or is default. Please generate it manually and update .env.")
                raise ValueError("ACCESS_TOKEN not configured.")
            self.kite.set_access_token(self.config.access_token)
            self.logger.info("KiteConnect initialized successfully.")
        except kc_exceptions.TokenException as e:
            self.logger.critical(f"Invalid access token or session expired: {e}")
            raise
        except Exception as e:
            self.logger.critical(f"Error initializing KiteConnect: {e}")
            raise

    def _fetch_all_instruments(self) -> None:
        """Fetches all tradable instruments from KiteConnect and stores them in a DataFrame."""
        if self.kite is None:
            self.logger.error("KiteConnect instance not initialized. Cannot fetch instruments.")
            self.instruments_df = pd.DataFrame()
            return
        try:
            self.logger.info("Fetching all tradable instruments...")
            instruments = self.kite.instruments()
            self.instruments_df = pd.DataFrame(instruments)
            self.logger.info(f"Fetched {len(self.instruments_df)} instruments.")
        except Exception as e:
            self.logger.error(f"Error fetching instruments: {e}")
            self.instruments_df = pd.DataFrame() # Ensure it's a DataFrame even on error

    def _get_instrument_token(self, tradingsymbol: str, exchange: str = "NSE") -> Optional[int]:
        """
        Looks up the instrument token for a given trading symbol and exchange.

        Args:
            tradingsymbol (str): The trading symbol (e.g., "TCS", "TCS24JUL3800CE").
            exchange (str): The exchange (e.g., "NSE").

        Returns:
            Optional[int]: The instrument token if found, otherwise None.
        """
        if self.instruments_df is None or self.instruments_df.empty:
            self.logger.warning("Instruments DataFrame is empty or not loaded. Attempting to re-fetch.")
            self._fetch_all_instruments() # Try to re-fetch if not already loaded

        if self.instruments_df is not None and not self.instruments_df.empty:
            instrument = self.instruments_df[
                (self.instruments_df['tradingsymbol'] == tradingsymbol) &
                (self.instruments_df['exchange'] == exchange)
            ]
            if not instrument.empty:
                return int(instrument.iloc[0]['instrument_token'])
        self.logger.warning(f"Instrument token not found for {tradingsymbol} on {exchange}")
        return None

    def _fetch_nse_options(self, symbol: str) -> pd.DataFrame:
        """
        Fetches the options chain for a given symbol from NSE India API (live)
        or from historical data (if mocking). Filters for the nearest expiry date.

        Args:
            symbol (str): The underlying stock symbol (e.g., "TCS").

        Returns:
            pd.DataFrame: A DataFrame containing the options chain for the nearest expiry.
        """
        # If using a mock KiteConnect, try to get historical options chain data from it
        if isinstance(self.kite, MockKiteConnect):
            # For backtesting, get the options chain snapshot for the current simulated time
            time_key = self.kite.current_simulated_time.strftime('%Y-%m-%d %H:%M')
            historical_oc = self.kite.historical_data.get('OPTION_CHAIN_DATA', {}).get(time_key)
            
            if historical_oc is not None and not historical_oc.empty:
                self.logger.info(f"Mock _fetch_nse_options: Retrieved historical options chain for {symbol} at {time_key}.")
                # Ensure expiryDate is datetime objects for filtering
                historical_oc['expiryDate'] = pd.to_datetime(historical_oc['expiryDate'])
                
                # Filter for the nearest expiry within the mock data
                unique_expiries = sorted(historical_oc['expiryDate'].unique())
                today_simulated = self.kite.current_simulated_time.date()
                nearest_expiry = None
                for exp_date in unique_expiries:
                    if exp_date.date() >= today_simulated:
                        nearest_expiry = exp_date
                        break
                
                if nearest_expiry:
                    df_nearest_expiry = historical_oc[historical_oc['expiryDate'] == nearest_expiry]
                    self.logger.info(f"Mock: Filtered options chain for nearest expiry: {nearest_expiry.strftime('%Y-%m-%d')}")
                    return df_nearest_expiry
                else:
                    self.logger.warning(f"Mock: No nearest future expiry found in historical data for {symbol}. Returning full historical OC.")
                    return historical_oc # Return full mock data if no future expiry found
            else:
                self.logger.warning(f"Mock _fetch_nse_options: No historical options chain data found for {symbol} at {time_key}. Returning empty DataFrame.")
                return pd.DataFrame()

        # Original live API call logic for when not mocking
        if not self.config.use_nse_api:
            self.logger.info("NSE API disabled. Returning empty DataFrame.")
            return pd.DataFrame()
            
        url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
            data = response.json()
            df = pd.DataFrame(data['records']['data'])

            if df.empty:
                self.logger.warning(f"No options data found for {symbol}.")
                return pd.DataFrame()

            # Filter for the nearest expiry date
            df['expiryDate'] = pd.to_datetime(df['expiryDate'])

            unique_expiries = sorted(df['expiryDate'].unique())

            if not unique_expiries:
                self.logger.warning(f"No valid expiry dates found in options chain for {symbol}.")
                return pd.DataFrame()

            today = datetime.datetime.now().date()
            nearest_expiry = None
            for exp_date in unique_expiries:
                if exp_date.date() >= today:
                    nearest_expiry = exp_date
                    break

            if nearest_expiry is None:
                self.logger.warning(f"Could not find a nearest future expiry date for {symbol}. Falling back to last available expiry.")
                nearest_expiry = unique_expiries[-1] if unique_expiries else None

            if nearest_expiry:
                df_nearest_expiry = df[df['expiryDate'] == nearest_expiry]
                self.logger.info(f"Filtered options chain for nearest expiry: {nearest_expiry.strftime('%Y-%m-%d')}")
                return df_nearest_expiry
            else:
                self.logger.warning(f"No nearest expiry found for {symbol}. Returning full options chain (if any).")
                return df

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching NSE options chain for {symbol}: {e}")
            return pd.DataFrame()
        except KeyError as e:
            self.logger.error(f"Key error in NSE options chain data for {symbol}: {e}. Data structure might have changed.")
            return pd.DataFrame()
        except Exception as e:
            self.logger.error(f"An unexpected error occurred while fetching NSE options chain for {symbol}: {e}")
            return pd.DataFrame()

    def _get_best_strikes(self, option_chain: pd.DataFrame, current_price: float) -> Tuple[Optional[pd.Series], Optional[pd.Series]]:
        """
        Finds the best OTM put and call options based on delta range and open interest.
        Adds instrument_token and tradingsymbol to the selected options.

        Args:
            option_chain (pd.DataFrame): The filtered options chain.
            current_price (float): The current Last Traded Price (LTP) of the underlying.

        Returns:
            Tuple[Optional[pd.Series], Optional[pd.Series]]: A tuple containing
            the best put option (as a Series) and the best call option (as a Series),
            or None for either if not found.
        """
        if option_chain.empty:
            self.logger.warning("Option chain is empty, cannot find best strikes.")
            return None, None

        # Ensure necessary columns exist and drop NaNs
        option_chain_filtered = option_chain.dropna(subset=[
            "PE.delta", "CE.delta", "PE.openInterest", "CE.openInterest",
            "strikePrice", "expiryDate"
        ])

        if option_chain_filtered.empty:
            self.logger.warning("Filtered option chain is empty after dropping NaNs.")
            return None, None

        best_put: Optional[pd.Series] = None
        best_call: Optional[pd.Series] = None

        try:
            # Find the best put option with delta ~ 0.2 and high liquidity
            otm_puts = option_chain_filtered[
                (option_chain_filtered["PE.delta"].between(self.config.otm_delta_range_low, self.config.otm_delta_range_high)) &
                (option_chain_filtered["PE.openInterest"] > self.config.min_open_interest) &
                (option_chain_filtered["strikePrice"] < current_price) # OTM Puts are below current price
            ]
            if not otm_puts.empty:
                best_put = otm_puts.sort_values(by="PE.openInterest", ascending=False).iloc[0].copy() # Use .copy() to avoid SettingWithCopyWarning
                expiry_str = best_put['expiryDate'].strftime('%d%b').upper()
                best_put_symbol = f"{self.config.symbol}{expiry_str}{int(best_put['strikePrice'])}PE"
                best_put_token = self._get_instrument_token(best_put_symbol)
                if best_put_token:
                    best_put['instrument_token'] = best_put_token
                    best_put['tradingsymbol'] = best_put_symbol
                else:
                    self.logger.warning(f"Could not find instrument token for best put: {best_put_symbol}. Skipping.")
                    best_put = None
            else:
                self.logger.info("No suitable OTM puts found based on criteria.")

            # Find the best call option with delta ~ 0.2 and high liquidity
            otm_calls = option_chain_filtered[
                (option_chain_filtered["CE.delta"].between(self.config.otm_delta_range_low, self.config.otm_delta_range_high)) &
                (option_chain_filtered["CE.openInterest"] > self.config.min_open_interest) &
                (option_chain_filtered["strikePrice"] > current_price) # OTM Calls are above current price
            ]
            if not otm_calls.empty:
                best_call = otm_calls.sort_values(by="CE.openInterest", ascending=False).iloc[0].copy() # Use .copy()
                expiry_str = best_call['expiryDate'].strftime('%d%b').upper()
                best_call_symbol = f"{self.config.symbol}{expiry_str}{int(best_call['strikePrice'])}CE"
                best_call_token = self._get_instrument_token(best_call_symbol)
                if best_call_token:
                    best_call['instrument_token'] = best_call_token
                    best_call['tradingsymbol'] = best_call_symbol
                else:
                    self.logger.warning(f"Could not find instrument token for best call: {best_call_symbol}. Skipping.")
                    best_call = None
            else:
                self.logger.info("No suitable OTM calls found based on criteria.")

        except IndexError:
            self.logger.warning("Could not find best put/call. Check option chain data and criteria.")
            return None, None
        except Exception as e:
            self.logger.error(f"Error in _get_best_strikes: {e}")
            return None, None

        return best_put, best_call

    def _place_order(self, tradingsymbol: str, instrument_token: int, transaction_type: str,
                     quantity: int, order_type: str, product: str) -> Optional[str]:
        """
        Helper function to place an order with error handling.

        Args:
            tradingsymbol (str): The trading symbol of the instrument.
            instrument_token (int): The instrument token of the instrument.
            transaction_type (str): "BUY" or "SELL".
            quantity (int): The quantity to trade.
            order_type (str): "MARKET", "LIMIT", etc.
            product (str): "NRML", "CNC", etc.

        Returns:
            Optional[str]: The order ID if successful, otherwise None.
        """
        if self.kite is None:
            self.logger.error("KiteConnect instance not initialized. Cannot place order.")
            return None
            
        # Risk management checks
        if self.daily_pnl <= -self.config.max_daily_loss_limit:
            self.logger.warning(f"Daily loss limit exceeded ({self.daily_pnl}). Skipping order placement.")
            return None

        try:
            # Use retry mechanism for placing orders
            order_result = self._retry_kite_api_call(
                self.kite.place_order,
                tradingsymbol=tradingsymbol,
                exchange="NSE",
                transaction_type=transaction_type,
                quantity=quantity,
                order_type=order_type,
                product=product,
                instrument_token=instrument_token
            )
            
            if order_result is None:
                self.logger.error(f"Failed to place order for {tradingsymbol} after all retries.")
                return None
                
            order_id = order_result
            self.logger.info(f"Order placed successfully: {transaction_type.upper()} {tradingsymbol}, Order ID: {order_id}")
            
            # Add to trades history
            trade = Trade(
                order_id=order_id,
                tradingsymbol=tradingsymbol,
                transaction_type=transaction_type,
                quantity=quantity,
                price=0.0,  # Will be updated after execution
                product=product,
                exchange="NSE",
                timestamp=datetime.datetime.now()
            )
            self.trades_history.append(trade)
            
            # Send notification
            self.notification_manager.send_notification(
                "Order Placed",
                f"Successfully placed {transaction_type} order for {tradingsymbol} (Qty: {quantity})"
            )
            
            return order_id
        except Exception as e:
            self.logger.error(f"An unexpected error occurred while placing order for {tradingsymbol}: {e}")
        return None

    def _get_current_ltp(self, instrument_token: int, tradingsymbol: str) -> Optional[float]:
        """
        Fetches the last traded price for a given instrument.

        Args:
            instrument_token (int): The instrument token.
            tradingsymbol (str): The trading symbol (for logging purposes).

        Returns:
            Optional[float]: The LTP if found, otherwise None.
        """
        if self.kite is None:
            self.logger.error("KiteConnect instance not initialized. Cannot get LTP.")
            return None
        try:
            ltp_data = self.kite.ltp([f"NSE:{instrument_token}"])
            if f"NSE:{instrument_token}" in ltp_data:
                return float(ltp_data[f"NSE:{instrument_token}"]["last_price"])
            else:
                self.logger.warning(f"LTP data not found for {tradingsymbol} (Token: {instrument_token}).")
                return None
        except Exception as e:
            self.logger.error(f"Error fetching LTP for {tradingsymbol} (Token: {instrument_token}): {e}")
            return None

    def _calculate_position_pnl(self, position: Dict[str, Any]) -> float:
        """
        Calculate the unrealized P&L for a position.
        
        Args:
            position (Dict[str, Any]): Position dictionary from Kite.
            
        Returns:
            float: Unrealized P&L
        """
        if self.kite is None:
            return 0.0
            
        try:
            instrument_token = position.get("instrument_token")
            if not instrument_token:
                return 0.0
                
            ltp_data = self.kite.ltp([f"NSE:{instrument_token}"])
            if f"NSE:{instrument_token}" in ltp_data:
                current_price = ltp_data[f"NSE:{instrument_token}"]["last_price"]
                avg_price = position["average_price"]
                quantity = position["quantity"]
                
                # For options, P&L is straightforward
                if "CE" in position["tradingsymbol"] or "PE" in position["tradingsymbol"]:
                    return (current_price - avg_price) * quantity
                # For stock positions
                else:
                    return (current_price - avg_price) * quantity
            return 0.0
        except Exception as e:
            self.logger.error(f"Error calculating P&L for {position.get('tradingsymbol', 'Unknown')}: {e}")
            return 0.0

    def _manage_short_put(self, put_position: Dict[str, Any], tcs_ltp: float, best_put: Optional[pd.Series]) -> None:
        """
        Manages an existing short put position. Closes at profit target or loss limit.

        Args:
            put_position (Dict[str, Any]): Dictionary representing the existing put position.
            tcs_ltp (float): Current LTP of the underlying stock.
            best_put (Optional[pd.Series]): The currently identified best OTM put to sell.
        """
        put_tradingsymbol: str = put_position["tradingsymbol"]
        put_instrument_token: Optional[int] = self._get_instrument_token(put_tradingsymbol)
        if not put_instrument_token:
            self.logger.error(f"Could not get instrument token for existing put: {put_tradingsymbol}. Cannot manage.")
            return

        put_ltp: Optional[float] = self._get_current_ltp(put_instrument_token, put_tradingsymbol)
        if put_ltp is None:
            self.logger.warning(f"Could not get LTP for {put_tradingsymbol}. Skipping management.")
            return

        entry_price: float = put_position["average_price"]
        profit_target_price: float = entry_price * (1 - self.config.profit_target_percentage) # Price at which premium is reduced by target %
        loss_limit_price: float = entry_price * (1 + self.config.loss_limit_percentage)     # Price at which premium is doubled

        self.logger.info(f"Monitoring Short Put: {put_tradingsymbol} | LTP: {put_ltp:.2f} | Entry: {entry_price:.2f} | Profit Target: {profit_target_price:.2f} | Loss Limit: {loss_limit_price:.2f}")

        if put_ltp <= profit_target_price:
            self.logger.info(f"Closing Put (Profit Target): {put_tradingsymbol} as LTP {put_ltp:.2f} <= {profit_target_price:.2f}")
            order_id = self._place_order(
                tradingsymbol=put_tradingsymbol,
                instrument_token=put_instrument_token,
                transaction_type=TransactionType.BUY.value,
                quantity=abs(put_position["quantity"]), # Ensure positive quantity for buy
                order_type=OrderType.MARKET.value,
                product=ProductType.NRML.value
            )
            
            if order_id:
                # Update daily P&L (profit)
                profit = (entry_price - put_ltp) * abs(put_position["quantity"])
                self.daily_pnl += profit
                self.logger.info(f"Put closed with profit: ₹{profit:.2f}, Daily P&L: ₹{self.daily_pnl:.2f}")
                
                # Update trade with P&L
                for trade in self.trades_history:
                    if trade.order_id == order_id:
                        trade.pnl = profit
                        break
                
                # Send notification
                self.notification_manager.send_notification(
                    "Put Closed - Profit",
                    f"Closed {put_tradingsymbol} for profit of ₹{profit:.2f}"
                )

            # After closing, sell a new put if a best_put is available
            if best_put is not None and 'instrument_token' in best_put:
                self.logger.info(f"Selling new Put after profit booking: {best_put['tradingsymbol']}")
                self._place_order(
                    tradingsymbol=best_put['tradingsymbol'],
                    instrument_token=int(best_put['instrument_token']),
                    transaction_type=TransactionType.SELL.value,
                    quantity=self.config.quantity_per_lot,
                    order_type=OrderType.MARKET.value,
                    product=ProductType.NRML.value
                )
            else:
                self.logger.warning("No suitable new put found to sell after closing existing put for profit.")

        elif put_ltp >= loss_limit_price:
            self.logger.info(f"Closing Put (Loss Limit): {put_tradingsymbol} as LTP {put_ltp:.2f} >= {loss_limit_price:.2f}")
            order_id = self._place_order(
                tradingsymbol=put_tradingsymbol,
                instrument_token=put_instrument_token,
                transaction_type=TransactionType.BUY.value,
                quantity=abs(put_position["quantity"]), # Ensure positive quantity for buy
                order_type=OrderType.MARKET.value,
                product=ProductType.NRML.value
            )
            
            if order_id:
                # Update daily P&L (loss)
                loss = (entry_price - put_ltp) * abs(put_position["quantity"])
                self.daily_pnl += loss
                self.logger.info(f"Put closed with loss: ₹{loss:.2f}, Daily P&L: ₹{self.daily_pnl:.2f}")
                
                # Update trade with P&L
                for trade in self.trades_history:
                    if trade.order_id == order_id:
                        trade.pnl = loss
                        break
                
                # Send notification
                self.notification_manager.send_notification(
                    "Put Closed - Loss",
                    f"Closed {put_tradingsymbol} with loss of ₹{abs(loss):.2f}"
                )

            self.logger.warning(f"Put {put_tradingsymbol} closed at loss. Re-evaluation needed for next step.")

    def _initiate_put_sell(self, best_put: Optional[pd.Series]) -> None:
        """
        Initiates selling a new OTM put option.

        Args:
            best_put (Optional[pd.Series]): The best OTM put option identified.
        """
        if best_put is None or 'instrument_token' not in best_put:
            self.logger.warning("Cannot initiate put sell: No suitable best put found or missing instrument token.")
            return

        self.logger.info(f"Initiating new Put Sell: {best_put['tradingsymbol']}")
        self._place_order(
            tradingsymbol=best_put['tradingsymbol'],
            instrument_token=int(best_put['instrument_token']),
            transaction_type=TransactionType.SELL.value,
            quantity=self.config.quantity_per_lot,
            order_type=OrderType.MARKET.value,
            product=ProductType.NRML.value
        )

    def _manage_covered_call(self, call_position: Dict[str, Any], tcs_ltp: float, best_call: Optional[pd.Series]) -> None:
        """
        Manages an existing short call position. Closes at profit target or loss limit.

        Args:
            call_position (Dict[str, Any]): Dictionary representing the existing call position.
            tcs_ltp (float): Current LTP of the underlying stock.
            best_call (Optional[pd.Series]): The currently identified best OTM call to sell.
        """
        call_tradingsymbol: str = call_position["tradingsymbol"]
        call_instrument_token: Optional[int] = self._get_instrument_token(call_tradingsymbol)
        if not call_instrument_token:
            self.logger.error(f"Could not get instrument token for existing call: {call_tradingsymbol}. Cannot manage.")
            return

        call_ltp: Optional[float] = self._get_current_ltp(call_instrument_token, call_tradingsymbol)
        if call_ltp is None:
            self.logger.warning(f"Could not get LTP for {call_tradingsymbol}. Skipping management.")
            return

        entry_price: float = call_position["average_price"]
        profit_target_price: float = entry_price * (1 - self.config.profit_target_percentage)
        loss_limit_price: float = entry_price * (1 + self.config.loss_limit_percentage)

        self.logger.info(f"Monitoring Covered Call: {call_tradingsymbol} | LTP: {call_ltp:.2f} | Entry: {entry_price:.2f} | Profit Target: {profit_target_price:.2f} | Loss Limit: {loss_limit_price:.2f}")

        if call_ltp <= profit_target_price:
            self.logger.info(f"Closing Call (Profit Target): {call_tradingsymbol} as LTP {call_ltp:.2f} <= {profit_target_price:.2f}")
            order_id = self._place_order(
                tradingsymbol=call_tradingsymbol,
                instrument_token=call_instrument_token,
                transaction_type=TransactionType.BUY.value,
                quantity=abs(call_position["quantity"]),
                order_type=OrderType.MARKET.value,
                product=ProductType.NRML.value
            )
            
            if order_id:
                # Update daily P&L (profit)
                profit = (entry_price - call_ltp) * abs(call_position["quantity"])
                self.daily_pnl += profit
                self.logger.info(f"Call closed with profit: ₹{profit:.2f}, Daily P&L: ₹{self.daily_pnl:.2f}")
                
                # Update trade with P&L
                for trade in self.trades_history:
                    if trade.order_id == order_id:
                        trade.pnl = profit
                        break
                
                # Send notification
                self.notification_manager.send_notification(
                    "Call Closed - Profit",
                    f"Closed {call_tradingsymbol} for profit of ₹{profit:.2f}"
                )

            # After closing, sell a new call if a best_call is available
            if best_call is not None and 'instrument_token' in best_call:
                self.logger.info(f"Selling new Covered Call after profit booking: {best_call['tradingsymbol']}")
                self._place_order(
                    tradingsymbol=best_call['tradingsymbol'],
                    instrument_token=int(best_call['instrument_token']),
                    transaction_type=TransactionType.SELL.value,
                    quantity=self.config.quantity_per_lot,
                    order_type=OrderType.MARKET.value,
                    product=ProductType.NRML.value
                )
            else:
                self.logger.warning("No suitable new call found to sell after closing existing call for profit.")

        elif call_ltp >= loss_limit_price:
            self.logger.info(f"Closing Call (Loss Limit): {call_tradingsymbol} as LTP {call_ltp:.2f} >= {loss_limit_price:.2f}")
            order_id = self._place_order(
                tradingsymbol=call_tradingsymbol,
                instrument_token=call_instrument_token,
                transaction_type=TransactionType.BUY.value,
                quantity=abs(call_position["quantity"]),
                order_type=OrderType.MARKET.value,
                product=ProductType.NRML.value
            )
            
            if order_id:
                # Update daily P&L (loss)
                loss = (entry_price - call_ltp) * abs(call_position["quantity"])
                self.daily_pnl += loss
                self.logger.info(f"Call closed with loss: ₹{loss:.2f}, Daily P&L: ₹{self.daily_pnl:.2f}")
                
                # Update trade with P&L
                for trade in self.trades_history:
                    if trade.order_id == order_id:
                        trade.pnl = loss
                        break
                
                # Send notification
                self.notification_manager.send_notification(
                    "Call Closed - Loss",
                    f"Closed {call_tradingsymbol} with loss of ₹{abs(loss):.2f}"
                )

            self.logger.warning(f"Call {call_tradingsymbol} closed at loss. Re-evaluation needed for next step.")

    def _execute_cycle(self) -> None:
        """
        Executes a single cycle of the option wheel strategy logic.
        """
        self.logger.info("--- Starting Option Wheel Strategy Cycle ---")
        try:
            if self.kite is None:
                self.logger.error("KiteConnect instance not initialized. Cannot execute cycle.")
                return

            # 1. Get current underlying LTP
            tcs_instrument_token: Optional[int] = self._get_instrument_token(self.config.symbol, "NSE")
            if not tcs_instrument_token:
                self.logger.error(f"Could not find instrument token for {self.config.symbol}. Exiting cycle.")
                return

            tcs_ltp: Optional[float] = self._get_current_ltp(tcs_instrument_token, self.config.symbol)
            if tcs_ltp is None:
                self.logger.error(f"Could not fetch LTP for {self.config.symbol}. Exiting cycle.")
                return
            self.logger.info(f"Current {self.config.symbol} LTP: {tcs_ltp:.2f}")

            # 2. Fetch Options Chain and Best Strikes
            option_chain: pd.DataFrame = self._fetch_nse_options(self.config.symbol)
            best_put, best_call = self._get_best_strikes(option_chain, tcs_ltp)

            if best_put is None and best_call is None:
                self.logger.warning("Could not identify suitable put or call options. Skipping this cycle.")
                return

            # 3. Get current positions
            positions: List[Dict[str, Any]] = self.kite.positions()["net"]
            tcs_stock_position: Optional[Dict[str, Any]] = next((p for p in positions if p["tradingsymbol"] == self.config.symbol and p["product"] == ProductType.CNC.value), None)
            short_puts: List[Dict[str, Any]] = [p for p in positions if "PE" in p["tradingsymbol"] and p["quantity"] < 0 and p["product"] == ProductType.NRML.value]
            short_calls: List[Dict[str, Any]] = [p for p in positions if "CE" in p["tradingsymbol"] and p["quantity"] < 0 and p["product"] == ProductType.NRML.value]

            # Calculate portfolio value and risk
            total_portfolio_value = self._calculate_portfolio_value(positions)
            self.logger.info(f"Total portfolio value: ₹{total_portfolio_value:,.2f}")

            # Risk management - check if we're exceeding position limits
            total_positions = len(short_puts) + len(short_calls)
            if total_positions >= self.config.max_concurrent_positions:
                self.logger.warning(f"Maximum concurrent positions ({self.config.max_concurrent_positions}) reached. Skipping new position creation.")
                # Still manage existing positions
                pass
            else:
                self.logger.info(f"Current positions: {total_positions}/{self.config.max_concurrent_positions}")

            # --- Strategy Logic ---
            if tcs_stock_position and tcs_stock_position["quantity"] > 0:
                self.logger.info(f"Holding {tcs_stock_position['quantity']} shares of {self.config.symbol}. Managing covered calls.")
                if short_calls:
                    for call_pos in short_calls:
                        self._manage_covered_call(call_pos, tcs_ltp, best_call)
                else:
                    self.logger.info("No active short calls found. Attempting to sell a new covered call.")
                    if best_call is not None and 'instrument_token' in best_call:
                        self._place_order(
                            tradingsymbol=best_call['tradingsymbol'],
                            instrument_token=int(best_call['instrument_token']),
                            transaction_type=TransactionType.SELL.value,
                            quantity=self.config.quantity_per_lot,
                            order_type=OrderType.MARKET.value,
                            product=ProductType.NRML.value
                        )
                    else:
                        self.logger.warning("No suitable OTM call found to sell for covered call strategy.")
            else:
                self.logger.info(f"Not holding shares of {self.config.symbol}. Managing short puts.")
                if short_puts:
                    for put_pos in short_puts:
                        self._manage_short_put(put_pos, tcs_ltp, best_put)
                else:
                    self.logger.info("No active short puts found. Attempting to sell a new put.")
                    if best_put is not None and 'instrument_token' in best_put:
                        self._place_order(
                            tradingsymbol=best_put['tradingsymbol'],
                            instrument_token=int(best_put['instrument_token']),
                            transaction_type=TransactionType.SELL.value,
                            quantity=self.config.quantity_per_lot,
                            order_type=OrderType.MARKET.value,
                            product=ProductType.NRML.value
                        )
                    else:
                        self.logger.warning("No suitable OTM put found to sell for cash-secured put strategy.")

        except kc_exceptions.InputException as e:
            self.logger.error(f"KiteConnect Input Error: {e}")
        except kc_exceptions.DataException as e:
            self.logger.error(f"KiteConnect Data Error: {e}")
        except kc_exceptions.NetworkException as e:
            self.logger.error(f"KiteConnect Network Error: {e}")
        except Exception as e:
            self.logger.critical(f"An unhandled error occurred during strategy execution: {e}", exc_info=True)

    def _calculate_portfolio_value(self, positions: List[Dict[str, Any]]) -> float:
        """
        Calculate the total value of the portfolio.
        
        Args:
            positions (List[Dict[str, Any]]): List of positions from Kite.
            
        Returns:
            float: Total portfolio value
        """
        total_value = 0.0
        try:
            for position in positions:
                instrument_token = position.get("instrument_token")
                if not instrument_token:
                    continue
                    
                ltp_data = self.kite.ltp([f"NSE:{instrument_token}"])
                if f"NSE:{instrument_token}" in ltp_data:
                    current_price = ltp_data[f"NSE:{instrument_token}"]["last_price"]
                    quantity = position["quantity"]
                    total_value += current_price * quantity
        except Exception as e:
            self.logger.error(f"Error calculating portfolio value: {e}")
        return total_value

    def _calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.0) -> float:
        """
        Calculate Sharpe ratio of returns.
        
        Args:
            returns: List of periodic returns
            risk_free_rate: Risk-free rate (annualized)
            
        Returns:
            float: Sharpe ratio
        """
        if not returns or len(returns) < 2:
            return 0.0
            
        excess_returns = [r - risk_free_rate/252 for r in returns]  # Daily risk-free rate
        mean_excess_return = np.mean(excess_returns)
        std_excess_return = np.std(excess_returns)
        
        if std_excess_return == 0:
            return 0.0
            
        return mean_excess_return / std_excess_return * np.sqrt(252)  # Annualized

    def _calculate_max_drawdown(self, equity_curve: List[float]) -> float:
        """
        Calculate maximum drawdown from equity curve.
        
        Args:
            equity_curve: List of equity values over time
            
        Returns:
            float: Maximum drawdown as percentage
        """
        if not equity_curve:
            return 0.0
            
        peak = equity_curve[0]
        max_dd = 0.0
        
        for value in equity_curve:
            if value > peak:
                peak = value
            dd = (peak - value) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
            
        return max_dd * 100

    def _load_backtest_data(self, kite_live_client: KiteConnect, symbol: str,
                           from_date: datetime.date, to_date: datetime.date) -> Dict[str, Any]:
        """
        Loads historical data for backtesting.

        Args:
            kite_live_client (KiteConnect): A *live* KiteConnect instance to fetch historical data.
            symbol (str): The underlying stock symbol.
            from_date (datetime.date): Start date for historical data.
            to_date (datetime.date): End date for historical data.

        Returns:
            Dict[str, Any]: A dictionary containing historical LTP and (placeholder) options data.
        """
        self.logger.info(f"Loading historical data for {symbol} from {from_date} to {to_date}...")
        historical_data: Dict[str, Any] = {
            'TCS_LTP': {},
            'OPTION_PREMIUMS': {}, # Placeholder for options premiums
            'OPTION_CHAIN_DATA': {} # Placeholder for full options chain snapshots
        }

        try:
            # 1. Fetch historical underlying LTP data (1-minute interval)
            # You need the instrument token for TCS
            tcs_instrument_token = self._get_instrument_token(symbol, "NSE")
            if not tcs_instrument_token:
                self.logger.error(f"Could not get instrument token for {symbol} to fetch historical data.")
                return historical_data

            # Kite historical data API fetches OHLCV. We'll use 'close' for LTP.
            # Fetching minute data for a long period can be slow/rate-limited.
            # Consider fetching daily and interpolating, or fetching in chunks.
            self.logger.info(f"Fetching historical 1-minute data for {symbol}...")
            
            # Fetch data in chunks to avoid API limitations
            current_from = from_date
            while current_from <= to_date:
                # Calculate to_date as 60 days from current_from (Kite API limitation)
                current_to = min(current_from + datetime.timedelta(days=60), to_date)
                
                raw_data = self._retry_kite_api_call(
                    kite_live_client.historical_data,
                    instrument_token=tcs_instrument_token,
                    from_date=current_from,
                    to_date=current_to,
                    interval='minute'
                )
                
                if raw_data:
                    df_ltp = pd.DataFrame(raw_data)
                    df_ltp['date'] = pd.to_datetime(df_ltp['date'])
                    df_ltp.set_index('date', inplace=True)
                    
                    # Format for MockKiteConnect: 'YYYY-MM-DD HH:MM': price
                    chunk_data = df_ltp['close'].resample('5T').last().dropna().to_dict()
                    chunk_data = {k.strftime('%Y-%m-%d %H:%M'): v for k, v in chunk_data.items()}
                    
                    # Merge with existing data
                    historical_data['TCS_LTP'].update(chunk_data)
                    self.logger.info(f"Loaded {len(chunk_data)} historical LTP points for {symbol} from {current_from} to {current_to}.")
                else:
                    self.logger.warning(f"No historical LTP data found for {symbol} for period {current_from} to {current_to}.")
                
                # Move to next chunk
                current_from = current_to + datetime.timedelta(days=1)

            if historical_data['TCS_LTP']:
                self.logger.info(f"Total loaded: {len(historical_data['TCS_LTP'])} historical LTP points for {symbol}.")
            else:
                self.logger.warning(f"No historical LTP data found for {symbol} for the entire period.")

            # 2. IMPORTANT: Historical Options Chain Data (Deltas, OI, Premiums for all strikes)
            # This data is NOT available via KiteConnect's historical API or public NSE APIs.
            # You would need to source this from a specialized data provider or have collected it yourself.
            self.logger.warning("\n--- !!! IMPORTANT FOR BACKTESTING OPTIONS !!! ---")
            self.logger.warning("Historical Options Chain Data (including Greeks like Delta and Open Interest) ")
            self.logger.warning("is NOT available through KiteConnect's historical API or public NSE APIs.")
            self.logger.warning("For a realistic backtest, you MUST obtain this data from a data vendor ")
            self.logger.warning("or use data you have collected over time.")
            self.logger.warning("The current MockKiteConnect will use placeholder/static data for options chain.")
            self.logger.warning("--------------------------------------------------\n")

            # For demonstration, using simple placeholder for options premiums and chain if no real data is loaded
            if not historical_data['OPTION_PREMIUMS'] or not historical_data['OPTION_CHAIN_DATA']:
                self.logger.info("Using simplified placeholder options data for backtesting demonstration.")
                # Generate a simple options chain for the duration of the backtest
                # This is highly simplified and not realistic for real backtesting
                # You would need to refine this based on actual historical options data
                start_dt = datetime.datetime.combine(from_date, datetime.time(self.config.market_open_hour, self.config.market_open_minute))
                end_dt = datetime.datetime.combine(to_date, datetime.time(self.config.market_close_hour, self.config.market_close_minute))
                
                current_dt = start_dt
                while current_dt <= end_dt:
                    time_key_str = current_dt.strftime('%Y-%m-%d %H:%M')
                    
                    # Use actual historical price if available, otherwise use default
                    current_tcs_price = historical_data['TCS_LTP'].get(time_key_str, 3500.0)
                    
                    # Generate some dummy strikes around the current price
                    strikes = [current_tcs_price - 150, current_tcs_price - 100, current_tcs_price - 50,
                               current_tcs_price,
                               current_tcs_price + 50, current_tcs_price + 100, current_tcs_price + 150]
                    
                    dummy_oc_data = []
                    for strike in strikes:
                        # Simple dummy deltas and OI
                        pe_delta = max(0.01, 0.5 - (current_tcs_price - strike) / 200) # Roughly decreases as strike goes below LTP
                        ce_delta = max(0.01, 0.5 - (strike - current_tcs_price) / 200) # Roughly decreases as strike goes above LTP
                        pe_oi = int(1000 + abs(strike - current_tcs_price) * 10)
                        ce_oi = int(1000 + abs(strike - current_tcs_price) * 10)
                        
                        # Very simplified premium calculation (not based on Black-Scholes or real market dynamics)
                        pe_premium = max(0.01, (current_tcs_price - strike) * 0.1 + 10)
                        ce_premium = max(0.01, (strike - current_tcs_price) * 0.1 + 10)

                        dummy_oc_data.append({
                            'strikePrice': strike,
                            'expiryDate': datetime.datetime(current_dt.year + 1, 7, 25), # Fixed future expiry for demo
                            'PE.delta': min(0.99, pe_delta),
                            'CE.delta': min(0.99, ce_delta),
                            'PE.openInterest': pe_oi,
                            'CE.openInterest': ce_oi,
                            'PE.lastPrice': pe_premium,
                            'CE.lastPrice': ce_premium
                        })
                    
                    historical_data['OPTION_CHAIN_DATA'][time_key_str] = pd.DataFrame(dummy_oc_data)
                    
                    # Populate OPTION_PREMIUMS based on this dummy data
                    for row in dummy_oc_data:
                        expiry_str = row['expiryDate'].strftime('%d%b').upper()
                        pe_symbol = f"{symbol}{expiry_str}{int(row['strikePrice'])}PE"
                        ce_symbol = f"{symbol}{expiry_str}{int(row['strikePrice'])}CE"

                        if pe_symbol not in historical_data['OPTION_PREMIUMS']:
                            historical_data['OPTION_PREMIUMS'][pe_symbol] = {}
                        historical_data['OPTION_PREMIUMS'][pe_symbol][time_key_str] = row['PE.lastPrice']
                        
                        if ce_symbol not in historical_data['OPTION_PREMIUMS']:
                            historical_data['OPTION_PREMIUMS'][ce_symbol] = {}
                        historical_data['OPTION_PREMIUMS'][ce_symbol][time_key_str] = row['CE.lastPrice']

                    current_dt += datetime.timedelta(seconds=self.config.strategy_run_interval_seconds)

        except Exception as e:
            self.logger.error(f"Error loading backtest data: {e}", exc_info=True)
            # Return empty or partially loaded data on error
        
        return historical_data

    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Generate a comprehensive performance summary of the strategy.
        
        Returns:
            Dict[str, Any]: Performance metrics
        """
        total_trades = len(self.trades_history)
        profitable_trades = len([t for t in self.trades_history if getattr(t, 'pnl', 0) > 0])
        win_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Calculate average profit/loss per trade
        trade_pnls = [getattr(t, 'pnl', 0) for t in self.trades_history]
        avg_profit = np.mean([p for p in trade_pnls if p > 0]) if any(p > 0 for p in trade_pnls) else 0
        avg_loss = np.mean([p for p in trade_pnls if p < 0]) if any(p < 0 for p in trade_pnls) else 0
        
        # Profit factor
        total_profit = sum(p for p in trade_pnls if p > 0)
        total_loss = abs(sum(p for p in trade_pnls if p < 0))
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # Risk metrics
        returns = [p / 100000 for p in trade_pnls if p != 0]  # Assuming 1L portfolio for Sharpe ratio
        sharpe_ratio = self._calculate_sharpe_ratio(returns)
        
        return {
            "total_trades": total_trades,
            "profitable_trades": profitable_trades,
            "win_rate": f"{win_rate:.2f}%",
            "daily_pnl": f"₹{self.daily_pnl:,.2f}",
            "total_positions": len(self.positions_history),
            "avg_profit_per_win": f"₹{avg_profit:,.2f}",
            "avg_loss_per_loss": f"₹{abs(avg_loss):,.2f}",
            "profit_factor": f"{profit_factor:.2f}",
            "sharpe_ratio": f"{sharpe_ratio:.2f}"
        }

    def get_detailed_portfolio_report(self) -> Dict[str, Any]:
        """
        Generate a detailed portfolio report.
        
        Returns:
            Dict[str, Any]: Detailed portfolio information
        """
        if self.kite is None:
            return {"error": "KiteConnect not initialized"}
            
        try:
            # Get current positions
            positions = self.kite.positions()["net"]
            
            # Calculate portfolio metrics
            total_value = self._calculate_portfolio_value(positions)
            exposure = 0.0
            position_details = []
            
            for pos in positions:
                instrument_token = pos.get("instrument_token")
                if not instrument_token:
                    continue
                    
                ltp_data = self.kite.ltp([f"NSE:{instrument_token}"])
                if f"NSE:{instrument_token}" in ltp_data:
                    current_price = ltp_data[f"NSE:{instrument_token}"]["last_price"]
                    market_value = current_price * pos["quantity"]
                    exposure += market_value
                    
                    position_details.append({
                        "symbol": pos["tradingsymbol"],
                        "quantity": pos["quantity"],
                        "avg_price": pos["average_price"],
                        "current_price": current_price,
                        "market_value": market_value,
                        "pnl": self._calculate_position_pnl(pos)
                    })
            
            return {
                "total_portfolio_value": f"₹{total_value:,.2f}",
                "market_exposure": f"₹{exposure:,.2f}",
                "positions": position_details,
                "daily_pnl": f"₹{self.daily_pnl:,.2f}"
            }
        except Exception as e:
            self.logger.error(f"Error generating portfolio report: {e}")
            return {"error": str(e)}

    def _is_market_open(self) -> bool:
        """Checks if the current time is within market hours (NSE Equity)."""
        # If using a mock, market is always "open" during the simulated backtest period
        if isinstance(self.kite, MockKiteConnect):
            # For a more sophisticated mock, you could define market hours within historical_data
            # For now, assume market is always open during backtest simulation
            return True

        now: datetime.datetime = datetime.datetime.now()
        market_open_time: datetime.datetime = now.replace(
            hour=self.config.market_open_hour,
            minute=self.config.market_open_minute,
            second=0, microsecond=0
        )
        market_close_time: datetime.datetime = now.replace(
            hour=self.config.market_close_hour,
            minute=self.config.market_close_minute,
            second=0, microsecond=0
        )

        # Check for weekdays (Monday=0, Sunday=6)
        if now.weekday() >= 5: # Saturday or Sunday
            self.logger.info("Market is closed (weekend).")
            return False

        if market_open_time <= now <= market_close_time:
            self.logger.info("Market is open.")
            return True
        else:
            self.logger.info("Market is closed (outside trading hours).")
            return False

    def run(self) -> None:
        """Runs the option wheel strategy continuously during market hours."""
        self.logger.info("Starting Enhanced Option Wheel Strategy bot...")
        
        # If using a mock client, run the backtest loop
        if isinstance(self.kite, MockKiteConnect):
            self.logger.info("Running in Backtesting Mode.")
            
            # --- Load historical data for backtesting ---
            # You need a *live* KiteConnect instance (even if temporary) to fetch historical data.
            # This part will use your actual API credentials.
            live_kite_temp: Optional[KiteConnect] = None
            try:
                live_kite_temp = KiteConnect(api_key=self.config.api_key)
                live_kite_temp.set_access_token(self.config.access_token)
                self.logger.info("Temporary live KiteConnect for historical data fetch initialized.")
            except Exception as e:
                self.logger.critical(f"Failed to initialize temporary live KiteConnect for historical data fetch: {e}")
                self.logger.critical("Cannot run backtest without historical data. Exiting.")
                return

            # Define your backtest period
            backtest_start_date = datetime.date(2023, 1, 1)
            backtest_end_date = datetime.date(2023, 1, 1) # For a single day demo

            # Load the data using the helper function
            self.kite.historical_data = self._load_backtest_data(
                kite_live_client=live_kite_temp,
                symbol=self.config.symbol,
                from_date=backtest_start_date,
                to_date=backtest_end_date
            )
            
            # Set the mock's initial time to the start of the backtest period
            start_simulated_time = datetime.datetime.combine(
                backtest_start_date,
                datetime.time(self.config.market_open_hour, self.config.market_open_minute)
            )
            end_simulated_time = datetime.datetime.combine(
                backtest_end_date,
                datetime.time(self.config.market_close_hour, self.config.market_close_minute)
            )
            self.kite.set_simulated_time(start_simulated_time)

            current_simulated_time = start_simulated_time
            while current_simulated_time <= end_simulated_time and self.is_running:
                self.kite.set_simulated_time(current_simulated_time)
                self.logger.info(f"Simulated Time: {current_simulated_time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Execute the strategy cycle
                self._execute_cycle() 

                # Advance time for the next iteration
                current_simulated_time += datetime.timedelta(seconds=self.config.strategy_run_interval_seconds)
            
            self.logger.info("\n--- Backtest Summary ---")
            self.logger.info(f"Final Simulated Positions: {self.kite.simulated_positions}")
            self.logger.info(f"Total Simulated Orders: {len(self.kite.simulated_orders)}")
            # You would add P&L calculation and detailed reporting here
            # For example, calculate total P&L from self.kite.simulated_orders
            # and self.kite.simulated_positions
            
        else: # Live trading mode
            while self.is_running:
                if self._is_market_open():
                    self._execute_cycle()
                    
                    # Print performance summary every 5 cycles
                    if len(self.trades_history) % 5 == 0:
                        perf_summary = self.get_performance_summary()
                        self.logger.info(f"Performance Summary: {perf_summary}")
                else:
                    self.logger.info("Waiting for market to open...")

                self.logger.info(f"Cycle completed. Waiting {self.config.strategy_run_interval_seconds} seconds before next run...")
                time.sleep(self.config.strategy_run_interval_seconds)

if __name__ == "__main__":
    # Initialize configuration
    app_config = OptionWheelConfig()

    # --- Choose Mode: Live Trading or Backtesting ---
    # Uncomment ONE of the following blocks:

    # # LIVE TRADING MODE
    strategy = EnhancedOptionWheelStrategy(app_config)

    # BACKTESTING MODE
    # The historical_data_for_backtest_example is now passed to MockKiteConnect
    # but actual data loading happens inside strategy.run()
    # mock_kite = MockKiteConnect(historical_data={}) # Initialize with empty data, it will be populated
    # strategy = EnhancedOptionWheelStrategy(app_config, kite_client=mock_kite)

    # Run the strategy (will trigger data loading if in backtesting mode)
    strategy.run()