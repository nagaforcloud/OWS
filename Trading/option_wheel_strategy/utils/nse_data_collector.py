"""
Script to download and process historical NIFTY options data from NSE.
"""
import requests
import pandas as pd
import numpy as np
import zipfile
import io
import os
import datetime
from typing import Optional, List
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NSEDataCollector:
    """Class to collect historical NIFTY options data from NSE."""
    
    def __init__(self, data_dir: str = "nifty_options_data"):
        """
        Initialize the data collector.
        
        Args:
            data_dir: Directory to store downloaded data
        """
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.base_url = "https://archives.nseindia.com/content/historical/DERIVATIVES"
        
    def download_bhavcopy(self, date: datetime.date) -> Optional[pd.DataFrame]:
        """
        Download NSE derivatives bhavcopy for a specific date.
        
        Args:
            date: Date for which to download bhavcopy
            
        Returns:
            DataFrame with bhavcopy data or None if failed
        """
        try:
            # Format URL: https://archives.nseindia.com/content/historical/DERIVATIVES/2023/JUN/fo01JUN2023bhav.csv.zip
            year = date.year
            month = date.strftime("%b").upper()
            day = date.strftime("%d")
            filename = f"fo{day}{month}{year}bhav.csv"
            
            url = f"{self.base_url}/{year}/{month}/{filename}.zip"
            logger.info(f"Downloading from: {url}")
            
            # Download the zip file
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Extract the CSV from zip
            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
                with zip_file.open(f"{filename}") as csv_file:
                    df = pd.read_csv(csv_file)
                    
            logger.info(f"Downloaded data for {date}: {len(df)} rows")
            return df
            
        except Exception as e:
            logger.error(f"Failed to download bhavcopy for {date}: {e}")
            return None
    
    def filter_nifty_options(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter dataframe to only include NIFTY options.
        
        Args:
            df: Raw bhavcopy dataframe
            
        Returns:
            Filtered dataframe with only NIFTY options
        """
        # Filter for NIFTY options
        nifty_options = df[
            (df['SYMBOL'] == 'NIFTY') & 
            (df['INSTRUMENT'].isin(['OPTIDX']))  # Options on index
        ].copy()
        
        logger.info(f"Filtered NIFTY options: {len(nifty_options)} rows")
        return nifty_options
    
    def process_greeks(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add calculated Greeks to the dataframe (simplified).
        
        Args:
            df: Dataframe with options data
            
        Returns:
            Dataframe with added Greeks
        """
        # This is a simplified Greek calculation for demonstration
        # In practice, you would use a proper options pricing model
        
        # Add time to expiry (assuming monthly expiry)
        df['EXPIRY_DT'] = pd.to_datetime(df['EXPIRY_DT'], format='%d-%b-%Y')
        df['TIMESTAMP'] = pd.to_datetime(df['TIMESTAMP'], format='%d-%b-%Y')
        df['DTE'] = (df['EXPIRY_DT'] - df['TIMESTAMP']).dt.days
        
        # Simplified Delta approximation (for demonstration)
        # In reality, you'd need underlying price, volatility, risk-free rate
        df['STRIKE_DISTANCE'] = abs(df['STRIKE_PR'] - df['CLOSE']) / df['STRIKE_PR']
        
        # Approximate Delta for calls and puts
        df['CALL_DELTA'] = np.where(
            df['OPTION_TYP'] == 'CE',
            0.5 + (0.5 * (1 - df['STRIKE_DISTANCE'])),  # Simplified
            0  # Placeholder
        )
        
        df['PUT_DELTA'] = np.where(
            df['OPTION_TYP'] == 'PE',
            -0.5 - (0.5 * (1 - df['STRIKE_DISTANCE'])),  # Simplified
            0  # Placeholder
        )
        
        # Set appropriate Delta based on option type
        df['DELTA'] = np.where(
            df['OPTION_TYP'] == 'CE',
            df['CALL_DELTA'],
            df['PUT_DELTA']
        )
        
        return df
    
    def download_date_range(self, start_date: datetime.date, 
                          end_date: datetime.date) -> List[pd.DataFrame]:
        """
        Download bhavcopy data for a date range.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            List of dataframes with NIFTY options data
        """
        dataframes = []
        current_date = start_date
        
        while current_date <= end_date:
            # Skip weekends
            if current_date.weekday() < 5:  # Monday=0, Sunday=6
                logger.info(f"Processing {current_date}")
                
                # Download bhavcopy
                df = self.download_bhavcopy(current_date)
                if df is not None:
                    # Filter for NIFTY options
                    nifty_df = self.filter_nifty_options(df)
                    if len(nifty_df) > 0:
                        # Process Greeks
                        nifty_df = self.process_greeks(nifty_df)
                        # Add date column
                        nifty_df['DATE'] = current_date
                        dataframes.append(nifty_df)
                        
                        # Save to file
                        filename = f"nifty_options_{current_date.strftime('%Y%m%d')}.csv"
                        filepath = os.path.join(self.data_dir, filename)
                        nifty_df.to_csv(filepath, index=False)
                        logger.info(f"Saved {len(nifty_df)} records to {filename}")
            
            current_date += datetime.timedelta(days=1)
            
        return dataframes
    
    def consolidate_data(self) -> pd.DataFrame:
        """
        Consolidate all downloaded data files into a single dataframe.
        
        Returns:
            Consolidated dataframe
        """
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
            consolidated = pd.concat(dataframes, ignore_index=True)
            consolidated = consolidated.sort_values(['DATE', 'SYMBOL', 'EXPIRY_DT', 'STRIKE_PR', 'OPTION_TYP'])
            
            # Save consolidated data
            consolidated_path = os.path.join(self.data_dir, 'nifty_options_consolidated.csv')
            consolidated.to_csv(consolidated_path, index=False)
            logger.info(f"Consolidated {len(consolidated)} records into {consolidated_path}")
            
            return consolidated
        else:
            logger.warning("No data files found to consolidate")
            return pd.DataFrame()


def main():
    """Main function to demonstrate data collection."""
    # Initialize collector
    collector = NSEDataCollector()
    
    # Define date range (last 30 days as an example)
    end_date = datetime.date.today() - datetime.timedelta(days=1)  # Yesterday
    start_date = end_date - datetime.timedelta(days=30)  # 30 days back
    
    logger.info(f"Downloading NIFTY options data from {start_date} to {end_date}")
    
    # Download data
    dataframes = collector.download_date_range(start_date, end_date)
    
    if dataframes:
        logger.info(f"Downloaded data for {len(dataframes)} days")
        
        # Consolidate data
        consolidated = collector.consolidate_data()
        
        if not consolidated.empty:
            logger.info("Data collection completed successfully")
            logger.info(f"Total records: {len(consolidated)}")
            logger.info(f"Date range: {consolidated['DATE'].min()} to {consolidated['DATE'].max()}")
            
            # Show sample data
            print("\nSample data:")
            print(consolidated.head(10))
            
            # Show data structure
            print("\nData structure:")
            print(consolidated.info())
        else:
            logger.warning("No data was consolidated")
    else:
        logger.warning("No data was downloaded")


if __name__ == "__main__":
    main()