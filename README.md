# Options Wheel Strategy Trading Bot

## Overview

This is a comprehensive options trading bot that implements the "Options Wheel Strategy" for the Indian stock market using Zerodha's KiteConnect API. This is a sophisticated income-generating strategy that involves selling out-of-the-money (OTM) options to collect premiums. The project is modular, production-ready, and includes both live trading and backtesting capabilities with advanced analytics and historical trade integration.

## 🚀 Features

### Core Strategy
- **Options Wheel Strategy**: Implementation of the classic "Wheel Strategy" for generating income
- **Cash-Secured Puts**: Sell OTM puts to collect premiums while maintaining sufficient cash to buy the underlying stock if assigned
- **Covered Calls**: When assigned, sell OTM calls against the holdings to collect additional premiums
- **Position Management**: Automatic management of profit targets and stop losses

### Safety & Compliance
- **Dry Run Mode**: Test all strategies without placing real trades
- **Live Trading Confirmation**: Mandatory confirmation for live trading mode
- **Kill Switch**: Emergency stop functionality with file-based activation
- **Indian Market Compliance**: Zerodha product alignment and holiday calendar integration
- **Timezone Enforcement**: All operations in Asia/Kolkata timezone

### Capital & Risk Management
- **Real-Time Margin Monitoring**: Prevents over-trading with live margin checks
- **Dynamic Position Sizing**: Risk-based lot sizing instead of fixed quantities
- **Auto Rolling Logic**: Automatic rolling of expiring options to optimize P&L
- **Risk Controls**: Daily loss limits, position limits, and portfolio risk management

### Advanced Analytics
- **Historical Trade Analysis**: Multi-file CSV loading with YoY/QoQ analysis
- **Option Greeks Analysis**: Proxy-based delta, gamma, theta analysis
- **Backtesting Realism**: Transaction cost modeling, slippage, and fill logic
- **Multi-Channel Notifications**: Telegram, Slack, Email, and Webhook support

## 📁 Project Structure

```
Trading/
├── .env                           # Environment variables and API keys
├── requirements.txt               # Python dependencies
├── IMPLEMENTATION_SUMMARY.md      # Documentation of components
├── TEST_CASES.md                  # Test case specifications
├── README.md                      # Comprehensive documentation
├── DEPLOYMENT.md                  # Deployment guide
├── ENHANCEMENTS_SUMMARY.md        # Summary of safety and compliance enhancements
├── run_tests.py                   # Test runner
├── Dockerfile                    # Docker support
├── docker-compose.yml            # Docker Compose configuration
├── docker-compose.dev.yml        # Development Docker Compose override
├── options_wheel_bot.service     # Systemd service file
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

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.9+
- Zerodha Kite API credentials
- Docker (for Docker deployment)
- Sufficient capital for trading
- Risk management understanding

### Quick Start
1. Clone the repository:
   ```bash
   git clone https://github.com/nagaforcloud/OWS.git
   cd OWS
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up your environment variables in `.env`:
   ```env
   # API Credentials
   KITE_API_KEY=your_api_key_here
   KITE_API_SECRET=your_api_secret_here
   KITE_ACCESS_TOKEN=your_access_token_here

   # Trading Parameters
   SYMBOL=NIFTY
   QUANTITY_PER_LOT=50
   PROFIT_TARGET_PERCENTAGE=0.50
   LOSS_LIMIT_PERCENTAGE=1.00

   # Risk Management
   MAX_CONCURRENT_POSITIONS=5
   MAX_DAILY_LOSS_LIMIT=5000.0
   MAX_PORTFOLIO_RISK=0.02

   # Safety & Compliance
   DRY_RUN=true
   KILL_SWITCH_FILE=STOP_TRADING
   ```

4. Run the bot:
   ```bash
   # For live trading (after setting DRY_RUN=false)
   python main.py

   # For backtesting
   USE_NIFTY=true python main.py
   ```

## 📊 Dashboard

The bot includes a web-based dashboard for monitoring:

```bash
streamlit run dashboard/dashboard.py
```

Access the dashboard at `http://localhost:8501`

## 🐳 Docker Deployment

1. Build and run with Docker Compose:
   ```bash
   docker-compose up -d
   ```

2. Access the dashboard at `http://localhost:8501`

## ⚠️ Important Notes

**This is for educational purposes only - trading involves significant financial risk.**

The system should never risk more than the user can afford to lose. Users must understand all risks before using the system for live trading. Always test thoroughly in a simulated environment before live trading.

## 📞 Support

For issues, questions, or contributions, please open an issue on the repository or contact the maintainers.