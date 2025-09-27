import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import os
import json

from models.models import Trade, Position
from models.enums import TransactionType, OrderType, ProductType
from utils.logging_utils import get_logger
from .mock_kite import MockKiteConnect
from config.config import OptionWheelConfig
from core.strategy import OptionWheelStrategy

logger = get_logger(__name__)

class NiftyBacktestingStrategy:
    """
    Backtesting strategy specifically for NIFTY options using historical data
    """
    
    def __init__(self, config: OptionWheelConfig, initial_capital: float = 100000.0):
        """
        Initialize the NIFTY backtesting strategy
        
        Args:
            config: OptionWheelConfig instance
            initial_capital: Initial capital for backtesting
        """
        self.config = config
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.current_portfolio_value = initial_capital
        self.current_underlying_price = 0.0
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.trade_history: List[Dict] = []
        self.performance_metrics = []
        
        # Transaction cost tracking
        self.total_fees_paid = 0.0
        self.total_stt_paid = 0.0
        self.total_brokerage_paid = 0.0
        self.total_taxes_paid = 0.0
        self.include_fees_in_backtest = os.getenv('INCLUDE_FEES_IN_BACKTEST', 'false').lower() == 'true'
        
        # Initialize mock Kite for backtesting
        self.kite = MockKiteConnect()
        
        # Initialize with mock data
        self.historical_data = {}
        self.data_index = 0
        self.current_date = None
        self.current_time = None
        
        # Strategy state for tracking
        self.cash_secured_puts_active = False
        self.covered_calls_active = False
        
        logger.info("NIFTY Backtesting Strategy initialized")
    
    def calculate_transaction_costs(self, trade_value: float, transaction_type: TransactionType, 
                                  order_type: str = "options") -> Dict[str, float]:
        """
        Calculate transaction costs for Zerodha F&O based on realistic fee structure
        
        Args:
            trade_value: Total value of the trade
            transaction_type: BUY or SELL
            order_type: Type of instrument ("options", "futures", "equity")
            
        Returns:
            Dictionary containing various cost components
        """
        if not self.include_fees_in_backtest:
            # If fees are not included, return zero costs
            return {
                'brokerage': 0.0,
                'stt': 0.0,
                'turnover_charges': 0.0,
                'gst': 0.0,
                'sebi_charges': 0.0,
                'stamp_duty': 0.0,
                'total_fees': 0.0
            }
        
        # Zerodha F&O charges structure
        brokerage = min(20, 0.03 * trade_value / 100)  # ₹20 per order or 0.03% of trade value, whichever is lower
        
        # STT (Securities Transaction Tax) - applicable only on sell side for options
        stt = 0.0
        if transaction_type == TransactionType.SELL and order_type == "options":
            stt = 0.017 * trade_value / 100  # 0.017% on sell side
        
        # Turnover charges
        turnover_charges = 0.00325 * trade_value / 100  # 0.00325% of trade value
        
        # GST on brokerage (18%)
        gst = 0.18 * brokerage
        
        # SEBI charges (₹10 per crore)
        sebi_charges = 10 * trade_value / 10000000  # ₹10 per crore of turnover
        
        # Stamp duty (varies by state, using 0.003% as an average)
        stamp_duty = 0.003 * trade_value / 100
        
        # Total fees
        total_fees = brokerage + stt + turnover_charges + gst + sebi_charges + stamp_duty
        
        return {
            'brokerage': brokerage,
            'stt': stt,
            'turnover_charges': turnover_charges,
            'gst': gst,
            'sebi_charges': sebi_charges,
            'stamp_duty': stamp_duty,
            'total_fees': total_fees
        }

    def apply_slippage(self, price: float, transaction_type: TransactionType, bid_price: float = None, ask_price: float = None) -> float:
        """
        Apply slippage to the trade price based on market conditions
        
        Args:
            price: Base price for the trade
            transaction_type: BUY or SELL
            bid_price: Available bid price (for sell orders)
            ask_price: Available ask price (for buy orders)
            
        Returns:
            Price after slippage adjustment
        """
        # Base slippage percentage (e.g., 0.05% for high-volume options)
        base_slippage_pct = 0.0005  # 0.05%
        
        # Add random component to make it more realistic
        import random
        slippage_factor = random.uniform(0.0002, 0.002)  # Random slippage between 0.02% and 0.2%
        
        if transaction_type == TransactionType.BUY:
            # For buy orders, slippage means paying more than expected
            slippage_price = price * (1 + slippage_factor)
            # If ask price is provided, use it as a limit
            if ask_price and ask_price > price:
                slippage_price = min(slippage_price, ask_price)
        else:  # SELL
            # For sell orders, slippage means receiving less than expected
            slippage_price = price * (1 - slippage_factor)
            # If bid price is provided, use it as a limit
            if bid_price and bid_price < price:
                slippage_price = max(slippage_price, bid_price)
        
        return slippage_price

    def simulate_fill_probability(self, price: float, bid: float, ask: float, order_type: str = "MARKET") -> Tuple[bool, float]:
        """
        Simulate whether an order would get filled and at what price
        
        Args:
            price: Target price for trade
            bid: Current bid price
            ask: Current ask price
            order_type: MARKET or LIMIT
            
        Returns:
            Tuple of (is_filled, fill_price)
        """
        if order_type == "MARKET":
            # Market orders always get filled but may experience slippage
            if self.current_underlying_price > 0:
                # For market orders, fill at midpoint of bid-ask or actual traded price with slippage
                mid_price = (bid + ask) / 2 if bid and ask else price
                filled_price = self.apply_slippage(mid_price, TransactionType.BUY if price >= mid_price else TransactionType.SELL, bid, ask)
                return True, filled_price
            else:
                return True, price
        else:  # LIMIT ORDER
            # Limit orders may not get filled depending on market price vs limit price
            if bid and ask:
                if price >= ask and TransactionType.SELL:
                    # Limit sell order above ask - might get filled at limit price or better
                    return random.random() > 0.3, price  # 70% fill probability
                elif price <= bid and TransactionType.BUY:
                    # Limit buy order below bid - might get filled at limit price or better
                    return random.random() > 0.3, price  # 70% fill probability
                elif bid < price < ask:
                    # Limit price in the spread - high probability of fill at a reasonable price
                    return random.random() > 0.1, price  # 90% fill probability
                else:
                    # Limit far from market - low probability of fill
                    return random.random() > 0.9, price  # 10% fill probability
            else:
                # If no bid/ask available, assume market order behavior
                filled_price = self.apply_slippage(price, TransactionType.BUY if random.random() > 0.5 else TransactionType.SELL)
                return True, filled_price
    
    def load_historical_data(self, symbol: str = "NIFTY", 
                           start_date: datetime = None, 
                           end_date: datetime = None) -> bool:
        """
        Load historical data for backtesting
        
        Args:
            symbol: Symbol to load data for
            start_date: Start date for backtesting
            end_date: End date for backtesting
            
        Returns:
            True if data loaded successfully, False otherwise
        """
        try:
            # For now, generate synthetic data if not available
            # In a real implementation, this would load from files or API
            from .sample_data_generator import generate_sample_stock_data, generate_sample_option_chain_data
            
            if start_date is None:
                start_date = datetime.now() - timedelta(days=90)  # 3 months of data
            if end_date is None:
                end_date = datetime.now()
            
            # Generate underlying price history
            self.underlying_data = generate_sample_stock_data(symbol, start_date, end_date)
            
            # Generate option chain history
            self.option_chain_data = []
            for date in self.underlying_data['date']:
                # Get underlying price for this date
                date_price = self.underlying_data[self.underlying_data['date'] == date]['close'].iloc[0]
                
                # Generate option chain for this date
                option_chain = generate_sample_option_chain_data(
                    symbol, 
                    date_price, 
                    num_strikes=11,  # Fewer strikes for faster processing
                    days_to_expiry=30
                )
                option_chain['date'] = date
                self.option_chain_data.append(option_chain)
            
            logger.info(f"Loaded historical data for {symbol} from {start_date} to {end_date}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading historical data: {str(e)}")
            return False
    
    def run_backtest(self, start_date: datetime = None, end_date: datetime = None) -> Dict:
        """
        Run the backtesting simulation
        
        Args:
            start_date: Start date for backtesting
            end_date: End date for backtesting
            
        Returns:
            Dictionary with backtesting results
        """
        logger.info("Starting NIFTY backtesting...")
        
        if not self.load_historical_data("NIFTY", start_date, end_date):
            logger.error("Failed to load historical data for backtesting")
            return {}
        
        # Initialize dates
        if start_date is None:
            start_date = self.underlying_data['date'].min()
        if end_date is None:
            end_date = self.underlying_data['date'].max()
        
        # Get date range
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        # Filter for weekdays only
        date_range = [d for d in date_range if d.weekday() < 5]
        
        # Initialize performance tracking
        initial_portfolio_value = self.current_capital
        max_portfolio_value = initial_portfolio_value
        min_portfolio_value = initial_portfolio_value
        
        # Run backtesting loop
        for date in date_range:
            self.current_date = date
            self.current_time = datetime.combine(date, datetime.min.time())
            
            # Update underlying price
            day_data = self.underlying_data[self.underlying_data['date'] == date]
            if not day_data.empty:
                self.current_underlying_price = day_data['close'].iloc[0]
            
            # Check if it's market hours
            # For backtesting, we'll simulate market hours execution
            if date.weekday() < 5:  # Monday to Friday
                # Execute strategy for this day
                self._execute_strategy_for_day()
            
            # Update portfolio value and track metrics
            current_portfolio_value = self._calculate_portfolio_value()
            self.current_portfolio_value = current_portfolio_value
            
            # Update drawdown tracking
            if current_portfolio_value > max_portfolio_value:
                max_portfolio_value = current_portfolio_value
            if current_portfolio_value < min_portfolio_value:
                min_portfolio_value = current_portfolio_value
            
            # Record performance for this day
            self.performance_metrics.append({
                'date': date,
                'portfolio_value': current_portfolio_value,
                'capital': self.current_capital,
                'underlying_price': self.current_underlying_price,
                'positions_count': len(self.positions),
                'max_portfolio_value': max_portfolio_value,
                'min_portfolio_value': min_portfolio_value
            })
        
        # Calculate final performance metrics
        final_results = self._calculate_performance_metrics(initial_portfolio_value)
        logger.info("Backtesting completed")
        
        return final_results
    
    def _execute_strategy_for_day(self):
        """
        Execute the options wheel strategy for a single day
        """
        try:
            # Get current option chain data for this date
            option_chain = self._get_option_chain_for_date(self.current_date)
            if option_chain is None:
                logger.warning(f"No option chain data for {self.current_date}")
                return
            
            # Determine strategy based on existing positions
            has_stock_position = any(p.quantity > 0 for p in self.positions.values())
            
            if not has_stock_position:
                # Execute Cash-Secured Puts strategy
                self._execute_cash_secured_puts(option_chain)
            else:
                # Execute Covered Calls strategy
                self._execute_covered_calls(option_chain)
            
            # Check existing positions for profit target or stop loss
            self._check_position_exit_criteria(option_chain)
            
        except Exception as e:
            logger.error(f"Error executing strategy for {self.current_date}: {str(e)}")
    
    def _get_option_chain_for_date(self, date: datetime) -> Optional[pd.DataFrame]:
        """
        Get option chain data for a specific date
        
        Args:
            date: Date to get option chain for
            
        Returns:
            DataFrame with option chain data or None if not available
        """
        for oc_data in self.option_chain_data:
            if (oc_data['date'] == date).any():
                return oc_data
        return None
    
    def _execute_cash_secured_puts(self, option_chain: pd.DataFrame):
        """
        Execute Cash-Secured Puts strategy: sell OTM puts
        
        Args:
            option_chain: Current option chain data
        """
        try:
            # Filter for PUT options
            puts = option_chain[(option_chain['instrument_type'] == 'PE')]
            
            # Filter for OTM puts (strike < underlying price)
            otm_puts = puts[puts['strike'] < self.current_underlying_price]
            
            # Filter by delta range (0.15 to 0.25 as specified in the strategy)
            # Note: Our sample data has simplified deltas
            suitable_puts = otm_puts[
                (otm_puts['delta'].abs() >= self.config.otm_delta_range_low) & 
                (otm_puts['delta'].abs() <= self.config.otm_delta_range_high)
            ]
            
            # Filter by minimum open interest
            suitable_puts = suitable_puts[suitable_puts['oi'] >= self.config.min_open_interest]
            
            # Sort by premium (last_price) descending to get best premium
            suitable_puts = suitable_puts.sort_values('last_price', ascending=False)
            
            # Check risk limits before placing order
            if len(self.positions) >= self.config.max_concurrent_positions:
                logger.info("Max concurrent positions limit reached")
                return
            
            # Select the best PUT option
            if not suitable_puts.empty:
                best_put = suitable_puts.iloc[0]
                
                # Calculate required capital (for cash-secured put)
                # Need to have funds to buy the underlying if assigned
                required_capital = best_put['strike'] * 50  # NIFTY lot size is 50
                
                # Check if we have enough capital
                if self.current_capital >= required_capital:
                    # Place order for 1 lot
                    order_id = f"BT{len(self.trades) + 1:06d}"
                    
                    # Apply slippage to the trade price
                    slippage_price = self.apply_slippage(
                        best_put['last_price'], 
                        TransactionType.SELL,
                        bid_price=best_put.get('bid_price', best_put['last_price'] * 0.99),
                        ask_price=best_put.get('ask_price', best_put['last_price'] * 1.01)
                    )
                    
                    # Simulate fill probability
                    filled, fill_price = self.simulate_fill_probability(
                        best_put['last_price'],
                        best_put.get('bid_price', best_put['last_price'] * 0.99),
                        best_put.get('ask_price', best_put['last_price'] * 1.01),
                        "MARKET"
                    )
                    
                    # If not filled, skip this trade
                    if not filled:
                        logger.info(f"Order for {best_put['tradingsymbol']} not filled due to market conditions")
                        pass
                    
                    # Use the fill price instead of original price
                    executed_price = fill_price
                    
                    # Create a mock trade
                    trade = Trade(
                        order_id=order_id,
                        symbol=best_put['tradingsymbol'],
                        exchange='NFO',
                        instrument_token=best_put['instrument_token'],
                        transaction_type=TransactionType.SELL,
                        order_type=OrderType.MARKET,
                        product=ProductType.MIS,  # Using MIS for intraday for backtesting
                        quantity=50,  # 1 lot of NIFTY
                        price=executed_price,
                        average_price=executed_price,
                        filled_quantity=50,
                        status='COMPLETE'
                    )
                    
                    # Calculate transaction costs
                    trade_value = best_put['last_price'] * 50
                    transaction_costs = self.calculate_transaction_costs(
                        trade_value, 
                        TransactionType.SELL, 
                        "options"
                    )
                    
                    # Update capital and portfolio
                    premium_received = best_put['last_price'] * 50
                    net_premium = premium_received - transaction_costs['total_fees']
                    self.current_capital += net_premium
                    
                    # Track fees paid
                    self.total_fees_paid += transaction_costs['total_fees']
                    self.total_stt_paid += transaction_costs['stt']
                    self.total_brokerage_paid += transaction_costs['brokerage']
                    self.total_taxes_paid += transaction_costs['gst'] + transaction_costs['turnover_charges'] + transaction_costs['sebi_charges'] + transaction_costs['stamp_duty']
                    
                    # Add to trades
                    self.trades.append(trade)
                    
                    # Create a position entry
                    position = Position(
                        symbol=best_put['tradingsymbol'],
                        exchange='NFO',
                        instrument_token=best_put['instrument_token'],
                        product=ProductType.MIS,
                        quantity=-50,  # Short position
                        average_price=best_put['last_price'],
                        last_price=best_put['last_price'],
                        sell_quantity=50,
                        sell_value=premium_received
                    )
                    self.positions[best_put['tradingsymbol']] = position
                    
                    # Record trade in history
                    self.trade_history.append({
                        'date': self.current_date,
                        'order_id': order_id,
                        'symbol': best_put['tradingsymbol'],
                        'action': 'SELL_PUT',
                        'quantity': 50,
                        'price': best_put['last_price'],
                        'premium': premium_received
                    })
                    
                    logger.info(f"Cash-Secured Put placed: {best_put['tradingsymbol']} at {best_put['last_price']}, premium: {premium_received}")
                    
                    # Set active strategy flag
                    self.cash_secured_puts_active = True
                else:
                    logger.info(f"Insufficient capital to place Cash-Secured Put. Required: {required_capital}, Available: {self.current_capital}")
            
        except Exception as e:
            logger.error(f"Error executing Cash-Secured Puts: {str(e)}")
    
    def _execute_covered_calls(self, option_chain: pd.DataFrame):
        """
        Execute Covered Calls strategy: sell OTM calls against stock holdings
        
        Args:
            option_chain: Current option chain data
        """
        try:
            # Find any stock positions (though in NIFTY context, this would be futures or ETF)
            # For this example, we'll assume we're working with futures/ETF
            
            # In the NIFTY options wheel, typically when we have "stock" it means we were assigned
            # the underlying from a cash-secured put. We'll look for any positive quantity positions.
            
            # Look for any position that represents the underlying
            underlying_positions = {k: v for k, v in self.positions.items() if v.quantity > 0}
            
            if not underlying_positions:
                return  # Nothing to write calls against
            
            # For this example, we'll focus on the main strategy of cash-secured puts
            # since covered calls are executed when we have stock, which happens after
            # put assignment but we don't have a mechanism to track that here
            
        except Exception as e:
            logger.error(f"Error executing Covered Calls: {str(e)}")
    
    def _check_position_exit_criteria(self, option_chain: pd.DataFrame):
        """
        Check existing positions for profit target or stop loss exit
        
        Args:
            option_chain: Current option chain data
        """
        try:
            positions_to_remove = []
            
            for symbol, position in self.positions.items():
                # Look up current price for this symbol
                current_data = option_chain[option_chain['tradingsymbol'] == symbol]
                if current_data.empty:
                    continue
                
                current_price = current_data['last_price'].iloc[0]
                
                # Calculate P&L
                if position.quantity < 0:  # Short position
                    pnl = (position.average_price - current_price) * abs(position.quantity)
                else:  # Long position
                    pnl = (current_price - position.average_price) * position.quantity
                
                # Calculate percentage P&L
                initial_value = position.average_price * abs(position.quantity)
                if initial_value > 0:
                    pnl_percentage = pnl / initial_value
                else:
                    continue
                
                # Check profit target (50% of premium received for short options)
                profit_target = self.config.profit_target_percentage
                if pnl_percentage >= profit_target:
                    # Close position at profit target
                    self._close_position(symbol, position, current_price, "PROFIT_TARGET")
                    positions_to_remove.append(symbol)
                    logger.info(f"Closed position {symbol} at profit target: {pnl_percentage:.2%}")
                
                # Check stop loss (100% of premium for short options)
                stop_loss = -self.config.loss_limit_percentage
                if pnl_percentage <= stop_loss:
                    # Close position at stop loss
                    self._close_position(symbol, position, current_price, "STOP_LOSS")
                    positions_to_remove.append(symbol)
                    logger.info(f"Closed position {symbol} at stop loss: {pnl_percentage:.2%}")
            
            # Remove closed positions
            for symbol in positions_to_remove:
                if symbol in self.positions:
                    del self.positions[symbol]
            
        except Exception as e:
            logger.error(f"Error checking position exit criteria: {str(e)}")
    
    def _close_position(self, symbol: str, position: Position, close_price: float, reason: str):
        """
        Close a position and record the trade
        
        Args:
            symbol: Symbol of the position to close
            position: Position object
            close_price: Price at which to close
            reason: Reason for closing (e.g., "PROFIT_TARGET", "STOP_LOSS", "EXPIRY")
        """
        try:
            # Calculate P&L
            if position.quantity < 0:  # Short position being bought back
                pnl = (position.average_price - close_price) * abs(position.quantity)
            else:  # Long position being sold
                pnl = (close_price - position.average_price) * position.quantity
            
            # Calculate transaction costs for closing trade
            transaction_value = close_price * abs(position.quantity)
            transaction_costs = self.calculate_transaction_costs(
                transaction_value, 
                TransactionType.BUY if position.quantity < 0 else TransactionType.SELL, 
                "options"
            )
            
            # Update capital after accounting for costs
            net_transaction_value = transaction_value - transaction_costs['total_fees']
            if position.quantity < 0:  # Closing short position
                self.current_capital += net_transaction_value
            else:  # Closing long position
                self.current_capital += net_transaction_value
            
            # Track fees paid
            self.total_fees_paid += transaction_costs['total_fees']
            self.total_stt_paid += transaction_costs['stt']
            self.total_brokerage_paid += transaction_costs['brokerage']
            self.total_taxes_paid += transaction_costs['gst'] + transaction_costs['turnover_charges'] + transaction_costs['sebi_charges'] + transaction_costs['stamp_duty']
            
            # Apply slippage to the closing trade price
            slippage_price = self.apply_slippage(
                close_price, 
                TransactionType.BUY if position.quantity < 0 else TransactionType.SELL,
                bid_price=close_price * 0.99,  # Mock bid/ask prices if not provided
                ask_price=close_price * 1.01
            )
            
            # Simulate fill probability for closing trade
            filled, fill_price = self.simulate_fill_probability(
                close_price,
                close_price * 0.99,  # Mock bid
                close_price * 1.01,  # Mock ask
                "MARKET"
            )
            
            # If not filled, skip this trade closure
            if not filled:
                logger.info(f"Closing order for {symbol} not filled due to market conditions")
                return
            
            # Use the fill price instead of original close price
            executed_close_price = fill_price
            
            # Create closing trade
            order_id = f"BTC{len(self.trades) + 1:06d}"
            
            trade = Trade(
                order_id=order_id,
                symbol=symbol,
                exchange=position.exchange,
                instrument_token=position.instrument_token,
                transaction_type=TransactionType.BUY if position.quantity < 0 else TransactionType.SELL,
                order_type=OrderType.MARKET,
                product=position.product,
                quantity=abs(position.quantity),
                price=executed_close_price,
                average_price=executed_close_price,
                filled_quantity=abs(position.quantity),
                status='COMPLETE'
            )
            
            # Add to trades
            self.trades.append(trade)
            
            # Record trade in history
            self.trade_history.append({
                'date': self.current_date,
                'order_id': order_id,
                'symbol': symbol,
                'action': f'CLOSE_{reason}',
                'quantity': abs(position.quantity),
                'price': close_price,
                'pnl': pnl,
                'reason': reason
            })
            
            # Update total P&L
            position.realized_pnl += pnl
            logger.info(f"Closed position {symbol} at {close_price} for P&L: {pnl:.2f} (Reason: {reason})")
            
        except Exception as e:
            logger.error(f"Error closing position for {symbol}: {str(e)}")
    
    def _calculate_portfolio_value(self) -> float:
        """
        Calculate current portfolio value
        
        Returns:
            Current portfolio value
        """
        # Portfolio value = current capital + value of all positions
        positions_value = 0
        
        for symbol, position in self.positions.items():
            # For options, we'd need current prices to calculate value
            # For simplicity in backtesting, just return capital
            # In a real system, we would calculate the current value of open options positions
            pass
        
        return self.current_capital
    
    def _calculate_performance_metrics(self, initial_capital: float) -> Dict:
        """
        Calculate performance metrics for the backtest
        
        Args:
            initial_capital: Initial capital at the start of backtest
            
        Returns:
            Dictionary with performance metrics
        """
        if not self.performance_metrics:
            return {}
        
        # Convert performance metrics to DataFrame for analysis
        perf_df = pd.DataFrame(self.performance_metrics)
        
        # Calculate returns
        final_capital = self.current_capital
        total_return = (final_capital - initial_capital) / initial_capital * 100
        
        # Calculate max drawdown
        if 'portfolio_value' in perf_df.columns:
            portfolio_values = perf_df['portfolio_value']
            running_max = portfolio_values.expanding().max()
            drawdown = (portfolio_values - running_max) / running_max
            max_drawdown = drawdown.min() * 100
        
        # Calculate win rate and other metrics
        total_trades = len(self.trades)
        
        # Find profitable trades from trade history
        profitable_trades = 0
        total_pnl = 0
        winning_pnl = 0
        losing_pnl = 0
        
        for trade_record in self.trade_history:
            if 'pnl' in trade_record:
                pnl = trade_record['pnl']
                total_pnl += pnl
                if pnl > 0:
                    profitable_trades += 1
                    winning_pnl += pnl
                else:
                    losing_pnl += pnl
        
        win_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Calculate profit factor
        profit_factor = abs(winning_pnl / losing_pnl) if losing_pnl != 0 else float('inf')
        
        # Calculate Sharpe ratio (simplified)
        daily_returns = []
        for i in range(1, len(self.performance_metrics)):
            prev_value = self.performance_metrics[i-1]['portfolio_value']
            curr_value = self.performance_metrics[i]['portfolio_value']
            if prev_value != 0:
                daily_return = (curr_value - prev_value) / prev_value
                daily_returns.append(daily_return)
        
        if daily_returns:
            avg_return = np.mean(daily_returns)
            volatility = np.std(daily_returns) if len(daily_returns) > 1 else 0
            sharpe_ratio = (avg_return / volatility) * np.sqrt(252) if volatility != 0 else 0  # Annualized
        else:
            sharpe_ratio = 0
        
        # Compile results
        results = {
            'initial_capital': initial_capital,
            'final_capital': final_capital,
            'total_return_percentage': total_return,
            'total_pnl': final_capital - initial_capital,
            'total_trades': total_trades,
            'profitable_trades': profitable_trades,
            'win_rate': win_rate,
            'max_drawdown_percentage': max_drawdown,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'trades_history': self.trade_history,
            'performance_over_time': self.performance_metrics,
            'positions_at_end': len(self.positions),
            'strategy_periods': len(self.performance_metrics),
            'transaction_costs': {
                'total_fees_paid': self.total_fees_paid,
                'total_stt_paid': self.total_stt_paid,
                'total_brokerage_paid': self.total_brokerage_paid,
                'total_taxes_paid': self.total_taxes_paid,
                'include_fees_in_calculation': self.include_fees_in_backtest
            }
        }
        
        return results
    
    def run_comparison_with_buy_hold(self) -> Tuple[Dict, Dict]:
        """
        Run comparison between the strategy and a simple buy-and-hold approach
        
        Returns:
            Tuple of (strategy_results, buy_hold_results)
        """
        # Run the main strategy backtest
        strategy_results = self.run_backtest()
        
        # For buy-and-hold, calculate what would have happened if we just held NIFTY
        if len(self.underlying_data) > 1:
            start_price = self.underlying_data['close'].iloc[0]
            end_price = self.underlying_data['close'].iloc[-1]
            
            # Calculate returns for buy-and-hold of NIFTY equivalent
            # Assuming we could buy NIFTY ETF with our initial capital
            # This is a simplified calculation
            nifty_shares = self.initial_capital / start_price
            buy_hold_final_value = nifty_shares * end_price
            buy_hold_return = (buy_hold_final_value - self.initial_capital) / self.initial_capital * 100
            
            buy_hold_results = {
                'initial_capital': self.initial_capital,
                'final_capital': buy_hold_final_value,
                'total_return_percentage': buy_hold_return,
                'total_pnl': buy_hold_final_value - self.initial_capital,
                'strategy': 'Buy and Hold NIFTY'
            }
        else:
            buy_hold_results = {}
        
        return strategy_results, buy_hold_results


# Example usage
if __name__ == "__main__":
    # Create a sample config
    config = OptionWheelConfig()
    
    # Initialize backtesting strategy
    backtester = NiftyBacktestingStrategy(config, initial_capital=100000)
    
    # Define date range for backtesting
    start_date = datetime.now() - timedelta(days=60)
    end_date = datetime.now()
    
    # Run backtesting
    results = backtester.run_backtest(start_date, end_date)
    
    # Print results
    if results:
        print("Backtesting Results:")
        print(f"Initial Capital: ₹{results['initial_capital']:,.2f}")
        print(f"Final Capital: ₹{results['final_capital']:,.2f}")
        print(f"Total Return: {results['total_return_percentage']:.2f}%")
        print(f"Total P&L: ₹{results['total_pnl']:,.2f}")
        print(f"Total Trades: {results['total_trades']}")
        print(f"Profitable Trades: {results['profitable_trades']}")
        print(f"Win Rate: {results['win_rate']:.2f}%")
        print(f"Max Drawdown: {results['max_drawdown_percentage']:.2f}%")
        print(f"Profit Factor: {results['profit_factor']:.2f}")
        print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
        print(f"Positions at End: {results['positions_at_end']}")
    else:
        print("Backtesting failed to return results")
    
    print("Backtesting completed successfully!")