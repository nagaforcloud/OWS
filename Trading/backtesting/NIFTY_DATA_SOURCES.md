# NIFTY Data Sources for Backtesting

## Overview
This document describes the various data sources available for backtesting the Options Wheel Strategy with NIFTY options.

## Data Sources

### 1. NSE India API
The primary source for live and historical NIFTY options data is the NSE India website API. This provides:
- Real-time option chain data with all Greeks
- Historical OHLC data for underlying (NIFTY index)
- Expiry dates and contract specifications
- Volume and open interest data

#### Access Method
The system uses the `NSEDataCollector` class to access NSE India data through their public APIs.

#### Data Types Available
- **Option Chain**: Complete chain for all strikes and expiry dates
- **Historical Data**: OHLC for underlying index
- **Greeks**: Delta, Gamma, Theta, Vega, Rho for options
- **OI & Volume**: Open Interest and trading volume for each contract

### 2. Sample/Synthetic Data
For initial testing and development, the system can generate synthetic market data using the `sample_data_generator.py` module. This provides:
- Realistic price movements with volatility
- Correlated option prices
- Complete option chains with Greeks
- Historical data for backtesting

#### Advantages
- No dependency on external APIs
- Consistent and reproducible results
- Fast testing without network requests

#### Limitations
- Not real market conditions
- May not capture real market anomalies
- Volatility patterns may differ from real market

## Data Categories

### 1. Current Market Data
- Option chain with bid/ask prices
- Greeks (Delta, Gamma, Theta, Vega, Rho)
- Open Interest
- Trading Volume

### 2. Historical Data
- OHLC for underlying
- Historical option prices
- Time-series data for backtesting

### 3. Contract Specifications
- Strike prices
- Expiry dates
- Lot sizes
- Tick sizes

## Data Usage in Backtesting

### Real Market Data Flow
1. Fetch current option chain from NSE API
2. Apply strategy logic to select optimal strikes
3. Simulate order placement at market prices
4. Track position performance over time
5. Apply risk management rules

### Sample Data Flow
1. Generate synthetic market data representing NIFTY
2. Create correlated option prices based on underlying
3. Apply same strategy logic as with real data
4. Simulate order placement and position management
5. Calculate performance metrics

## Data Quality Considerations

### For Real Data
- Ensure data freshness (avoid stale data)
- Handle API rate limits
- Verify data consistency across calls
- Account for market holidays

### For Sample Data
- Ensure volatility is realistic
- Verify correlation between underlying and options
- Test with various market conditions (bull, bear, sideways)

## APIs Used

### NSE India Endpoints
- `/api/option-chain-indices?symbol=NIFTY` - Current option chain
- `/api/historical/indicesHistory?symbol=NIFTY&...` - Historical data
- Expiry date information from option chain records

### Error Handling
The system implements automatic fallbacks and retry mechanisms for handling network issues or API unavailability.

## File Structure for Saved Data
When data is downloaded or generated, it's stored in structured format:
```
backtesting_data/
├── nifty_option_chain.csv          # Current option chain
├── nifty_historical_90d.csv        # Historical price data
├── nifty_21900CE_60d.csv          # Individual contract history
├── data_summary.json               # Metadata and summary
└── data_info.json                  # Data source and collection info
```

## Data Validation
The system validates data before using it for backtesting:
- Price ranges are reasonable
- Greeks values are within expected ranges
- Volume and OI are positive values
- Dates are sequential and valid