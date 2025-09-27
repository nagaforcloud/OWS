"""
Mock KiteConnect for backtesting.
"""
import pandas as pd
import datetime
import logging
from typing import List, Dict, Any, Optional


class MockKiteConnect:
    """
    A mock class to simulate KiteConnect API calls for backtesting purposes.
    It provides predefined or historical data instead of making live API requests.
    """
    def __init__(self, historical_data: Dict[str, Any]):
        # Import here to avoid circular imports
        from ..utils.logging_utils import setup_logging
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