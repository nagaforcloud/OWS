from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from decimal import Decimal
from .enums import OrderType, ProductType, TransactionType, StrategyType, PositionType, OptionType, OrderStatus, ExchangeType
from enum import Enum

@dataclass
class Trade:
    """Represents a trade executed by the strategy"""
    order_id: str
    symbol: str
    exchange: str
    instrument_token: int
    transaction_type: TransactionType
    order_type: OrderType
    product: ProductType
    quantity: int
    price: float
    trigger_price: Optional[float] = None
    disclosed_quantity: Optional[int] = None
    validity: str = "DAY"
    variety: str = "regular"
    tag: Optional[str] = None
    
    # Additional fields
    average_price: float = 0.0
    filled_quantity: int = 0
    pending_quantity: int = 0
    cancelled_quantity: int = 0
    order_timestamp: Optional[datetime] = None
    exchange_order_id: Optional[str] = None
    status: OrderStatus = OrderStatus.OPEN
    status_message: Optional[str] = None
    
    # Tax & Accounting Hooks (Future-Proofing)
    trade_type: str = "fno"  # Options trade by default: "intraday", "delivery", "fno" 
    tax_category: str = "STT_applicable"  # For future tax calculations
    stt_paid: float = 0.0  # Securities Transaction Tax
    brokerage: float = 0.0  # Brokerage fees
    taxes: float = 0.0  # Other taxes (GST, STT, etc.)
    turnover_charges: float = 0.0  # Turnover charges
    stamp_duty: float = 0.0  # Stamp duty
    
    def total_value(self) -> float:
        """Calculate the total value of the trade"""
        return self.price * self.quantity

    def is_buy(self) -> bool:
        """Check if this is a buy trade"""
        return self.transaction_type == TransactionType.BUY

    def is_sell(self) -> bool:
        """Check if this is a sell trade"""
        return self.transaction_type == TransactionType.SELL

    def net_pnl(self) -> float:
        """Calculate net P&L after taxes and fees"""
        gross_pnl = (self.average_price - self.price) * self.quantity if self.is_buy() else (self.price - self.average_price) * self.quantity
        total_costs = self.brokerage + self.taxes + self.turnover_charges + self.stamp_duty
        return gross_pnl - total_costs

@dataclass
class Position:
    """Represents a position in the portfolio"""
    symbol: str
    exchange: str
    instrument_token: int
    product: ProductType
    
    # Quantity fields
    quantity: int = 0
    overnight_quantity: int = 0
    multiplier: float = 1.0
    
    # Price fields
    average_price: float = 0.0
    last_price: float = 0.0
    close_price: float = 0.0
    
    # P&L fields
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    
    # Additional fields
    buy_quantity: int = 0
    buy_price: float = 0.0
    buy_value: float = 0.0
    sell_quantity: int = 0
    sell_price: float = 0.0
    sell_value: float = 0.0
    day_buy_quantity: int = 0
    day_buy_price: float = 0.0
    day_sell_quantity: int = 0
    day_sell_price: float = 0.0
    
    def pnl(self) -> float:
        """Calculate total P&L (realized + unrealized)"""
        return self.realized_pnl + self.unrealized_pnl

    def position_type(self) -> PositionType:
        """Determine the position type based on quantity"""
        if self.quantity > 0:
            return PositionType.LONG
        elif self.quantity < 0:
            return PositionType.SHORT
        else:
            return PositionType.FLAT

    def market_value(self) -> float:
        """Calculate the current market value of the position"""
        return self.last_price * self.quantity

    def absolute_quantity(self) -> int:
        """Get the absolute value of quantity"""
        return abs(self.quantity)

@dataclass
class OptionContract:
    """Represents an option contract with Greeks and other data"""
    symbol: str
    instrument_token: int
    exchange: ExchangeType
    option_type: OptionType
    strike_price: float
    expiry_date: datetime
    last_price: float
    open_interest: int
    volume: int
    oi_day_high: float
    oi_day_low: float
    bid_price: float
    ask_price: float
    underlying_value: float
    
    # Greeks (if available)
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    rho: Optional[float] = None
    implied_volatility: Optional[float] = None
    
    def intrinsic_value(self, underlying_price: float) -> float:
        """Calculate the intrinsic value of the option"""
        if self.option_type == OptionType.CALL:
            return max(0, underlying_price - self.strike_price)
        else:  # PUT
            return max(0, self.strike_price - underlying_price)
    
    def time_value(self, underlying_price: float) -> float:
        """Calculate the time value of the option"""
        intrinsic_value = self.intrinsic_value(underlying_price)
        return max(0, self.last_price - intrinsic_value)
    
    def is_in_the_money(self, underlying_price: float) -> bool:
        """Check if the option is in the money"""
        if self.option_type == OptionType.CALL:
            return underlying_price > self.strike_price
        else:  # PUT
            return underlying_price < self.strike_price

@dataclass
class StrategyState:
    """Represents the current state of the strategy"""
    current_positions: list
    historical_trades: list
    daily_pnl: float
    total_pnl: float
    strategy_type: StrategyType
    last_updated: datetime
    active_orders: list = None
    strategy_running: bool = True
    
    def __post_init__(self):
        """Initialize optional fields if not provided"""
        if self.active_orders is None:
            self.active_orders = []

@dataclass
class RiskMetrics:
    """Risk metrics for portfolio monitoring"""
    portfolio_value: float
    portfolio_risk_percentage: float
    daily_loss: float
    daily_loss_limit: float
    max_daily_loss_exceeded: bool
    current_positions_count: int
    max_positions_limit: int
    max_positions_exceeded: bool
    margin_utilization: float
    max_margin_utilization: float
    margin_limit_exceeded: bool
    value_at_risk: float
    sharpe_ratio: float
    max_drawdown: float
    current_drawdown: float
    
    def risk_limits_exceeded(self) -> bool:
        """Check if any risk limits are exceeded"""
        return (
            self.max_daily_loss_exceeded or 
            self.max_positions_exceeded or 
            self.margin_limit_exceeded
        )