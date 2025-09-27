"""
NSE Data Collector for Options Wheel Strategy.
Downloads and processes historical options data from NSE India.
"""
import requests
import pandas as pd
import numpy as np
import datetime
import os
from typing import List, Dict, Optional, Tuple
import logging
import zipfile
from io import BytesIO

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NSEDataCollector:
    """Class to collect historical options data from NSE India."""
    
    def __init__(self, data_dir: str = "nse_data"):
        """
        Initialize the data collector.
        
        Args:
            data_dir: Directory to store downloaded data
        """
        self.data_dir = data_dir
        self.base_url = "https://archives.nseindia.com/content/historical/DERIVATIVES"
        os.makedirs(data_dir, exist_ok=True)
        
    def _get_url_for_date(self, date: datetime.date) -> str:
        """
        Generate URL for downloading data for a specific date.
        
        Args:
            date: Date for which to generate URL
            
        Returns:
            URL for downloading data
        """
        year = date.year
        month = date.strftime("%b").upper()
        day = date.strftime("%d")
        filename = f"fo{day}{month}{year}bhav.csv.zip"
        url = f"{self.base_url}/{year}/{month}/{filename}"
        return url
    
    def _download_file(self, url: str, date: datetime.date) -> Optional[bytes]:
        """
        Download a file from URL.
        
        Args:
            url: URL to download from
            date: Date for logging purposes
            
        Returns:
            File content as bytes or None if failed
        """
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            logger.info(f"Downloading data for {date} from {url}")
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"Failed to download data for {date}: {e}")
            return None
    
    def _extract_csv_from_zip(self, zip_content: bytes) -> Optional[pd.DataFrame]:
        """
        Extract CSV data from ZIP file.
        
        Args:
            zip_content: ZIP file content as bytes
            
        Returns:
            DataFrame with CSV data or None if failed
        """
        try:
            with zipfile.ZipFile(BytesIO(zip_content)) as zip_file:
                # Get the first CSV file in the ZIP
                csv_filename = [f for f in zip_file.namelist() if f.endswith('.csv')][0]
                with zip_file.open(csv_filename) as csv_file:
                    df = pd.read_csv(csv_file)
                    return df
        except Exception as e:
            logger.error(f"Failed to extract CSV from ZIP: {e}")
            return None
    
    def _process_options_data(self, df: pd.DataFrame, date: datetime.date) -> pd.DataFrame:
        """
        Process raw options data to extract relevant information.
        
        Args:
            df: Raw data from NSE
            date: Date for the data
            
        Returns:
            Processed DataFrame with options data
        """
        try:
            # Filter for options data (OPTIDX for index options)
            options_df = df[df['INSTRUMENT'] == 'OPTIDX'].copy()
            
            if options_df.empty:
                logger.warning(f"No options data found for {date}")
                return options_df
            
            # Convert date columns
            options_df['TIMESTAMP'] = pd.to_datetime(options_df['TIMESTAMP'], format='%d-%b-%Y')
            options_df['EXPIRY_DT'] = pd.to_datetime(options_df['EXPIRY_DT'], format='%d-%b-%Y')
            
            # Add date column
            options_df['DATE'] = date
            
            # Rename columns for consistency
            options_df.rename(columns={
                'SYMBOL': 'SYMBOL',
                'EXPIRY_DT': 'EXPIRY_DT',
                'STRIKE_PR': 'STRIKE_PR',
                'OPTION_TYP': 'OPTION_TYP',
                'OPEN': 'OPEN',
                'HIGH': 'HIGH',
                'LOW': 'LOW',
                'CLOSE': 'CLOSE',
                'SETTLE_PR': 'SETTLE_PR',
                'CONTRACTS': 'CONTRACTS',
                'VAL_INLAKH': 'VAL_INLAKH',
                'OPEN_INT': 'OPEN_INT',
                'CHG_IN_OI': 'CHG_IN_OI'
            }, inplace=True)
            
            # Add instrument type column
            options_df['INSTRUMENT'] = 'OPTIDX'
            
            logger.info(f"Processed {len(options_df)} options records for {date}")
            return options_df
            
        except Exception as e:
            logger.error(f"Failed to process options data for {date}: {e}")
            return pd.DataFrame()
    
    def download_single_day(self, date: datetime.date) -> Optional[pd.DataFrame]:
        """
        Download and process options data for a single day.
        
        Args:
            date: Date for which to download data
            
        Returns:
            DataFrame with options data or None if failed
        """
        # Skip weekends
        if date.weekday() >= 5:
            logger.info(f"Skipping weekend {date}")
            return None
        
        # Generate URL
        url = self._get_url_for_date(date)
        
        # Download file
        zip_content = self._download_file(url, date)
        if zip_content is None:
            return None
        
        # Extract CSV
        df = self._extract_csv_from_zip(zip_content)
        if df is None:
            return None
        
        # Process data
        processed_df = self._process_options_data(df, date)
        return processed_df
    
    def download_date_range(self, start_date: datetime.date, 
                          end_date: datetime.date) -> Dict[datetime.date, pd.DataFrame]:
        """
        Download options data for a date range.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            Dictionary mapping dates to DataFrames
        """
        dataframes = {}
        current_date = start_date
        
        while current_date <= end_date:
            df = self.download_single_day(current_date)
            if df is not None and not df.empty:
                dataframes[current_date] = df
                # Save to file
                filename = f"nse_options_{current_date.strftime('%Y%m%d')}.csv"
                filepath = os.path.join(self.data_dir, filename)
                df.to_csv(filepath, index=False)
                logger.info(f"Saved data for {current_date} to {filepath}")
            
            current_date += datetime.timedelta(days=1)
        
        return dataframes
    
    def consolidate_data(self) -> pd.DataFrame:
        """
        Consolidate all downloaded data files into a single DataFrame.
        
        Returns:
            Consolidated DataFrame
        """
        try:
            # Find all CSV files
            csv_files = [f for f in os.listdir(self.data_dir) 
                        if f.startswith('nse_options_') and f.endswith('.csv')]
            
            if not csv_files:
                logger.warning("No CSV files found to consolidate")
                return pd.DataFrame()
            
            # Read and concatenate all files
            dataframes = []
            for csv_file in csv_files:
                filepath = os.path.join(self.data_dir, csv_file)
                df = pd.read_csv(filepath)
                # Convert date columns
                df['DATE'] = pd.to_datetime(df['DATE'])
                df['TIMESTAMP'] = pd.to_datetime(df['TIMESTAMP'])
                df['EXPIRY_DT'] = pd.to_datetime(df['EXPIRY_DT'])
                dataframes.append(df)
            
            if not dataframes:
                return pd.DataFrame()
            
            consolidated_df = pd.concat(dataframes, ignore_index=True)
            consolidated_df = consolidated_df.sort_values(['DATE', 'SYMBOL', 'EXPIRY_DT', 'STRIKE_PR', 'OPTION_TYP'])
            
            # Save consolidated data
            consolidated_path = os.path.join(self.data_dir, 'nse_options_consolidated.csv')
            consolidated_df.to_csv(consolidated_path, index=False)
            logger.info(f"Consolidated {len(consolidated_df)} records into {consolidated_path}")
            
            return consolidated_df
            
        except Exception as e:
            logger.error(f"Failed to consolidate data: {e}")
            return pd.DataFrame()
    
    def get_data_summary(self) -> Dict:
        """
        Get summary statistics of downloaded data.
        
        Returns:
            Dictionary with summary statistics
        """
        try:
            consolidated_path = os.path.join(self.data_dir, 'nse_options_consolidated.csv')
            if not os.path.exists(consolidated_path):
                logger.warning("No consolidated data found")
                return {}
            
            df = pd.read_csv(consolidated_path)
            df['DATE'] = pd.to_datetime(df['DATE'])
            
            summary = {
                'total_records': len(df),
                'date_range': {
                    'start': df['DATE'].min().strftime('%Y-%m-%d'),
                    'end': df['DATE'].max().strftime('%Y-%m-%d')
                },
                'symbols': df['SYMBOL'].unique().tolist(),
                'total_days': df['DATE'].nunique(),
                'avg_records_per_day': len(df) // df['DATE'].nunique() if df['DATE'].nunique() > 0 else 0
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate data summary: {e}")
            return {}


def main():
    """Main function to demonstrate usage."""
    # Initialize collector
    collector = NSEDataCollector("nse_historical_data")
    
    # Download last 7 days of data (example)
    end_date = datetime.date.today() - datetime.timedelta(days=1)  # Yesterday
    start_date = end_date - datetime.timedelta(days=7)
    
    print(f"Downloading NSE options data from {start_date} to {end_date}")
    
    # Download data
    dataframes = collector.download_date_range(start_date, end_date)
    
    if dataframes:
        print(f"Downloaded data for {len(dataframes)} days")
        
        # Consolidate data
        consolidated = collector.consolidate_data()
        
        if not consolidated.empty:
            # Show summary
            summary = collector.get_data_summary()
            print("\nData Summary:")
            for key, value in summary.items():
                print(f"  {key}: {value}")
        else:
            print("No data was consolidated")
    else:
        print("No data was downloaded")


if __name__ == "__main__":
    main()