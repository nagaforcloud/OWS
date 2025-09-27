# Trading Option Wheel Strategy

A sophisticated implementation of the Options Wheel trading strategy for the Indian stock market using Zerodha's KiteConnect API. This project provides both live trading and backtesting capabilities with a modular, production-ready architecture.

## Overview

The Options Wheel strategy is an income-generating strategy that involves selling options to collect premiums. This implementation automates the process of:

1. Selling Out-of-the-Money (OTM) Cash-Secured Puts when not holding the underlying stock
2. If assigned (stock delivered), selling OTM Covered Calls
3. Managing existing positions with profit targets and stop-losses
4. Continuously running during market hours to maximize premium collection

## Project Structure

```
Trading/
├── .env                           # Environment variables and API keys
├── requrirements.txt              # Python dependencies
├── Wheel_Script_V1.py             # Initial monolithic implementation
├── Wheel_Script_V2.py             # Refactored version with better structure
├── Wheel_Script_Enhanced.py       # Enhanced version with additional features
├── Wheel_Script_Enhanced_backup.py# Backup of enhanced version
└── option_wheel_strategy/         # Modular implementation (recommended)
    ├── __init__.py
    ├── .env                       # Environment variables
    ├── main.py                    # Main entry point
    ├── requirements.txt           # Dependencies
    ├── README.md                  # Module documentation
    ├── prepare_nifty_data.py      # NIFTY data preparation script
    ├── NIFTY_DATA_SOURCES.md      # Data sources documentation
    ├── config/
    │   ├── __init__.py
    │   └── config.py              # Configuration management
    ├── core/
    │   ├── __init__.py
    │   └── strategy.py            # Core strategy implementation
    ├── models/
    │   ├── __init__.py
    │   ├── enums.py               # Enumerations
    │   └── models.py              # Data models
    ├── utils/
    │   ├── __init__.py
    │   └── logging_utils.py       # Logging utilities
    ├── notifications/
    │   ├── __init__.py
    │   └── notification_manager.py# Notification system
    └── backtesting/
        ├── __init__.py
        ├── mock_kite.py           # Mock KiteConnect for backtesting
        ├── sample_data_generator.py# Sample data generation
        ├── nse_data_collector.py  # NSE data collection
        └── nifty_backtesting.py   # NIFTY backtesting
```

## Features

### Core Trading Features
- **Automated Options Trading**: Automatically identifies and trades OTM options based on delta and open interest criteria
- **Strategy Implementation**: Full implementation of the Options Wheel strategy for income generation
- **Risk Management**: Configurable position limits, daily loss limits, and portfolio risk controls
- **Position Management**: Automatic profit booking and stop-loss execution
- **Real-time Monitoring**: Continuous monitoring of positions during market hours

### Technical Features
- **Modular Design**: Clean separation of concerns with dedicated modules for configuration, core logic, models, utilities, and notifications
- **Live Trading**: Connects to Zerodha's Kite API for real trading
- **Backtesting**: Includes a comprehensive mock trading environment for strategy testing
- **Error Handling**: Robust error handling with retry mechanisms for network issues
- **Graceful Shutdown**: Proper cleanup and state saving on shutdown signals
- **State Persistence**: Saves and loads strategy state for continuity between sessions
- **Enhanced Logging**: Comprehensive logging with file rotation for debugging and monitoring
- **Performance Analytics**: Real-time performance metrics and reporting
- **Notifications**: Configurable webhook notifications for important events
- **Database Integration**: SQLite database for persistent storage of trades, positions, and performance metrics
- **Advanced Risk Management**: Comprehensive risk controls including VaR, position sizing, and margin management
- **Data Collection**: Automated downloading and processing of historical options data from NSE
- **Dashboard Interface**: Web-based dashboard for monitoring and controlling the strategy

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd Trading
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. For dashboard functionality, install additional dependencies:
   ```bash
   pip install streamlit plotly
   ```

4. Configure your environment variables in the `.env` file (see Configuration section)

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd Trading
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure your environment variables in the `.env` file (see Configuration section)

## Configuration

All configuration parameters can be set through environment variables in the `.env` file:

### API Credentials
- `KITE_API_KEY`: Your Zerodha Kite API key
- `KITE_API_SECRET`: Your Zerodha Kite API secret
- `KITE_ACCESS_TOKEN`: Your Zerodha Kite access token (generated after login)

### Trading Parameters
- `SYMBOL`: Trading symbol (default: "TCS")
- `QUANTITY_PER_LOT`: Number of shares per lot (default: 150)
- `PROFIT_TARGET_PERCENTAGE`: Profit target as percentage of premium (default: 0.50)
- `LOSS_LIMIT_PERCENTAGE`: Loss limit as percentage of premium (default: 1.00)
- `OTM_DELTA_RANGE_LOW`: Lower bound for OTM delta range (default: 0.15)
- `OTM_DELTA_RANGE_HIGH`: Upper bound for OTM delta range (default: 0.25)
- `MIN_OPEN_INTEREST`: Minimum open interest for option selection (default: 1000)

### Strategy Timing
- `STRATEGY_RUN_INTERVAL_SECONDS`: Interval between strategy cycles (default: 300)
- `MARKET_OPEN_HOUR`: Market open hour (default: 9)
- `MARKET_OPEN_MINUTE`: Market open minute (default: 15)
- `MARKET_CLOSE_HOUR`: Market close hour (default: 15)
- `MARKET_CLOSE_MINUTE`: Market close minute (default: 30)

### Risk Management
- `MAX_CONCURRENT_POSITIONS`: Maximum concurrent positions (default: 5)
- `MAX_DAILY_LOSS_LIMIT`: Maximum daily loss limit in currency units (default: 5000.0)
- `MAX_PORTFOLIO_RISK`: Maximum portfolio risk as percentage (default: 0.02)

### Notification Settings
- `ENABLE_NOTIFICATIONS`: Enable/disable notifications (default: false)
- `NOTIFICATION_WEBHOOK_URL`: Webhook URL for notifications

### Data Settings
- `USE_NSE_API`: Use NSE API for options data (default: true)
- `DATA_REFRESH_INTERVAL`: Data refresh interval in seconds (default: 60)

## Usage

### Live Trading
1. Configure your API credentials in the `.env` file
2. Run the strategy:
   ```bash
   cd option_wheel_strategy
   python main.py
   ```

### Backtesting
1. Prepare data for backtesting:
   ```bash
   python prepare_nifty_data.py
   ```
2. Choose option 1 for sample data or option 2 for real NSE data
3. Set `USE_NIFTY=true` in your `.env` file
4. Run the strategy:
   ```bash
   python main.py
   ```

## Strategy Logic

The Options Wheel strategy implemented in this project follows these principles:

1. **Cash-Secured Puts**: When not holding the underlying stock, the strategy sells OTM puts with deltas between 0.15-0.25 and high open interest
2. **Covered Calls**: When holding the stock (either purchased or assigned from put exercise), the strategy sells OTM calls with similar delta criteria
3. **Position Management**: Existing positions are monitored and automatically closed when they reach profit targets (50% of premium) or hit stop-losses (100% of premium loss)
4. **Continuous Operation**: The strategy runs continuously during market hours, identifying new opportunities and managing existing positions

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

1. **Underlying asset prices** (stock/index prices)
2. **Options chain data** including:
   - Strike prices
   - Expiry dates
   - Option prices (bid/ask or last traded)
   - Greeks (Delta, Gamma, Theta, Vega)
   - Open Interest
   - Volume

## Risk Management

The strategy includes several risk management features:

- **Position Limits**: Maximum concurrent positions to prevent overexposure
- **Daily Loss Limits**: Automatic trading halt when daily losses exceed threshold
- **Portfolio Risk Controls**: Maximum portfolio risk percentage settings
- **Stop-Loss Mechanism**: Automatic closure of positions at predefined loss levels
- **Graceful Shutdown**: Proper cleanup on critical errors or manual interruption

## Notifications

The system can send notifications via webhooks for:
- Order placements
- Position closures
- System events
- Performance updates

To enable notifications:
1. Set `ENABLE_NOTIFICATIONS=true` in your `.env` file
2. Configure `NOTIFICATION_WEBHOOK_URL` with your webhook endpoint

## Development Evolution

This project has evolved through several iterations:

1. **V1**: Monolithic implementation with basic functionality
2. **V2**: Refactored version with better structure and configuration management
3. **Enhanced**: Added advanced features like state persistence and enhanced logging
4. **Modular**: Fully modular implementation with separate components for each concern

The modular version in the `option_wheel_strategy` directory is the recommended implementation for production use.

## Getting Started with Zerodha API

To use the live trading features, you'll need to:

1. Create an account with Zerodha and enroll in their API program
2. Generate your API key and secret from the Kite dashboard
3. Manually generate an access token by:
   - Running the login URL generation code
   - Visiting the URL in your browser
   - Logging in and copying the request token from the redirect URL
   - Using the request token to generate an access token
4. Update your `.env` file with the API credentials and access token

## Logging

The system uses enhanced logging with:
- File output with rotation (10MB max size, 5 backup files)
- Console output for real-time monitoring
- Detailed log format including timestamp, module, function, and line number

Logs are written to `option_wheel.log` in the project directory.

## Performance Metrics

The system tracks and reports on several performance metrics:
- Total trades executed
- Win rate percentage
- Average profit per winning trade
- Average loss per losing trade
- Profit factor
- Sharpe ratio
- Maximum drawdown

These metrics are logged periodically during strategy execution.

## Testing

The project includes a comprehensive test suite to ensure functionality and prevent regressions:

### Running Tests

1. **Unit Tests**: Test individual components in isolation
   ```bash
   cd Trading
   python -m pytest tests/test_config.py -v
   python -m pytest tests/test_models.py -v
   ```

2. **Integration Tests**: Test component interactions
   ```bash
   python -m pytest tests/test_strategy.py -v
   python -m pytest tests/test_backtesting.py -v
   ```

3. **Complete Test Suite**: Run all tests
   ```bash
   python run_tests.py
   ```

4. **Smoke Tests**: Quick verification of basic functionality
   ```bash
   python tests/smoke_test.py
   ```

### Test Coverage

Generate coverage reports:
```bash
python -m pytest tests/ --cov=option_wheel_strategy --cov-report=html
```

### Writing Tests

See `tests/README.md` for detailed information on writing and running tests.

## Contributing

Contributions to enhance the strategy, add new features, or fix bugs are welcome. Please follow standard GitHub practices for submitting pull requests.

## Disclaimer

This software is provided for educational purposes only. Trading options involves significant risk of loss. Past performance is not indicative of future results. Use this software at your own risk. The authors are not responsible for any financial losses incurred through the use of this software.