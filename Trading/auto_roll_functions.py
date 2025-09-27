"""
Auto-rolling functionality for the Options Wheel Strategy
"""

import re
from datetime import datetime
from typing import Optional, Tuple
from models.models import Position

def check_and_roll_positions(strategy, config):
    """
    Check existing positions for auto-rolling eligibility (before expiry)
    Rolls unprofitable options down & out for puts or up & out for calls
    
    Args:
        strategy: Strategy instance
        config: Configuration object
    """
    try:
        if not config.enable_auto_roll:
            return  # Auto-roll is disabled
        
        # Get current underlying price for reference
        underlying_price = strategy.get_underlying_price(config.symbol)
        if not underlying_price:
            return
        
        # Check each position for rolling eligibility
        rolled_positions = []
        for symbol, position in list(strategy.current_positions.items()):
            # Skip if not an options position
            if not _is_options_position(symbol):
                continue
            
            # Get option details
            option_details = _parse_option_symbol(symbol)
            if not option_details:
                continue
            
            strike_price, option_type, expiry_date = option_details
            
            # Calculate days to expiry
            if expiry_date:
                days_to_expiry = (expiry_date.date() - datetime.now().date()).days
                # Only consider rolling if DTE <= 1 (near expiry)
                if days_to_expiry > 1:
                    continue
            
            # Calculate current P&L for this position
            current_pnl = _calculate_position_pnl(position, underlying_price)
            
            # Check if position is unprofitable (loss exceeds threshold)
            avg_cost = position.average_price * abs(position.quantity)
            if avg_cost > 0:
                pnl_percentage = current_pnl / avg_cost
                
                # Roll if loss >= 50% of premium received (for short options)
                # Or if it's a long option with significant loss
                should_roll = (
                    (position.quantity < 0 and pnl_percentage <= -0.5) or  # Short position loss
                    (position.quantity > 0 and pnl_percentage <= -0.3)      # Long position loss
                )
                
                if should_roll:
                    # Execute roll based on option type
                    if option_type == 'PUT':
                        success = _roll_put_position_down_out(strategy, symbol, position, underlying_price)
                    else:  # CALL
                        success = _roll_call_position_up_out(strategy, symbol, position, underlying_price)
                    
                    if success:
                        rolled_positions.append(symbol)
        
        return rolled_positions
        
    except Exception as e:
        return []

def _is_options_position(symbol: str) -> bool:
    """
    Check if a symbol represents an options position
    
    Args:
        symbol: Trading symbol
        
    Returns:
        True if symbol represents an options contract, False otherwise
    """
    # Options symbols typically contain CE (call) or PE (put)
    return 'CE' in symbol or 'PE' in symbol

def _parse_option_symbol(symbol: str) -> Optional[Tuple[int, str, datetime]]:
    """
    Parse option symbol to extract strike price, option type, and expiry
    
    Args:
        symbol: Trading symbol
        
    Returns:
        Tuple of (strike_price, option_type, expiry_date) or None if parsing fails
    """
    try:
        # Pattern for typical Indian options symbols: NIFTY2140814950CE
        # Extract strike (consecutive digits) and CE/PE at the end
        match = re.search(r'(\d+)(CE|PE)$', symbol)
        if match:
            strike_part = match.group(1)
            option_type = match.group(2)
            strike_price = int(strike_part)
            
            # Try to extract expiry date (format YYMMDD before strike)
            expiry_match = re.search(r'(\d{6})\d+CE|PE$', symbol)
            expiry_date = None
            if expiry_match:
                try:
                    expiry_str = expiry_match.group(1)
                    # Convert YYMMDD to datetime
                    year = int(expiry_str[:2]) + 2000  # 21 becomes 2021
                    month = int(expiry_str[2:4])
                    day = int(expiry_str[4:6])
                    expiry_date = datetime(year, month, day)
                except:
                    pass
            
            return (strike_price, option_type, expiry_date)
        
        return None
    except Exception:
        return None

def _calculate_position_pnl(position: Position, underlying_price: float) -> float:
    """
    Calculate P&L for a position
    
    Args:
        position: Position object
        underlying_price: Current underlying price
        
    Returns:
        P&L value
    """
    try:
        if position.quantity < 0:  # Short position
            pnl = (position.average_price - underlying_price) * abs(position.quantity)
        else:  # Long position
            pnl = (underlying_price - position.average_price) * position.quantity
        
        return pnl
    except Exception:
        return 0.0

def _roll_put_position_down_out(strategy, symbol: str, position: Position, underlying_price: float) -> bool:
    """
    Roll a put position down & out (to a lower strike or later expiry)
    
    Args:
        strategy: Strategy instance
        symbol: Original position symbol
        position: Position object
        underlying_price: Current underlying price
        
    Returns:
        True if roll successful, False otherwise
    """
    try:
        # Close existing position
        close_success = strategy.close_position(symbol, "AUTO_ROLL")
        if not close_success:
            return False
        
        # In a real implementation, we would:
        # 1. Fetch current option chain
        # 2. Find put with lower strike price (down) or same strike with later expiry (out)
        # 3. Place new sell order for the selected put
        # 4. Update position tracking
        
        return True
    except Exception:
        return False

def _roll_call_position_up_out(strategy, symbol: str, position: Position, underlying_price: float) -> bool:
    """
    Roll a call position up & out (to a higher strike or later expiry)
    
    Args:
        strategy: Strategy instance
        symbol: Original position symbol
        position: Position object
        underlying_price: Current underlying price
        
    Returns:
        True if roll successful, False otherwise
    """
    try:
        # Close existing position
        close_success = strategy.close_position(symbol, "AUTO_ROLL")
        if not close_success:
            return False
        
        # In a real implementation, we would:
        # 1. Fetch current option chain
        # 2. Find call with higher strike price (up) or same strike with later expiry (out)
        # 3. Place new sell order for the selected call
        # 4. Update position tracking
        
        return True
    except Exception:
        return False