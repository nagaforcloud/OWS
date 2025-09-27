# Historical NIFTY Options Data Sources

## 1. Official Sources

### NSE India
- **Website**: https://www.nseindia.com/
- **Data**: Provides daily options data files (.csv format)
- **Access**: Free but requires manual download
- **Frequency**: Daily data only
- **Content**: OHLC, volume, open interest for options

### NSE Data API
- **API**: https://www.nseindia.com/getNseDataAPI.html
- **Data**: Real-time and historical data
- **Access**: Some limitations, may require registration
- **Limitations**: Not optimized for bulk historical data

## 2. Commercial Data Providers

### Alpha Dots
- **Website**: https://www.alphadots.in/
- **Data**: High-quality historical options data
- **Access**: Paid service
- **Features**: Greeks, bid-ask spreads, tick data

### Option Chain
- **Website**: https://www.optionchain.in/
- **Data**: Historical options data with Greeks
- **Access**: Paid service
- **Features**: User-friendly interface, API access

### ICharts
- **Website**: https://www.icharts.in/
- **Data**: Historical stock and options data
- **Access**: Paid service
- **Features**: Charting tools, data export

## 3. Free/Paid Alternatives

### Yahoo Finance
- **Data**: Limited options data
- **Access**: Free
- **Limitations**: No Greeks, limited history

### Quandl (now part of Nasdaq Data Link)
- **Data**: Various financial datasets
- **Access**: Free tier available, paid for more data
- **Limitations**: Limited Indian market data

## 4. Self-Collection Approaches

### Web Scraping NSE
- **Approach**: Automated scraping of NSE website
- **Tools**: Python with requests, BeautifulSoup
- **Considerations**: Terms of service, rate limiting

### KiteConnect Historical Data
- **Approach**: Use Zerodha's API to collect historical data
- **Tools**: KiteConnect Python library
- **Limitations**: Requires active subscription, rate limits

## Recommendations

For backtesting the Option Wheel Strategy, you'll need:
1. **Underlying asset prices** (NIFTY spot/index prices)
2. **Options chain data** including:
   - Strike prices
   - Expiry dates
   - Option prices (bid/ask or last traded)
   - Greeks (Delta, Gamma, Theta, Vega)
   - Open Interest
   - Volume

### Best Approach for Your Project:
1. **Start with NSE Bhavcopy files** for basic historical data
2. **Supplement with a commercial provider** for Greeks and detailed options data
3. **Implement a data collection system** for ongoing data gathering

### Minimum Viable Data for Backtesting:
- Date/time
- Underlying price
- Strike prices
- Call/Put prices
- Expiry dates
- Open Interest (for liquidity filtering)