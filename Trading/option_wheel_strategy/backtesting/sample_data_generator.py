"""
Sample data generator for NIFTY options backtesting.
"""
import pandas as pd
import numpy as np
import datetime
import os
from typing import List, Dict, Any

def generate_sample_nifty_data(days: int = 30, 
                             start_date: datetime.date = None) -> pd.DataFrame:
    """
    Generate sample NIFTY options data for backtesting.
    
    Args:
        days: Number of days of data to generate
        start_date: Start date for data generation
        
    Returns:
        DataFrame with sample NIFTY options data
    """
    if start_date is None:
        start_date = datetime.date.today() - datetime.timedelta(days=days)
    
    data = []
    
    # Generate data for each day
    for i in range(days):
        current_date = start_date + datetime.timedelta(days=i)
        
        # Skip weekends
        if current_date.weekday() >= 5:
            continue
            
        # Simulate underlying NIFTY price with some randomness
        base_price = 18000 + (i * 20) + np.random.normal(0, 100)  # Trending upward with noise
        
        # Generate expiry dates (weekly and monthly)
        # Weekly expiries on Thursdays
        weekly_expiry = current_date + datetime.timedelta(days=(3 - current_date.weekday()) % 7)
        if weekly_expiry <= current_date:
            weekly_expiry += datetime.timedelta(days=7)
            
        # Monthly expiry (last Thursday of the month)
        next_month = current_date.replace(day=28) + datetime.timedelta(days=4)
        monthly_expiry = next_month - datetime.timedelta(days=next_month.weekday() - 3)
        if monthly_expiry <= current_date:
            monthly_expiry += datetime.timedelta(days=30)
        
        # Generate strike prices around the current underlying price
        strikes = np.arange(base_price - 1000, base_price + 1050, 50)  # 50 point intervals
        
        # Generate options data for both expiries
        for expiry in [weekly_expiry, monthly_expiry]:
            days_to_expiry = (expiry - current_date).days
            
            for strike in strikes:
                # Calculate moneyness
                moneyness = (strike - base_price) / base_price
                
                # Generate realistic option prices using simplified Black-Scholes logic
                # This is a very simplified approximation for demonstration
                time_value = max(0.1, days_to_expiry / 365.0)
                volatility = 0.15  # 15% volatility
                
                # Calculate intrinsic value
                call_intrinsic = max(0, base_price - strike)
                put_intrinsic = max(0, strike - base_price)
                
                # Calculate time value component
                time_value_component = base_price * volatility * np.sqrt(time_value) * 0.4
                
                # Calculate option prices
                call_price = call_intrinsic + time_value_component * (1 - abs(moneyness))
                put_price = put_intrinsic + time_value_component * (1 - abs(moneyness))
                
                # Ensure minimum price
                call_price = max(0.05, call_price)
                put_price = max(0.05, put_price)
                
                # Generate Greeks (simplified)
                call_delta = min(1.0, max(0.0, 0.5 + moneyness))
                put_delta = max(-1.0, min(0.0, -0.5 + moneyness))
                
                # Generate open interest (more for at-the-money options)
                oi_factor = 1 - abs(moneyness)  # Higher for ATM
                open_interest = int(1000 + (5000 * oi_factor) + np.random.normal(0, 1000))
                open_interest = max(0, open_interest)
                
                # Add call option data
                data.append({
                    'DATE': current_date,
                    'TIMESTAMP': current_date,
                    'SYMBOL': 'NIFTY',
                    'EXPIRY_DT': expiry,
                    'STRIKE_PR': strike,
                    'OPTION_TYP': 'CE',
                    'OPEN': call_price,
                    'HIGH': call_price * 1.05,
                    'LOW': call_price * 0.95,
                    'CLOSE': call_price,
                    'SETTLE_PR': call_price,
                    'CONTRACTS': int(open_interest / 100),
                    'VAL_INLAKH': call_price * open_interest * 0.01,
                    'OPEN_INT': open_interest,
                    'CHG_IN_OI': int(open_interest * 0.1),
                    'DELTA': call_delta
                })
                
                # Add put option data
                data.append({
                    'DATE': current_date,
                    'TIMESTAMP': current_date,
                    'SYMBOL': 'NIFTY',
                    'EXPIRY_DT': expiry,
                    'STRIKE_PR': strike,
                    'OPTION_TYP': 'PE',
                    'OPEN': put_price,
                    'HIGH': put_price * 1.05,
                    'LOW': put_price * 0.95,
                    'CLOSE': put_price,
                    'SETTLE_PR': put_price,
                    'CONTRACTS': int(open_interest / 100),
                    'VAL_INLAKH': put_price * open_interest * 0.01,
                    'OPEN_INT': open_interest,
                    'CHG_IN_OI': int(open_interest * 0.1),
                    'DELTA': put_delta
                })
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Convert date columns
    df['DATE'] = pd.to_datetime(df['DATE'])
    df['TIMESTAMP'] = pd.to_datetime(df['TIMESTAMP'])
    df['EXPIRY_DT'] = pd.to_datetime(df['EXPIRY_DT'])
    
    return df


def save_sample_data(data_dir: str = "sample_data"):
    """
    Generate and save sample NIFTY options data.
    
    Args:
        data_dir: Directory to save sample data
    """
    os.makedirs(data_dir, exist_ok=True)
    
    # Generate sample data
    print("Generating sample NIFTY options data...")
    df = generate_sample_nifty_data(days=60)
    
    # Save to CSV
    filepath = os.path.join(data_dir, "sample_nifty_options.csv")
    df.to_csv(filepath, index=False)
    print(f"Saved {len(df)} records to {filepath}")
    
    # Also save as consolidated data for the data handler
    consolidated_path = os.path.join(data_dir, "nifty_options_consolidated.csv")
    df.to_csv(consolidated_path, index=False)
    print(f"Saved consolidated data to {consolidated_path}")
    
    # Show data summary
    print(f"\nData Summary:")
    print(f"Date range: {df['DATE'].min()} to {df['DATE'].max()}")
    print(f"Records: {len(df)}")
    print(f"Unique strike prices: {df['STRIKE_PR'].nunique()}")
    print(f"Unique expiry dates: {df['EXPIRY_DT'].nunique()}")
    
    # Show sample data
    print(f"\nSample data:")
    print(df.head(10))
    
    return df


def create_sample_data_files():
    """Create sample data files for immediate testing."""
    # Create sample data directory
    sample_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample_data")
    os.makedirs(sample_dir, exist_ok=True)
    
    # Generate and save sample data
    df = save_sample_data(sample_dir)
    
    return df


if __name__ == "__main__":
    create_sample_data_files()