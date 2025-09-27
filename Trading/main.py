#!/usr/bin/env python3
"""
Main entry point for the Options Wheel Strategy Trading Bot
"""
import sys
import os
import signal
import time
from datetime import datetime
import logging

# Add the project root to the Python path to import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.config import OptionWheelConfig
from core.strategy import OptionWheelStrategy
from backtesting.nifty_backtesting import NiftyBacktestingStrategy
from backtesting.prepare_nifty_data import generate_sample_data
from utils.logging_utils import setup_logging, get_logger
from kiteconnect import KiteConnect
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = get_logger(__name__)

def create_kite_client(config: OptionWheelConfig):
    """
    Create and return a KiteConnect client instance
    
    Args:
        config: OptionWheelConfig instance
        
    Returns:
        KiteConnect client instance or None if failed
    """
    try:
        kite = KiteConnect(api_key=config.api_key)
        
        # If access token is provided, set it directly
        if config.access_token:
            kite.set_access_token(config.access_token)
            logger.info("KiteConnect client initialized with access token")
            return kite
        else:
            logger.warning("No access token provided. You'll need to authenticate manually.")
            # Print the login URL for user to authenticate
            login_url = kite.login_url()
            print(f"Please visit this URL to authenticate: {login_url}")
            return kite
            
    except Exception as e:
        logger.error(f"Error creating KiteConnect client: {e}")
        return None

def run_backtesting(config: OptionWheelConfig):
    """
    Run the backtesting strategy
    
    Args:
        config: OptionWheelConfig instance
        
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info("Starting backtesting mode...")
    
    try:
        # Initialize the backtesting strategy
        backtester = NiftyBacktestingStrategy(config, initial_capital=100000)
        
        # Define date range for backtesting (last 30 days)
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # Run backtesting
        logger.info(f"Running backtest from {start_date.date()} to {end_date.date()}")
        results = backtester.run_backtest(start_date, end_date)
        
        # Print results
        if results:
            print("=" * 60)
            print("BACKTESTING RESULTS")
            print("=" * 60)
            print(f"Initial Capital: ₹{results['initial_capital']:,.2f}")
            print(f"Final Capital: ₹{results['final_capital']:,.2f}")
            print(f"Total Return: {results['total_return_percentage']:.2f}%")
            print(f"Total P&L: ₹{results['total_pnl']:,.2f}")
            print(f"Total Trades: {results['total_trades']}")
            print(f"Profitable Trades: {results['profitable_trades']}")
            print(f"Win Rate: {results['win_rate']:.2f}%")
            print(f"Max Drawdown: {results['max_drawdown_percentage']:.2f}%")
            print(f"Profit Factor: {results['profit_factor']:.2f}")
            print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
            print(f"Positions at End: {results['positions_at_end']}")
            print(f"Strategy Periods: {results['strategy_periods']}")
            print("=" * 60)
            
            # Save results to file
            results_file = f"backtest_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            import json
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"Results saved to: {results_file}")
            
        else:
            logger.error("Backtesting failed to return results")
            return False
            
    except Exception as e:
        logger.error(f"Error running backtesting: {e}")
        return False
    
    return True

def run_live_trading(config: OptionWheelConfig):
    """
    Run the live trading strategy
    
    Args:
        config: OptionWheelConfig instance
        
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info("Starting live trading mode...")
    
    # Check if dry run mode is enabled
    if config.dry_run:
        logger.info("[DRY RUN MODE] Orders will be simulated but not placed on exchange")
    else:
        # Only for live trading (not dry run), get user confirmation
        print("\n⚠️  LIVE TRADING MODE ENABLED")
        print("This will place real orders on the exchange.")
        confirmation = input("Type 'CONFIRM' to proceed with live trading: ")
        if confirmation.strip() != 'CONFIRM':
            print("Live trading cancelled. Confirmation required to proceed.")
            return False
        print("Live trading confirmed. Starting strategy...")

    # Create Kite client
    kite_client = create_kite_client(config)
    
    if not kite_client:
        logger.error("Could not create KiteConnect client. Exiting.")
        return False

    # Initialize the strategy
    strategy = OptionWheelStrategy(config, kite_client=kite_client)
    
    # Set up signal handling for graceful shutdown
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, initiating graceful shutdown...")
        strategy.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start the strategy
    logger.info("Starting Options Wheel Strategy...")
    strategy.start()
    
    try:
        # Keep the main thread alive
        while strategy.running:
            # Check for kill switch
            if strategy.check_kill_switch():
                logger.warning("Kill switch activated, stopping strategy...")
                strategy.stop()
                break
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, stopping strategy...")
        strategy.stop()
    
    return True

def prepare_backtesting_data():
    """
    Prepare backtesting data by generating sample data
    
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info("Preparing backtesting data...")
    output_dir = "backtesting_data"
    success = generate_sample_data(output_dir)
    
    if success:
        logger.info(f"Backtesting data prepared in: {output_dir}")
        print(f"Backtesting data has been prepared in: {output_dir}")
        print("You can now run backtesting using the bot.")
        return True
    else:
        logger.error("Failed to prepare backtesting data")
        return False

def main():
    """
    Main function that determines the execution mode based on configuration
    
    Returns:
        None
    """
    print("=" * 60)
    print("OPTIONS WHEEL STRATEGY TRADING BOT")
    print("=" * 60)
    
    # Initialize configuration
    try:
        config = OptionWheelConfig()
        print(f"Configuration loaded. Trading symbol: {config.symbol}")
    except ValueError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)
    
    # Determine execution mode based on configuration
    if config.use_nifty:
        print("Mode: Backtesting with NIFTY data")
        success = run_backtesting(config)
    elif os.getenv("PREPARE_DATA", "").lower() == "true":
        print("Mode: Preparing backtesting data")
        success = prepare_backtesting_data()
    else:
        print("Mode: Live trading (if API credentials are valid)")
        success = run_live_trading(config)
    
    if success:
        print("\nExecution completed successfully.")
    else:
        print("\nExecution failed. Check logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()