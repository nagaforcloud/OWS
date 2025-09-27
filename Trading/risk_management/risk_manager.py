from dataclasses import dataclass
from typing import Dict, List, Optional
import logging
from datetime import datetime, date
from models.models import Position, Trade, RiskMetrics
from utils.logging_utils import get_logger
from config.config import OptionWheelConfig

logger = get_logger(__name__)

@dataclass
class RiskConfig:
    """Risk configuration parameters"""
    max_portfolio_risk: float
    max_daily_loss: float
    max_concurrent_positions: int
    max_position_size_percentage: float
    max_margin_utilization: float
    min_distance_to_strike: float  # For options - min distance to underlying

@dataclass
class PositionRisk:
    """Risk metrics for an individual position"""
    symbol: str
    position_size: float
    position_percentage: float
    volatility_risk: float
    concentration_risk: float
    greek_risk: Dict[str, float]  # delta, gamma, theta, vega, rho
    stop_loss_distance: float
    profit_target_distance: float
    days_to_expiry: int
    underlying_correlation: float

class RiskManager:
    """
    Manages risk controls for the trading strategy
    """
    
    def __init__(self, config: OptionWheelConfig):
        """
        Initialize the risk manager
        
        Args:
            config: OptionWheelConfig instance
        """
        self.config = config
        self.daily_loss = 0.0
        self.daily_loss_limit = config.max_daily_loss_limit
        self.max_concurrent_positions = config.max_concurrent_positions
        self.max_portfolio_risk = config.max_portfolio_risk
        self.positions: Dict[str, Position] = {}
        
        # Track daily trades for loss calculation
        self.daily_trades: List[Trade] = []
        self.daily_pnl = 0.0
        
        logger.info("Risk Manager initialized")
    
    def should_place_order(self, symbol: str, quantity: int, price: float, 
                          portfolio_value: float) -> tuple[bool, List[str]]:
        """
        Determine if an order should be placed based on risk checks
        
        Args:
            symbol: Symbol to trade
            quantity: Quantity to trade
            price: Price at which to trade
            portfolio_value: Current portfolio value
            
        Returns:
            tuple[bool, List[str]]: (should_place_order, list_of_issues)
        """
        issues = []
        
        # Check daily loss limit
        if self.daily_loss <= -self.daily_loss_limit:
            issues.append(f"Daily loss limit exceeded: {self.daily_loss} <= -{self.daily_loss_limit}")
        
        # Check concurrent positions limit
        current_positions_count = len(self.positions)
        if current_positions_count >= self.max_concurrent_positions:
            issues.append(
                f"Max concurrent positions limit reached: {current_positions_count} >= {self.max_concurrent_positions}"
            )
        
        # Check portfolio risk limit
        trade_value = abs(quantity * price)
        if portfolio_value > 0:
            trade_risk_percentage = trade_value / portfolio_value
            if trade_risk_percentage > self.max_portfolio_risk:
                issues.append(
                    f"Trade risk exceeds portfolio risk limit: {trade_risk_percentage:.2%} > {self.max_portfolio_risk:.2%}"
                )
        
        # Check position size relative to portfolio
        if portfolio_value > 0:
            position_value = 0
            if symbol in self.positions:
                existing_position = self.positions[symbol]
                position_value = existing_position.quantity * existing_position.last_price
            new_position_value = position_value + trade_value
            position_risk_percentage = new_position_value / portfolio_value
            max_position_risk = self.max_portfolio_risk * 2  # Allow some flexibility
            if position_risk_percentage > max_position_risk:
                issues.append(
                    f"Position risk exceeds limit: {position_risk_percentage:.2%} > {max_position_risk:.2%}"
                )
        
        should_place = len(issues) == 0
        if not should_place:
            logger.warning(f"Order blocked due to risk issues: {issues}")
        
        return should_place, issues
    
    def calculate_position_risk(self, position: Position, 
                               market_data: Optional[Dict] = None) -> PositionRisk:
        """
        Calculate risk metrics for an individual position
        
        Args:
            position: Position to analyze
            market_data: Optional market data for the symbol
            
        Returns:
            PositionRisk: Risk metrics for the position
        """
        # Get current market data if not provided
        if not market_data:
            # This would typically come from market data API
            market_data = {
                'last_price': position.last_price,
                'volatility': 0.2,  # Default implied volatility
                'greeks': {'delta': 0.5, 'gamma': 0.1, 'theta': -0.01, 'vega': 0.1, 'rho': 0.005}
            }
        
        # Calculate position metrics
        position_value = abs(position.quantity * position.last_price)
        portfolio_value = 100000  # Placeholder - would come from portfolio calculation
        position_percentage = position_value / portfolio_value if portfolio_value > 0 else 0.0
        
        # Calculate various risks
        volatility_risk = market_data['volatility'] * position_value
        concentration_risk = position_percentage  # Simplified measure
        
        # Greek risks (simplified)
        greeks = market_data.get('greeks', {})
        greek_risks = {
            'delta_risk': abs(greeks.get('delta', 0) * position_value),
            'gamma_risk': abs(greeks.get('gamma', 0) * position_value),
            'theta_risk': abs(greeks.get('theta', 0) * position_value),
            'vega_risk': abs(greeks.get('vega', 0) * position_value),
            'rho_risk': abs(greeks.get('rho', 0) * position_value)
        }
        
        # Placeholder for stop loss and profit target distances
        stop_loss_distance = 0.05  # 5% for example
        profit_target_distance = 0.03  # 3% for example
        
        # Placeholder for days to expiry (for options)
        days_to_expiry = 30
        
        # Placeholder for underlying correlation
        underlying_correlation = 1.0
        
        return PositionRisk(
            symbol=position.symbol,
            position_size=position_value,
            position_percentage=position_percentage,
            volatility_risk=volatility_risk,
            concentration_risk=concentration_risk,
            greek_risk=greek_risks,
            stop_loss_distance=stop_loss_distance,
            profit_target_distance=profit_target_distance,
            days_to_expiry=days_to_expiry,
            underlying_correlation=underlying_correlation
        )
    
    def calculate_portfolio_risk(self, positions: List[Position], 
                                portfolio_value: float) -> RiskMetrics:
        """
        Calculate overall portfolio risk metrics
        
        Args:
            positions: List of positions in the portfolio
            portfolio_value: Total portfolio value
            
        Returns:
            RiskMetrics: Overall portfolio risk metrics
        """
        total_position_value = sum(abs(p.quantity * p.last_price) for p in positions)
        portfolio_risk_percentage = total_position_value / portfolio_value if portfolio_value > 0 else 0.0
        
        # Calculate Value at Risk (VaR) - simplified approach
        # In a real system, this would be more sophisticated
        var_confidence = 0.95
        var_period = 1  # 1-day VaR
        # Placeholder VaR calculation
        var_value = self.daily_loss * 1.65  # Assuming normal distribution
        
        # Calculate Sharpe Ratio - simplified approach
        # Placeholder - would use actual return data
        sharpe_ratio = 1.5 if portfolio_value > 100000 else 0.8  # Placeholder
        
        # Calculate Max Drawdown - simplified approach
        # Placeholder - would track historical portfolio values
        max_drawdown = abs(self.daily_loss) / portfolio_value if portfolio_value > 0 else 0.0
        current_drawdown = abs(self.daily_loss) / portfolio_value if portfolio_value > 0 else 0.0
        
        # Check if limits are exceeded
        max_daily_loss_exceeded = abs(self.daily_loss) >= self.daily_loss_limit
        max_positions_exceeded = len(positions) >= self.max_concurrent_positions
        
        # Placeholder for margin utilization
        margin_utilization = total_position_value / portfolio_value if portfolio_value > 0 else 0.0
        max_margin_utilization = self.max_portfolio_risk
        margin_limit_exceeded = margin_utilization >= max_margin_utilization
        
        return RiskMetrics(
            portfolio_value=portfolio_value,
            portfolio_risk_percentage=portfolio_risk_percentage,
            daily_loss=self.daily_loss,
            daily_loss_limit=self.daily_loss_limit,
            max_daily_loss_exceeded=max_daily_loss_exceeded,
            current_positions_count=len(positions),
            max_positions_limit=self.max_concurrent_positions,
            max_positions_exceeded=max_positions_exceeded,
            margin_utilization=margin_utilization,
            max_margin_utilization=max_margin_utilization,
            margin_limit_exceeded=margin_limit_exceeded,
            value_at_risk=var_value,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            current_drawdown=current_drawdown
        )
    
    def update_position(self, position: Position):
        """
        Update the risk manager with a new or updated position
        
        Args:
            position: Updated position
        """
        self.positions[position.symbol] = position
        logger.debug(f"Updated position for {position.symbol}")
    
    def remove_position(self, symbol: str):
        """
        Remove a position from tracking
        
        Args:
            symbol: Symbol of position to remove
        """
        if symbol in self.positions:
            del self.positions[symbol]
            logger.debug(f"Removed position for {symbol}")
    
    def update_daily_pnl(self, trade: Trade):
        """
        Update daily P&L with a new trade
        
        Args:
            trade: Trade that affects P&L
        """
        # This would calculate P&L based on the trade
        # For now, just add the trade to tracking
        self.daily_trades.append(trade)
        
        # Calculate daily P&L - simplified calculation
        # In a real system, this would calculate P&L based on entry/exit prices
        if trade.transaction_type == 'BUY':
            trade_pnl = -(trade.filled_quantity * trade.average_price)
        else:  # SELL
            trade_pnl = trade.filled_quantity * trade.average_price
            
        self.daily_pnl += trade_pnl
        self.daily_loss = -self.daily_pnl  # Loss is negative P&L
        
        logger.debug(f"Updated daily P&L: {self.daily_pnl}, Daily Loss: {self.daily_loss}")
    
    def generate_risk_report(self) -> Dict:
        """
        Generate a comprehensive risk report
        
        Returns:
            Dict: Risk report with various metrics
        """
        # Calculate portfolio metrics
        portfolio_value = 100000  # Placeholder - would come from actual portfolio calculation
        
        # Create risk metrics
        risk_metrics = self.calculate_portfolio_risk(list(self.positions.values()), portfolio_value)
        
        # Calculate individual position risks
        position_risks = {}
        for symbol, position in self.positions.items():
            position_risks[symbol] = self.calculate_position_risk(position)
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'portfolio_metrics': {
                'total_value': portfolio_value,
                'total_positions': len(self.positions),
                'daily_pnl': self.daily_pnl,
                'daily_loss': self.daily_loss,
                'total_position_value': sum(abs(p.quantity * p.last_price) for p in self.positions.values())
            },
            'risk_limits': {
                'max_daily_loss': self.daily_loss_limit,
                'max_concurrent_positions': self.max_concurrent_positions,
                'max_portfolio_risk': self.max_portfolio_risk
            },
            'risk_metrics': {
                'portfolio_risk_percentage': risk_metrics.portfolio_risk_percentage,
                'max_daily_loss_exceeded': risk_metrics.max_daily_loss_exceeded,
                'max_positions_exceeded': risk_metrics.max_positions_exceeded,
                'margin_limit_exceeded': risk_metrics.margin_limit_exceeded,
                'value_at_risk': risk_metrics.value_at_risk,
                'sharpe_ratio': risk_metrics.sharpe_ratio,
                'max_drawdown': risk_metrics.max_drawdown,
                'current_drawdown': risk_metrics.current_drawdown
            },
            'position_risks': position_risks,
            'risk_limits_breached': risk_metrics.risk_limits_exceeded()
        }
        
        logger.info("Risk report generated")
        return report
    
    def check_risk_limits_breached(self) -> List[str]:
        """
        Check if any risk limits are breached
        
        Returns:
            List[str]: List of breached risk limits
        """
        breaches = []
        
        if abs(self.daily_loss) >= self.daily_loss_limit:
            breaches.append(f"Daily loss limit exceeded: {self.daily_loss:.2f} >= {self.daily_loss_limit:.2f}")
        
        if len(self.positions) >= self.max_concurrent_positions:
            breaches.append(f"Max concurrent positions exceeded: {len(self.positions)} >= {self.max_concurrent_positions}")
        
        # Portfolio risk check would depend on portfolio value
        portfolio_value = 100000  # Placeholder
        total_position_value = sum(abs(p.quantity * p.last_price) for p in self.positions.values())
        if portfolio_value > 0:
            portfolio_risk = total_position_value / portfolio_value
            if portfolio_risk >= self.max_portfolio_risk:
                breaches.append(f"Portfolio risk limit exceeded: {portfolio_risk:.2%} >= {self.max_portfolio_risk:.2%}")
        
        return breaches
    
    def reset_daily_counters(self):
        """
        Reset daily counters at the start of a new trading day
        """
        self.daily_loss = 0.0
        self.daily_pnl = 0.0
        self.daily_trades = []
        logger.info("Daily risk counters reset")


# Example usage
if __name__ == "__main__":
    # Create a sample config
    config = OptionWheelConfig()
    
    # Initialize risk manager
    risk_manager = RiskManager(config)
    
    # Example of checking if an order should be placed
    should_place, issues = risk_manager.should_place_order("TCS", 150, 3450.0, 100000.0)
    print(f"Should place order: {should_place}")
    print(f"Issues: {issues}")
    
    # Example of generating a risk report
    report = risk_manager.generate_risk_report()
    print("Risk report:", report)
    
    # Example of position risk calculation
    from models.models import Position
    from models.enums import ProductType
    
    sample_position = Position(
        symbol="TCS",
        exchange="NSE",
        instrument_token=12345,
        product=ProductType.MIS,
        quantity=150,
        average_price=3450.0,
        last_price=3455.0
    )
    
    risk_manager.update_position(sample_position)
    position_risk = risk_manager.calculate_position_risk(sample_position)
    print("Position risk:", position_risk)