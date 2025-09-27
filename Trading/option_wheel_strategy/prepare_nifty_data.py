"""
Script to download and prepare NIFTY options data for backtesting.
"""
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from option_wheel_strategy.backtesting.sample_data_generator import create_sample_data_files
from option_wheel_strategy.backtesting.nse_data_collector import NSEDataCollector


def prepare_nifty_data():
    """Prepare NIFTY options data for backtesting."""
    print("Preparing NIFTY options data for backtesting...")
    print("Choose an option:")
    print("1. Generate sample data (quick start)")
    print("2. Download real historical data from NSE (requires internet)")
    
    choice = input("Enter your choice (1 or 2): ").strip()
    
    if choice == "1":
        print("Generating sample NIFTY options data...")
        try:
            create_sample_data_files()
            print("Sample data generated successfully!")
            print("You can now run backtesting with this sample data.")
        except Exception as e:
            print(f"Error generating sample data: {e}")
            
    elif choice == "2":
        print("Downloading real historical data from NSE...")
        print("Note: This may take some time and requires a stable internet connection.")
        
        try:
            # Initialize collector
            collector = NSEDataCollector("nifty_historical_data")
            
            # Define date range (last 60 days)
            import datetime
            end_date = datetime.date.today() - datetime.timedelta(days=1)  # Yesterday
            start_date = end_date - datetime.timedelta(days=60)  # 60 days back
            
            print(f"Downloading data from {start_date} to {end_date}")
            
            # Download data
            dataframes = collector.download_date_range(start_date, end_date)
            
            if dataframes:
                print(f"Downloaded data for {len(dataframes)} days")
                
                # Consolidate data
                consolidated = collector.consolidate_data()
                
                if not consolidated.empty:
                    print("Data collection completed successfully!")
                    print(f"Total records: {len(consolidated)}")
                    print(f"Date range: {consolidated['DATE'].min()} to {consolidated['DATE'].max()}")
                    print("Data is ready for backtesting.")
                else:
                    print("No data was consolidated")
            else:
                print("No data was downloaded")
                
        except Exception as e:
            print(f"Error downloading data: {e}")
            print("Falling back to sample data generation...")
            create_sample_data_files()
            
    else:
        print("Invalid choice. Generating sample data as fallback...")
        create_sample_data_files()


if __name__ == "__main__":
    prepare_nifty_data()