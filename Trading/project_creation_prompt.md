# Detailed Prompt for Recreating the Options Wheel Strategy Trading Bot

## Project Overview

Create a comprehensive options trading bot that implements the "Options Wheel Strategy" for the Indian stock market using Zerodha's KiteConnect API. This is a sophisticated income-generating strategy that involves selling out-of-the-money (OTM) options to collect premiums. The project should be modular, production-ready, and include both live trading and backtesting capabilities.

## Core Strategy Description

The Options Wheel Strategy works as follows:
1. When not holding the underlying stock, sell OTM Cash-Secured Puts with deltas between 0.15-0.25
2. If assigned (stock delivered), sell OTM Covered Calls on the holdings
3. Manage existing positions with profit targets (typically 50% of premium) and stop-losses (typically 100% of premium)
4. Continuously run during market hours to maximize premium collection

## Project Architecture Requirements

Create a modular, well-organized project structure:

```
Trading/
├── .env                           # Environment variables and API keys
├── requirements.txt               # Python dependencies
├── IMPLEMENTATION_SUMMARY.md      # Documentation of components
├── TEST_CASES.md                  # Test case specifications
├── README.md                      # Comprehensive documentation
├── run_tests.py                   # Test runner
├── option_wheel_strategy/         # Modular implementation
│   ├── __init__.py
│   ├── .env                       # Environment variables
│   ├── main.py                    # Main entry point
│   ├── requirements.txt           # Dependencies
│   ├── prepare_nifty_data.py      # NIFTY data preparation script
│   ├── NIFTY_DATA_SOURCES.md      # Data sources documentation
│   ├── config/
│   │   ├── __init__.py
│   │   └── config.py              # Configuration management
│   ├── core/
│   │   ├── __init__.py
│   │   └── strategy.py            # Core strategy implementation
│   ├── models/
│   │   ├── __init__.py
│   │   ├── enums.py               # Enumerations
│   │   └── models.py              # Data models
│   ├── utils/
│   │   ├── __init__.py
│   │   └── logging_utils.py       # Logging utilities
│   ├── notifications/
│   │   ├── __init__.py
│   │   └── notification_manager.py# Notification system
│   ├── database/
│   │   ├── __init__.py
│   │   └── database.py            # SQLite database for persistence
│   ├── risk_management/
│   │   ├── __init__.py
│   │   └── risk_manager.py        # Advanced risk controls
│   ├── dashboard/
│   │   ├── __init__.py
│   │   └── dashboard.py           # Web-based dashboard (Streamlit)
│   ├── backtesting/
│   │   ├── __init__.py
│   │   ├── mock_kite.py           # Mock KiteConnect for backtesting
│   │   ├── sample_data_generator.py# Sample data generation
│   │   ├── nse_data_collector.py  # NSE data collection
│   │   └── nifty_backtesting.py   # NIFTY backtesting
└── tests/                         # Test files
    ├── __init__.py
    ├── test_config.py
    ├── test_models.py
    ├── test_strategy.py
    ├── test_backtesting.py
    ├── test_integration.py
    ├── test_enhanced.py
    ├── smoke_test.py
    └── README.md
```

## Core Dependencies

The project should use the following Python dependencies:
- requests
- pandas
- numpy
- kiteconnect
- python-dotenv
- streamlit (for dashboard)
- plotly (for visualization)
- sqlite3 (for database)

## Detailed Component Requirements

### 1. Configuration Module (`config/config.py`)
- Create a `OptionWheelConfig` dataclass with environment variable loading
- Include all of the following configuration parameters:
  - API Credentials: `api_key`, `api_secret`, `access_token`
  - Trading Parameters: `symbol`, `quantity_per_lot`, `profit_target_percentage`, `loss_limit_percentage`
  - Delta Range: `otm_delta_range_low`, `otm_delta_range_high`
  - Open Interest: `min_open_interest`
  - Strategy Timing: `strategy_run_interval_seconds`, market open/close hours
  - Risk Management: `max_concurrent_positions`, `max_daily_loss_limit`, `max_portfolio_risk`
  - Notification Settings: `enable_notifications`, `notification_webhook_url`
  - Data Settings: `use_nse_api`, `data_refresh_interval`

### 2. Data Models (`models/models.py` and `models/enums.py`)
- Create `OrderType`, `ProductType`, `TransactionType` enums
- Create `Position` and `Trade` dataclasses with appropriate fields
- Include proper data validation and type hints

### 3. Core Strategy (`core/strategy.py`)
This should be the most comprehensive module with the following features:

- **Initialization**: Accept config and optional Kite client for dependency injection
- **Instrument Management**: Fetch and cache all instruments from Kite
- **Options Chain**: Fetch from NSE India API with expiry date filtering
- **Strike Selection**: Find best OTM puts/calls based on delta range and open interest
- **Order Management**: Place orders with retry mechanism and error handling
- **Position Management**: Track and manage existing positions with profit targets and stop-losses
- **Risk Management**: Check limits before placing orders
- **State Persistence**: Save/load strategy state between sessions
- **Backtesting Support**: Work with mock Kite for historical testing
- **Market Hours**: Check if market is open before executing cycles
- **Performance Metrics**: Calculate P&L, win rate, Sharpe ratio, max drawdown
- **Logging**: Comprehensive logging with file rotation
- **Notifications**: Send webhook notifications for key events
- **Graceful Shutdown**: Handle signals and save final state

### 4. Database Module (`database/database.py`)
- Create SQLite database with tables for:
  - Trades (order_id, symbol, type, quantity, price, etc.)
  - Positions (symbol, quantity, avg_price, product, etc.)
  - Performance metrics (metric_name, value, timestamp)
  - Strategy sessions (session_id, start_time, end_time, P&L)
- Include proper indexing for performance
- Add CRUD methods for each entity
- Include methods to retrieve and analyze historical data
- Implement context managers for database connections

### 5. Risk Management (`risk_management/risk_manager.py`)
- Create `RiskConfig` dataclass with risk parameters
- Create `PositionRisk` dataclass for individual position risk metrics
- Implement methods to check:
  - Position size limits
  - Portfolio risk exposure
  - Concurrent positions limit
  - Daily loss limits
  - Margin utilization
- Calculate risk metrics like VaR and Sharpe ratio
- Generate comprehensive risk reports
- Implement `should_place_order()` method that checks all risk limits

### 6. Dashboard (`dashboard/dashboard.py`)
- Use Streamlit to create web-based monitoring interface
- Include real-time portfolio overview with current positions
- Show performance charts and equity curve visualization
- Display risk metrics with gauges
- Show recent trades log
- Include strategy control buttons (start/pause/stop)
- Add configuration management interface
- Create tabs for Overview, Performance, Risk, and Controls

### 7. Backtesting System (`backtesting/`)
- Create `MockKiteConnect` class that simulates Kite API calls
- Implement historical data loading from various sources
- Add NSE data collection utilities
- Create sample data generators for quick testing
- Implement backtesting for NIFTY options
- Include performance calculation for backtests
- Create `prepare_nifty_data.py` script that offers users a choice:
  - Option 1: Generate sample data for quick start
  - Option 2: Download real NSE data for more realistic backtesting
- Implement time-simulated backtesting that advances through historical data points
- Include methods to load historical underlying prices and options premiums
- Support for different backtesting timeframes and intervals

### 8. Notifications (`notifications/notification_manager.py`)
- Send webhook notifications for:
  - Order placements
  - Position closures
  - System events
  - Performance updates
- Handle errors gracefully
- Use configurable webhook URLs

### 9. Utilities (`utils/logging_utils.py`)
- Set up enhanced logging with both file and console handlers
- Implement rotating file handlers (10MB max, 5 backups)
- Include comprehensive log format with timestamp, module, function, line number

## Advanced Features

### 1. State Persistence
- Save daily P&L, positions history, and trades history to JSON file
- Load state on startup to maintain continuity
- Handle serialization/deserialization of complex objects

### 2. Error Handling & Retry Mechanism
- Implement retry logic for network errors with exponential backoff
- Handle different types of KiteConnect exceptions
- Gracefully handle token expiration and re-initialization

### 3. Market Data Integration
- Fetch options chain from NSE India API
- Filter for nearest expiry date
- Handle API changes and errors gracefully
- Support for both live data and historical backtesting

### 4. Performance Analytics
- Calculate win rate, average profit/loss per trade
- Compute profit factor, Sharpe ratio, maximum drawdown
- Generate detailed performance reports
- Track portfolio value over time

### 5. Risk Controls
- Position size limits based on portfolio value
- Daily loss limits with automatic trading halt
- Portfolio risk percentage limits
- Margin utilization monitoring
- Maximum concurrent positions limit

## Testing Requirements

Create comprehensive test suites:
- Unit tests for configuration, models, utilities
- Integration tests for strategy logic
- Backtesting tests with mock data
- Error handling tests for edge cases
- Test coverage for all major functionality
- Include test for all risk management features

## Documentation Requirements

### README.md should include:
- Project overview and strategy explanation
- Installation and setup instructions
- Configuration requirements
- Usage examples for live trading and backtesting
- API credential setup for Zerodha
- Risk management features
- Dashboard usage
- Backtesting capabilities
- Development and testing instructions

### Additional Documentation:
- IMPLEMENTATION_SUMMARY.md: Summary of all components
- TEST_CASES.md: Detailed test case specifications
- NIFTY_DATA_SOURCES.md: Information about data sources for backtesting

## Configuration (.env)

The .env file should support the following variables:
```
# API Credentials
KITE_API_KEY=your_api_key_here
KITE_API_SECRET=your_api_secret_here
KITE_ACCESS_TOKEN=your_access_token_here

# Trading Parameters
SYMBOL=TCS
QUANTITY_PER_LOT=150
PROFIT_TARGET_PERCENTAGE=0.50
LOSS_LIMIT_PERCENTAGE=1.00
OTM_DELTA_RANGE_LOW=0.15
OTM_DELTA_RANGE_HIGH=0.25
MIN_OPEN_INTEREST=1000

# Strategy Timing
STRATEGY_RUN_INTERVAL_SECONDS=300
MARKET_OPEN_HOUR=9
MARKET_OPEN_MINUTE=15
MARKET_CLOSE_HOUR=15
MARKET_CLOSE_MINUTE=30

# Risk Management
MAX_CONCURRENT_POSITIONS=5
MAX_DAILY_LOSS_LIMIT=5000.0
MAX_PORTFOLIO_RISK=0.02

# Notification Settings
ENABLE_NOTIFICATIONS=false
NOTIFICATION_WEBHOOK_URL=

# Data Settings
USE_NSE_API=true
DATA_REFRESH_INTERVAL=60
USE_NIFTY=false
```

## Main Execution Flow (`main.py`)

The main entry point should:
- Initialize configuration from environment variables
- Support both live trading and backtesting modes via `USE_NIFTY` environment variable
- For live trading: Create OptionWheelStrategy with real KiteConnect client
- For backtesting: Use NiftyBacktestingStrategy with mock data
- Handle proper initialization and cleanup
- Support graceful shutdown with signal handling
- Load historical data for backtesting when in backtest mode
- Implement continuous execution loop during market hours
- Support command-line arguments for different modes

## Additional Requirements

1. **Code Quality**: Use type hints, proper docstrings, and follow Python best practices
2. **Security**: Never log sensitive API credentials
3. **Performance**: Optimize for running continuously during market hours
4. **Monitoring**: Comprehensive logging with different log levels
5. **Scalability**: Design to support additional strategies in the future
6. **Reliability**: Handle all possible error conditions gracefully
7. **Date/Time Handling**: Use appropriate timezone handling for Indian market hours (IST)
8. **Memory Management**: Implement efficient data structures for handling large options chains
9. **API Rate Limiting**: Respect Zerodha's API rate limits and implement appropriate delays
10. **Data Validation**: Validate all inputs from APIs and user configurations

## Testing Guidelines

Each module should have comprehensive unit tests covering:
- Normal operation scenarios
- Error conditions and edge cases
- Boundary conditions
- Integration between components
- All public methods and functions

The system should be designed for continuous operation in live trading mode while also supporting backtesting with historical data.

## Important Notes

- This is for educational purposes only - trading involves significant financial risk
- The system should never risk more than the user can afford to lose
- Users must understand all risks before using the system for live trading
- Always test thoroughly in a simulated environment before live trading
- The system should be compliant with Zerodha API terms of service