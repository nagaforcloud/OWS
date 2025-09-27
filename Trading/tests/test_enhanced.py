"""
Enhanced tests for the Options Wheel Strategy.
"""
import sys
import os
import unittest
import tempfile
import sqlite3
import pandas as pd
import datetime
from unittest.mock import Mock, patch, MagicMock

# Add the project root to the path
project_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, project_root)


class TestDatabaseIntegration(unittest.TestCase):
    """Test cases for database integration."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a temporary database for testing
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test_strategy.db')
        
    def tearDown(self):
        """Clean up after each test method."""
        # Remove temporary files
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)
    
    def test_database_initialization(self):
        """Test database initialization."""
        try:
            from option_wheel_strategy.database.database import StrategyDatabase
            db = StrategyDatabase(self.db_path)
            
            # Check that database file was created
            self.assertTrue(os.path.exists(self.db_path))
            
            # Check that tables were created
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check trades table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trades'")
            self.assertTrue(cursor.fetchone())
            
            # Check positions table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='positions'")
            self.assertTrue(cursor.fetchone())
            
            # Check performance_metrics table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='performance_metrics'")
            self.assertTrue(cursor.fetchone())
            
            conn.close()
            
        except Exception as e:
            self.fail(f"Database initialization failed: {e}")
    
    def test_save_trade(self):
        """Test saving a trade."""
        try:
            from option_wheel_strategy.database.database import StrategyDatabase
            db = StrategyDatabase(self.db_path)
            
            trade_data = {
                'order_id': 'TEST_ORDER_001',
                'tradingsymbol': 'NIFTY24JAN20000CE',
                'transaction_type': 'SELL',
                'quantity': 50,
                'price': 150.50,
                'product': 'NRML',
                'exchange': 'NSE',
                'timestamp': datetime.datetime.now().isoformat(),
                'pnl': 0.0,
                'strategy_id': 'test_session_001'
            }
            
            # Save trade
            result = db.save_trade(trade_data)
            self.assertTrue(result)
            
            # Retrieve trade and verify
            trades_df = db.get_trades(strategy_id='test_session_001')
            self.assertEqual(len(trades_df), 1)
            self.assertEqual(trades_df.iloc[0]['order_id'], 'TEST_ORDER_001')
            
        except Exception as e:
            self.fail(f"Save trade test failed: {e}")
    
    def test_save_position(self):
        """Test saving a position."""
        try:
            from option_wheel_strategy.database.database import StrategyDatabase
            db = StrategyDatabase(self.db_path)
            
            position_data = {
                'tradingsymbol': 'NIFTY24JAN20000CE',
                'quantity': -50,
                'average_price': 150.50,
                'product': 'NRML',
                'exchange': 'NSE',
                'instrument_token': 123456,
                'pnl': 250.0,
                'market_value': 7250.0,
                'timestamp': datetime.datetime.now().isoformat(),
                'strategy_id': 'test_session_001'
            }
            
            # Save position
            result = db.save_position(position_data)
            self.assertTrue(result)
            
            # Retrieve position and verify
            positions_df = db.get_positions(strategy_id='test_session_001')
            self.assertEqual(len(positions_df), 1)
            self.assertEqual(positions_df.iloc[0]['tradingsymbol'], 'NIFTY24JAN20000CE')
            
        except Exception as e:
            self.fail(f"Save position test failed: {e}")


class TestRiskManagement(unittest.TestCase):
    """Test cases for risk management."""

    def test_risk_config_creation(self):
        """Test risk configuration creation."""
        try:
            from option_wheel_strategy.risk_management.risk_manager import RiskConfig
            config = RiskConfig()
            
            # Check default values
            self.assertEqual(config.max_portfolio_risk, 0.02)
            self.assertEqual(config.max_position_size, 0.05)
            self.assertEqual(config.max_daily_loss_limit, 5000.0)
            self.assertEqual(config.max_concurrent_positions, 10)
            
        except Exception as e:
            self.fail(f"RiskConfig creation failed: {e}")
    
    def test_risk_manager_initialization(self):
        """Test risk manager initialization."""
        try:
            from option_wheel_strategy.risk_management.risk_manager import RiskConfig, RiskManager
            config = RiskConfig()
            risk_manager = RiskManager(config)
            
            # Check initial state
            self.assertEqual(risk_manager.portfolio_value, 0.0)
            self.assertEqual(risk_manager.available_margin, 0.0)
            self.assertEqual(risk_manager.positions, [])
            self.assertEqual(risk_manager.daily_losses, 0.0)
            
        except Exception as e:
            self.fail(f"RiskManager initialization failed: {e}")
    
    def test_position_size_limit_check(self):
        """Test position size limit checking."""
        try:
            from option_wheel_strategy.risk_management.risk_manager import RiskConfig, RiskManager
            config = RiskConfig(max_position_size=0.05)  # 5% limit
            risk_manager = RiskManager(config)
            
            # Update portfolio state
            risk_manager.portfolio_value = 100000.0  # 100k portfolio
            
            # Test within limit
            result = risk_manager.check_position_size_limit('TEST', 100, 40.0)  # 4k position, 4% of portfolio
            self.assertTrue(result)
            
            # Test exceeding limit
            result = risk_manager.check_position_size_limit('TEST', 200, 40.0)  # 8k position, 8% of portfolio
            self.assertFalse(result)
            
        except Exception as e:
            self.fail(f"Position size limit check failed: {e}")
    
    def test_portfolio_risk_limit_check(self):
        """Test portfolio risk limit checking."""
        try:
            from option_wheel_strategy.risk_management.risk_manager import RiskConfig, RiskManager
            config = RiskConfig(max_portfolio_risk=0.02)  # 2% limit
            risk_manager = RiskManager(config)
            
            # Update portfolio state with high risk exposure
            risk_manager.portfolio_value = 100000.0
            
            # Mock positions with high risk exposure
            mock_positions = [
                {
                    'tradingsymbol': 'TEST1',
                    'quantity': -100,
                    'average_price': 50.0,
                    'current_price': 60.0,
                    'pnl': -1000.0,
                    'market_value': -6000.0,
                    'risk_exposure': 0.06,  # 6% of portfolio
                    'days_to_expiry': 10,
                    'delta': -0.3
                }
            ]
            
            # Use reflection to set positions directly
            risk_manager.positions = []
            for pos in mock_positions:
                from option_wheel_strategy.risk_management.risk_manager import PositionRisk
                position_risk = PositionRisk(
                    tradingsymbol=pos['tradingsymbol'],
                    quantity=pos['quantity'],
                    average_price=pos['average_price'],
                    current_price=pos['current_price'],
                    pnl=pos['pnl'],
                    market_value=pos['market_value'],
                    risk_exposure=pos['risk_exposure'],
                    days_to_expiry=pos['days_to_expiry'],
                    delta=pos['delta']
                )
                risk_manager.positions.append(position_risk)
            
            # Test exceeding limit (6% > 2%)
            result = risk_manager.check_portfolio_risk_limit()
            self.assertFalse(result)
            
        except Exception as e:
            self.fail(f"Portfolio risk limit check failed: {e}")


class TestNSEDataCollector(unittest.TestCase):
    """Test cases for NSE data collector."""

    def test_url_generation(self):
        """Test URL generation for NSE data download."""
        try:
            from option_wheel_strategy.backtesting.nse_data_collector import NSEDataCollector
            collector = NSEDataCollector()
            
            # Test URL for a specific date
            test_date = datetime.date(2023, 1, 15)
            url = collector._get_url_for_date(test_date)
            
            # Check that URL contains expected components
            self.assertIn("archives.nseindia.com", url)
            self.assertIn("2023", url)
            self.assertIn("JAN", url)
            self.assertIn("15", url)
            self.assertIn("fo15JAN2023bhav.csv.zip", url)
            
        except Exception as e:
            self.fail(f"URL generation test failed: {e}")
    
    def test_data_processing(self):
        """Test processing of raw options data."""
        try:
            from option_wheel_strategy.backtesting.nse_data_collector import NSEDataCollector
            import pandas as pd
            
            # Create mock raw data
            raw_data = pd.DataFrame({
                'INSTRUMENT': ['OPTIDX', 'OPTIDX', 'FUTIDX'],
                'SYMBOL': ['NIFTY', 'NIFTY', 'NIFTY'],
                'EXPIRY_DT': ['25-Jan-2023', '25-Jan-2023', '25-Jan-2023'],
                'STRIKE_PR': [18000, 18500, 0],
                'OPTION_TYP': ['CE', 'PE', 'XX'],
                'OPEN': [150, 100, 18200],
                'HIGH': [160, 110, 18300],
                'LOW': [140, 90, 18100],
                'CLOSE': [155, 105, 18250],
                'SETTLE_PR': [152, 102, 18240],
                'CONTRACTS': [1000, 800, 500],
                'VAL_INLAKH': [1500, 800, 9000],
                'OPEN_INT': [5000, 4000, 2000],
                'CHG_IN_OI': [100, 50, 20],
                'TIMESTAMP': ['15-Jan-2023', '15-Jan-2023', '15-Jan-2023']
            })
            
            collector = NSEDataCollector()
            processed_data = collector._process_options_data(raw_data, datetime.date(2023, 1, 15))
            
            # Check that only options data is processed
            self.assertEqual(len(processed_data), 2)
            self.assertTrue(all(processed_data['INSTRUMENT'] == 'OPTIDX'))
            
            # Check that date column was added
            self.assertTrue('DATE' in processed_data.columns)
            
        except Exception as e:
            self.fail(f"Data processing test failed: {e}")


def run_enhanced_tests():
    """Run all enhanced tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestRiskManagement))
    suite.addTests(loader.loadTestsFromTestCase(TestNSEDataCollector))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_enhanced_tests()
    sys.exit(0 if success else 1)