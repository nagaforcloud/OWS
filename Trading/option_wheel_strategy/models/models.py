"""
Data models for the Option Wheel Strategy.
"""
from dataclasses import dataclass
from typing import Optional
import datetime


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