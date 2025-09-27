# 🚀 Deployment Guide for Options Wheel Strategy Trading Bot

This guide covers deployment options for the Options Wheel Strategy Trading Bot, including Docker containers, systemd services, and cloud deployment.

## 📋 Table of Contents
1. [Prerequisites](#prerequisites)
2. [Docker Deployment](#docker-deployment)
3. [Systemd Service Deployment](#systemd-service-deployment)
4. [Cloud Deployment](#cloud-deployment)
5. [Environment Configuration](#environment-configuration)
6. [Monitoring and Maintenance](#monitoring-and-maintenance)

## 🛠️ Prerequisites

Before deploying, ensure you have:

- Python 3.9+
- Docker and Docker Compose (for Docker deployment)
- Systemd (for Linux service deployment)
- Access to Zerodha Kite API credentials
- Sufficient capital for trading
- Risk management understanding

```bash
# Check Python version
python --version

# Install Docker (Ubuntu/Debian)
sudo apt update
sudo apt install docker.io docker-compose -y
sudo usermod -aG docker $USER

# Install Systemd (usually pre-installed on most Linux distributions)
systemctl --version
```

## 🐳 Docker Deployment

### Quick Start with Docker

1. **Build and run with Docker Compose:**
```bash
cd /path/to/trading-bot
docker-compose up -d
```

2. **Access the dashboard:**
Open your browser to `http://localhost:8501`

### Docker Commands

- **Build the image:**
```bash
docker build -t options-wheel-bot .
```

- **Run the container:**
```bash
docker run -d \
  --name=options-wheel-bot \
  -p 8501:8501 \
  -v ./data:/app/data \
  -v ./logs:/app/logs \
  -v ./trading_data.db:/app/trading_data.db \
  -v .env:/app/.env \
  options-wheel-bot
```

- **View logs:**
```bash
docker logs options-wheel-bot
```

- **Stop the container:**
```bash
docker stop options-wheel-bot
```

### Development Mode

For development with live reloading:
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

## ⚙️ Systemd Service Deployment

### Setup Steps

1. **Create a dedicated user:**
```bash
sudo useradd -r -s /bin/false tradingbot
```

2. **Install the bot to /opt:**
```bash
sudo mkdir -p /opt/trading-bot
sudo cp -r . /opt/trading-bot/
sudo chown -r tradingbot:tradingbot /opt/trading-bot
```

3. **Create a virtual environment:**
```bash
cd /opt/trading-bot
sudo -u tradingbot python3 -m venv venv
sudo -u tradingbot venv/bin/pip install -r requirements.txt
```

4. **Copy the service file:**
```bash
sudo cp options_wheel_bot.service /etc/systemd/system/
```

5. **Enable and start the service:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable options-wheel-bot
sudo systemctl start options-wheel-bot
```

6. **Check service status:**
```bash
sudo systemctl status options-wheel-bot
```

### Service Management

- **Start the service:**
```bash
sudo systemctl start options-wheel-bot
```

- **Stop the service:**
```bash
sudo systemctl stop options-wheel-bot
```

- **Restart the service:**
```bash
sudo systemctl restart options-wheel-bot
```

- **View logs:**
```bash
sudo journalctl -u options-wheel-bot -f
```

## ☁️ Cloud Deployment

### AWS Deployment

#### EC2 Instance

1. **Launch an EC2 instance:**
   - Ubuntu 20.04 LTS or newer
   - t3.micro or t3.small (for dashboard access)
   - Open ports 22 (SSH) and 8501 (Streamlit)

2. **Install Docker:**
```bash
sudo apt update
sudo apt install docker.io docker-compose -y
sudo usermod -aG docker ubuntu
```

3. **Deploy the bot:**
```bash
git clone <repository-url> /home/ubuntu/trading-bot
cd /home/ubuntu/trading-bot
docker-compose up -d
```

#### ECS/Fargate

Create a task definition and service in AWS ECS to run the container.

### Google Cloud Platform

#### Compute Engine

Similar to AWS EC2:
1. Create a Compute Engine instance
2. Install Docker
3. Deploy using Docker Compose

#### Cloud Run

For stateless deployments, you can deploy to Cloud Run with the dashboard exposed.

## ⚙️ Environment Configuration

### Required Environment Variables

Create a `.env` file with your configuration:

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
MIN_CASH_RESERVE=10000
RISK_PER_TRADE_PERCENT=0.01

# Notification Settings
ENABLE_NOTIFICATIONS=false
NOTIFICATION_WEBHOOK_URL=
NOTIFICATION_TYPE=webhook
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
SLACK_WEBHOOK_URL=
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SENDER_EMAIL=
RECIPIENT_EMAIL=

# Data Settings
USE_NSE_API=true
DATA_REFRESH_INTERVAL=60
USE_NIFTY=false
HOLIDAY_FILE_PATH=./data/nse_holidays.csv

# Safety & Compliance Settings
DRY_RUN=true
USE_HOLIDAY_CALENDAR=false
STRATEGY_MODE=balanced
ENABLE_AUTO_ROLL=false
KILL_SWITCH_FILE=STOP_TRADING

# Backtesting Settings
INCLUDE_FEES_IN_BACKTEST=true
USE_SAMPLE_DATA=false
```

### Safety Configuration

#### Dry Run Mode
Set `DRY_RUN=true` to test all strategies without placing real trades:
```env
DRY_RUN=true  # Logs orders but never places real trades
```

#### Live Trading Confirmation
On first execution in live mode (`DRY_RUN=false`), the system will prompt:
```
⚠️ LIVE TRADING MODE ENABLED. Type 'CONFIRM' to proceed:
```

#### Kill Switch
Create a file named `STOP_TRADING` in the root directory to emergency stop trading:
```bash
touch STOP_TRADING  # Creates kill switch file
```

## 🔍 Monitoring and Maintenance

### Health Checks

The Docker container includes a built-in health check that verifies the Streamlit dashboard is responding.

### Log Monitoring

Monitor logs regularly:
```bash
# Docker
docker logs options-wheel-bot -f

# Systemd
sudo journalctl -u options-wheel-bot -f
```

### Backup Strategy

Regularly backup important files:
- `trading_data.db` - Database with positions and trades
- `strategy_state.json` - Strategy state
- `logs/` directory - Log files
- `.env` - Configuration (excluding sensitive data)

### Updates and Maintenance

1. **Pull latest code:**
```bash
git pull origin main
```

2. **Update dependencies:**
```bash
pip install -r requirements.txt --upgrade
```

3. **Restart services:**
```bash
sudo systemctl restart options-wheel-bot
# or
docker-compose restart
```

## 🔒 Security Considerations

### Credential Security
- Store API keys securely (consider using AWS Secrets Manager or HashiCorp Vault)
- Never commit `.env` files to version control
- Use environment variables for sensitive configuration

### Network Security
- Restrict network access to necessary ports only
- Use HTTPS for dashboard access in production
- Implement firewall rules to restrict access

### Access Control
- Regularly rotate API keys
- Use dedicated service accounts with minimal privileges
- Implement role-based access control where possible

### Process Security
- Run services with dedicated non-root users
- Implement proper file permissions
- Use systemd security directives in service files

## 🧪 Testing Deployment

### Local Testing
```bash
# Test Docker build
docker build -t options-wheel-bot-test .

# Test Docker run
docker run --rm -p 8501:8501 options-wheel-bot-test

# Test systemd service
sudo systemctl start options-wheel-bot-test
sudo systemctl status options-wheel-bot-test
```

### Integration Testing
1. Verify all environment variables are loaded correctly
2. Test database connectivity
3. Verify notification channels work
4. Check health endpoint responds correctly
5. Test dry run mode works as expected
6. Verify kill switch functionality

## 🚨 Emergency Procedures

### Immediate Stop Trading
1. Create kill switch file: `touch STOP_TRADING`
2. Restart the service/container: `sudo systemctl restart options-wheel-bot`

### Manual Intervention Required
1. Stop automated trading: `sudo systemctl stop options-wheel-bot`
2. Access dashboard for manual position management
3. Contact support if needed

### Recovery Procedures
1. Check logs for error details
2. Verify configuration files
3. Test API connectivity
4. Validate data integrity
5. Restart services after resolving issues

## 📈 Scaling Considerations

For high-volume trading or managing multiple strategies:

### Database Scaling
- Use PostgreSQL instead of SQLite for production
- Implement connection pooling for high-frequency operations
- Add read replicas for reporting queries

### Load Balancing
- Deploy multiple instances behind a load balancer
- Use shared database for state synchronization
- Implement sticky sessions for user sessions

### Monitoring & Alerting
- Implement Prometheus/Grafana for metrics
- Set up alerts for critical events
- Use centralized logging (ELK stack)

### Resource Optimization
- Monitor CPU and memory usage
- Implement caching for frequently accessed data
- Optimize database queries with proper indexing

## 📚 Documentation Updates

Keep documentation in sync with implementation:
- Update README.md when adding new features
- Document breaking changes in CHANGELOG.md
- Update deployment guide for new deployment methods
- Maintain test cases for new functionality

## 🎯 Conclusion

This deployment guide provides flexible options for running the Options Wheel Trading Bot in various environments. Choose the deployment method that best fits your infrastructure and operational requirements.

Always test deployments in a paper trading or simulation environment before going live with real capital.

⚠️ **Remember: This is for educational purposes only - trading involves significant financial risk. Users must understand all risks before using the system for live trading.**