import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

def setup_logging(log_level=logging.INFO, log_file=None, max_bytes=10*1024*1024, backup_count=5):
    """
    Set up enhanced logging with both file and console handlers
    
    Args:
        log_level: Logging level (default: INFO)
        log_file: Path to log file (default: 'logs/trading_bot.log')
        max_bytes: Maximum size of log file before rotation (default: 10MB)
        backup_count: Number of backup files to keep (default: 5)
    """
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Set default log file
    if log_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"logs/trading_bot_{timestamp}.log"
    
    # Create logger
    logger = logging.getLogger('trading_bot')
    logger.setLevel(log_level)
    
    # Clear any existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create formatter with comprehensive details
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # Create file handler with rotation
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=max_bytes, 
        backupCount=backup_count
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    # Also configure root logger to ensure all logs are captured
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Add handlers to root logger as well if needed
    if not root_logger.handlers:
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
    
    return logger

def get_logger(name: str = 'trading_bot'):
    """
    Get a logger instance with the specified name
    
    Args:
        name: Name of the logger (default: 'trading_bot')
        
    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)

def log_exception(logger, msg: str = "An exception occurred"):
    """
    Log an exception with traceback
    
    Args:
        logger: Logger instance
        msg: Message to log with the exception
    """
    logger.exception(msg)

# Global logger instance
logger = setup_logging()

if __name__ == "__main__":
    # Example usage
    logger.info("Logging setup complete")
    logger.debug("This is a debug message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    try:
        1 / 0
    except ZeroDivisionError:
        log_exception(logger, "Division by zero error occurred")