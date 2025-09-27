import requests
import pandas as pd
import numpy as np
import time
import datetime
import logging
import os
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple

from kiteconnect import KiteConnect
from kiteconnect import exceptions as kc_exceptions

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("option_wheel.log"),
                        logging.StreamHandler()
                    ])

@dataclass
class OptionWheelConfig:
    """
    Configuration parameters for the Option Wheel Strategy.
    Sensitive data (API_KEY, API_SECRET, ACCESS_TOKEN) are loaded from environment variables.
    Default values are provided for development/testing if environment variables are not set.
    """
    api_key: str = field(default_factory=lambda: os.getenv("KITE_API_KEY", "YOUR_KITE_API_KEY_DEFAULT"))
    api_secret: str = field(default_factory=lambda: os.getenv("KITE_API_SECRET", "YOUR_KITE_API_SECRET_DEFAULT"))
    access_token: str = field(default_factory=lambda: os.getenv("KITE_ACCESS_TOKEN", "YOUR_KITE_ACCESS_TOKEN_DEFAULT"))
    
    symbol: str = os.getenv("SYMBOL", "TCS")
    quantity_per_lot: int = int(os.getenv("QUANTITY_PER_LOT", 150))
    profit_target_percentage: float = float(os.getenv("PROFIT_TARGET_PERCENTAGE", 0.50))
    loss_limit_percentage: float = float(os.getenv("LOSS_LIMIT_PERCENTAGE", 1.00))
    otm_delta_range_low: float = float(os.getenv("OTM_DELTA_RANGE_LOW", 0.15))
    otm_delta_range_high: float = float(os.getenv("OTM_DELTA_RANGE_HIGH", 0.25))
    min_open_interest: int = int(os.getenv("MIN_OPEN_INTEREST", 1000))
    strategy_run_interval_seconds: int = int(os.getenv("STRATEGY_RUN_INTERVAL_SECONDS", 300))
    market_open_hour: int = int(os.getenv("MARKET_OPEN_HOUR", 9))
    market_open_minute: int = int(os.getenv("MARKET_OPEN_MINUTE", 15))
    market_close_hour: int = int(os.getenv("MARKET_CLOSE_HOUR", 15))
    market_close_minute: int = int(os.getenv("MARKET_CLOSE_MINUTE", 30))

class MockKiteConnect:
    """
    A mock class to simulate KiteConnect API calls for backtesting purposes.
    It provides predefined or historical data instead of making live API requests.
    """
    def __init__(self, historical_data: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
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

class OptionWheelStrategy:
    """
    Implements the Option Wheel Strategy using Zerodha KiteConnect.

    The strategy involves:
    1. Selling Out-of-the-Money (OTM) Cash-Secured Puts.
    2. If assigned (stock delivered), selling OTM Covered Calls.
    3. Managing existing positions (profit booking, stop-loss).
    """

    # Constants for clarity and avoiding magic strings
    EXCHANGE_NSE: str = "NSE"
    PRODUCT_NRML: str = "NRML"
    PRODUCT_CNC: str = "CNC"
    TRANSACTION_TYPE_BUY: str = "BUY"
    TRANSACTION_TYPE_SELL: str = "SELL"
    ORDER_TYPE_MARKET: str = "MARKET"

    def __init__(self, config: OptionWheelConfig, kite_client: Optional[Any] = None):
        """
        Initializes the OptionWheelStrategy with provided configuration.

        Args:
            config (OptionWheelConfig): Configuration object containing API keys,
                                        strategy parameters, and market timings.
            kite_client (Optional[Any]): An optional KiteConnect client instance.
                                         Used for dependency injection during testing/mocking.
        """
        self.config = config
        self.kite = kite_client
        self.instruments_df: Optional[pd.DataFrame] = None
        self.logger = logging.getLogger(__name__)

        # Only initialize real KiteConnect if a mock client is not provided
        if self.kite is None:
            self._init_kite()
        
        # Always fetch instruments, whether from real API or mock
        self._fetch_all_instruments()

    def _init_kite(self) -> None:
        """
        Initializes the KiteConnect object.
        ACCESS_TOKEN needs to be obtained dynamically after a successful login.
        For a production setup, you would typically have a web server that handles the
        login redirect and stores the access token securely.
        For a script, you'll need to manually get the request_token from the redirect URL
        after navigating to kite.login_url() in your browser, and then generate the access token.

        Example of manual access token generation (run this once to get the token):
        # from kiteconnect import KiteConnect
        # kite_temp = KiteConnect(api_key=self.config.api_key)
        # print(kite_temp.login_url()) # Open this URL in browser, login, copy request_token from redirect URL
        # request_token = "YOUR_REQUEST_TOKEN_FROM_BROWSER_REDIRECT"
        # data = kite_temp.generate_session(request_token, api_secret=self.config.api_secret)
        # access_token = data["access_token"]
        # print(f"Generated Access Token: {access_token}")
        # Update your .env file with this value for KITE_ACCESS_TOKEN.
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
        try:
            order_id = self.kite.place_order(
                tradingsymbol=tradingsymbol,
                exchange=self.EXCHANGE_NSE,
                transaction_type=transaction_type,
                quantity=quantity,
                order_type=order_type,
                product=product,
                instrument_token=instrument_token
            )
            self.logger.info(f"Order placed successfully: {transaction_type.upper()} {tradingsymbol}, Order ID: {order_id}")
            return order_id
        except kc_exceptions.InputException as e:
            self.logger.error(f"Input error placing order for {tradingsymbol}: {e}")
        except kc_exceptions.DataException as e:
            self.logger.error(f"Data error placing order for {tradingsymbol}: {e}")
        except kc_exceptions.NetworkException as e:
            self.logger.error(f"Network error placing order for {tradingsymbol}: {e}")
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
            ltp_data = self.kite.ltp([f"{self.EXCHANGE_NSE}:{instrument_token}"])
            if f"{self.EXCHANGE_NSE}:{instrument_token}" in ltp_data:
                return float(ltp_data[f"{self.EXCHANGE_NSE}:{instrument_token}"]["last_price"])
            else:
                self.logger.warning(f"LTP data not found for {tradingsymbol} (Token: {instrument_token}).")
                return None
        except Exception as e:
            self.logger.error(f"Error fetching LTP for {tradingsymbol} (Token: {instrument_token}): {e}")
            return None

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
            self._place_order(
                tradingsymbol=put_tradingsymbol,
                instrument_token=put_instrument_token,
                transaction_type=self.TRANSACTION_TYPE_BUY,
                quantity=abs(put_position["quantity"]), # Ensure positive quantity for buy
                order_type=self.ORDER_TYPE_MARKET,
                product=self.PRODUCT_NRML
            )
            # After closing, sell a new put if a best_put is available
            if best_put is not None and 'instrument_token' in best_put:
                self.logger.info(f"Selling new Put after profit booking: {best_put['tradingsymbol']}")
                self._place_order(
                    tradingsymbol=best_put['tradingsymbol'],
                    instrument_token=int(best_put['instrument_token']),
                    transaction_type=self.TRANSACTION_TYPE_SELL,
                    quantity=self.config.quantity_per_lot,
                    order_type=self.ORDER_TYPE_MARKET,
                    product=self.PRODUCT_NRML
                )
            else:
                self.logger.warning("No suitable new put found to sell after closing existing put for profit.")

        elif put_ltp >= loss_limit_price:
            self.logger.info(f"Closing Put (Loss Limit): {put_tradingsymbol} as LTP {put_ltp:.2f} >= {loss_limit_price:.2f}")
            self._place_order(
                tradingsymbol=put_tradingsymbol,
                instrument_token=put_instrument_token,
                transaction_type=self.TRANSACTION_TYPE_BUY,
                quantity=abs(put_position["quantity"]), # Ensure positive quantity for buy
                order_type=self.ORDER_TYPE_MARKET,
                product=self.PRODUCT_NRML
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
            transaction_type=self.TRANSACTION_TYPE_SELL,
            quantity=self.config.quantity_per_lot,
            order_type=self.ORDER_TYPE_MARKET,
            product=self.PRODUCT_NRML
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
            self._place_order(
                tradingsymbol=call_tradingsymbol,
                instrument_token=call_instrument_token,
                transaction_type=self.TRANSACTION_TYPE_BUY,
                quantity=abs(call_position["quantity"]),
                order_type=self.ORDER_TYPE_MARKET,
                product=self.PRODUCT_NRML
            )
            # After closing, sell a new call if a best_call is available
            if best_call is not None and 'instrument_token' in best_call:
                self.logger.info(f"Selling new Covered Call after profit booking: {best_call['tradingsymbol']}")
                self._place_order(
                    tradingsymbol=best_call['tradingsymbol'],
                    instrument_token=int(best_call['instrument_token']),
                    transaction_type=self.TRANSACTION_TYPE_SELL,
                    quantity=self.config.quantity_per_lot,
                    order_type=self.ORDER_TYPE_MARKET,
                    product=self.PRODUCT_NRML
                )
            else:
                self.logger.warning("No suitable new call found to sell after closing existing call for profit.")

        elif call_ltp >= loss_limit_price:
            self.logger.info(f"Closing Call (Loss Limit): {call_tradingsymbol} as LTP {call_ltp:.2f} >= {loss_limit_price:.2f}")
            self._place_order(
                tradingsymbol=call_tradingsymbol,
                instrument_token=call_instrument_token,
                transaction_type=self.TRANSACTION_TYPE_BUY,
                quantity=abs(call_position["quantity"]),
                order_type=self.ORDER_TYPE_MARKET,
                product=self.PRODUCT_NRML
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
            tcs_instrument_token: Optional[int] = self._get_instrument_token(self.config.symbol, self.EXCHANGE_NSE)
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
            tcs_stock_position: Optional[Dict[str, Any]] = next((p for p in positions if p["tradingsymbol"] == self.config.symbol and p["product"] == self.PRODUCT_CNC), None)
            short_puts: List[Dict[str, Any]] = [p for p in positions if "PE" in p["tradingsymbol"] and p["quantity"] < 0 and p["product"] == self.PRODUCT_NRML]
            short_calls: List[Dict[str, Any]] = [p for p in positions if "CE" in p["tradingsymbol"] and p["quantity"] < 0 and p["product"] == self.PRODUCT_NRML]

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
                            transaction_type=self.TRANSACTION_TYPE_SELL,
                            quantity=self.config.quantity_per_lot,
                            order_type=self.ORDER_TYPE_MARKET,
                            product=self.PRODUCT_NRML
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
                            transaction_type=self.TRANSACTION_TYPE_SELL,
                            quantity=self.config.quantity_per_lot,
                            order_type=self.ORDER_TYPE_MARKET,
                            product=self.PRODUCT_NRML
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
            tcs_instrument_token = self._get_instrument_token(symbol, self.EXCHANGE_NSE)
            if not tcs_instrument_token:
                self.logger.error(f"Could not get instrument token for {symbol} to fetch historical data.")
                return historical_data

            # Kite historical data API fetches OHLCV. We'll use 'close' for LTP.
            # Fetching minute data for a long period can be slow/rate-limited.
            # Consider fetching daily and interpolating, or fetching in chunks.
            self.logger.info(f"Fetching historical 1-minute data for {symbol}...")
            raw_data = kite_live_client.historical_data(
                instrument_token=tcs_instrument_token,
                from_date=from_date,
                to_date=to_date,
                interval='minute'
            )
            
            if raw_data:
                df_ltp = pd.DataFrame(raw_data)
                df_ltp['date'] = pd.to_datetime(df_ltp['date'])
                df_ltp.set_index('date', inplace=True)
                
                # Format for MockKiteConnect: 'YYYY-MM-DD HH:MM': price
                historical_data['TCS_LTP'] = df_ltp['close'].resample('5T').last().dropna().to_dict()
                historical_data['TCS_LTP'] = {k.strftime('%Y-%m-%d %H:%M'): v for k, v in historical_data['TCS_LTP'].items()}
                self.logger.info(f"Loaded {len(historical_data['TCS_LTP'])} historical LTP points for {symbol}.")
            else:
                self.logger.warning(f"No historical LTP data found for {symbol} for the given period.")

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

            # Placeholder for how you would load this data if you had it
            # Example: Load from a CSV file
            # try:
            #     # Assuming a CSV with columns like: timestamp, strikePrice, expiryDate, PE.delta, CE.delta, PE.openInterest, CE.openInterest, PE.lastPrice, CE.lastPrice
            #     df_options_history = pd.read_csv('path/to/your/historical_options_chain.csv')
            #     df_options_history['timestamp'] = pd.to_datetime(df_options_history['timestamp'])
            #     df_options_history['expiryDate'] = pd.to_datetime(df_options_history['expiryDate'])
            #     
            #     # Group by timestamp to create snapshots
            #     for time_key_dt, group_df in df_options_history.groupby(pd.Grouper(key='timestamp', freq='5T')):
            #         time_key_str = time_key_dt.strftime('%Y-%m-%d %H:%M')
            #         historical_data['OPTION_CHAIN_DATA'][time_key_str] = group_df.drop(columns=['timestamp']).reset_index(drop=True)
            #         
            #         # Also populate OPTION_PREMIUMS for individual strikes
            #         for _, row in group_df.iterrows():
            #             expiry_str = row['expiryDate'].strftime('%d%b').upper()
            #             pe_symbol = f"{symbol}{expiry_str}{int(row['strikePrice'])}PE"
            #             ce_symbol = f"{symbol}{expiry_str}{int(row['strikePrice'])}CE"
            #             
            #             if pe_symbol not in historical_data['OPTION_PREMIUMS']:
            #                 historical_data['OPTION_PREMIUMS'][pe_symbol] = {}
            #             historical_data['OPTION_PREMIUMS'][pe_symbol][time_key_str] = row['PE.lastPrice']
            #             
            #             if ce_symbol not in historical_data['OPTION_PREMIUMS']:
            #                 historical_data['OPTION_PREMIUMS'][ce_symbol] = {}
            #             historical_data['OPTION_PREMIUMS'][ce_symbol][time_key_str] = row['CE.lastPrice']
            #
            #     self.logger.info(f"Loaded historical options chain data from CSV.")
            # except FileNotFoundError:
            #     self.logger.warning("Historical options chain CSV not found. Using placeholder data for options.")
            # except Exception as e:
            #     self.logger.error(f"Error loading historical options chain from CSV: {e}")

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
                    
                    # Simulate a simple options chain based on underlying price
                    # This is a very rough approximation!
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

    def run(self) -> None:
        """Runs the option wheel strategy continuously during market hours."""
        self.logger.info("Starting Option Wheel Strategy bot...")
        
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
            while current_simulated_time <= end_simulated_time:
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
            while True:
                if self._is_market_open():
                    self._execute_cycle()
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
    # strategy = OptionWheelStrategy(app_config)

    # BACKTESTING MODE
    # The historical_data_for_backtest_example is now passed to MockKiteConnect
    # but actual data loading happens inside strategy.run()
    mock_kite = MockKiteConnect(historical_data={}) # Initialize with empty data, it will be populated
    strategy = OptionWheelStrategy(app_config, kite_client=mock_kite)

    # Run the strategy (will trigger data loading if in backtesting mode)
    strategy.run()
