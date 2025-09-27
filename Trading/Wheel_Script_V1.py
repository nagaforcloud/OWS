import requests
import pandas as pd
import numpy as np
import time
import datetime
import logging
from kiteconnect import KiteConnect
from kiteconnect import exceptions as kc_exceptions # Import KiteConnect exceptions

# --- Configuration ---
# It's highly recommended to store these in environment variables or a separate config file
# and load them securely, especially for API keys and secrets.
CONFIG = {
    "API_KEY": "YOUR_KITE_API_KEY",  # Replace with your actual Kite API Key
    "API_SECRET": "YOUR_KITE_API_SECRET",  # Replace with your actual Kite API Secret
    "ACCESS_TOKEN": "YOUR_KITE_ACCESS_TOKEN", # Replace with your actual Kite Access Token after login
                                             # See init_kite() for how to get this.
    "SYMBOL": "TCS",
    "QUANTITY_PER_LOT": 150,  # Standard lot size for TCS options
    "PROFIT_TARGET_PERCENTAGE": 0.50,  # Close at 50% profit
    "LOSS_LIMIT_PERCENTAGE": 1.00,     # Close at 100% loss (i.e., double the premium received)
    "OTM_DELTA_RANGE_LOW": 0.15,
    "OTM_DELTA_RANGE_HIGH": 0.25,
    "MIN_OPEN_INTEREST": 1000,
    "STRATEGY_RUN_INTERVAL_SECONDS": 300, # Run every 5 minutes
    "MARKET_OPEN_HOUR": 9,
    "MARKET_OPEN_MINUTE": 15,
    "MARKET_CLOSE_HOUR": 15,
    "MARKET_CLOSE_MINUTE": 30
}

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("option_wheel.log"),
                        logging.StreamHandler()
                    ])

# Global variable for KiteConnect instance and instruments
kite = None
instruments_df = None

# 1. Setup Zerodha API
def init_kite():
    """
    Initializes the KiteConnect object.
    ACCESS_TOKEN needs to be obtained dynamically after a successful login.
    For a production setup, you would typically have a web server that handles the
    login redirect and stores the access token securely.
    For a script, you'll need to manually get the request_token from the redirect URL
    after navigating to kite.login_url() in your browser, and then generate the access token.

    Example of manual access token generation (run this once to get the token):
    # from kiteconnect import KiteConnect
    # kite = KiteConnect(api_key=CONFIG["API_KEY"])
    # print(kite.login_url()) # Open this URL in browser, login, copy request_token from redirect URL
    # request_token = "YOUR_REQUEST_TOKEN_FROM_BROWSER_REDIRECT"
    # data = kite.generate_session(request_token, api_secret=CONFIG["API_SECRET"])
    # access_token = data["access_token"]
    # print(f"Generated Access Token: {access_token}")
    # Update CONFIG['ACCESS_TOKEN'] with this value.
    """
    global kite
    if kite is None:
        try:
            kite = KiteConnect(api_key=CONFIG["API_KEY"])
            if not CONFIG["ACCESS_TOKEN"] or CONFIG["ACCESS_TOKEN"] == "YOUR_KITE_ACCESS_TOKEN":
                logging.error("ACCESS_TOKEN is not set. Please generate it manually and update CONFIG.")
                raise ValueError("ACCESS_TOKEN not configured.")
            kite.set_access_token(CONFIG["ACCESS_TOKEN"])
            logging.info("KiteConnect initialized successfully.")
            return kite
        except kc_exceptions.TokenException as e:
            logging.error(f"Invalid access token or session expired: {e}")
            raise
        except Exception as e:
            logging.error(f"Error initializing KiteConnect: {e}")
            raise
    return kite

def fetch_all_instruments():
    """Fetches all tradable instruments from KiteConnect."""
    global instruments_df
    if instruments_df is None:
        try:
            logging.info("Fetching all tradable instruments...")
            instruments = kite.instruments()
            instruments_df = pd.DataFrame(instruments)
            logging.info(f"Fetched {len(instruments_df)} instruments.")
        except Exception as e:
            logging.error(f"Error fetching instruments: {e}")
            instruments_df = pd.DataFrame() # Ensure it's a DataFrame even on error
    return instruments_df

def get_instrument_token(tradingsymbol, exchange="NSE"):
    """Looks up instrument token for a given trading symbol."""
    if instruments_df is None or instruments_df.empty:
        fetch_all_instruments() # Try to fetch if not already loaded

    if instruments_df is not None and not instruments_df.empty:
        # For options, tradingsymbol might be like 'TCS24JUL3800CE'
        # For equity, it's 'TCS'
        instrument = instruments_df[
            (instruments_df['tradingsymbol'] == tradingsymbol) &
            (instruments_df['exchange'] == exchange)
        ]
        if not instrument.empty:
            return instrument.iloc[0]['instrument_token']
    logging.warning(f"Instrument token not found for {tradingsymbol} on {exchange}")
    return None

# 2. Fetch TCS Options Chain from NSE API
def fetch_nse_options(symbol):
    """
    Fetches the options chain for a given symbol from NSE India API.
    Filters for the nearest expiry date.
    """
    url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        df = pd.DataFrame(data['records']['data'])

        if df.empty:
            logging.warning(f"No options data found for {symbol}.")
            return pd.DataFrame()

        # Filter for the nearest expiry date
        # Convert expiryDate to datetime objects
        df['expiryDate'] = pd.to_datetime(df['expiryDate'])
        
        # Get unique expiry dates and sort them
        unique_expiries = sorted(df['expiryDate'].unique())
        
        if not unique_expiries:
            logging.warning(f"No valid expiry dates found in options chain for {symbol}.")
            return pd.DataFrame()

        # Find the nearest future expiry
        today = datetime.datetime.now().date()
        nearest_expiry = None
        for exp_date in unique_expiries:
            if exp_date.date() >= today:
                nearest_expiry = exp_date
                break
        
        if nearest_expiry is None:
            logging.warning(f"Could not find a nearest future expiry date for {symbol}.")
            # Fallback: use the latest expiry if no future expiry is found (e.g., after market close on expiry day)
            nearest_expiry = unique_expiries[-1] if unique_expiries else None

        if nearest_expiry:
            df_nearest_expiry = df[df['expiryDate'] == nearest_expiry]
            logging.info(f"Filtered options chain for nearest expiry: {nearest_expiry.strftime('%Y-%m-%d')}")
            return df_nearest_expiry
        else:
            logging.warning(f"No nearest expiry found for {symbol}. Returning full options chain.")
            return df

    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching NSE options chain for {symbol}: {e}")
        return pd.DataFrame()
    except KeyError as e:
        logging.error(f"Key error in NSE options chain data for {symbol}: {e}. Data structure might have changed.")
        return pd.DataFrame()
    except Exception as e:
        logging.error(f"An unexpected error occurred while fetching NSE options chain for {symbol}: {e}")
        return pd.DataFrame()

def get_best_strikes(option_chain, current_price):
    """
    Finds the best OTM put and call options based on delta range and open interest.
    Adds instrument_token to the selected options.
    """
    if option_chain.empty:
        logging.warning("Option chain is empty, cannot find best strikes.")
        return None, None

    # Ensure necessary columns exist and drop NaNs
    required_cols_pe = ["PE.delta", "PE.openInterest", "strikePrice", "expiryDate"]
    required_cols_ce = ["CE.delta", "CE.openInterest", "strikePrice", "expiryDate"]

    # Filter for options that have both PE and CE data, or handle separately if needed
    # For simplicity, we'll assume a row contains both PE and CE data if it's a valid strike
    option_chain_filtered = option_chain.dropna(subset=[
        "PE.delta", "CE.delta", "PE.openInterest", "CE.openInterest",
        "strikePrice", "expiryDate"
    ])

    if option_chain_filtered.empty:
        logging.warning("Filtered option chain is empty after dropping NaNs.")
        return None, None

    best_put = None
    best_call = None

    try:
        # Find the best put option with delta ~ 0.2 and high liquidity
        otm_puts = option_chain_filtered[
            (option_chain_filtered["PE.delta"].between(CONFIG["OTM_DELTA_RANGE_LOW"], CONFIG["OTM_DELTA_RANGE_HIGH"])) &
            (option_chain_filtered["PE.openInterest"] > CONFIG["MIN_OPEN_INTEREST"]) &
            (option_chain_filtered["strikePrice"] < current_price) # OTM Puts are below current price
        ]
        if not otm_puts.empty:
            best_put = otm_puts.sort_values(by="PE.openInterest", ascending=False).iloc[0]
            # Construct tradingsymbol for put option: SYMBOLDDMMYYSTRIKEPE (e.g., TCS24JUL3800PE)
            expiry_str = best_put['expiryDate'].strftime('%d%b').upper() # e.g., 24JUL
            best_put_symbol = f"{CONFIG['SYMBOL']}{expiry_str}{int(best_put['strikePrice'])}PE"
            best_put_token = get_instrument_token(best_put_symbol)
            if best_put_token:
                best_put['instrument_token'] = best_put_token
                best_put['tradingsymbol'] = best_put_symbol
            else:
                logging.warning(f"Could not find instrument token for best put: {best_put_symbol}. Skipping.")
                best_put = None
        else:
            logging.info("No suitable OTM puts found based on criteria.")

        # Find the best call option with delta ~ 0.2 and high liquidity
        otm_calls = option_chain_filtered[
            (option_chain_filtered["CE.delta"].between(CONFIG["OTM_DELTA_RANGE_LOW"], CONFIG["OTM_DELTA_RANGE_HIGH"])) &
            (option_chain_filtered["CE.openInterest"] > CONFIG["MIN_OPEN_INTEREST"]) &
            (option_chain_filtered["strikePrice"] > current_price) # OTM Calls are above current price
        ]
        if not otm_calls.empty:
            best_call = otm_calls.sort_values(by="CE.openInterest", ascending=False).iloc[0]
            # Construct tradingsymbol for call option: SYMBOLDDMMYYSTRIKEC (e.g., TCS24JUL3800CE)
            expiry_str = best_call['expiryDate'].strftime('%d%b').upper() # e.g., 24JUL
            best_call_symbol = f"{CONFIG['SYMBOL']}{expiry_str}{int(best_call['strikePrice'])}CE"
            best_call_token = get_instrument_token(best_call_symbol)
            if best_call_token:
                best_call['instrument_token'] = best_call_token
                best_call['tradingsymbol'] = best_call_symbol
            else:
                logging.warning(f"Could not find instrument token for best call: {best_call_symbol}. Skipping.")
                best_call = None
        else:
            logging.info("No suitable OTM calls found based on criteria.")

    except IndexError:
        logging.warning("Could not find best put/call. Check option chain data and criteria.")
        return None, None
    except Exception as e:
        logging.error(f"Error in get_best_strikes: {e}")
        return None, None

    return best_put, best_call

def place_order(tradingsymbol, instrument_token, transaction_type, quantity, order_type, product):
    """Helper function to place an order with error handling."""
    try:
        order_id = kite.place_order(
            tradingsymbol=tradingsymbol,
            exchange=kite.EXCHANGE_NSE,
            transaction_type=transaction_type,
            quantity=quantity,
            order_type=order_type,
            product=product,
            instrument_token=instrument_token # Use instrument token
        )
        logging.info(f"Order placed successfully: {transaction_type.upper()} {tradingsymbol}, Order ID: {order_id}")
        return order_id
    except kc_exceptions.InputException as e:
        logging.error(f"Input error placing order for {tradingsymbol}: {e}")
    except kc_exceptions.DataException as e:
        logging.error(f"Data error placing order for {tradingsymbol}: {e}")
    except kc_exceptions.NetworkException as e:
        logging.error(f"Network error placing order for {tradingsymbol}: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred while placing order for {tradingsymbol}: {e}")
    return None

def get_current_ltp(instrument_token, tradingsymbol):
    """Fetches the last traded price for a given instrument."""
    try:
        ltp_data = kite.ltp([f"NSE:{instrument_token}"]) # Use instrument token for LTP
        if f"NSE:{instrument_token}" in ltp_data:
            return ltp_data[f"NSE:{instrument_token}"]["last_price"]
        else:
            logging.warning(f"LTP data not found for {tradingsymbol} (Token: {instrument_token}).")
            return None
    except Exception as e:
        logging.error(f"Error fetching LTP for {tradingsymbol} (Token: {instrument_token}): {e}")
        return None

def manage_short_put(put_position, tcs_ltp, best_put):
    """Manages an existing short put position."""
    put_tradingsymbol = put_position["tradingsymbol"]
    put_instrument_token = get_instrument_token(put_tradingsymbol)
    if not put_instrument_token:
        logging.error(f"Could not get instrument token for existing put: {put_tradingsymbol}. Cannot manage.")
        return

    put_ltp = get_current_ltp(put_instrument_token, put_tradingsymbol)
    if put_ltp is None:
        logging.warning(f"Could not get LTP for {put_tradingsymbol}. Skipping management.")
        return

    entry_price = put_position["average_price"]
    profit_target_price = entry_price * (1 - CONFIG["PROFIT_TARGET_PERCENTAGE"]) # Price at which premium is reduced by target %
    loss_limit_price = entry_price * (1 + CONFIG["LOSS_LIMIT_PERCENTAGE"])     # Price at which premium is doubled

    logging.info(f"Monitoring Short Put: {put_tradingsymbol} | LTP: {put_ltp:.2f} | Entry: {entry_price:.2f} | Profit Target: {profit_target_price:.2f} | Loss Limit: {loss_limit_price:.2f}")

    if put_ltp <= profit_target_price:
        logging.info(f"Closing Put (Profit Target): {put_tradingsymbol} as LTP {put_ltp:.2f} <= {profit_target_price:.2f}")
        place_order(
            tradingsymbol=put_tradingsymbol,
            instrument_token=put_instrument_token,
            transaction_type=kite.TRANSACTION_TYPE_BUY,
            quantity=abs(put_position["quantity"]), # Ensure positive quantity for buy
            order_type=kite.ORDER_TYPE_MARKET,
            product=kite.PRODUCT_NRML
        )
        # After closing, sell a new put if a best_put is available
        if best_put is not None and 'instrument_token' in best_put:
            logging.info(f"Selling new Put after profit booking: {best_put['tradingsymbol']}")
            place_order(
                tradingsymbol=best_put['tradingsymbol'],
                instrument_token=best_put['instrument_token'],
                transaction_type=kite.TRANSACTION_TYPE_SELL,
                quantity=CONFIG["QUANTITY_PER_LOT"],
                order_type=kite.ORDER_TYPE_MARKET,
                product=kite.PRODUCT_NRML
            )
        else:
            logging.warning("No suitable new put found to sell after closing existing put for profit.")

    elif put_ltp >= loss_limit_price:
        logging.info(f"Closing Put (Loss Limit): {put_tradingsymbol} as LTP {put_ltp:.2f} >= {loss_limit_price:.2f}")
        place_order(
            tradingsymbol=put_tradingsymbol,
            instrument_token=put_instrument_token,
            transaction_type=kite.TRANSACTION_TYPE_BUY,
            quantity=abs(put_position["quantity"]), # Ensure positive quantity for buy
            order_type=kite.ORDER_TYPE_MARKET,
            product=kite.PRODUCT_NRML
        )
        # Decide what to do after a loss. For a wheel, you might wait or sell a new put.
        # For now, we'll just close and let the main loop decide if a new put should be sold.
        logging.warning(f"Put {put_tradingsymbol} closed at loss. Re-evaluation needed for next step.")

    # If the put is ITM (In-The-Money) and near expiry, consider assignment
    # This is a complex scenario and often involves rolling the put or preparing for delivery.
    # For simplicity, this script doesn't explicitly handle ITM put assignment,
    # but in a real wheel, you'd monitor this closely.
    # if put_position["strikePrice"] > tcs_ltp and (best_put['expiryDate'] - datetime.datetime.now()).days <= 7:
    #     logging.warning(f"Put {put_tradingsymbol} is ITM and near expiry. Prepare for assignment or roll.")


def initiate_put_sell(best_put):
    """Initiates selling a new OTM put option."""
    if best_put is None or 'instrument_token' not in best_put:
        logging.warning("Cannot initiate put sell: No suitable best put found or missing instrument token.")
        return

    logging.info(f"Initiating new Put Sell: {best_put['tradingsymbol']}")
    place_order(
        tradingsymbol=best_put['tradingsymbol'],
        instrument_token=best_put['instrument_token'],
        transaction_type=kite.TRANSACTION_TYPE_SELL,
        quantity=CONFIG["QUANTITY_PER_LOT"],
        order_type=kite.ORDER_TYPE_MARKET,
        product=kite.PRODUCT_NRML
    )

def manage_covered_call(call_position, tcs_ltp, best_call):
    """Manages an existing short call position."""
    call_tradingsymbol = call_position["tradingsymbol"]
    call_instrument_token = get_instrument_token(call_tradingsymbol)
    if not call_instrument_token:
        logging.error(f"Could not get instrument token for existing call: {call_tradingsymbol}. Cannot manage.")
        return

    call_ltp = get_current_ltp(call_instrument_token, call_tradingsymbol)
    if call_ltp is None:
        logging.warning(f"Could not get LTP for {call_tradingsymbol}. Skipping management.")
        return

    entry_price = call_position["average_price"]
    profit_target_price = entry_price * (1 - CONFIG["PROFIT_TARGET_PERCENTAGE"])
    loss_limit_price = entry_price * (1 + CONFIG["LOSS_LIMIT_PERCENTAGE"])

    logging.info(f"Monitoring Covered Call: {call_tradingsymbol} | LTP: {call_ltp:.2f} | Entry: {entry_price:.2f} | Profit Target: {profit_target_price:.2f} | Loss Limit: {loss_limit_price:.2f}")

    if call_ltp <= profit_target_price:
        logging.info(f"Closing Call (Profit Target): {call_tradingsymbol} as LTP {call_ltp:.2f} <= {profit_target_price:.2f}")
        place_order(
            tradingsymbol=call_tradingsymbol,
            instrument_token=call_instrument_token,
            transaction_type=kite.TRANSACTION_TYPE_BUY,
            quantity=abs(call_position["quantity"]),
            order_type=kite.ORDER_TYPE_MARKET,
            product=kite.PRODUCT_NRML
        )
        # After closing, sell a new call if a best_call is available
        if best_call is not None and 'instrument_token' in best_call:
            logging.info(f"Selling new Covered Call after profit booking: {best_call['tradingsymbol']}")
            place_order(
                tradingsymbol=best_call['tradingsymbol'],
                instrument_token=best_call['instrument_token'],
                transaction_type=kite.TRANSACTION_TYPE_SELL,
                quantity=CONFIG["QUANTITY_PER_LOT"],
                order_type=kite.ORDER_TYPE_MARKET,
                product=kite.PRODUCT_NRML
            )
        else:
            logging.warning("No suitable new call found to sell after closing existing call for profit.")

    elif call_ltp >= loss_limit_price:
        logging.info(f"Closing Call (Loss Limit): {call_tradingsymbol} as LTP {call_ltp:.2f} >= {loss_limit_price:.2f}")
        place_order(
            tradingsymbol=call_tradingsymbol,
            instrument_token=call_instrument_token,
            transaction_type=kite.TRANSACTION_TYPE_BUY,
            quantity=abs(call_position["quantity"]),
            order_type=kite.ORDER_TYPE_MARKET,
            product=kite.PRODUCT_NRML
        )
        logging.warning(f"Call {call_tradingsymbol} closed at loss. Re-evaluation needed for next step.")

    # If the call is ITM (In-The-Money) and near expiry, prepare for assignment (shares called away)
    # if call_position["strikePrice"] < tcs_ltp and (best_call['expiryDate'] - datetime.datetime.now()).days <= 7:
    #     logging.warning(f"Call {call_tradingsymbol} is ITM and near expiry. Prepare for shares to be called away.")


def execute_wheel_strategy():
    """
    Main function to execute the option wheel strategy logic.
    """
    logging.info("--- Starting Option Wheel Strategy Cycle ---")
    try:
        # 1. Get current TCS LTP
        tcs_instrument_token = get_instrument_token(CONFIG["SYMBOL"], "NSE")
        if not tcs_instrument_token:
            logging.error(f"Could not find instrument token for {CONFIG['SYMBOL']}. Exiting cycle.")
            return

        tcs_ltp_data = kite.ltp([f"NSE:{tcs_instrument_token}"])
        if f"NSE:{tcs_instrument_token}" not in tcs_ltp_data:
            logging.error(f"Could not fetch LTP for {CONFIG['SYMBOL']}. Exiting cycle.")
            return
        tcs_ltp = tcs_ltp_data[f"NSE:{tcs_instrument_token}"]["last_price"]
        logging.info(f"Current {CONFIG['SYMBOL']} LTP: {tcs_ltp:.2f}")

        # 2. Fetch Options Chain and Best Strikes
        option_chain = fetch_nse_options(CONFIG["SYMBOL"])
        best_put, best_call = get_best_strikes(option_chain, tcs_ltp)

        if best_put is None and best_call is None:
            logging.warning("Could not identify suitable put or call options. Skipping this cycle.")
            return

        # 3. Get current positions
        positions = kite.positions()["net"]
        tcs_stock_position = next((p for p in positions if p["tradingsymbol"] == CONFIG["SYMBOL"] and p["product"] == "CNC"), None)
        short_puts = [p for p in positions if "PE" in p["tradingsymbol"] and p["quantity"] < 0 and p["product"] == "NRML"]
        short_calls = [p for p in positions if "CE" in p["tradingsymbol"] and p["quantity"] < 0 and p["product"] == "NRML"]

        # --- Strategy Logic ---
        if tcs_stock_position and tcs_stock_position["quantity"] > 0:
            logging.info(f"Holding {tcs_stock_position['quantity']} shares of {CONFIG['SYMBOL']}. Managing covered calls.")
            if short_calls:
                for call_pos in short_calls:
                    manage_covered_call(call_pos, tcs_ltp, best_call)
            else:
                logging.info("No active short calls found. Attempting to sell a new covered call.")
                if best_call is not None and 'instrument_token' in best_call:
                    place_order(
                        tradingsymbol=best_call['tradingsymbol'],
                        instrument_token=best_call['instrument_token'],
                        transaction_type=kite.TRANSACTION_TYPE_SELL,
                        quantity=CONFIG["QUANTITY_PER_LOT"],
                        order_type=kite.ORDER_TYPE_MARKET,
                        product=kite.PRODUCT_NRML
                    )
                else:
                    logging.warning("No suitable OTM call found to sell for covered call strategy.")
        else:
            logging.info(f"Not holding shares of {CONFIG['SYMBOL']}. Managing short puts.")
            if short_puts:
                for put_pos in short_puts:
                    manage_short_put(put_pos, tcs_ltp, best_put)
            else:
                logging.info("No active short puts found. Attempting to sell a new put.")
                if best_put is not None and 'instrument_token' in best_put:
                    place_order(
                        tradingsymbol=best_put['tradingsymbol'],
                        instrument_token=best_put['instrument_token'],
                        transaction_type=kite.TRANSACTION_TYPE_SELL,
                        quantity=CONFIG["QUANTITY_PER_LOT"],
                        order_type=kite.ORDER_TYPE_MARKET,
                        product=kite.PRODUCT_NRML
                    )
                else:
                    logging.warning("No suitable OTM put found to sell for cash-secured put strategy.")

    except kc_exceptions.InputException as e:
        logging.error(f"KiteConnect Input Error: {e}")
    except kc_exceptions.DataException as e:
        logging.error(f"KiteConnect Data Error: {e}")
    except kc_exceptions.NetworkException as e:
        logging.error(f"KiteConnect Network Error: {e}")
    except Exception as e:
        logging.critical(f"An unhandled error occurred during strategy execution: {e}", exc_info=True)

def is_market_open():
    """Checks if the current time is within market hours (NSE Equity)."""
    now = datetime.datetime.now()
    market_open_time = now.replace(hour=CONFIG["MARKET_OPEN_HOUR"], minute=CONFIG["MARKET_OPEN_MINUTE"], second=0, microsecond=0)
    market_close_time = now.replace(hour=CONFIG["MARKET_CLOSE_HOUR"], minute=CONFIG["MARKET_CLOSE_MINUTE"], second=0, microsecond=0)

    # Check for weekdays (Monday=0, Sunday=6)
    if now.weekday() >= 5: # Saturday or Sunday
        logging.info("Market is closed (weekend).")
        return False

    if market_open_time <= now <= market_close_time:
        logging.info("Market is open.")
        return True
    else:
        logging.info("Market is closed (outside trading hours).")
        return False

# 4. Run the strategy continuously
def run_strategy():
    """Runs the option wheel strategy continuously during market hours."""
    # Initialize KiteConnect once
    try:
        init_kite()
        fetch_all_instruments() # Fetch instruments once at startup
    except Exception as e:
        logging.critical(f"Failed to initialize KiteConnect or fetch instruments. Exiting strategy: {e}")
        return

    while True:
        if is_market_open():
            execute_wheel_strategy()
        else:
            logging.info("Waiting for market to open...")

        logging.info(f"Cycle completed. Waiting {CONFIG['STRATEGY_RUN_INTERVAL_SECONDS']} seconds before next run...")
        time.sleep(CONFIG["STRATEGY_RUN_INTERVAL_SECONDS"])

if __name__ == "__main__":
    run_strategy()