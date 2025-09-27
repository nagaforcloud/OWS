from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
from models.enums import OrderType, ProductType, TransactionType
from kiteconnect import KiteConnect

class MockKiteConnect:
    """
    Mock implementation of KiteConnect API for backtesting purposes
    """
    
    def __init__(self, api_key: str = "test_key", access_token: str = "test_token"):
        """
        Initialize the mock KiteConnect
        
        Args:
            api_key: API key (not used in mock)
            access_token: Access token (not used in mock)
        """
        self.api_key = api_key
        self.access_token = access_token
        
        # Initialize with default mock data
        self.instruments = self._generate_instruments()
        self.market_data = self._generate_market_data()
        self.orders = {}
        self.positions = {}
        self.holdings = []
        
        print("Mock KiteConnect initialized for backtesting")
    
    def _generate_instruments(self) -> List[Dict]:
        """
        Generate mock instruments data
        """
        instruments = []
        
        # Generate NIFTY options instruments
        base_strike = 22000
        expiry_dates = [
            datetime.now() + timedelta(days=7),
            datetime.now() + timedelta(days=14),
            datetime.now() + timedelta(days=21)
        ]
        
        for expiry in expiry_dates:
            for strike in range(base_strike - 1000, base_strike + 1000, 50):
                for option_type in ["CE", "PE"]:  # Call and Put
                    instrument = {
                        "instrument_token": random.randint(100000, 999999),
                        "exchange_token": random.randint(10000, 99999),
                        "tradingsymbol": f"NIFTY{strike}{option_type}{expiry.strftime('%y%b%d').upper()}",
                        "name": f"NIFTY {strike} {option_type}",
                        "exchange": "NFO",
                        "instrument_type": option_type,
                        "last_price": random.uniform(50, 300),
                        "strike": strike,
                        "expiry": expiry,
                        "tick_size": 0.05,
                        "lot_size": 50,
                        "currency": "INR"
                    }
                    instruments.append(instrument)
        
        return instruments
    
    def _generate_market_data(self) -> Dict:
        """
        Generate mock market data
        """
        market_data = {}
        
        for instrument in self.instruments:
            symbol = instrument["tradingsymbol"]
            market_data[symbol] = {
                "instrument_token": instrument["instrument_token"],
                "last_price": instrument["last_price"],
                "ohlc": {
                    "open": instrument["last_price"] * random.uniform(0.99, 1.01),
                    "high": instrument["last_price"] * random.uniform(1.00, 1.03),
                    "low": instrument["last_price"] * random.uniform(0.97, 1.00),
                    "close": instrument["last_price"] * random.uniform(0.99, 1.01)
                },
                "change": random.uniform(-5, 5),
                "volume": random.randint(1000, 100000),
                "buy_quantity": random.randint(100, 1000),
                "sell_quantity": random.randint(100, 1000),
                "open_interest": random.randint(10000, 1000000)
            }
        
        # Add some underlying stocks
        underlying_symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK"]
        for symbol in underlying_symbols:
            market_data[symbol] = {
                "instrument_token": random.randint(100000, 999999),
                "last_price": random.uniform(500, 3000),
                "ohlc": {
                    "open": random.uniform(500, 3000),
                    "high": random.uniform(500, 3000),
                    "low": random.uniform(500, 3000),
                    "close": random.uniform(500, 3000)
                },
                "change": random.uniform(-5, 5),
                "volume": random.randint(100000, 5000000),
                "buy_quantity": random.randint(10000, 50000),
                "sell_quantity": random.randint(10000, 50000),
                "open_interest": random.randint(1000000, 10000000)
            }
        
        return market_data
    
    def instruments(self, exchange: Optional[str] = None) -> List[Dict]:
        """
        Get list of instruments
        
        Args:
            exchange: Exchange to filter by (e.g. NSE, BSE, NFO)
            
        Returns:
            List of instrument dictionaries
        """
        if exchange:
            return [inst for inst in self.instruments if inst.get("exchange") == exchange]
        return self.instruments
    
    def quote(self, instruments: List[str]) -> Dict[str, Dict]:
        """
        Get quote for instruments
        
        Args:
            instruments: List of instrument symbols
            
        Returns:
            Dictionary with instrument symbols as keys and market data as values
        """
        result = {}
        for symbol in instruments:
            if symbol in self.market_data:
                result[symbol] = self.market_data[symbol]
            else:
                # Create mock data for symbol if not found
                result[symbol] = {
                    "instrument_token": random.randint(100000, 999999),
                    "last_price": random.uniform(100, 2000),
                    "ohlc": {
                        "open": random.uniform(100, 2000),
                        "high": random.uniform(100, 2000),
                        "low": random.uniform(100, 2000),
                        "close": random.uniform(100, 2000)
                    },
                    "change": random.uniform(-5, 5),
                    "volume": random.randint(100000, 5000000),
                    "buy_quantity": random.randint(10000, 50000),
                    "sell_quantity": random.randint(10000, 50000),
                    "open_interest": random.randint(1000000, 10000000)
                }
        return result
    
    def historical_data(self, instrument_token: int, from_date: datetime, to_date: datetime, 
                       interval: str, continuous: bool = False, oi: bool = False) -> List[Dict]:
        """
        Get historical data for an instrument
        
        Args:
            instrument_token: Instrument token
            from_date: Start date
            to_date: End date
            interval: Candle interval (minute, day, etc.)
            continuous: Continuous data for futures
            oi: Include open interest
            
        Returns:
            List of candle data
        """
        candles = []
        current_date = from_date
        
        while current_date <= to_date:
            candle = {
                "date": current_date.isoformat(),
                "open": random.uniform(100, 2000),
                "high": random.uniform(100, 2000),
                "low": random.uniform(100, 2000),
                "close": random.uniform(100, 2000),
                "volume": random.randint(1000, 100000),
                "oi": random.randint(1000, 100000) if oi else 0
            }
            # Ensure high >= low, open/close within range
            candle["high"] = max(candle["high"], candle["open"], candle["close"], candle["low"])
            candle["low"] = min(candle["low"], candle["open"], candle["close"])
            
            candles.append(candle)
            current_date += timedelta(days=1)
        
        return candles
    
    def place_order(self, 
                   variety: str,
                   exchange: str,
                   tradingsymbol: str,
                   transaction_type: str,
                   quantity: int,
                   product: str,
                   order_type: str,
                   price: Optional[float] = None,
                   validity: str = "DAY",
                   disclosed_quantity: Optional[int] = 0,
                   trigger_price: Optional[float] = 0,
                   squareoff: Optional[float] = None,
                   stoploss: Optional[float] = None,
                   trailing_stoploss: Optional[float] = None,
                   tag: Optional[str] = None) -> str:
        """
        Place an order
        
        Args:
            variety: Order variety (regular, amo, etc.)
            exchange: Exchange (NSE, BSE, NFO, etc.)
            tradingsymbol: Trading symbol
            transaction_type: Transaction type (BUY, SELL)
            quantity: Quantity to order
            product: Product type (MIS, CNC, NRML)
            order_type: Order type (MARKET, LIMIT, SL, SL-M)
            price: Price for LIMIT orders
            validity: Order validity (DAY, IOC, TTL)
            
        Returns:
            Order ID
        """
        order_id = f"TEST{random.randint(100000, 999999)}"
        
        order_details = {
            "order_id": order_id,
            "exchange_order_id": f"EXCH{random.randint(100000, 999999)}",
            "placed_by": "TEST_USER",
            "status": "OPEN",
            "status_message": None,
            "status_message_raw": None,
            "order_timestamp": datetime.now().isoformat(),
            "exchange_timestamp": datetime.now().isoformat(),
            "exchange": exchange,
            "tradingsymbol": tradingsymbol,
            "instrument_token": self.market_data.get(tradingsymbol, {}).get("instrument_token", random.randint(100000, 999999)),
            "order_type": order_type,
            "transaction_type": transaction_type,
            "validity": validity,
            "product": product,
            "quantity": quantity,
            "disclosed_quantity": disclosed_quantity,
            "price": price if price else self.market_data.get(tradingsymbol, {}).get("last_price", 0.0),
            "trigger_price": trigger_price,
            "average_price": 0.0,
            "filled_quantity": 0,
            "pending_quantity": quantity,
            "cancelled_quantity": 0,
            "market_protection": 0.0,
            "variety": variety,
            "order_timestamp": datetime.now().isoformat(),
            "exchange_timestamp": datetime.now().isoformat(),
            "instrument_token": random.randint(100000, 999999),
            "order_id": order_id,
            "parent_order_id": None
        }
        
        self.orders[order_id] = order_details
        print(f"Mock order placed: {order_id} for {tradingsymbol}")
        return order_id
    
    def modify_order(self, 
                    variety: str,
                    order_id: str,
                    parent_order_id: Optional[str] = None,
                    quantity: Optional[int] = None,
                    price: Optional[float] = None,
                    order_type: Optional[str] = None,
                    trigger_price: Optional[float] = None,
                    validity: Optional[str] = None) -> Dict:
        """
        Modify an existing order
        """
        if order_id in self.orders:
            order = self.orders[order_id]
            if quantity is not None:
                order["quantity"] = quantity
            if price is not None:
                order["price"] = price
            if order_type is not None:
                order["order_type"] = order_type
            if trigger_price is not None:
                order["trigger_price"] = trigger_price
            if validity is not None:
                order["validity"] = validity
            
            print(f"Mock order modified: {order_id}")
            return order
        
        raise Exception(f"Order {order_id} not found")
    
    def cancel_order(self, variety: str, order_id: str, parent_order_id: Optional[str] = None) -> Dict:
        """
        Cancel an existing order
        """
        if order_id in self.orders:
            order = self.orders[order_id]
            order["status"] = "CANCELLED"
            order["cancelled_quantity"] = order["quantity"]
            order["pending_quantity"] = 0
            print(f"Mock order cancelled: {order_id}")
            return order
        
        raise Exception(f"Order {order_id} not found")
    
    def orders(self) -> List[Dict]:
        """
        Get list of all orders
        """
        return list(self.orders.values())
    
    def order_history(self, order_id: str) -> List[Dict]:
        """
        Get history of an order
        """
        if order_id in self.orders:
            return [self.orders[order_id]]
        return []
    
    def trades(self) -> List[Dict]:
        """
        Get list of all completed trades
        """
        # Return completed trades only
        completed_trades = []
        for order in self.orders.values():
            if order["status"] == "COMPLETE":
                trade = {
                    "order_id": order["order_id"],
                    "exchange_order_id": order["exchange_order_id"],
                    "tradingsymbol": order["tradingsymbol"],
                    "exchange": order["exchange"],
                    "instrument_token": order["instrument_token"],
                    "transaction_type": order["transaction_type"],
                    "order_type": order["order_type"],
                    "product": order["product"],
                    "quantity": order["filled_quantity"],
                    "average_price": order["average_price"],
                    "fill_timestamp": order["exchange_timestamp"],
                    "exchange_timestamp": order["exchange_timestamp"]
                }
                completed_trades.append(trade)
        
        return completed_trades
    
    def positions(self) -> Dict[str, List[Dict]]:
        """
        Get positions
        
        Returns:
            Dictionary with net and day positions
        """
        # For mock, return empty positions or generated positions
        return {
            "net": [],  # Net positions
            "day": []   # Day positions
        }
    
    def holdings(self) -> List[Dict]:
        """
        Get holdings
        """
        return self.holdings
    
    def margins(self, segment: Optional[str] = None) -> Dict:
        """
        Get margin information
        """
        return {
            "enabled": True,
            "net": 100000.0,  # Available margin
            "available": {
                "ad_hoc_margin": 0,
                "cash": 100000.0,
                "collateral": 0,
                "intraday_payin": 0
            },
            "utilised": {
                "debits": 0,
                "exposure": 0,
                "m2m_realised": 0,
                "m2m_unrealised": 0,
                "option_premium": 0,
                "payout": 0,
                "span": 0,
                "holding_sales": 0,
                "turnover": 0
            }
        }
    
    def profile(self) -> Dict:
        """
        Get user profile
        """
        return {
            "user_id": "TEST123",
            "user_name": "Test User",
            "user_shortname": "Test",
            "email": "test@example.com",
            "user_type": "investor",
            "broker": "Z",
            "exchanges": ["NSE", "BSE", "MCX", "NFO", "CDS", "BFO", "BSECD"],
            "products": ["MIS", "CNC", "NRML"],
            "order_types": ["MARKET", "LIMIT", "SL", "SL-M"]
        }
    
    # Additional methods for updating state during backtesting
    def update_market_data(self, new_data: Dict):
        """
        Update market data for backtesting
        
        Args:
            new_data: New market data to merge with existing data
        """
        self.market_data.update(new_data)
    
    def execute_order(self, order_id: str):
        """
        Simulate order execution for backtesting
        
        Args:
            order_id: Order ID to execute
        """
        if order_id in self.orders:
            order = self.orders[order_id]
            order["status"] = "COMPLETE"
            order["average_price"] = order["price"] or self.market_data.get(order["tradingsymbol"], {}).get("last_price", 0.0)
            order["filled_quantity"] = order["quantity"]
            order["pending_quantity"] = 0
            print(f"Mock order executed: {order_id} at {order['average_price']}")
    
    def set_current_time(self, current_time: datetime):
        """
        Set current time for backtesting
        
        Args:
            current_time: Current time to use for time-sensitive operations
        """
        self.current_time = current_time


# Example usage
if __name__ == "__main__":
    # Create a mock KiteConnect instance
    mock_kite = MockKiteConnect()
    
    # Test getting instruments
    nfo_instruments = mock_kite.instruments("NFO")
    print(f"Generated {len(nfo_instruments)} NFO instruments")
    
    # Test placing an order
    order_id = mock_kite.place_order(
        variety="regular",
        exchange="NSE",
        tradingsymbol="RELIANCE",
        transaction_type="BUY",
        quantity=1,
        product="MIS",
        order_type="MARKET"
    )
    print(f"Placed mock order: {order_id}")
    
    # Test getting market data
    quotes = mock_kite.quote(["RELIANCE", "TCS"])
    print(f"Got quotes for RELIANCE and TCS: {list(quotes.keys())}")