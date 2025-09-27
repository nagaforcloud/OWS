# Detailed Prompt for Recreating the Enhanced Options Wheel Strategy Trading Bot

## Project Overview

Create a comprehensive options trading bot that implements the "Options Wheel Strategy" for the Indian stock market using Zerodha's KiteConnect API. This is a sophisticated income-generating strategy that involves selling out-of-the-money (OTM) options to collect premiums. The project should be modular, production-ready, and include both live trading and backtesting capabilities with advanced analytics, historical trade integration, and comprehensive safety and compliance features.

## 🛡️ Core Strategy Description

The Options Wheel Strategy works as follows:
1. When not holding the underlying stock, sell OTM Cash-Secured Puts with deltas between 0.15-0.25
2. If assigned (stock delivered), sell OTM Covered Calls on the holdings
3. Manage existing positions with profit targets (typically 50% of premium) and stop-losses (typically 100% of premium)
4. Continuously run during market hours to maximize premium collection

## 🔐 Safety & Compliance Enhancements

### 1. Safety & User Protection
- **Dry Run Mode**: Add `DRY_RUN=true/false` to `.env`. When enabled, logs all orders but never places real trades. Clearly indicate `[DRY RUN]` in logs and dashboard.
- **Live Trading Confirmation**: On first execution in live mode (`DRY_RUN=false`), prompt user: `⚠️ LIVE TRADING MODE ENABLED. Type 'CONFIRM' to proceed:`. Abort if input ≠ 'CONFIRM'.
- **Kill Switch**: Check for existence of a file (e.g., `STOP_TRADING`) in the root directory. If present, gracefully shut down the strategy loop. Document this in README.md.

### 2. Indian Market Compliance & Realism
- **Holiday Calendar Integration**: Use `mcal` or static NSE holiday list to skip non-trading days. Add config: `USE_HOLIDAY_CALENDAR=true`, `HOLIDAY_FILE_PATH=./data/nse_holidays.csv`. Skip strategy execution on holidays and weekends.
- **Timezone Enforcement**: All datetime operations must use `Asia/Kolkata`. Never use naive datetime; always timezone-aware.
- **Broker Compliance Rules**: Enforce Zerodha product-type alignment: Cash-Secured Puts: product=NRML, backed by sufficient cash. Covered Calls: product=NRML, with underlying shares in CNC.
- **Tax & Accounting Hooks**: In Trade model, add: `trade_type: Literal["intraday", "delivery", "fno"]`, `tax_category: str` (e.g., "STT_applicable"). Not used now, but enables future P&L categorization.

### 3. Capital & Margin Management
- **Real-Time Margin Monitoring**: Before placing any order, call `kite.margins()` to get: `available.cash`, `utilised.debits`. Add config: `MIN_CASH_RESERVE=10000`. Never use all capital.
- **Dynamic Position Sizing**: Replace hardcoded `QUANTITY_PER_LOT` with risk-based sizing: `max_risk = portfolio_value * config.risk_per_trade_percent`, `max_lots = max_risk / (strike_price * config.quantity_per_lot)`. Add config: `RISK_PER_TRADE_PERCENT=0.01`.

### 4. Market Data Reliability
- **Options Chain Fallbacks**: Primary: NSE India API, Fallback: Kite instruments + OHLC data. Cache chain for `DATA_REFRESH_INTERVAL` seconds.
- **Delta Approximation**: If real delta unavailable, estimate using: `moneyness = underlying_price / strike_price`, `delta = 0.5 + (moneyness - 1) * 2`. Prefer ATM IV from historical data if available.

### 5. Backtesting Realism
- **Transaction Cost Modeling**: Deduct real Zerodha F&O charges per trade: Brokerage: ₹20 per executed order or 0.03% (whichever lower), STT: 0.017% on sell side, GST: 18% on brokerage, SEBI turnover fee: ₹10 per crore, Stamp duty: Varies by state (~0.003%). Add config: `INCLUDE_FEES_IN_BACKTEST=true`.
- **Slippage & Fill Logic**: Apply slippage (e.g., 0.05%) to entry/exit prices. Only fill if historical bid/ask supports order price. Simulate partial fills for large orders.

### 6. Advanced Monitoring & Alerting
- **Multi-Channel Notifications**: Support: Telegram, Slack, Email, Webhook. Add config: `NOTIFICATION_TYPE=telegram`, `TELEGRAM_BOT_TOKEN=...`, `TELEGRAM_CHAT_ID=...`.
- **Critical Alerts**: Send immediate alerts for: Margin shortfall, Daily loss limit breached, API token expired, Strategy loop stalled (>2x interval without heartbeat).
- **Health Endpoint**: In Streamlit dashboard, add `/health` indicator (green/red). Show last cycle timestamp and error count.

### 7. Strategy Flexibility
- **Strategy Modes**: Add config: `STRATEGY_MODE=conservative` (options: conservative, balanced, aggressive). Map to delta ranges: conservative: 0.10–0.15, balanced: 0.15–0.25 (default), aggressive: 0.25–0.35.
- **Auto-Rolling Logic**: Before expiry (e.g., DTE ≤ 1), auto-roll unprofitable options: Roll puts down & out, Roll calls up & out. Configurable via: `ENABLE_AUTO_ROLL=true`.

### 8. Deployment & DevOps
- **Docker Support**: Add `Dockerfile` and `docker-compose.yml`. Mount volume for data/logs: `-v ./data:/app/data`.
- **Process Management**: Include example systemd service file (`options_wheel_bot.service`). Auto-restart on failure.
- **Documentation**: In README.md, document alternatives to `.env`: AWS Secrets Manager, HashiCorp Vault, Kubernetes Secrets.

## Project Architecture Requirements

Create a modular, well-organized project structure:

```
Trading/
├── .env                           # Environment variables and API keys
├── requirements.txt               # Python dependencies
├── IMPLEMENTATION_SUMMARY.md      # Documentation of components
├── TEST_CASES.md                  # Test case specifications
├── README.md                      # Comprehensive documentation
├── DEPLOYMENT.md                 # Deployment guide
├── ENHANCEMENTS_SUMMARY.md       # Summary of safety and compliance enhancements
├── run_tests.py                   # Test runner
├── Dockerfile                    # Docker support
├── docker-compose.yml            # Docker Compose configuration
├── docker-compose.dev.yml        # Development Docker Compose override
├── options_wheel_bot.service     # Systemd service file
├── auto_roll_functions.py         # Auto rolling functions
├── basic_functionality_test.py    # Basic functionality tests
├── final_verification.py          # Final verification checks
├── health_check.py                # Health check utilities
├── main.py                        # Main entry point
├── __init__.py
├── __main__.py
├── config/
│   ├── __init__.py
│   └── config.py                  # Configuration management
├── core/
│   ├── __init__.py
│   └── strategy.py                # Core strategy implementation
├── models/
│   ├── __init__.py
│   ├── enums.py                   # Enumerations
│   └── models.py                  # Data models
├── utils/
│   ├── __init__.py
│   └── logging_utils.py           # Logging utilities
├── notifications/
│   ├── __init__.py
│   └── notification_manager.py    # Notification system
├── database/
│   ├── __init__.py
│   └── database.py                # SQLite database for persistence
├── risk_management/
│   ├── __init__.py
│   └── risk_manager.py            # Advanced risk controls
├── dashboard/
│   ├── __init__.py
│   └── dashboard.py               # Web-based dashboard (Streamlit) with advanced analytics
├── backtesting/
│   ├── __init__.py
│   ├── mock_kite.py               # Mock KiteConnect for backtesting
│   ├── nifty_backtesting.py       # NIFTY backtesting
│   ├── nse_data_collector.py      # NSE data collection
│   ├── prepare_nifty_data.py      # NIFTY data preparation script
│   └── sample_data_generator.py   # Sample data generation
├── data/                          # Data files
│   ├── nse_holidays.csv           # NSE holiday calendar (example)
│   └── ...
├── logs/                          # Log files
├── historical_trades/             # Historical trade CSV files
│   └── ...
├── docs/                          # Documentation files
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
- requests>=2.28.0
- pandas>=1.5.0
- numpy>=1.9.0
- kiteconnect>=4.0.0
- python-dotenv>=0.19.0
- streamlit>=1.12.0
- plotly>=5.10.0
- sqlite3>=2.6.0 (built-in)
- pytz>=2022.1
- matplotlib>=3.5.0
- seaborn>=0.11.0
- scipy>=1.9.0
- ta>=0.10.0
- schedule>=1.1.0
- apscheduler>=3.9.0

## Detailed Component Requirements

### 1. Configuration Module (`config/config.py`)

Create a `OptionWheelConfig` dataclass with environment variable loading that includes all the following configuration parameters:

**API Credentials:**
- `api_key`: Kite API key
- `api_secret`: Kite API secret
- `access_token`: Kite access token

**Trading Parameters:**
- `symbol`: Trading symbol (default: NIFTY)
- `quantity_per_lot`: Number of units per lot (default: 50 for NIFTY)
- `profit_target_percentage`: Profit target as percentage of premium (default: 0.50)
- `loss_limit_percentage`: Stop loss as percentage of premium (default: 1.00)

**Delta Range:**
- `otm_delta_range_low`: Lower bound for OTM delta (default: 0.15)
- `otm_delta_range_high`: Upper bound for OTM delta (default: 0.25)

**Open Interest:**
- `min_open_interest`: Minimum open interest for option selection (default: 1000)

**Strategy Timing:**
- `strategy_run_interval_seconds`: Interval between strategy cycles (default: 300)
- `market_open_hour`: Market open hour (default: 9)
- `market_open_minute`: Market open minute (default: 15)
- `market_close_hour`: Market close hour (default: 15)
- `market_close_minute`: Market close minute (default: 30)

**Risk Management:**
- `max_concurrent_positions`: Maximum concurrent positions (default: 5)
- `max_daily_loss_limit`: Maximum daily loss limit (default: 5000.0)
- `max_portfolio_risk`: Maximum portfolio risk percentage (default: 0.02)

**Notification Settings:**
- `enable_notifications`: Enable/disable notifications (default: false)
- `notification_webhook_url`: Webhook URL for notifications (default: "")

**Data Settings:**
- `use_nse_api`: Use NSE API for data (default: true)
- `data_refresh_interval`: Data refresh interval in seconds (default: 60)
- `use_nifty`: Use NIFTY for backtesting (default: false)

**Enhanced Safety & Compliance Settings:**
- `dry_run`: Enable dry run mode (default: false)
- `use_holiday_calendar`: Use holiday calendar (default: false)
- `holiday_file_path`: Path to holiday file (default: ./data/nse_holidays.csv)
- `strategy_mode`: Strategy mode (conservative, balanced, aggressive) (default: balanced)
- `risk_per_trade_percent`: Risk per trade as percentage of portfolio (default: 0.01)
- `min_cash_reserve`: Minimum cash reserve (default: 10000)
- `enable_auto_roll`: Enable auto-rolling logic (default: false)
- `kill_switch_file`: Kill switch file name (default: STOP_TRADING)

**Note**: There was a duplicate `__post_init__` and `_validate_config` method in the original code. Only one of each should be implemented.

### 2. Data Models (`models/models.py` and `models/enums.py`)

Create the following enumerations in `models/enums.py`:
- `OrderType`: LIMIT, MARKET, SL, SLM
- `ProductType`: CNC, NRML, MIS
- `TransactionType`: BUY, SELL
- `StrategyType`: CASH_SECURED_PUT, COVERED_CALL
- `PositionType`: LONG, SHORT, FLAT
- `OptionType`: CALL (CE), PUT (PE)
- `OrderStatus`: COMPLETE, REJECTED, CANCELLED, OPEN, TRIGGER_PENDING
- `ExchangeType`: NSE, BSE, NFO, BFO, CDS, MCX

Create data classes with appropriate fields in `models/models.py`:
- `Trade`: Represents a trade executed by the strategy with additional tax and fee tracking
- `Position`: Represents a position in the portfolio with comprehensive P&L tracking
- `OptionContract`: Represents an option contract with Greeks and other data
- `StrategyState`: Represents the current state of the strategy
- `RiskMetrics`: Risk metrics for portfolio monitoring

### 3. Core Strategy (`core/strategy.py`)

This should be the most comprehensive module with the following features:

#### Initialization
- Accept config and optional Kite client for dependency injection
- Initialize all components (notification manager, database manager, risk manager)

#### Instrument Management
- Fetch and cache all instruments from Kite
- Filter instruments by exchange and symbol

#### Options Chain
- Fetch from NSE India API with expiry date filtering
- Implement caching with refresh intervals
- Fallback to Kite instruments when NSE API is unavailable

#### Strike Selection
- Find best OTM puts/calls based on delta range and open interest
- Implement strategy modes (conservative, balanced, aggressive) with different delta ranges
- Use improved delta approximation when real delta is unavailable

#### Order Management
- Place orders with retry mechanism and error handling
- Implement dry run mode that logs but doesn't place real orders
- Validate orders against broker compliance rules

#### Position Management
- Track and manage existing positions with profit targets and stop-losses
- Implement auto-rolling logic for expiring options
- Calculate P&L and risk metrics for each position

#### Risk Management
- Check limits before placing orders
- Implement real-time margin monitoring
- Dynamic position sizing based on portfolio risk
- Validate against broker compliance rules

#### State Persistence
- Save/load strategy state between sessions
- Implement JSON serialization for complex objects
- Handle state migration when schema changes

#### Backtesting Support
- Work with mock Kite for historical testing
- Support transaction cost modeling and slippage simulation
- Implement realistic fill logic

#### Market Hours
- Check if market is open before executing cycles
- Implement holiday calendar integration
- Use proper timezone handling (Asia/Kolkata)

#### Performance Metrics
- Calculate P&L, win rate, Sharpe ratio, max drawdown
- Track portfolio value over time
- Generate detailed performance reports

#### Logging
- Comprehensive logging with file rotation
- Include module, function, and line number information
- Separate log levels for different types of messages

#### Notifications
- Send webhook notifications for key events
- Support multi-channel notifications (Telegram, Slack, Email, Webhook)
- Implement critical alerts system for margin shortfalls, loss limits, etc.

#### Graceful Shutdown
- Handle signals and save final state
- Implement kill switch functionality
- Support graceful shutdown with confirmation for live trading

#### Auto Rolling Logic
- Check for positions expiring soon (DTE <= 1)
- Roll puts down & out (lower strike)
- Roll calls up & out (higher strike)

### 4. Database Module (`database/database.py`)

Create SQLite database with tables for:
- Trades (order_id, symbol, type, quantity, price, etc.)
- Positions (symbol, quantity, avg_price, product, etc.)
- Performance metrics (metric_name, value, timestamp)
- Strategy sessions (session_id, start_time, end_time, P&L)

Include proper indexing for performance:
- Indexes on frequently queried columns (symbol, timestamp, etc.)
- Composite indexes for complex queries

Add CRUD methods for each entity:
- Create, Read, Update, Delete operations for all entities
- Batch operations for bulk data insertion
- Query methods for retrieving historical data

Include methods to retrieve and analyze historical data:
- Performance metrics calculation
- P&L analysis by symbol, date range, etc.
- Risk metrics calculation

Implement context managers for database connections:
- Ensure proper resource cleanup
- Handle connection pooling for high-frequency operations

### 5. Risk Management (`risk_management/risk_manager.py`)

Create `RiskConfig` dataclass with risk parameters:
- Daily loss limits
- Position size limits
- Portfolio risk limits
- Margin utilization limits

Create `PositionRisk` dataclass for individual position risk metrics:
- Position size as percentage of portfolio
- Margin utilization for each position
- Risk contribution to overall portfolio

Implement methods to check:
- Position size limits based on portfolio value
- Portfolio risk exposure (VaR, Sharpe ratio)
- Concurrent positions limit
- Daily loss limits with automatic trading halt
- Margin utilization monitoring
- Maximum concurrent positions limit

Calculate risk metrics like:
- Value at Risk (VaR)
- Sharpe ratio
- Maximum drawdown
- Portfolio risk percentage

Generate comprehensive risk reports:
- Daily risk summary
- Position-level risk analysis
- Portfolio-level risk metrics
- Risk limit breach alerts

Implement `should_place_order()` method that checks all risk limits:
- Validate against all configured risk parameters
- Return detailed reason for rejection if order is blocked
- Log all risk limit checks

### 6. Dashboard (`dashboard/dashboard.py`)

#### Enhanced Dashboard with Historical Trade Analysis:

Use Streamlit to create web-based monitoring interface with advanced analytics:

##### Real-time Portfolio Overview:
- Current positions and P&L metrics
- Risk metrics with gauges
- Performance charts with equity curve
- Strategy status indicators

##### Multiple Tabs Structure:
- Overview: Real-time portfolio metrics and charts
- Positions: Current holdings and P&L
- Trades: Recent transactions
- **Historical Trades: Advanced analysis of historical CSV trade data**
- Performance: Key metrics and analytics
- Risk: Risk management overview
- Controls: Strategy management controls

##### Historical Trade Analysis Features:

###### Multi-File CSV Loading:
- Automatically discovers and combines tradebook CSV files from main directory and `historical_trades` folder
- Processes multiple files with same structure
- Shows source file and directory information
- Path is hardcoded to search in `/Users/nagashankar/pythonScripts/OWS` and `/Users/nagashankar/pythonScripts/OWS/historical_trades`

###### Advanced Filtering System:
- Date range filter in sidebar
- Year filter to analyze specific years
- Quarter filter to analyze specific quarters
- Symbol filter to focus on particular instruments
- All filters work together for targeted analysis

###### Year-over-Year Analysis:
- Performance comparison charts by year
- YoY P&L comparison
- YoY trade volume analysis

###### Quarter-over-Quarter Analysis:
- Performance comparison charts by quarter
- QoQ P&L comparison
- QoQ trade volume analysis

###### Option Greeks Analysis (Proxy-based):
- **Theta Analysis**: Distribution of trades by Days to Expiry (DTE)
- **Delta Analysis**: Call vs Put option distribution
- **Gamma Analysis**: Trade distribution across strike price ranges
- Extracts strike prices and option types from symbol names
- Calculates Days to Expiry using trade date vs. expiry date

###### Interactive Charts:
- Cumulative performance chart
- Daily trade volume
- Year-over-year performance
- Quarter-over-quarter performance
- Symbol performance
- Greeks analysis visualizations (theta, delta, gamma proxies)

###### Data Table:
- Shows historical trades with source file and directory information
- Formatted for Indian Rupee values
- Sortable and filterable columns

##### Performance Charts:
- Equity curves and P&L analysis
- Risk-adjusted return metrics
- Sharpe ratio and other performance indicators

##### Risk Metrics:
- Portfolio risk visualization
- Risk limit monitoring
- Margin utilization tracking

##### Strategy Controls:
- Start/pause/stop strategy buttons
- Configuration management
- Manual position closing controls

##### Health Endpoint:
- System health indicator (green/red)
- Last cycle timestamp
- Error count monitoring

### 7. Backtesting System (`backtesting/`)

Create `MockKiteConnect` class in `mock_kite.py` that simulates Kite API calls:
- Implement all necessary Kite methods for backtesting
- Simulate realistic API responses and errors
- Support for historical data loading

Implement historical data loading from various sources in `nifty_backtesting.py`:
- NSE India API historical data
- Local CSV files with historical prices
- Generated sample data for quick testing

Add NSE data collection utilities in `nse_data_collector.py`:
- Download historical data from NSE
- Process and format data for backtesting
- Handle data quality issues and gaps

Create sample data generators in `sample_data_generator.py` for quick testing:
- Generate realistic sample stock data
- Generate realistic sample option chain data
- Support for different market scenarios (bull, bear, sideways)

Implement backtesting for NIFTY options in `nifty_backtesting.py`:
- Time-simulated backtesting that advances through historical data points
- Support for different backtesting timeframes and intervals
- Realistic order execution simulation

Include performance calculation for backtests:
- Calculate P&L, win rate, Sharpe ratio, max drawdown
- Generate detailed performance reports
- Compare with buy-and-hold benchmark

Create `prepare_nifty_data.py` script that offers users a choice:
- Option 1: Generate sample data for quick start
- Option 2: Download real NSE data for more realistic backtesting

Implement time-simulated backtesting that advances through historical data points:
- Process historical data chronologically
- Simulate market hours and trading sessions
- Handle corporate actions and dividends

Include methods to load historical underlying prices and options premiums:
- Load historical price data for underlying assets
- Load historical option chain data
- Handle data interpolation for missing timestamps

Support for different backtesting timeframes and intervals:
- Intraday backtesting
- Daily backtesting
- Weekly backtesting
- Monthly backtesting

Add realistic transaction cost modeling:
- Zerodha F&O charges (brokerage, STT, GST, etc.)
- Slippage simulation
- Fill logic based on bid/ask spreads

### 8. Notifications (`notifications/notification_manager.py`)

Send webhook notifications for:
- Order placements
- Position closures
- System events
- Performance updates
- Critical alerts (margin shortfall, daily loss limit breached, etc.)

Handle errors gracefully:
- Retry failed notifications with exponential backoff
- Log notification errors without stopping strategy
- Support graceful degradation when notification services are unavailable

Use configurable webhook URLs:
- Support for different notification services
- Environment variable configuration
- Secure handling of API keys and tokens

Support multi-channel notifications:
- Telegram bots
- Slack webhooks
- Email notifications
- Custom webhook endpoints

Implement critical alerts system:
- Immediate alerts for system-critical events
- Configurable alert thresholds
- Duplicate alert suppression

### 9. Utilities (`utils/logging_utils.py`)

Set up enhanced logging with both file and console handlers:
- File handler with daily rotation
- Console handler for real-time monitoring
- Different log levels for development and production

Implement rotating file handlers (10MB max, 5 backups):
- Prevent log files from growing too large
- Maintain history of past log files
- Automatic cleanup of old log files

Include comprehensive log format with timestamp, module, function, line number:
- ISO8601 timestamps with timezone
- Module and function context
- Line number for precise debugging
- Log level indicators

## Advanced Features

### 1. State Persistence
- Save daily P&L, positions history, and trades history to JSON file
- Load state on startup to maintain continuity
- Handle serialization/deserialization of complex objects
- Implement state migration when schema changes

### 2. Error Handling & Retry Mechanism
- Implement retry logic for network errors with exponential backoff
- Handle different types of KiteConnect exceptions
- Gracefully handle token expiration and re-initialization
- Log detailed error information for debugging

### 3. Market Data Integration
- Fetch options chain from NSE India API
- Filter for nearest expiry date
- Handle API changes and errors gracefully
- Support for both live data and historical backtesting
- Implement fallback mechanisms for data reliability

### 4. Performance Analytics
- Calculate win rate, average profit/loss per trade
- Compute profit factor, Sharpe ratio, maximum drawdown
- Generate detailed performance reports
- Track portfolio value over time
- Compare performance across different time periods

### 5. Risk Controls
- Position size limits based on portfolio value
- Daily loss limits with automatic trading halt
- Portfolio risk percentage limits
- Margin utilization monitoring
- Maximum concurrent positions limit

### 6. Date/Time Handling
- Use appropriate timezone handling for Indian market hours (IST)
- Handle daylight saving time transitions
- Support for different date formats in data files
- Implement business day calculations

### 7. Memory Management
- Implement efficient data structures for handling large options chains
- Use generators for memory-efficient data processing
- Implement caching with size limits
- Handle garbage collection appropriately

### 8. API Rate Limiting
- Respect Zerodha's API rate limits and implement appropriate delays
- Implement request queuing for high-frequency operations
- Monitor API usage and log rate limiting events
- Handle rate limit exceeded errors gracefully

### 9. Data Validation
- Validate all inputs from APIs and user configurations
- Implement data quality checks for incoming market data
- Handle malformed or missing data gracefully
- Log data validation errors for troubleshooting

### 10. Historical Trade Integration
- Support for importing and analyzing historical trade CSV files
- Multi-file CSV loading from multiple directories
- Advanced filtering capabilities (date range, year, quarter, symbol)
- Year-over-year and quarter-over-quarter analysis
- Option Greeks proxy analysis (theta, delta, gamma)

### 11. Advanced Analytics
- Year-over-year performance comparison
- Quarter-over-quarter performance analysis
- Option Greeks proxy analysis (theta, delta, gamma)
- Risk-adjusted return metrics
- Correlation analysis between different symbols

### 12. Filtering Capabilities
- Date range filters for targeted analysis
- Year filters for annual performance review
- Quarter filters for quarterly analysis
- Symbol filters for instrument-specific analysis
- Combined filter support for complex analysis

### 13. Auto-Rolling Logic
- Auto rolling functions in `auto_roll_functions.py`
- Check for positions expiring soon (DTE <= 1)
- Roll puts down & out (lower strike)
- Roll calls up & out (higher strike)

### 14. Health Check Utilities
- Health check functions in `health_check.py`
- System status verification
- Database connectivity checks
- API connectivity checks

### 15. Verification and Testing
- Basic functionality tests in `basic_functionality_test.py`
- Final verification checks in `final_verification.py`
- Comprehensive test suite in `/tests/` directory

## Testing Requirements

Create comprehensive test suites:
- Unit tests for configuration, models, utilities
- Integration tests for strategy logic
- Backtesting tests with mock data
- Error handling tests for edge cases
- Test coverage for all major functionality
- Include test for all risk management features
- Test safety features (dry run, kill switch, confirmation)
- Test compliance features (holiday calendar, timezone enforcement)
- Test enhanced analytics features

### Test Categories:

#### Unit Tests
- Configuration validation and loading
- Model serialization and deserialization
- Utility function correctness
- Enum value validations
- Data validation functions

#### Integration Tests
- Strategy cycle execution
- Order placement and management
- Position tracking and management
- Risk limit enforcement
- State persistence and recovery

#### Backtesting Tests
- Mock KiteConnect functionality
- Historical data loading and processing
- Performance metric calculation
- Transaction cost modeling
- Slippage and fill logic simulation

#### Enhanced Feature Tests
- Dry run mode functionality
- Kill switch activation and deactivation
- Live trading confirmation workflow
- Holiday calendar integration
- Timezone enforcement
- Multi-channel notifications
- Critical alerts system
- Auto-rolling logic

#### Error Handling Tests
- Network error handling and retry logic
- API error simulation and handling
- Configuration validation errors
- Data quality issues and recovery
- Resource limit exceeded scenarios

#### Performance Tests
- High-frequency data processing
- Large portfolio position management
- Concurrent strategy execution
- Memory usage optimization
- Database performance under load

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
- Safety features (dry run, kill switch, confirmation)
- Compliance notes (Zerodha product rules, tax hooks)
- Deployment guide (Docker, systemd, cloud)
- Backtesting realism (fees, slippage, fill logic)
- Holiday handling (how to update nse_holidays.csv)

### Additional Documentation:
- IMPLEMENTATION_SUMMARY.md: Summary of all components
- TEST_CASES.md: Detailed test case specifications
- NIFTY_DATA_SOURCES.md: Information about data sources for backtesting
- DEPLOYMENT.md: Comprehensive deployment guide
- ENHANCEMENTS_SUMMARY.md: Summary of safety and compliance enhancements
- COMPREHENSIVE_TEST_REPORT.md: Detailed test report
- AUDIT_SUMMARY.md: Security audit summary
- FINAL_SUMMARY.md: Final project summary

## Configuration (.env)

The .env file should support the following variables:
```
# API Credentials
KITE_API_KEY=your_api_key_here
KITE_API_SECRET=your_api_secret_here
KITE_ACCESS_TOKEN=your_access_token_here

# Trading Parameters
SYMBOL=NIFTY
QUANTITY_PER_LOT=50
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

# Safety & Compliance Settings
DRY_RUN=true
USE_HOLIDAY_CALENDAR=false
HOLIDAY_FILE_PATH=./data/nse_holidays.csv
STRATEGY_MODE=balanced
RISK_PER_TRADE_PERCENT=0.01
MIN_CASH_RESERVE=10000
ENABLE_AUTO_ROLL=false
KILL_SWITCH_FILE=STOP_TRADING

# Additional Settings
INCLUDE_FEES_IN_BACKTEST=true
NOTIFICATION_TYPE=webhook
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
- Implement live trading confirmation for safety
- Check for kill switch file before starting
- Validate configuration parameters

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
11. **Historical Trade Integration**: Support for importing and analyzing historical trade CSV files
12. **Advanced Analytics**: Year-over-year, quarter-over-quarter, and Greeks-based analysis
13. **Filtering Capabilities**: Date range, symbol, year, and quarter filters for targeted analysis
14. **Safety Features**: Dry run mode, kill switch, and live trading confirmation
15. **Compliance Features**: Holiday calendar integration and timezone enforcement
16. **Production Readiness**: Docker support, systemd service files, and deployment guides
17. **Enhanced Monitoring**: Multi-channel notifications and critical alerts system
18. **Capital Management**: Real-time margin monitoring and dynamic position sizing
19. **Strategy Flexibility**: Strategy modes and auto-rolling logic
20. **Database Integration**: SQLite database for persistence with proper indexing
21. **Dashboard Integration**: Streamlit dashboard with real-time analytics
22. **Backtesting System**: Comprehensive backtesting with realistic market conditions

## Testing Guidelines

Each module should have comprehensive unit tests covering:
- Normal operation scenarios
- Error conditions and edge cases
- Boundary conditions
- Integration between components
- All public methods and functions
- Safety and compliance features
- Enhanced analytics functionality

The system should be designed for continuous operation in live trading mode while also supporting backtesting with historical data and advanced analytics for historical trade performance review.

## Important Notes

- This is for educational purposes only - trading involves significant financial risk
- The system should never risk more than the user can afford to lose
- Users must understand all risks before using the system for live trading
- Always test thoroughly in a simulated environment before live trading
- The system should be compliant with Zerodha API terms of service
- All safety features must be thoroughly tested before live deployment
- Users should understand Indian market regulations and tax implications

## File Organization Notes

- The main application code is in the `Trading/` directory
- Historical trade CSV files should be placed in the `historical_trades/` directory or main project directory
- Configuration files and logs have dedicated directories
- The dashboard automatically looks for tradebook CSV files in `/Users/nagashankar/pythonScripts/OWS` and `/Users/nagashankar/pythonScripts/OWS/historical_trades`
- The project uses SQLite for data persistence with `trading_data.db` as the main database
- There is a hardcoded path in the dashboard for CSV file loading that should be configurable