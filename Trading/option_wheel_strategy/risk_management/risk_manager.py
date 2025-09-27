"""
Risk Management Module for Options Wheel Strategy.
Provides comprehensive risk controls and portfolio management.
"""
import pandas as pd
import numpy as np
import datetime
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RiskConfig:
    """Configuration for risk management parameters."""
    max_portfolio_risk: float = 0.02  # 2% of portfolio
    max_position_size: float = 0.05   # 5% of portfolio per position
    max_daily_loss_limit: float = 5000.0
    max_concurrent_positions: int = 10
    max_sector_exposure: float = 0.20  # 20% per sector
    max_correlation_risk: float = 0.70  # 70% correlation threshold
    stop_loss_multiplier: float = 2.0  # Stop loss at 2x credit received
    margin_utilization_limit: float = 0.80  # Use max 80% of available margin


@dataclass
class PositionRisk:
    """Risk metrics for a single position."""
    tradingsymbol: str
    quantity: int
    average_price: float
    current_price: float
    pnl: float
    market_value: float
    risk_exposure: float
    days_to_expiry: int
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0


class RiskManager:
    """Comprehensive risk management system for options trading."""
    
    def __init__(self, config: RiskConfig):
        """
        Initialize risk manager.
        
        Args:
            config: Risk configuration parameters
        """
        self.config = config
        self.portfolio_value = 0.0
        self.available_margin = 0.0
        self.positions: List[PositionRisk] = []
        self.sector_exposures: Dict[str, float] = {}
        self.daily_losses = 0.0
        self.daily_pnl = 0.0
    
    def update_portfolio_state(self, portfolio_value: float, 
                             available_margin: float,
                             positions: List[Dict[str, Any]]) -> None:
        """
        Update portfolio state for risk calculations.
        
        Args:
            portfolio_value: Current portfolio value
            available_margin: Available margin
            positions: Current positions
        """
        self.portfolio_value = portfolio_value
        self.available_margin = available_margin
        
        # Convert positions to PositionRisk objects
        self.positions = []
        for pos in positions:
            # Extract Greeks if available
            delta = pos.get('delta', 0.0)
            gamma = pos.get('gamma', 0.0)
            theta = pos.get('theta', 0.0)
            vega = pos.get('vega', 0.0)
            
            position_risk = PositionRisk(
                tradingsymbol=pos.get('tradingsymbol', ''),
                quantity=pos.get('quantity', 0),
                average_price=pos.get('average_price', 0.0),
                current_price=pos.get('current_price', 0.0),
                pnl=pos.get('pnl', 0.0),
                market_value=pos.get('market_value', 0.0),
                risk_exposure=abs(pos.get('market_value', 0.0)) / portfolio_value if portfolio_value > 0 else 0,
                days_to_expiry=pos.get('days_to_expiry', 0),
                delta=delta,
                gamma=gamma,
                theta=theta,
                vega=vega
            )
            self.positions.append(position_risk)
    
    def check_position_size_limit(self, symbol: str, quantity: int, 
                                price: float) -> bool:
        """
        Check if a new position exceeds position size limits.
        
        Args:
            symbol: Trading symbol
            quantity: Number of shares/contracts
            price: Price per unit
            
        Returns:
            True if within limits, False otherwise
        """
        position_value = abs(quantity * price)
        max_position_value = self.portfolio_value * self.config.max_position_size
        
        if position_value > max_position_value:
            logger.warning(f"Position size limit exceeded for {symbol}: "
                          f"{position_value:,.2f} > {max_position_value:,.2f}")
            return False
        
        return True
    
    def check_portfolio_risk_limit(self) -> bool:
        """
        Check if total portfolio risk is within limits.
        
        Returns:
            True if within limits, False otherwise
        """
        total_risk_exposure = sum(pos.risk_exposure for pos in self.positions)
        max_risk_exposure = self.config.max_portfolio_risk
        
        if total_risk_exposure > max_risk_exposure:
            logger.warning(f"Portfolio risk limit exceeded: "
                          f"{total_risk_exposure:.2%} > {max_risk_exposure:.2%}")
            return False
        
        return True
    
    def check_concurrent_positions_limit(self) -> bool:
        """
        Check if number of concurrent positions is within limits.
        
        Returns:
            True if within limits, False otherwise
        """
        if len(self.positions) > self.config.max_concurrent_positions:
            logger.warning(f"Concurrent positions limit exceeded: "
                          f"{len(self.positions)} > {self.config.max_concurrent_positions}")
            return False
        
        return True
    
    def check_daily_loss_limit(self) -> bool:
        """
        Check if daily loss limit has been exceeded.
        
        Returns:
            True if within limits, False otherwise
        """
        if self.daily_losses <= -self.config.max_daily_loss_limit:
            logger.warning(f"Daily loss limit exceeded: "
                          f"{self.daily_losses:,.2f} <= -{self.config.max_daily_loss_limit:,.2f}")
            return False
        
        return True
    
    def check_margin_utilization(self) -> bool:
        """
        Check if margin utilization is within limits.
        
        Returns:
            True if within limits, False otherwise
        """
        if self.portfolio_value > 0:
            margin_utilization = (self.portfolio_value - self.available_margin) / self.portfolio_value
            if margin_utilization > self.config.margin_utilization_limit:
                logger.warning(f"Margin utilization limit exceeded: "
                              f"{margin_utilization:.2%} > {self.config.margin_utilization_limit:.2%}")
                return False
        
        return True
    
    def calculate_value_at_risk(self, confidence_level: float = 0.95) -> float:
        """
        Calculate Value at Risk (VaR) for the portfolio.
        
        Args:
            confidence_level: Confidence level for VaR calculation
            
        Returns:
            Value at Risk
        """
        if not self.positions:
            return 0.0
        
        # Simple parametric VaR calculation
        # In a real implementation, you would use historical simulation or Monte Carlo
        portfolio_returns = [pos.pnl / pos.market_value if pos.market_value != 0 else 0 
                           for pos in self.positions]
        
        if not portfolio_returns:
            return 0.0
        
        # Calculate standard deviation of returns
        std_dev = np.std(portfolio_returns)
        
        # Calculate VaR (simplified)
        var = self.portfolio_value * std_dev * np.sqrt(1)  # 1 day horizon
        
        return var
    
    def calculate_sharpe_ratio(self, risk_free_rate: float = 0.05) -> float:
        """
        Calculate Sharpe ratio of the portfolio.
        
        Args:
            risk_free_rate: Annual risk-free rate
            
        Returns:
            Sharpe ratio
        """
        if not self.positions:
            return 0.0
        
        # Calculate portfolio return
        total_pnl = sum(pos.pnl for pos in self.positions)
        portfolio_return = total_pnl / self.portfolio_value if self.portfolio_value > 0 else 0
        
        # Calculate portfolio risk (standard deviation of returns)
        portfolio_returns = [pos.pnl / pos.market_value if pos.market_value != 0 else 0 
                           for pos in self.positions]
        portfolio_risk = np.std(portfolio_returns) if portfolio_returns else 0
        
        # Calculate Sharpe ratio
        if portfolio_risk > 0:
            sharpe_ratio = (portfolio_return - risk_free_rate/252) / portfolio_risk * np.sqrt(252)
            return sharpe_ratio
        else:
            return 0.0
    
    def get_risk_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive risk report.
        
        Returns:
            Dictionary with risk metrics
        """
        total_risk_exposure = sum(pos.risk_exposure for pos in self.positions)
        total_positions = len(self.positions)
        margin_utilization = ((self.portfolio_value - self.available_margin) / 
                            self.portfolio_value if self.portfolio_value > 0 else 0)
        var = self.calculate_value_at_risk()
        sharpe_ratio = self.calculate_sharpe_ratio()
        
        report = {
            'portfolio_value': self.portfolio_value,
            'available_margin': self.available_margin,
            'total_positions': total_positions,
            'total_risk_exposure': total_risk_exposure,
            'daily_pnl': self.daily_pnl,
            'daily_losses': self.daily_losses,
            'margin_utilization': margin_utilization,
            'value_at_risk': var,
            'sharpe_ratio': sharpe_ratio,
            'risk_limits': {
                'max_portfolio_risk': self.config.max_portfolio_risk,
                'max_position_size': self.config.max_position_size,
                'max_daily_loss_limit': self.config.max_daily_loss_limit,
                'max_concurrent_positions': self.config.max_concurrent_positions,
                'margin_utilization_limit': self.config.margin_utilization_limit
            },
            'risk_status': {
                'position_size_ok': self.check_position_size_limit('', 1, 1),  # Dummy check
                'portfolio_risk_ok': self.check_portfolio_risk_limit(),
                'concurrent_positions_ok': self.check_concurrent_positions_limit(),
                'daily_loss_ok': self.check_daily_loss_limit(),
                'margin_utilization_ok': self.check_margin_utilization()
            }
        }
        
        return report
    
    def should_place_order(self, symbol: str, quantity: int, price: float) -> bool:
        """
        Check if an order should be placed based on risk limits.
        
        Args:
            symbol: Trading symbol
            quantity: Number of shares/contracts
            price: Price per unit
            
        Returns:
            True if order should be placed, False otherwise
        """
        checks = [
            self.check_position_size_limit(symbol, quantity, price),
            self.check_portfolio_risk_limit(),
            self.check_concurrent_positions_limit(),
            self.check_daily_loss_limit(),
            self.check_margin_utilization()
        ]
        
        return all(checks)
    
    def update_daily_pnl(self, pnl: float) -> None:
        """
        Update daily P&L and losses.
        
        Args:
            pnl: Profit/Loss for the day
        """
        self.daily_pnl += pnl
        if pnl < 0:
            self.daily_losses += pnl


def main():
    """Main function to demonstrate usage."""
    # Initialize risk manager
    config = RiskConfig()
    risk_manager = RiskManager(config)
    
    # Update portfolio state (example values)
    positions = [
        {
            'tradingsymbol': 'NIFTY24JAN20000CE',
            'quantity': -50,
            'average_price': 150.0,
            'current_price': 140.0,
            'pnl': 500.0,
            'market_value': -7000.0,
            'days_to_expiry': 15,
            'delta': -0.3
        },
        {
            'tradingsymbol': 'NIFTY24JAN19500PE',
            'quantity': -50,
            'average_price': 100.0,
            'current_price': 90.0,
            'pnl': 500.0,
            'market_value': -4500.0,
            'days_to_expiry': 15,
            'delta': 0.25
        }
    ]
    
    risk_manager.update_portfolio_state(
        portfolio_value=100000.0,
        available_margin=20000.0,
        positions=positions
    )
    
    # Check if we can place a new order
    can_place_order = risk_manager.should_place_order('NIFTY24JAN19000CE', -50, 75.0)
    print(f"Can place order: {can_place_order}")
    
    # Get risk report
    report = risk_manager.get_risk_report()
    print("\nRisk Report:")
    for key, value in report.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for sub_key, sub_value in value.items():
                print(f"    {sub_key}: {sub_value}")
        else:
            print(f"  {key}: {value}")


if __name__ == "__main__":
    main()