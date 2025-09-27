"""
Database integration for Options Wheel Strategy.
Provides persistent storage for trades, positions, and performance metrics.
"""
import sqlite3
import pandas as pd
import datetime
import os
import logging
from typing import List, Dict, Optional, Any
from contextlib import contextmanager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StrategyDatabase:
    """SQLite database for storing strategy data."""
    
    def __init__(self, db_path: str = "strategy_data.db"):
        """
        Initialize the database.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._initialize_database()
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()
    
    def _initialize_database(self):
        """Initialize database tables."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Create trades table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        order_id TEXT NOT NULL,
                        tradingsymbol TEXT NOT NULL,
                        transaction_type TEXT NOT NULL,
                        quantity INTEGER NOT NULL,
                        price REAL NOT NULL,
                        product TEXT NOT NULL,
                        exchange TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        status TEXT DEFAULT 'completed',
                        pnl REAL DEFAULT 0.0,
                        strategy_id TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create positions table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS positions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tradingsymbol TEXT NOT NULL,
                        quantity INTEGER NOT NULL,
                        average_price REAL NOT NULL,
                        product TEXT NOT NULL,
                        exchange TEXT NOT NULL,
                        instrument_token INTEGER,
                        pnl REAL DEFAULT 0.0,
                        market_value REAL DEFAULT 0.0,
                        timestamp TEXT NOT NULL,
                        strategy_id TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create performance_metrics table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS performance_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        metric_name TEXT NOT NULL,
                        metric_value REAL NOT NULL,
                        timestamp TEXT NOT NULL,
                        strategy_id TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create strategy_sessions table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS strategy_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL UNIQUE,
                        start_time TEXT NOT NULL,
                        end_time TEXT,
                        status TEXT DEFAULT 'running',
                        initial_capital REAL,
                        final_capital REAL,
                        total_pnl REAL DEFAULT 0.0,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes for better performance
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_trades_timestamp 
                    ON trades(timestamp)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_trades_strategy 
                    ON trades(strategy_id)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_positions_symbol 
                    ON positions(tradingsymbol)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_metrics_timestamp 
                    ON performance_metrics(timestamp)
                """)
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def save_trade(self, trade_data: Dict[str, Any]) -> bool:
        """
        Save a trade record to the database.
        
        Args:
            trade_data: Dictionary containing trade information
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO trades (
                        order_id, tradingsymbol, transaction_type, quantity, 
                        price, product, exchange, timestamp, status, pnl, strategy_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trade_data.get('order_id'),
                    trade_data.get('tradingsymbol'),
                    trade_data.get('transaction_type'),
                    trade_data.get('quantity'),
                    trade_data.get('price', 0.0),
                    trade_data.get('product'),
                    trade_data.get('exchange'),
                    trade_data.get('timestamp'),
                    trade_data.get('status', 'completed'),
                    trade_data.get('pnl', 0.0),
                    trade_data.get('strategy_id')
                ))
                
                conn.commit()
                logger.info(f"Trade saved: {trade_data.get('order_id')}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to save trade: {e}")
            return False
    
    def save_position(self, position_data: Dict[str, Any]) -> bool:
        """
        Save a position record to the database.
        
        Args:
            position_data: Dictionary containing position information
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO positions (
                        tradingsymbol, quantity, average_price, product, 
                        exchange, instrument_token, pnl, market_value, 
                        timestamp, strategy_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    position_data.get('tradingsymbol'),
                    position_data.get('quantity'),
                    position_data.get('average_price'),
                    position_data.get('product'),
                    position_data.get('exchange'),
                    position_data.get('instrument_token'),
                    position_data.get('pnl', 0.0),
                    position_data.get('market_value', 0.0),
                    position_data.get('timestamp'),
                    position_data.get('strategy_id')
                ))
                
                conn.commit()
                logger.info(f"Position saved: {position_data.get('tradingsymbol')}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to save position: {e}")
            return False
    
    def save_performance_metric(self, metric_data: Dict[str, Any]) -> bool:
        """
        Save a performance metric to the database.
        
        Args:
            metric_data: Dictionary containing metric information
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO performance_metrics (
                        metric_name, metric_value, timestamp, strategy_id
                    ) VALUES (?, ?, ?, ?)
                """, (
                    metric_data.get('metric_name'),
                    metric_data.get('metric_value'),
                    metric_data.get('timestamp'),
                    metric_data.get('strategy_id')
                ))
                
                conn.commit()
                logger.info(f"Metric saved: {metric_data.get('metric_name')}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to save metric: {e}")
            return False
    
    def create_strategy_session(self, session_data: Dict[str, Any]) -> bool:
        """
        Create a new strategy session.
        
        Args:
            session_data: Dictionary containing session information
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO strategy_sessions (
                        session_id, start_time, initial_capital
                    ) VALUES (?, ?, ?)
                """, (
                    session_data.get('session_id'),
                    session_data.get('start_time'),
                    session_data.get('initial_capital')
                ))
                
                conn.commit()
                logger.info(f"Strategy session created: {session_data.get('session_id')}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to create strategy session: {e}")
            return False
    
    def update_strategy_session(self, session_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Update an existing strategy session.
        
        Args:
            session_id: Session ID to update
            update_data: Dictionary containing update information
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Build dynamic update query
                set_clauses = []
                values = []
                
                for key, value in update_data.items():
                    if key in ['end_time', 'status', 'final_capital', 'total_pnl']:
                        set_clauses.append(f"{key} = ?")
                        values.append(value)
                
                if not set_clauses:
                    return False
                
                values.append(session_id)
                
                query = f"""
                    UPDATE strategy_sessions 
                    SET {', '.join(set_clauses)} 
                    WHERE session_id = ?
                """
                
                cursor.execute(query, values)
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"Strategy session updated: {session_id}")
                    return True
                else:
                    logger.warning(f"No strategy session found to update: {session_id}")
                    return False
                
        except Exception as e:
            logger.error(f"Failed to update strategy session: {e}")
            return False
    
    def get_trades(self, strategy_id: Optional[str] = None, 
                   start_date: Optional[str] = None, 
                   end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Retrieve trades from the database.
        
        Args:
            strategy_id: Filter by strategy ID
            start_date: Filter by start date (inclusive)
            end_date: Filter by end date (inclusive)
            
        Returns:
            DataFrame with trades data
        """
        try:
            with self._get_connection() as conn:
                query = "SELECT * FROM trades WHERE 1=1"
                params = []
                
                if strategy_id:
                    query += " AND strategy_id = ?"
                    params.append(strategy_id)
                
                if start_date:
                    query += " AND timestamp >= ?"
                    params.append(start_date)
                
                if end_date:
                    query += " AND timestamp <= ?"
                    params.append(end_date)
                
                query += " ORDER BY timestamp DESC"
                
                df = pd.read_sql_query(query, conn, params=params)
                return df
                
        except Exception as e:
            logger.error(f"Failed to retrieve trades: {e}")
            return pd.DataFrame()
    
    def get_positions(self, strategy_id: Optional[str] = None) -> pd.DataFrame:
        """
        Retrieve positions from the database.
        
        Args:
            strategy_id: Filter by strategy ID
            
        Returns:
            DataFrame with positions data
        """
        try:
            with self._get_connection() as conn:
                query = "SELECT * FROM positions WHERE 1=1"
                params = []
                
                if strategy_id:
                    query += " AND strategy_id = ?"
                    params.append(strategy_id)
                
                query += " ORDER BY timestamp DESC"
                
                df = pd.read_sql_query(query, conn, params=params)
                return df
                
        except Exception as e:
            logger.error(f"Failed to retrieve positions: {e}")
            return pd.DataFrame()
    
    def get_performance_metrics(self, strategy_id: Optional[str] = None,
                              metric_name: Optional[str] = None) -> pd.DataFrame:
        """
        Retrieve performance metrics from the database.
        
        Args:
            strategy_id: Filter by strategy ID
            metric_name: Filter by metric name
            
        Returns:
            DataFrame with performance metrics data
        """
        try:
            with self._get_connection() as conn:
                query = "SELECT * FROM performance_metrics WHERE 1=1"
                params = []
                
                if strategy_id:
                    query += " AND strategy_id = ?"
                    params.append(strategy_id)
                
                if metric_name:
                    query += " AND metric_name = ?"
                    params.append(metric_name)
                
                query += " ORDER BY timestamp DESC"
                
                df = pd.read_sql_query(query, conn, params=params)
                return df
                
        except Exception as e:
            logger.error(f"Failed to retrieve performance metrics: {e}")
            return pd.DataFrame()
    
    def get_strategy_sessions(self, session_id: Optional[str] = None) -> pd.DataFrame:
        """
        Retrieve strategy sessions from the database.
        
        Args:
            session_id: Filter by specific session ID
            
        Returns:
            DataFrame with strategy sessions data
        """
        try:
            with self._get_connection() as conn:
                query = "SELECT * FROM strategy_sessions WHERE 1=1"
                params = []
                
                if session_id:
                    query += " AND session_id = ?"
                    params.append(session_id)
                
                query += " ORDER BY start_time DESC"
                
                df = pd.read_sql_query(query, conn, params=params)
                return df
                
        except Exception as e:
            logger.error(f"Failed to retrieve strategy sessions: {e}")
            return pd.DataFrame()
    
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Get summary statistics for a strategy session.
        
        Args:
            session_id: Session ID to summarize
            
        Returns:
            Dictionary with session summary statistics
        """
        try:
            with self._get_connection() as conn:
                # Get session info
                session_query = "SELECT * FROM strategy_sessions WHERE session_id = ?"
                session_df = pd.read_sql_query(session_query, conn, params=[session_id])
                
                if session_df.empty:
                    return {}
                
                session_info = session_df.iloc[0].to_dict()
                
                # Get trades for this session
                trades_query = "SELECT * FROM trades WHERE strategy_id = ?"
                trades_df = pd.read_sql_query(trades_query, conn, params=[session_id])
                
                # Calculate summary statistics
                summary = {
                    'session_info': session_info,
                    'total_trades': len(trades_df),
                    'total_pnl': session_info.get('total_pnl', 0.0),
                    'profitable_trades': len(trades_df[trades_df['pnl'] > 0]) if not trades_df.empty else 0,
                    'win_rate': len(trades_df[trades_df['pnl'] > 0]) / len(trades_df) if len(trades_df) > 0 else 0,
                    'avg_win': trades_df[trades_df['pnl'] > 0]['pnl'].mean() if len(trades_df[trades_df['pnl'] > 0]) > 0 else 0,
                    'avg_loss': trades_df[trades_df['pnl'] < 0]['pnl'].mean() if len(trades_df[trades_df['pnl'] < 0]) > 0 else 0
                }
                
                return summary
                
        except Exception as e:
            logger.error(f"Failed to generate session summary: {e}")
            return {}


def main():
    """Main function to demonstrate usage."""
    # Initialize database
    db = StrategyDatabase("test_strategy.db")
    
    # Create a test strategy session
    session_data = {
        'session_id': 'test_session_001',
        'start_time': datetime.datetime.now().isoformat(),
        'initial_capital': 100000.0
    }
    
    if db.create_strategy_session(session_data):
        print("Strategy session created successfully")
    
    # Save a test trade
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
    
    if db.save_trade(trade_data):
        print("Trade saved successfully")
    
    # Save a test position
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
    
    if db.save_position(position_data):
        print("Position saved successfully")
    
    # Save a test performance metric
    metric_data = {
        'metric_name': 'daily_pnl',
        'metric_value': 250.0,
        'timestamp': datetime.datetime.now().isoformat(),
        'strategy_id': 'test_session_001'
    }
    
    if db.save_performance_metric(metric_data):
        print("Performance metric saved successfully")
    
    # Retrieve and display data
    print("\nRetrieved trades:")
    trades_df = db.get_trades(strategy_id='test_session_001')
    print(trades_df)
    
    print("\nRetrieved positions:")
    positions_df = db.get_positions(strategy_id='test_session_001')
    print(positions_df)
    
    print("\nRetrieved performance metrics:")
    metrics_df = db.get_performance_metrics(strategy_id='test_session_001')
    print(metrics_df)
    
    # Get session summary
    print("\nSession summary:")
    summary = db.get_session_summary('test_session_001')
    for key, value in summary.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()