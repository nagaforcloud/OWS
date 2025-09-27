from enum import Enum

class OrderType(Enum):
    """Order type for trading operations"""
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    SL = "SL"  # Stop Loss
    SLM = "SL-M"  # Stop Loss Market

class ProductType(Enum):
    """Product type for trading operations"""
    CNC = "CNC"  # Cash and Carry
    NRML = "NRML"  # Normal
    MIS = "MIS"  # Margin Intraday Squareoff

class TransactionType(Enum):
    """Transaction type (BUY or SELL)"""
    BUY = "BUY"
    SELL = "SELL"

class StrategyType(Enum):
    """Type of strategy being executed"""
    CASH_SECURED_PUT = "CASH_SECURED_PUT"
    COVERED_CALL = "COVERED_CALL"

class PositionType(Enum):
    """Type of position"""
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"

class OptionType(Enum):
    """Type of option"""
    CALL = "CE"  # Call European
    PUT = "PE"   # Put European

class OrderStatus(Enum):
    """Status of an order"""
    COMPLETE = "COMPLETE"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    OPEN = "OPEN"
    TRIGGER_PENDING = "TRIGGER_PENDING"

class ExchangeType(Enum):
    """Exchange types available"""
    NSE = "NSE"
    BSE = "BSE"
    NFO = "NFO"  # NSE Futures and Options
    BFO = "BFO"  # BSE Futures and Options
    CDS = "CDS"  # Currency Derivatives Segment
    MCX = "MCX"  # Multi Commodity Exchange