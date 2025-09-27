"""
Enums for the Option Wheel Strategy.
"""
from enum import Enum


class OrderType(Enum):
    """Order types supported by Kite."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"
    SL_M = "SL-M"


class ProductType(Enum):
    """Product types supported by Kite."""
    NRML = "NRML"
    CNC = "CNC"
    MIS = "MIS"


class TransactionType(Enum):
    """Transaction types supported by Kite."""
    BUY = "BUY"
    SELL = "SELL"