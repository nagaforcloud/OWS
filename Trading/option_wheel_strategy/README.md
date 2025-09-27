# Option Wheel Strategy

A modular implementation of the Options Wheel trading strategy for the Indian stock market using Zerodha's KiteConnect API.

## Overview

The Options Wheel strategy is an income-generating strategy that involves selling options to collect premiums. This implementation provides both live trading and backtesting capabilities.

## Modular Structure

```
option_wheel_strategy/
├── main.py                 # Main entry point
├── requirements.txt        # Dependencies
├── .env                    # Environment variables
├── README.md               # Documentation
├── config/
│   ├── __init__.py
│   └── config.py          # Configuration management
├── core/
│   ├── __init__.py
│   └── strategy.py        # Core strategy implementation
├── models/
│   ├── __init__.py
│   ├── enums.py           # Enumerations
│   └── models.py          # Data models
├── utils/
│   ├── __init__.py
│   ├── logging_utils.py   # Logging utilities
│   └── nse_data_collector.py  # NSE data collection
├── notifications/
│   ├── __init__.py
│   └── notification_manager.py  # Notification system
├── database/
│   ├── __init__.py
│   └── database.py        # Database integration
├── risk_management/
│   ├── __init__.py
│   └── risk_manager.py    # Risk management system
├── dashboard/
│   ├── __init__.py
│   └── dashboard.py       # Web dashboard
└── backtesting/
    ├── __init__.py
    ├── mock_kite.py       # Mock KiteConnect for backtesting
    ├── nifty_data_handler.py     # NIFTY data handling
    ├── sample_data_generator.py  # Sample data generation
    ├── nifty_backtesting.py      # NIFTY backtesting
    └── nse_data_collector.py     # NSE data collection
```

## Features

- **Modular Design**: Clean separation of concerns with dedicated modules
- **Live Trading**: Connects to Zerodha's Kite API for real trading
- **Backtesting**: Includes a mock trading environment for strategy testing
- **Risk Management**: Position limits, daily loss limits, and portfolio risk controls
- **Notifications**: Configurable webhook notifications for important events
- **Performance Analytics**: Comprehensive performance metrics and reporting
- **State Persistence**: Saves and loads strategy state for continuity
- **Error Handling**: Robust error handling with retry mechanisms
- **Logging**: Enhanced logging with file rotation
- **Database Integration**: SQLite database for persistent storage of trades and positions
- **Advanced Risk Management**: Comprehensive risk controls including VaR and margin management
- **Data Collection**: Automated downloading of historical options data from NSE
- **Dashboard Interface**: Web-based dashboard for monitoring and controlling the strategy

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure your environment variables in the `.env` file

## Usage

Run the strategy:
```bash
python main.py
```

## Configuration

All configuration parameters can be set through environment variables in the `.env` file:

- **API Credentials**: Kite API key, secret, and access token
- **Trading Parameters**: Symbol, lot size, profit targets, etc.
- **Risk Management**: Position limits, loss limits, etc.
- **Notifications**: Webhook URL for notifications
- **Strategy Timing**: Market hours, run intervals, etc.

## Strategy Logic

1. **Cash-Secured Puts**: When not holding the underlying stock, sells OTM puts
2. **Covered Calls**: When holding the stock, sells OTM calls
3. **Position Management**: Closes positions at profit targets or stop-losses
4. **Continuous Operation**: Runs continuously during market hours

## Backtesting

### With Sample Data (Quick Start)
1. Run the data preparation script:
   ```bash
   python prepare_nifty_data.py
   ```
2. Choose option 1 to generate sample data
3. Set `USE_NIFTY=true` in your `.env` file
4. Run the strategy:
   ```bash
   python main.py
   ```

### With Real NIFTY Data
1. Run the data preparation script:
   ```bash
   python prepare_nifty_data.py
   ```
2. Choose option 2 to download real data from NSE
3. Set `USE_NIFTY=true` in your `.env` file
4. Run the strategy:
   ```bash
   python main.py
   ```

## Risk Management

- Maximum concurrent positions
- Daily loss limits
- Portfolio risk controls
- Graceful shutdown on critical errors

## Notifications

The system can send notifications via webhooks for:
- Order placements
- Position closures
- System events
- Performance updates

## Data Sources for Backtesting

### Official Sources
- **NSE India**: Provides daily options data files (.csv format)
  - Free but requires manual download
  - Daily data only

### Commercial Data Providers
- **Alpha Dots**: High-quality historical options data with Greeks
- **Option Chain**: Historical options data with Greeks
- **ICharts**: Historical stock and options data

### Self-Collection Approaches
- **Web Scraping NSE**: Automated scraping of NSE website
- **KiteConnect Historical Data**: Use Zerodha's API to collect historical data

## Historical Data Requirements

For effective backtesting of the Option Wheel Strategy, you'll need:

1. **Underlying asset prices** (NIFTY spot/index prices)
2. **Options chain data** including:
   - Strike prices
   - Expiry dates
   - Option prices (bid/ask or last traded)
   - Greeks (Delta, Gamma, Theta, Vega)
   - Open Interest
   - Volume

## Sample Data Generation

The sample data generator creates realistic NIFTY options data with:

- Proper strike price intervals
- Realistic option pricing using simplified Black-Scholes logic
- Accurate Greeks (Delta) calculations
- Realistic open interest distributions
- Multiple expiry dates (weekly and monthly)

This allows you to immediately start backtesting without needing to download real data.