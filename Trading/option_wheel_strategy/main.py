"""
Main entry point for the Option Wheel Strategy.
"""
import sys
import os
import datetime

# Add the parent directory to the Python path so we can import from our package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from option_wheel_strategy.config.config import OptionWheelConfig
from option_wheel_strategy.core.strategy import OptionWheelStrategy
from option_wheel_strategy.backtesting.mock_kite import MockKiteConnect
from option_wheel_strategy.backtesting.nifty_backtesting import NiftyBacktestingStrategy


def main():
    """Main entry point for the Option Wheel Strategy."""
    # Initialize configuration
    app_config = OptionWheelConfig()
    
    # Check if we want to run with NIFTY data
    use_nifty = os.getenv("USE_NIFTY", "false").lower() == "true"
    
    if use_nifty:
        print("Running with NIFTY options data...")
        # Run with NIFTY data
        run_nifty_backtest()
    else:
        # Run with original configuration
        run_standard_strategy(app_config)


def run_standard_strategy(app_config: OptionWheelConfig):
    """Run the standard strategy (TCS or other symbol)."""
    # --- Choose Mode: Live Trading or Backtesting ---
    # Uncomment ONE of the following blocks:

    # LIVE TRADING MODE
    strategy = OptionWheelStrategy(app_config)

    # BACKTESTING MODE
    # The historical_data_for_backtest_example is now passed to MockKiteConnect
    # but actual data loading happens inside strategy.run()
    # mock_kite = MockKiteConnect(historical_data={}) # Initialize with empty data, it will be populated
    # strategy = OptionWheelStrategy(app_config, kite_client=mock_kite)

    # Run the strategy (will trigger data loading if in backtesting mode)
    strategy.run()


def run_nifty_backtest():
    """Run backtest with NIFTY options data."""
    # Initialize NIFTY backtesting strategy
    backtest = NiftyBacktestingStrategy()
    
    # Define date range (last 30 days)
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=30)
    
    # Run backtest
    results = backtest.run_backtest(start_date, end_date)
    
    print("NIFTY Backtest Results:")
    for key, value in results.items():
        print(f"  {key}: {value}")
    
    print("\nTo run a full backtest, you would implement the strategy execution loop here.")


if __name__ == "__main__":
    main()