"""
Logging utilities for the Option Wheel Strategy.
"""
import logging
from logging.handlers import RotatingFileHandler


def setup_logging(log_level=logging.INFO, log_file: str = "option_wheel.log") -> logging.Logger:
    """Set up enhanced logging with both file and console handlers."""
    logger = logging.getLogger("OptionWheel")
    logger.setLevel(log_level)
    
    # Prevent adding multiple handlers if function is called multiple times
    if logger.handlers:
        return logger
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger