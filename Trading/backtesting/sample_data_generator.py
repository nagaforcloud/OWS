import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import os

def generate_sample_stock_data(symbol: str = "TCS", start_date: datetime = None, 
                             end_date: datetime = None, num_days: int = 100) -> pd.DataFrame:
    """
    Generate sample stock price data for backtesting
    
    Args:
        symbol: Stock symbol to generate data for
        start_date: Start date for the data
        end_date: End date for the data
        num_days: Number of days of data to generate
        
    Returns:
        DataFrame with stock price data
    """
    if start_date is None:
        start_date = datetime.now() - timedelta(days=num_days)
    if end_date is None:
        end_date = datetime.now()
    
    # Generate date range
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    # Filter out weekends
    dates = [d for d in dates if d.weekday() < 5]  # Monday to Friday
    
    if len(dates) > num_days:
        dates = dates[:num_days]
    
    # Generate price data with realistic characteristics
    initial_price = random.uniform(500, 3000)  # Starting price between 500 and 3000
    prices = [initial_price]
    
    # Generate price movements with some trend and volatility
    for i in range(1, len(dates)):
        # Daily return with some volatility and mild trend
        daily_return = np.random.normal(0.001, 0.02)  # Mean return 0.1%, volatility 2%
        new_price = prices[-1] * (1 + daily_return)
        new_price = max(new_price, 1.0)  # Ensure price doesn't go negative
        prices.append(new_price)
    
    # Create DataFrame with OHLC data
    data = {
        'date': dates,
        'symbol': symbol,
        'open': [],
        'high': [],
        'low': [],
        'close': prices,
        'volume': [],
        'oi': []  # Open interest (for options)
    }
    
    # Generate OHLC from close prices
    for i, close_price in enumerate(prices):
        # Create intraday volatility
        daily_volatility = random.uniform(0.01, 0.05)  # 1-5% daily volatility
        high_low_spread = close_price * daily_volatility
        
        # Generate open, high, low based on close
        open_price = prices[i-1] if i > 0 else close_price
        high_price = max(open_price, close_price) + random.uniform(0, high_low_spread/2)
        low_price = min(open_price, close_price) - random.uniform(0, high_low_spread/2)
        
        # Ensure low <= open/close/high
        low_price = min(low_price, open_price, close_price)
        high_price = max(high_price, open_price, close_price)
        
        data['open'].append(open_price)
        data['high'].append(high_price)
        data['low'].append(max(low_price, 0.5))  # Ensure positive low
        data['volume'].append(random.randint(100000, 5000000))
        data['oi'].append(random.randint(10000, 1000000))
    
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    return df


def generate_sample_option_chain_data(underlying_symbol: str = "NIFTY", 
                                    underlying_price: float = 22000,
                                    num_strikes: int = 21,
                                    days_to_expiry: int = 30) -> pd.DataFrame:
    """
    Generate sample option chain data for backtesting
    
    Args:
        underlying_symbol: Symbol of the underlying asset
        underlying_price: Current price of the underlying
        num_strikes: Number of strike prices to generate on each side of ATM
        days_to_expiry: Days to expiry for the options
        
    Returns:
        DataFrame with option chain data
    """
    
    # Generate strike prices around the current underlying price
    strike_interval = 50  # NIFTY typically has 50 point strike intervals
    atm_strike = round(underlying_price / strike_interval) * strike_interval
    
    strikes = []
    for i in range(-(num_strikes//2), (num_strikes//2) + 1):
        strike = atm_strike + (i * strike_interval)
        if strike > 0:  # Only positive strikes
            strikes.append(strike)
    
    # Calculate expiry date
    expiry_date = datetime.now() + timedelta(days=days_to_expiry)
    
    # Generate option prices based on Black-Scholes like model
    data = []
    
    for strike in strikes:
        for option_type in ['CE', 'PE']:  # Call, Put
            # Calculate intrinsic value
            if option_type == 'CE':
                intrinsic_value = max(0, underlying_price - strike)
            else:
                intrinsic_value = max(0, strike - underlying_price)
            
            # Generate time value based on time to expiry and moneyness
            time_to_expiry = days_to_expiry / 365.0
            moneyness = abs(underlying_price - strike) / underlying_price
            
            # Higher time value for ATM options, lower for deep ITM/OTM
            base_time_value = 20 * time_to_expiry * (1 - moneyness) if moneyness < 0.2 else 20 * time_to_expiry * 0.2
            base_time_value = max(base_time_value, 5)  # Minimum time value
            
            # Generate option price
            option_price = intrinsic_value + base_time_value
            option_price += random.uniform(-5, 5)  # Add some randomness
            option_price = max(option_price, 0.05)  # Minimum price
            
            # Generate greeks (simplified)
            # Delta: 0 to 1 for calls, -1 to 0 for puts
            if option_type == 'CE':
                delta = max(0.05, min(0.95, 0.5 + (underlying_price - strike) / (2 * underlying_price)))
            else:
                delta = max(-0.95, min(-0.05, -0.5 + (strike - underlying_price) / (2 * underlying_price)))
            
            # Other greeks (simplified)
            gamma = random.uniform(0.001, 0.01)
            theta = -random.uniform(0.1, 1.0)  # Negative for long options
            vega = random.uniform(0.1, 0.5)
            
            data.append({
                'instrument_token': random.randint(100000, 999999),
                'exchange_token': random.randint(10000, 99999),
                'tradingsymbol': f"{underlying_symbol}{strike}{option_type}{expiry_date.strftime('%y%b%d').upper()}",
                'name': f"{underlying_symbol} {strike} {option_type}",
                'exchange': 'NFO',
                'instrument_type': option_type,
                'strike': strike,
                'expiry': expiry_date,
                'tick_size': 0.05,
                'lot_size': 50,
                'currency': 'INR',
                'last_price': option_price,
                'close': option_price,
                'open': option_price * random.uniform(0.99, 1.01),
                'high': option_price * random.uniform(1.00, 1.03),
                'low': option_price * random.uniform(0.97, 1.00),
                'volume': random.randint(1000, 100000),
                'oi': random.randint(10000, 10000000),
                'total_oi': random.randint(10000, 10000000),
                'oi_day_high': random.randint(10000, 10000000),
                'oi_day_low': random.randint(10000, 10000000),
                'underlying': underlying_symbol,
                'underlying_value': underlying_price,
                'delta': round(delta, 3),
                'gamma': round(gamma, 4),
                'theta': round(theta, 3),
                'vega': round(vega, 3),
                'rho': round(random.uniform(-0.1, 0.1), 3),
                'intrinsic_value': round(intrinsic_value, 2),
                'time_value': round(option_price - intrinsic_value, 2),
                'implied_volatility': round(random.uniform(0.15, 0.40), 3),  # 15-40% IV
            })
    
    df = pd.DataFrame(data)
    return df


def generate_sample_options_history(symbol: str, start_date: datetime, 
                                  end_date: datetime, strike: float, option_type: str) -> pd.DataFrame:
    """
    Generate historical option price data
    
    Args:
        symbol: Underlying symbol
        start_date: Start date for historical data
        end_date: End date for historical data
        strike: Strike price of the option
        option_type: Option type (CE or PE)
        
    Returns:
        DataFrame with historical option prices
    """
    
    # Generate date range
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    # Filter out weekends
    dates = [d for d in dates if d.weekday() < 5]
    
    # Generate underlying price history
    initial_underlying = random.uniform(21000, 23000)  # e.g., NIFTY-like price
    underlying_prices = [initial_underlying]
    
    for i in range(1, len(dates)):
        daily_return = np.random.normal(0.0005, 0.015)  # Smaller daily return for index
        new_price = underlying_prices[-1] * (1 + daily_return)
        new_price = max(new_price, 100)  # Ensure positive price
        underlying_prices.append(new_price)
    
    # Generate option prices based on underlying, strike, and time decay
    data = {
        'date': dates,
        'symbol': f"{symbol}{strike}{option_type}{dates[-1].strftime('%y%b%d').upper()}",
        'open': [],
        'high': [],
        'low': [],
        'close': [],
        'volume': [],
        'oi': [],
        'underlying_price': underlying_prices,
        'strike': strike,
        'option_type': option_type
    }
    
    for i, (date, underlying_price) in enumerate(zip(dates, underlying_prices)):
        days_to_expiry = max(1, (end_date - date).days)
        
        # Calculate intrinsic value
        if option_type == 'CE':
            intrinsic_value = max(0, underlying_price - strike)
        else:
            intrinsic_value = max(0, strike - underlying_price)
        
        # Calculate time value (decreases as expiry approaches)
        time_to_expiry = days_to_expiry / 365.0
        moneyness = abs(underlying_price - strike) / underlying_price
        
        # Time value is higher for ATM options, lower for ITM/OTM
        base_time_value = 15 * time_to_expiry * (1 - moneyness * 2) if moneyness < 0.15 else 15 * time_to_expiry * 0.2
        base_time_value = max(base_time_value, 2)  # Minimum time value
        
        # Generate option price
        option_price = intrinsic_value + base_time_value
        option_price += random.uniform(-3, 3)  # Add some randomness
        option_price = max(option_price, 0.05)  # Minimum price
        
        # Generate OHLC
        open_price = option_price * random.uniform(0.995, 1.005)
        high_price = max(open_price, option_price) + random.uniform(0, 2)
        low_price = min(open_price, option_price) - random.uniform(0, 2)
        low_price = max(low_price, 0.05)  # Ensure minimum value
        close_price = option_price
        
        data['open'].append(open_price)
        data['high'].append(high_price)
        data['low'].append(low_price)
        data['close'].append(close_price)
        data['volume'].append(random.randint(500, 50000))
        data['oi'].append(random.randint(5000, 5000000))
    
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    return df


def generate_mock_backtesting_data(output_dir: str = "backtesting_data") -> Dict[str, str]:
    """
    Generate comprehensive mock data for backtesting and save to files
    
    Args:
        output_dir: Directory to save the generated data
        
    Returns:
        Dictionary mapping data type to file path
    """
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    file_paths = {}
    
    # Generate stock data for multiple symbols
    symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK"]
    stock_data_dir = os.path.join(output_dir, "stock_data")
    os.makedirs(stock_data_dir, exist_ok=True)
    
    for symbol in symbols[:3]:  # Generate data for first 3 symbols
        df = generate_sample_stock_data(symbol, num_days=200)  # 200 days of data
        file_path = os.path.join(stock_data_dir, f"{symbol.lower()}_data.csv")
        df.to_csv(file_path, index=False)
        file_paths[f"stock_{symbol}"] = file_path
        print(f"Generated stock data for {symbol}: {file_path}")
    
    # Generate option chain data for NIFTY
    nifty_option_chain = generate_sample_option_chain_data("NIFTY", 22000, 11, 30)
    option_chain_path = os.path.join(output_dir, "nifty_option_chain.csv")
    nifty_option_chain.to_csv(option_chain_path, index=False)
    file_paths["nifty_option_chain"] = option_chain_path
    print(f"Generated NIFTY option chain: {option_chain_path}")
    
    # Generate historical option data for a few strikes
    historical_options_dir = os.path.join(output_dir, "historical_options")
    os.makedirs(historical_options_dir, exist_ok=True)
    
    start_date = datetime.now() - timedelta(days=60)
    end_date = datetime.now()
    
    for strike in [21900, 22000, 22100]:  # ATM and nearby strikes
        for opt_type in ["CE", "PE"]:
            hist_df = generate_sample_options_history("NIFTY", start_date, end_date, strike, opt_type)
            file_path = os.path.join(historical_options_dir, f"nifty_{strike}{opt_type}_60d.csv")
            hist_df.to_csv(file_path, index=False)
            file_paths[f"nifty_{strike}{opt_type}"] = file_path
            print(f"Generated historical data for NIFTY {strike}{opt_type}: {file_path}")
    
    # Generate a summary file
    summary_data = {
        "data_types": list(file_paths.keys()),
        "total_files": len(file_paths),
        "generation_time": datetime.now().isoformat(),
        "description": "Sample data for Options Wheel Strategy backtesting"
    }
    
    summary_path = os.path.join(output_dir, "data_summary.json")
    import json
    with open(summary_path, 'w') as f:
        json.dump(summary_data, f, indent=2, default=str)
    
    file_paths["summary"] = summary_path
    print(f"Generated data summary: {summary_path}")
    
    return file_paths


if __name__ == "__main__":
    print("Generating sample backtesting data...")
    
    # Generate comprehensive mock data
    data_files = generate_mock_backtesting_data()
    
    print("\
Generated data files:")
    for data_type, file_path in data_files.items():
        print(f"  {data_type}: {file_path}")
    
    print(f"\
Total files generated: {len(data_files)}")
    
    # Show sample of stock data
    import pandas as pd
    sample_stock_file = data_files.get("stock_RELIANCE")
    if sample_stock_file:
        print(f"\
Sample of RELIANCE data from {sample_stock_file}:")
        df = pd.read_csv(sample_stock_file)
        print(df.head())
    
    # Show sample of option chain data
    sample_option_file = data_files.get("nifty_option_chain")
    if sample_option_file:
        print(f"\
Sample of NIFTY option chain from {sample_option_file}:")
        df = pd.read_csv(sample_option_file)
        print(df.head())
