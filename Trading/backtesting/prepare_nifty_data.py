#!/usr/bin/env python3
"""
Script to prepare NIFTY data for backtesting
Offers users a choice between:
1. Generate sample data for quick start
2. Download real NSE data for more realistic backtesting
"""

import sys
import os
import argparse
from datetime import datetime, timedelta
import pandas as pd
import json

# Add the parent directory to the path to import project modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtesting.sample_data_generator import generate_mock_backtesting_data
from backtesting.nse_data_collector import NSEDataCollector, get_nse_data_for_backtesting
from utils.logging_utils import get_logger

logger = get_logger(__name__)

def generate_sample_data(output_dir: str = "backtesting_data"):
    """
    Generate sample data for backtesting
    
    Args:
        output_dir: Directory to save the generated data
    """
    print("Generating sample data for backtesting...")
    print("This will create realistic but synthetic market data for testing.")
    
    try:
        data_files = generate_mock_backtesting_data(output_dir)
        
        print(f"\\n✓ Sample data generation completed!")
        print(f"Data saved to: {output_dir}")
        print(f"Total files created: {len(data_files)}")
        
        print("\\nGenerated data includes:")
        for data_type, file_path in data_files.items():
            print(f"  - {data_type}: {file_path}")
        
        # Create a data summary file
        summary = {
            "type": "sample",
            "description": "Synthetic market data for Options Wheel Strategy backtesting",
            "generation_date": datetime.now().isoformat(),
            "files": data_files
        }
        
        summary_path = os.path.join(output_dir, "data_info.json")
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        print(f"\\n✓ Data summary saved to: {summary_path}")
        
    except Exception as e:
        logger.error(f"Error generating sample data: {str(e)}")
        print(f"✗ Error generating sample data: {str(e)}")
        return False
    
    return True

def download_real_data(output_dir: str = "backtesting_data"):
    """
    Download real NSE data for backtesting
    
    Args:
        output_dir: Directory to save the downloaded data
    """
    print("Downloading real NSE data for backtesting...")
    print("This will connect to NSE India API to get actual market data.")
    
    try:
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize data collector
        collector = NSEDataCollector()
        
        print("Fetching NIFTY option chain data...")
        nifty_data = get_nse_data_for_backtesting("NIFTY", days_back=30)
        
        if not nifty_data.get('option_chain'):
            print("✗ Could not fetch NIFTY option chain data")
            return False
        
        # Save option chain to CSV
        option_chain_path = os.path.join(output_dir, "nifty_option_chain_real.csv")
        success = collector.save_option_chain_to_csv("NIFTY", option_chain_path)
        
        if not success:
            print("✗ Could not save option chain data")
            return False
        
        # Get historical data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)  # 3 months of data
        
        print(f"Fetching NIFTY historical data from {start_date.date()} to {end_date.date()}...")
        historical_df = collector.get_historical_data("NIFTY", start_date, end_date)
        
        if historical_df is not None:
            historical_path = os.path.join(output_dir, "nifty_historical_90d.csv")
            historical_df.to_csv(historical_path, index=False)
            print(f"✓ Saved historical data to: {historical_path}")
        else:
            print("⚠ Could not fetch historical data, proceeding with available data")
        
        # Get expiry dates
        expiry_dates = collector.get_expiry_dates("NIFTY")
        nearest_expiry = collector.get_nearest_expiry("NIFTY")
        
        print(f"Found {len(expiry_dates)} expiry dates")
        print(f"Nearest expiry: {nearest_expiry}")
        
        # Create a data summary file
        summary = {
            "type": "real",
            "description": "Real NSE market data for Options Wheel Strategy backtesting",
            "collection_date": datetime.now().isoformat(),
            "underlying_price": nifty_data.get('current_price'),
            "nearest_expiry": nearest_expiry.isoformat() if nearest_expiry else None,
            "total_expiry_dates": len(expiry_dates),
            "files": {
                "option_chain": option_chain_path,
                "historical_data": historical_path if historical_df is not None else None
            }
        }
        
        summary_path = os.path.join(output_dir, "data_info.json")
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        print(f"\\n✓ Data collection completed!")
        print(f"Data saved to: {output_dir}")
        print(f"Current NIFTY price: {nifty_data.get('current_price')}")
        
    except Exception as e:
        logger.error(f"Error downloading real data: {str(e)}")
        print(f"✗ Error downloading real data: {str(e)}")
        return False
    
    return True

def main():
    parser = argparse.ArgumentParser(description='Prepare NIFTY data for backtesting')
    parser.add_argument('--output-dir', '-o', default='backtesting_data',
                        help='Output directory for backtesting data (default: backtesting_data)')
    parser.add_argument('--data-type', '-t', choices=['sample', 'real'], 
                        help='Type of data to prepare (sample or real). If not specified, user will be prompted.')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("NIFTY Data Preparation for Backtesting")
    print("=" * 60)
    
    if args.data_type:
        # Use the provided data type
        data_type = args.data_type
    else:
        # Prompt user for data type
        print("\\nChoose the type of data to prepare:")
        print("1. Sample data (synthetic, for quick testing)")
        print("2. Real data (from NSE India API, for realistic backtesting)")
        
        while True:
            choice = input("\\nEnter your choice (1 or 2): ").strip()
            if choice == '1':
                data_type = 'sample'
                break
            elif choice == '2':
                data_type = 'real'
                break
            else:
                print("Invalid choice. Please enter 1 or 2.")
    
    print(f"\\nSelected: {data_type} data")
    print(f"Output directory: {args.output_dir}")
    
    # Confirm before proceeding
    confirm = input(f"\\nProceed with {data_type} data preparation? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Operation cancelled.")
        return
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    success = False
    if data_type == 'sample':
        success = generate_sample_data(args.output_dir)
    elif data_type == 'real':
        success = download_real_data(args.output_dir)
    
    if success:
        print(f"\\n✓ {data_type.title()} data preparation completed successfully!")
        print(f"Data is ready in: {args.output_dir}")
        print("\\nTo run backtesting with this data:")
        print(f"  1. Check the files in {args.output_dir}")
        print('  2. Run: python -c "from backtesting.nifty_backtesting import NiftyBacktestingStrategy; from config.config import OptionWheelConfig; b = NiftyBacktestingStrategy(OptionWheelConfig()); b.run_backtest()"')
    else:
        print(f"\\n✗ {data_type.title()} data preparation failed!")
        print("Please check the logs for more details.")
        sys.exit(1)

if __name__ == "__main__":
    main()