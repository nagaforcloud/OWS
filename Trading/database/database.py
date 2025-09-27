import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging
from models.models import Trade, Position
from utils.logging_utils import get_logger

logger = get_logger(__name__)

class DatabaseManager:
    """
    SQLite database manager for storing trades, positions, and performance metrics
    """
    
    def __init__(self, db_path: str = "trading_data.db"):
        """
        Initialize the database manager
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.init_db()
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def init_db(self):
        """
        Initialize the database with required tables
        """
        try:
            with self.get_connection() as conn:
                # Create trades table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        order_id TEXT UNIQUE NOT NULL,
                        symbol TEXT NOT NULL,
                        exchange TEXT NOT NULL,
                        instrument_token INTEGER NOT NULL,
                        transaction_type TEXT NOT NULL,
                        order_type TEXT NOT NULL,
                        product TEXT NOT NULL,
                        quantity INTEGER NOT NULL,
                        price REAL NOT NULL,
                        trigger_price REAL,
                        average_price REAL DEFAULT 0.0,
                        filled_quantity INTEGER DEFAULT 0,
                        pending_quantity INTEGER DEFAULT 0,
                        cancelled_quantity INTEGER DEFAULT 0,
                        order_timestamp TEXT,
                        exchange_order_id TEXT,
                        status TEXT DEFAULT 'OPEN',
                        status_message TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create positions table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS positions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT UNIQUE NOT NULL,
                        exchange TEXT NOT NULL,
                        instrument_token INTEGER NOT NULL,
                        product TEXT NOT NULL,
                        quantity INTEGER DEFAULT 0,
                        overnight_quantity INTEGER DEFAULT 0,
                        multiplier REAL DEFAULT 1.0,
                        average_price REAL DEFAULT 0.0,
                        last_price REAL DEFAULT 0.0,
                        close_price REAL DEFAULT 0.0,
                        realized_pnl REAL DEFAULT 0.0,
                        unrealized_pnl REAL DEFAULT 0.0,
                        buy_quantity INTEGER DEFAULT 0,
                        buy_price REAL DEFAULT 0.0,
                        buy_value REAL DEFAULT 0.0,
                        sell_quantity INTEGER DEFAULT 0,
                        sell_price REAL DEFAULT 0.0,
                        sell_value REAL DEFAULT 0.0,
                        day_buy_quantity INTEGER DEFAULT 0,
                        day_buy_price REAL DEFAULT 0.0,
                        day_sell_quantity INTEGER DEFAULT 0,
                        day_sell_price REAL DEFAULT 0.0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create performance metrics table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS performance_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        metric_name TEXT NOT NULL,
                        value REAL NOT NULL,
                        timestamp TEXT NOT NULL,
                        additional_data TEXT,  -- JSON field for additional metric data
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create strategy sessions table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS strategy_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT UNIQUE NOT NULL,
                        start_time TEXT NOT NULL,
                        end_time TEXT,
                        pnl REAL DEFAULT 0.0,
                        trades_count INTEGER DEFAULT 0,
                        status TEXT DEFAULT 'ACTIVE',
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create indexes for performance
                conn.execute('CREATE INDEX IF NOT EXISTS idx_trades_order_id ON trades(order_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(created_at)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_performance_timestamp ON performance_metrics(timestamp)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_sessions_start_time ON strategy_sessions(start_time)')
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except sqlite3.Error as e:
            logger.error(f"Error initializing database: {str(e)}")
            raise
    
    def save_trade(self, trade: Trade) -> bool:
        """
        Save a trade to the database
        
        Args:
            trade: Trade object to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO trades 
                    (order_id, symbol, exchange, instrument_token, transaction_type, 
                     order_type, product, quantity, price, trigger_price, 
                     average_price, filled_quantity, pending_quantity, 
                     cancelled_quantity, order_timestamp, exchange_order_id, 
                     status, status_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    trade.order_id, trade.symbol, trade.exchange, trade.instrument_token,
                    trade.transaction_type.value, trade.order_type.value, trade.product.value,
                    trade.quantity, trade.price, trade.trigger_price,
                    trade.average_price, trade.filled_quantity, trade.pending_quantity,
                    trade.cancelled_quantity, 
                    trade.order_timestamp.isoformat() if trade.order_timestamp else None,
                    trade.exchange_order_id, trade.status.value, trade.status_message
                ))
                conn.commit()
                logger.debug(f"Trade saved: {trade.order_id}")
                return True
        except sqlite3.Error as e:
            logger.error(f"Error saving trade {trade.order_id}: {str(e)}")
            return False
    
    def save_position(self, position: Position) -> bool:
        """
        Save a position to the database
        
        Args:
            position: Position object to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO positions
                    (symbol, exchange, instrument_token, product, quantity,
                     overnight_quantity, multiplier, average_price, last_price,
                     close_price, realized_pnl, unrealized_pnl, buy_quantity,
                     buy_price, buy_value, sell_quantity, sell_price, sell_value,
                     day_buy_quantity, day_buy_price, day_sell_quantity, day_sell_price,
                     updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    position.symbol, position.exchange, position.instrument_token,
                    position.product.value, position.quantity, position.overnight_quantity,
                    position.multiplier, position.average_price, position.last_price,
                    position.close_price, position.realized_pnl, position.unrealized_pnl,
                    position.buy_quantity, position.buy_price, position.buy_value,
                    position.sell_quantity, position.sell_price, position.sell_value,
                    position.day_buy_quantity, position.day_buy_price, position.day_sell_quantity,
                    position.day_sell_price
                ))
                conn.commit()
                logger.debug(f"Position saved: {position.symbol}")
                return True
        except sqlite3.Error as e:
            logger.error(f"Error saving position {position.symbol}: {str(e)}")
            return False
    
    def save_performance_metric(self, metric_name: str, value: float, 
                               timestamp: Optional[datetime] = None, 
                               additional_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Save a performance metric to the database
        
        Args:
            metric_name: Name of the metric
            value: Value of the metric
            timestamp: Timestamp for the metric (defaults to now)
            additional_data: Additional data as a dictionary (will be stored as JSON)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if timestamp is None:
                timestamp = datetime.now()
            
            with self.get_connection() as conn:
                conn.execute('''
                    INSERT INTO performance_metrics
                    (metric_name, value, timestamp, additional_data)
                    VALUES (?, ?, ?, ?)
                ''', (
                    metric_name, value, timestamp.isoformat(),
                    json.dumps(additional_data) if additional_data else None
                ))
                conn.commit()
                logger.debug(f"Performance metric saved: {metric_name} = {value}")
                return True
        except sqlite3.Error as e:
            logger.error(f"Error saving performance metric {metric_name}: {str(e)}")
            return False
    
    def save_strategy_session(self, session_id: str, start_time: datetime, 
                             notes: Optional[str] = None) -> bool:
        """
        Save a strategy session to the database
        
        Args:
            session_id: Unique identifier for the session
            start_time: Start time of the session
            notes: Optional notes about the session
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                conn.execute('''
                    INSERT INTO strategy_sessions
                    (session_id, start_time, notes)
                    VALUES (?, ?, ?)
                ''', (session_id, start_time.isoformat(), notes))
                conn.commit()
                logger.info(f"Strategy session saved: {session_id}")
                return True
        except sqlite3.Error as e:
            logger.error(f"Error saving strategy session {session_id}: {str(e)}")
            return False
    
    def update_strategy_session(self, session_id: str, end_time: datetime, 
                               pnl: float, trades_count: int, status: str = "COMPLETED") -> bool:
        """
        Update a strategy session when it ends
        
        Args:
            session_id: Unique identifier for the session
            end_time: End time of the session
            pnl: Total P&L for the session
            trades_count: Number of trades in the session
            status: Status of the session (defaults to COMPLETED)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                conn.execute('''
                    UPDATE strategy_sessions
                    SET end_time = ?, pnl = ?, trades_count = ?, status = ?
                    WHERE session_id = ?
                ''', (end_time.isoformat(), pnl, trades_count, status, session_id))
                conn.commit()
                logger.info(f"Strategy session updated: {session_id}")
                return True
        except sqlite3.Error as e:
            logger.error(f"Error updating strategy session {session_id}: {str(e)}")
            return False
    
    def get_trade(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a trade by order ID
        
        Args:
            order_id: Order ID of the trade to retrieve
            
        Returns:
            Optional[Dict]: Trade data as dictionary or None if not found
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('SELECT * FROM trades WHERE order_id = ?', (order_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Error retrieving trade {order_id}: {str(e)}")
            return None
    
    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a position by symbol
        
        Args:
            symbol: Symbol of the position to retrieve
            
        Returns:
            Optional[Dict]: Position data as dictionary or None if not found
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('SELECT * FROM positions WHERE symbol = ?', (symbol,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Error retrieving position {symbol}: {str(e)}")
            return None
    
    def get_all_positions(self) -> List[Dict[str, Any]]:
        """
        Retrieve all positions
        
        Returns:
            List[Dict]: List of all position data as dictionaries
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('SELECT * FROM positions')
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error retrieving positions: {str(e)}")
            return []
    
    def get_trades_by_symbol(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Retrieve all trades for a given symbol
        
        Args:
            symbol: Symbol to filter trades
            
        Returns:
            List[Dict]: List of trade data as dictionaries
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('SELECT * FROM trades WHERE symbol = ?', (symbol,))
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error retrieving trades for {symbol}: {str(e)}")
            return []
    
    def get_performance_metrics(self, metric_name: str, 
                               start_time: Optional[datetime] = None,
                               end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Retrieve performance metrics by name within a time range
        
        Args:
            metric_name: Name of the metric to retrieve
            start_time: Optional start time for filtering
            end_time: Optional end time for filtering
            
        Returns:
            List[Dict]: List of performance metric data as dictionaries
        """
        try:
            with self.get_connection() as conn:
                if start_time and end_time:
                    cursor = conn.execute('''
                        SELECT * FROM performance_metrics 
                        WHERE metric_name = ? AND timestamp BETWEEN ? AND ?
                        ORDER BY timestamp
                    ''', (metric_name, start_time.isoformat(), end_time.isoformat()))
                elif start_time:
                    cursor = conn.execute('''
                        SELECT * FROM performance_metrics 
                        WHERE metric_name = ? AND timestamp >= ?
                        ORDER BY timestamp
                    ''', (metric_name, start_time.isoformat()))
                elif end_time:
                    cursor = conn.execute('''
                        SELECT * FROM performance_metrics 
                        WHERE metric_name = ? AND timestamp <= ?
                        ORDER BY timestamp
                    ''', (metric_name, end_time.isoformat()))
                else:
                    cursor = conn.execute('''
                        SELECT * FROM performance_metrics 
                        WHERE metric_name = ?
                        ORDER BY timestamp
                    ''', (metric_name,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Error retrieving performance metrics {metric_name}: {str(e)}")
            return []
    
    def get_daily_pnl(self, date: str) -> float:
        """
        Calculate daily P&L for a given date
        
        Args:
            date: Date in 'YYYY-MM-DD' format
            
        Returns:
            float: Daily P&L
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT SUM(realized_pnl) as total_pnl 
                    FROM trades 
                    WHERE DATE(created_at) = ?
                ''', (date,))
                result = cursor.fetchone()
                return result['total_pnl'] or 0.0
        except sqlite3.Error as e:
            logger.error(f"Error calculating daily P&L for {date}: {str(e)}")
            return 0.0
    
    def get_all_trades(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieve all trades (with limit)
        
        Args:
            limit: Maximum number of trades to retrieve (default: 100)
            
        Returns:
            List[Dict]: List of trade data as dictionaries
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('SELECT * FROM trades ORDER BY created_at DESC LIMIT ?', (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error retrieving trades: {str(e)}")
            return []


# Example usage
if __name__ == "__main__":
    # Create database manager
    db = DatabaseManager()
    
    # Example of saving a trade
    from ..models.models import Trade
    from ..models.enums import OrderType, ProductType, TransactionType, OrderStatus
    
    sample_trade = Trade(
        order_id="TEST123456",
        symbol="TCS",
        exchange="NSE",
        instrument_token=12345,
        transaction_type=TransactionType.SELL,
        order_type=OrderType.LIMIT,
        product=ProductType.MIS,
        quantity=150,
        price=3450.50,
        order_timestamp=datetime.now()
    )
    
    # Save the trade
    db.save_trade(sample_trade)
    
    # Retrieve the trade
    retrieved_trade = db.get_trade("TEST123456")
    print("Retrieved trade:", retrieved_trade)
    
    # Example of saving performance metric
    db.save_performance_metric("daily_pnl", 1500.75, datetime.now(), {"strategy": "wheel"})
    
    # Get performance metrics
    metrics = db.get_performance_metrics("daily_pnl")
    print("Performance metrics:", metrics)