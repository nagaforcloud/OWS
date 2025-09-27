"""
Module to handle historical NIFTY options data for backtesting.
"""
import pandas as pd
import numpy as np
import datetime
import os
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class NiftyOptionsDataHandler:
    """Class to handle historical NIFTY options data for backtesting."""
    
    def __init__(self, data_dir: str = "nifty_options_data"):
        """
        Initialize the data handler.
        
        Args:
            data_dir: Directory containing historical data files
        """
        self.data_dir = data_dir
        self.data: Optional[pd.DataFrame] = None
        self.options_chain_cache: Dict[str, pd.DataFrame] = {}
        
    def load_data(self, filepath: Optional[str] = None) -> bool:
        """
        Load historical NIFTY options data.
        
        Args:
            filepath: Path to specific data file, or None to load consolidated data
            
        Returns:
            True if data loaded successfully, False otherwise
        """
        try:
            if filepath is None:
                # Try to load consolidated data first
                consolidated_path = os.path.join(self.data_dir, 'nifty_options_consolidated.csv')
                if os.path.exists(consolidated_path):
                    filepath = consolidated_path
                else:
                    # If no consolidated data, try to load individual files
                    return self._load_individual_files()
            
            if os.path.exists(filepath):
                self.data = pd.read_csv(filepath)
                # Convert date columns
                self.data['DATE'] = pd.to_datetime(self.data['DATE'])
                self.data['EXPIRY_DT'] = pd.to_datetime(self.data['EXPIRY_DT'])
                self.data['TIMESTAMP'] = pd.to_datetime(self.data['TIMESTAMP'])
                
                logger.info(f"Loaded {len(self.data)} records from {filepath}")
                return True
            else:
                logger.error(f"Data file not found: {filepath}")
                return False
                
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            return False
    
    def _load_individual_files(self) -> bool:
        """Load data from individual files."""
        try:
            all_files = [f for f in os.listdir(self.data_dir) if f.startswith('nifty_options_') and f.endswith('.csv')]
            dataframes = []
            
            for file in all_files:
                filepath = os.path.join(self.data_dir, file)
                df = pd.read_csv(filepath)
                df['DATE'] = pd.to_datetime(df['DATE'])
                df['EXPIRY_DT'] = pd.to_datetime(df['EXPIRY_DT'])
                df['TIMESTAMP'] = pd.to_datetime(df['TIMESTAMP'])
                dataframes.append(df)
                
            if dataframes:
                self.data = pd.concat(dataframes, ignore_index=True)
                self.data = self.data.sort_values(['DATE', 'SYMBOL', 'EXPIRY_DT', 'STRIKE_PR', 'OPTION_TYP'])
                logger.info(f"Loaded {len(self.data)} records from {len(all_files)} files")
                return True
            else:
                logger.warning("No data files found")
                return False
                
        except Exception as e:
            logger.error(f"Error loading individual files: {e}")
            return False
    
    def get_options_chain(self, date: datetime.date, 
                         symbol: str = "NIFTY") -> pd.DataFrame:
        """
        Get options chain for a specific date.
        
        Args:
            date: Date for which to get options chain
            symbol: Underlying symbol (default: NIFTY)
            
        Returns:
            DataFrame with options chain data
        """
        # Check cache first
        cache_key = f"{date}_{symbol}"
        if cache_key in self.options_chain_cache:
            return self.options_chain_cache[cache_key].copy()
        
        if self.data is None:
            logger.warning("No data loaded")
            return pd.DataFrame()
        
        # Filter data for the specific date and symbol
        date_str = pd.to_datetime(date)
        options_chain = self.data[
            (self.data['DATE'] == date_str) & 
            (self.data['SYMBOL'] == symbol)
        ].copy()
        
        if options_chain.empty:
            logger.warning(f"No options data found for {symbol} on {date}")
            return pd.DataFrame()
        
        # Cache the result
        self.options_chain_cache[cache_key] = options_chain.copy()
        
        logger.info(f"Retrieved options chain for {symbol} on {date}: {len(options_chain)} records")
        return options_chain
    
    def get_underlying_price(self, date: datetime.date, 
                           symbol: str = "NIFTY") -> Optional[float]:
        """
        Get underlying price for a specific date.
        
        Args:
            date: Date for which to get underlying price
            symbol: Underlying symbol (default: NIFTY)
            
        Returns:
            Underlying price or None if not found
        """
        if self.data is None:
            logger.warning("No data loaded")
            return None
        
        # For index options, we might need to get the index price from a different source
        # For now, we'll use the CLOSE price of the nearest future contract as a proxy
        date_str = pd.to_datetime(date)
        index_data = self.data[
            (self.data['DATE'] == date_str) & 
            (self.data['SYMBOL'] == symbol) &
            (self.data['INSTRUMENT'] == 'FUTIDX')  # Futures on index
        ]
        
        if not index_data.empty:
            # Return the close price of the nearest expiry future
            nearest_future = index_data.loc[index_data['EXPIRY_DT'].idxmin()]
            return nearest_future['CLOSE']
        else:
            # If no futures data, try to estimate from options prices
            options_data = self.data[
                (self.data['DATE'] == date_str) & 
                (self.data['SYMBOL'] == symbol) &
                (self.data['INSTRUMENT'] == 'OPTIDX')
            ]
            
            if not options_data.empty:
                # Use the average of strike prices weighted by open interest as a proxy
                # This is a rough approximation
                options_data = options_data.dropna(subset=['STRIKE_PR', 'OPEN_INT'])
                if not options_data.empty and options_data['OPEN_INT'].sum() > 0:
                    weighted_avg_strike = np.average(
                        options_data['STRIKE_PR'], 
                        weights=options_data['OPEN_INT']
                    )
                    return weighted_avg_strike
        
        logger.warning(f"Could not determine underlying price for {symbol} on {date}")
        return None
    
    def get_nearest_expiry_options(self, date: datetime.date, 
                                 symbol: str = "NIFTY") -> pd.DataFrame:
        """
        Get options chain for the nearest expiry date.
        
        Args:
            date: Date for which to get options chain
            symbol: Underlying symbol (default: NIFTY)
            
        Returns:
            DataFrame with options chain for nearest expiry
        """
        options_chain = self.get_options_chain(date, symbol)
        
        if options_chain.empty:
            return options_chain
        
        # Find the nearest future expiry
        future_expiries = options_chain[options_chain['EXPIRY_DT'] >= pd.to_datetime(date)]['EXPIRY_DT'].unique()
        
        if len(future_expiries) == 0:
            logger.warning(f"No future expiries found for {symbol} on {date}")
            return pd.DataFrame()
        
        # Sort and get the nearest expiry
        nearest_expiry = sorted(future_expiries)[0]
        
        # Filter for nearest expiry
        nearest_expiry_options = options_chain[options_chain['EXPIRY_DT'] == nearest_expiry]
        
        logger.info(f"Filtered options for nearest expiry {nearest_expiry.date()}: {len(nearest_expiry_options)} records")
        return nearest_expiry_options
    
    def format_for_strategy(self, options_chain: pd.DataFrame, 
                          underlying_price: float) -> pd.DataFrame:
        """
        Format options chain data for use in the option wheel strategy.
        
        Args:
            options_chain: Raw options chain data
            underlying_price: Current underlying price
            
        Returns:
            Formatted DataFrame compatible with strategy
        """
        if options_chain.empty:
            return options_chain
        
        # Create a formatted DataFrame that matches the strategy's expected structure
        formatted_data = []
        
        # Group by strike price and expiry to combine call and put data
        grouped = options_chain.groupby(['STRIKE_PR', 'EXPIRY_DT'])
        
        for (strike, expiry), group in grouped:
            # Separate call and put data
            call_data = group[group['OPTION_TYP'] == 'CE']
            put_data = group[group['OPTION_TYP'] == 'PE']
            
            record = {
                'strikePrice': strike,
                'expiryDate': expiry,
            }
            
            # Add call data if available
            if not call_data.empty:
                call_row = call_data.iloc[0]
                record.update({
                    'CE.lastPrice': call_row['CLOSE'],
                    'CE.openInterest': call_row['OPEN_INT'],
                    'CE.delta': call_row.get('DELTA', 0.5),  # Use calculated or default delta
                    'CE.volume': call_row.get('CONTRACTS', 0),
                })
            
            # Add put data if available
            if not put_data.empty:
                put_row = put_data.iloc[0]
                record.update({
                    'PE.lastPrice': put_row['CLOSE'],
                    'PE.openInterest': put_row['OPEN_INT'],
                    'PE.delta': put_row.get('DELTA', -0.5),  # Use calculated or default delta
                    'PE.volume': put_row.get('CONTRACTS', 0),
                })
            
            formatted_data.append(record)
        
        formatted_df = pd.DataFrame(formatted_data)
        
        # Add underlying price for reference
        formatted_df['underlyingPrice'] = underlying_price
        
        logger.info(f"Formatted options chain: {len(formatted_df)} strike-expiry combinations")
        return formatted_df


def main():
    """Main function to demonstrate data handling."""
    # Initialize data handler
    data_handler = NiftyOptionsDataHandler()
    
    # Try to load data
    if data_handler.load_data():
        logger.info("Data loaded successfully")
        
        # Get sample date (use a date from your data)
        sample_date = datetime.date.today() - datetime.timedelta(days=5)
        
        # Get underlying price
        underlying_price = data_handler.get_underlying_price(sample_date)
        logger.info(f"Underlying price on {sample_date}: {underlying_price}")
        
        # Get options chain
        options_chain = data_handler.get_nearest_expiry_options(sample_date)
        logger.info(f"Options chain records: {len(options_chain)}")
        
        if not options_chain.empty:
            # Format for strategy
            formatted_chain = data_handler.format_for_strategy(options_chain, underlying_price or 18000)
            logger.info(f"Formatted chain records: {len(formatted_chain)}")
            
            # Show sample data
            print("\nSample formatted data:")
            print(formatted_chain.head())
    else:
        logger.warning("Failed to load data")
        print("Please run the nse_data_collector.py script first to download historical data.")


if __name__ == "__main__":
    main()