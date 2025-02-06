import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

def setup_logger(name: str, log_file: Optional[str] = None, log_to_console: bool = True, debug: bool = False) -> logging.Logger:
    """Configure and return a logger instance
    
    Args:
        name: Logger name
        log_file: Specific log filename (default: None, uses name.log)
        log_to_console: Whether to output logs to console (default: True)
        debug: Enable debug logging (default: False)
    """
    # Create logs directory if it doesn't exist
    Path("logs").mkdir(exist_ok=True)
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # Remove any existing handlers
    logger.handlers = []
    
    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG if debug else logging.INFO)
        console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # File handler
    file_handler = RotatingFileHandler(
        f"logs/{log_file or f'{name}.log'}",
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger 