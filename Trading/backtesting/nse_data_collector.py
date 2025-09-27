import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
from typing import Dict, List, Optional
import logging
from io import StringIO

logger = logging.getLogger(__name__)

class NSEDataCollector:
    """
    Collects data from NSE India API for options chain and historical data
    """
    
    def __init__(self):
        """Initialize the NSE Data Collector"""
        self.base_url = "https://www.nseindia.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Get initial cookies
        try:
            self.session.get(self.base_url)
        except Exception as e:
            logger.warning(f"Could not initialize session: {e}")
    
    def get_option_chain(self, symbol: str = "NIFTY") -> Optional[Dict]:
        """
        Fetch option chain data for a given symbol
        
        Args:
            symbol: Symbol to fetch option chain for (e.g., "NIFTY", "BANKNIFTY")
            
        Returns:
            Dictionary containing option chain data or None if failed
        """
        try:
            # NSE now uses different endpoints for different symbols
            if symbol.upper() == "NIFTY":
                url = f"{self.base_url}/api/option-chain-indices?symbol=NIFTY"
            elif symbol.upper() == "BANKNIFTY":
                url = f"{self.base_url}/api/option-chain-indices?symbol=BANKNIFTY"
            else:
                # For stocks
                url = f"{self.base_url}/api/option-chain-equities?symbol={symbol.upper()}"
            
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Successfully fetched option chain for {symbol}")
                return data
            else:
                logger.error(f"Failed to fetch option chain for {symbol}. Status code: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching option chain for {symbol}: {str(e)}")
            return None
    
    def get_expiry_dates(self, symbol: str = "NIFTY") -> List[datetime]:
        """
        Get available expiry dates for options
        
        Args:
            symbol: Symbol to get expiry dates for
            
        Returns:
            List of expiry dates
        """
        option_chain = self.get_option_chain(symbol)
        if not option_chain:
            return []
        
        try:
            records = option_chain.get('records', {})
            expiry_dates = records.get('expiryDates', [])
            
            # Convert to datetime objects
            dates = []
            for date_str in expiry_dates:
                try:
                    date_obj = datetime.strptime(date_str, '%d-%b-%Y')
                    dates.append(date_obj)
                except ValueError:
                    continue
            
            return sorted(dates)
        except Exception as e:
            logger.error(f"Error parsing expiry dates for {symbol}: {str(e)}")
            return []
    
    def get_current_underlying_price(self, symbol: str = "NIFTY") -> Optional[float]:
        """
        Get the current price of the underlying asset
        
        Args:
            symbol: Symbol to get price for
            
        Returns:
            Current price or None if failed
        """
        option_chain = self.get_option_chain(symbol)
        if not option_chain:
            return None
        
        try:
            records = option_chain.get('records', {})
            timestamp = records.get('timestamp')
            filtered_data = records.get('filtered', {}).get('data', [])
            
            # We can get the underlying value from the records
            underlying_value = records.get('underlyingValue')
            if underlying_value:
                return float(underlying_value)
            
            # Alternatively, calculate from the option chain data
            if filtered_data:
                # Get the first entry and calculate from it
                entry = filtered_data[0]
                return float(entry.get('underlyingValue', 0))
            
            return None
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {str(e)}")
            return None
    
    def get_historical_data(self, symbol: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """
        Get historical price data for a symbol
        
        Args:
            symbol: Symbol to get historical data for
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with historical data or None if failed
        """
        try:
            # Format dates for NSE API
            start_str = start_date.strftime('%d-%m-%Y')
            end_str = end_date.strftime('%d-%m-%Y')
            
            # Different URLs for indices and stocks
            if symbol.upper() in ["NIFTY", "BANKNIFTY"]:
                # This is a simplified approach - actual NSE API may require different endpoints
                url = f"{self.base_url}/api/historical/indicesHistory?symbol={symbol.upper()}&from={start_str}&to={end_str}"
            else:
                # For equities
                url = f"{self.base_url}/api/historical/cm/equity?symbol={symbol.upper()}&series=[\"EQ\"]&from={start_str}&to={end_str}"
            
            response = self.session.get(url, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    df = pd.DataFrame(data['data'])
                    # Convert date column to datetime
                    if 'CH_TIMESTAMP' in df.columns:
                        df['date'] = pd.to_datetime(df['CH_TIMESTAMP'])
                    elif 'timestamp' in df.columns:
                        df['date'] = pd.to_datetime(df['timestamp'])
                    
                    logger.info(f"Successfully fetched historical data for {symbol}")
                    return df
                else:
                    logger.warning(f"No data found in response for {symbol}")
                    return None
            else:
                logger.error(f"Failed to fetch historical data for {symbol}. Status code: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
            return None
    
    def get_options_data_for_expiry(self, symbol: str, expiry_date: datetime) -> Optional[Dict]:
        """
        Get option chain data for a specific expiry date
        
        Args:
            symbol: Symbol to get data for
            expiry_date: Expiry date to filter for
            
        Returns:
            Option chain data for the specific expiry or None if failed
        """
        try:
            option_chain = self.get_option_chain(symbol)
            if not option_chain:
                return None
            
            expiry_str = expiry_date.strftime('%d-%b-%Y')
            records = option_chain.get('records', {})
            
            # Filter data for the specific expiry
            filtered_data = []
            all_data = records.get('data', [])
            
            for entry in all_data:
                if entry.get('expiryDate') == expiry_str:
                    filtered_data.append(entry)
            
            result = {
                'expiry_date': expiry_str,
                'underlying_value': records.get('underlyingValue'),
                'timestamp': records.get('timestamp'),
                'data': filtered_data
            }
            
            logger.info(f"Successfully fetched options data for {symbol} expiry {expiry_str}")
            return result
            
        except Exception as e:
            logger.error(f"Error fetching options data for {symbol} expiry {expiry_date}: {str(e)}")
            return None
    
    def get_nearest_expiry(self, symbol: str = "NIFTY") -> Optional[datetime]:
        """
        Get the nearest expiry date for options
        
        Args:
            symbol: Symbol to get nearest expiry for
            
        Returns:
            Nearest expiry date or None if failed
        """
        expiry_dates = self.get_expiry_dates(symbol)
        if expiry_dates:
            # Filter for future dates and return the nearest
            future_dates = [date for date in expiry_dates if date >= datetime.now()]
            return min(future_dates) if future_dates else None
        return None
    
    def get_top_strikes(self, symbol: str = "NIFTY", num_strikes: int = 5) -> Optional[Dict]:
        """
        Get the top strikes by volume/oi for analysis
        
        Args:
            symbol: Symbol to analyze
            num_strikes: Number of top strikes to return
            
        Returns:
            Dictionary with top strikes or None if failed
        """
        try:
            option_chain = self.get_option_chain(symbol)
            if not option_chain:
                return None
            
            records = option_chain.get('records', {})
            filtered_data = records.get('filtered', {}).get('data', [])
            
            # Calculate total volume and OI for each strike
            strikes_data = []
            for entry in filtered_data:
                strike_price = entry.get('strikePrice')
                
                # Calculate total volume and OI for CE and PE at this strike
                ce_data = entry.get('CE', {})
                pe_data = entry.get('PE', {})
                
                total_volume = ce_data.get('totalTradedVolume', 0) + pe_data.get('totalTradedVolume', 0)
                total_oi = ce_data.get('openInterest', 0) + pe_data.get('openInterest', 0)
                
                strikes_data.append({
                    'strike_price': strike_price,
                    'total_volume': total_volume,
                    'total_oi': total_oi,
                    'ce_data': ce_data,
                    'pe_data': pe_data
                })
            
            # Sort by total OI (or volume) to find top strikes
            strikes_data.sort(key=lambda x: x['total_oi'], reverse=True)
            
            return {
                'underlying_value': records.get('underlyingValue'),
                'top_strikes': strikes_data[:num_strikes]
            }
            
        except Exception as e:
            logger.error(f"Error getting top strikes for {symbol}: {str(e)}")
            return None
    
    def save_option_chain_to_csv(self, symbol: str, file_path: str) -> bool:
        """
        Save option chain data to CSV file
        
        Args:
            symbol: Symbol to fetch data for
            file_path: Path to save the CSV file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            option_chain = self.get_option_chain(symbol)
            if not option_chain:
                return False
            
            # Flatten the option chain data for CSV
            records = option_chain.get('records', {})
            data = records.get('data', [])
            
            if not data:
                logger.warning(f"No data available to save for {symbol}")
                return False
            
            # Prepare flattened data
            flattened_data = []
            for entry in data:
                strike = entry.get('strikePrice')
                expiry = entry.get('expiryDate')
                
                # Extract CE data
                ce_data = entry.get('CE', {})
                if ce_data:
                    ce_row = {
                        'symbol': symbol,
                        'strike_price': strike,
                        'expiry_date': expiry,
                        'option_type': 'CE',
                        'identifier': ce_data.get('identifier'),
                        'instrument_token': ce_data.get('instrumentToken'),
                        'last_price': ce_data.get('lastPrice'),
                        'change': ce_data.get('change'),
                        'p_change': ce_data.get('pChange'),
                        'volume': ce_data.get('totalTradedVolume'),
                        'oi': ce_data.get('openInterest'),
                        'iv': ce_data.get('impliedVolatility'),
                        'oi_day_high': ce_data.get('openInterestDayHigh'),
                        'oi_day_low': ce_data.get('openInterestDayLow'),
                        'bid_qty': ce_data.get('bidQty'),
                        'bid_price': ce_data.get('bidprice'),
                        'ask_qty': ce_data.get('askQty'),
                        'ask_price': ce_data.get('askPrice')
                    }
                    flattened_data.append(ce_row)
                
                # Extract PE data
                pe_data = entry.get('PE', {})
                if pe_data:
                    pe_row = {
                        'symbol': symbol,
                        'strike_price': strike,
                        'expiry_date': expiry,
                        'option_type': 'PE',
                        'identifier': pe_data.get('identifier'),
                        'instrument_token': pe_data.get('instrumentToken'),
                        'last_price': pe_data.get('lastPrice'),
                        'change': pe_data.get('change'),
                        'p_change': pe_data.get('pChange'),
                        'volume': pe_data.get('totalTradedVolume'),
                        'oi': pe_data.get('openInterest'),
                        'iv': pe_data.get('impliedVolatility'),
                        'oi_day_high': pe_data.get('openInterestDayHigh'),
                        'oi_day_low': pe_data.get('openInterestDayLow'),
                        'bid_qty': pe_data.get('bidQty'),
                        'bid_price': pe_data.get('bidprice'),
                        'ask_qty': pe_data.get('askQty'),
                        'ask_price': pe_data.get('askPrice')
                    }
                    flattened_data.append(pe_row)
            
            # Create DataFrame and save to CSV
            df = pd.DataFrame(flattened_data)
            df.to_csv(file_path, index=False)
            
            logger.info(f"Option chain data saved to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving option chain to CSV: {str(e)}")
            return False


def get_nse_data_for_backtesting(symbol: str = "NIFTY", days_back: int = 30) -> Dict:
    """
    Convenience function to get all necessary data for backtesting
    
    Args:
        symbol: Symbol to collect data for
        days_back: Number of days of historical data to collect
        
    Returns:
        Dictionary with all collected data
    """
    collector = NSEDataCollector()
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    # Collect all necessary data
    data = {
        'timestamp': datetime.now(),
        'symbol': symbol,
        'current_price': collector.get_current_underlying_price(symbol),
        'expiry_dates': collector.get_expiry_dates(symbol),
        'nearest_expiry': collector.get_nearest_expiry(symbol),
        'option_chain': collector.get_option_chain(symbol),
        'top_strikes': collector.get_top_strikes(symbol),
        'historical_data': collector.get_historical_data(symbol, start_date, end_date)
    }
    
    return data


if __name__ == "__main__":
    # Example usage
    collector = NSEDataCollector()
    
    print("Testing NSE Data Collector...")
    
    # Test getting option chain for NIFTY
    print("1. Getting NIFTY option chain...")
    nifty_option_chain = collector.get_option_chain("NIFTY")
    if nifty_option_chain:
        print(f"Retrieved NIFTY option chain with {len(nifty_option_chain.get('records', {}).get('data', []))} strikes")
    
    # Test getting expiry dates
    print("2. Getting expiry dates...")
    expiry_dates = collector.get_expiry_dates("NIFTY")
    print(f"Expiry dates: {expiry_dates}")
    
    # Test getting current price
    print("3. Getting current NIFTY price...")
    current_price = collector.get_current_underlying_price("NIFTY")
    print(f"Current NIFTY price: {current_price}")
    
    # Test getting nearest expiry
    print("4. Getting nearest expiry...")
    nearest_expiry = collector.get_nearest_expiry("NIFTY")
    print(f"Nearest expiry: {nearest_expiry}")
    
    # Test getting top strikes
    print("5. Getting top strikes by OI...")
    top_strikes = collector.get_top_strikes("NIFTY", 3)
    if top_strikes:
        print(f"Top strikes by OI: {top_strikes['top_strikes'][:3]}")
    
    # Test saving option chain to CSV
    print("6. Saving option chain to CSV...")
    success = collector.save_option_chain_to_csv("NIFTY", "nifty_option_chain.csv")
    print(f"Saved option chain to CSV: {success}")
    
    # Test collecting all data for backtesting
    print("7. Collecting all data for backtesting...")
    backtesting_data = get_nse_data_for_backtesting("NIFTY", 7)
    print(f"Collected data types: {list(backtesting_data.keys())}")
    
    print("NSE Data Collector tests completed.")