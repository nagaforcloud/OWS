"""
Enhanced backtesting module with NIFTY data support.
"""
import pandas as pd
import datetime
import os
from typing import List, Dict, Any, Optional
import sys
import logging

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from option_wheel_strategy.backtesting.mock_kite import MockKiteConnect
from option_wheel_strategy.backtesting.nifty_data_handler import NiftyOptionsDataHandler


class NiftyBacktestingStrategy:
    """
    Backtesting strategy specifically for NIFTY options using historical data.
    """
    
    def __init__(self, data_dir: str = "sample_data"):
        """
        Initialize the backtesting strategy.
        
        Args:
            data_dir: Directory containing historical data
        """
        self.data_dir = data_dir
        self.data_handler = NiftyOptionsDataHandler(data_dir)
        self.mock_kite = None
        self.logger = logging.getLogger(__name__)
        
    def initialize_backtest(self, start_date: datetime.date, 
                         end_date: datetime.date) -> bool:
        """
        Initialize backtesting with historical data.
        
        Args:
            start_date: Start date for backtesting
            end_date: End date for backtesting
            
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Load historical data
            if not self.data_handler.load_data():
                self.logger.error("Failed to load historical data")
                return False
            
            # Initialize mock Kite client with empty data
            self.mock_kite = MockKiteConnect(historical_data={})
            
            # Prepare historical data for mock Kite
            self._prepare_historical_data(start_date, end_date)
            
            self.logger.info("Backtesting initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing backtest: {e}")
            return False
    
    def _prepare_historical_data(self, start_date: datetime.date, 
                              end_date: datetime.date):
        """
        Prepare historical data for use in backtesting.
        
        Args:
            start_date: Start date for backtesting
            end_date: End date for backtesting
        """
        # This method would prepare the data in the format expected by MockKiteConnect
        # For now, we'll set up a basic structure
        self.mock_kite.historical_data = {
            'TCS_LTP': {},  # Not used for NIFTY, but required by mock
            'OPTION_PREMIUMS': {},
            'OPTION_CHAIN_DATA': {}
        }
        
        # Populate with sample data for demonstration
        current_date = start_date
        while current_date <= end_date:
            if current_date.weekday() < 5:  # Weekdays only
                # Get options chain for this date
                options_chain = self.data_handler.get_nearest_expiry_options(current_date, "NIFTY")
                underlying_price = self.data_handler.get_underlying_price(current_date, "NIFTY")
                
                if not options_chain.empty and underlying_price:
                    # Format for mock Kite
                    time_key = current_date.strftime('%Y-%m-%d')
                    
                    # Format options chain data
                    formatted_chain = self.data_handler.format_for_strategy(
                        options_chain, underlying_price
                    )
                    
                    self.mock_kite.historical_data['OPTION_CHAIN_DATA'][time_key] = formatted_chain
                    
                    # Add underlying price
                    self.mock_kite.historical_data['TCS_LTP'][time_key] = underlying_price
                    
            current_date += datetime.timedelta(days=1)
    
    def run_backtest(self, start_date: datetime.date, 
                   end_date: datetime.date) -> Dict[str, Any]:
        """
        Run backtest for the specified date range.
        
        Args:
            start_date: Start date for backtesting
            end_date: End date for backtesting
            
        Returns:
            Dictionary with backtest results
        """
        # Initialize backtesting
        if not self.initialize_backtest(start_date, end_date):
            return {"error": "Failed to initialize backtest"}
        
        # For now, we'll just return basic information
        # In a full implementation, this would run the actual backtest
        
        results = {
            "status": "initialized",
            "start_date": start_date,
            "end_date": end_date,
            "data_points": len(self.mock_kite.historical_data['OPTION_CHAIN_DATA']),
            "message": "Ready to run backtest with historical NIFTY options data"
        }
        
        return results


def run_sample_backtest():
    """Run a sample backtest with generated data."""
    # First, generate sample data if it doesn't exist
    sample_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample_data")
    
    if not os.path.exists(os.path.join(sample_dir, "nifty_options_consolidated.csv")):
        print("Generating sample data...")
        try:
            from option_wheel_strategy.backtesting.sample_data_generator import create_sample_data_files
            create_sample_data_files()
        except ImportError:
            print("Could not generate sample data. Please run sample_data_generator.py first.")
            return
    
    # Initialize backtesting strategy
    backtest = NiftyBacktestingStrategy(sample_dir)
    
    # Define date range
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=30)
    
    print(f"Running sample backtest from {start_date} to {end_date}")
    
    # Run backtest
    results = backtest.run_backtest(start_date, end_date)
    
    print("Backtest Results:")
    for key, value in results.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    run_sample_backtest()