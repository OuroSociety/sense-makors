import os
import sys
from loguru import logger
from pathlib import Path

# Get log level from environment or use INFO as default
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Create logs directory if it doesn't exist
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Configure logger
logger.remove()  # Remove default handler

# Add console handler
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=LOG_LEVEL,
    colorize=True,
)

# Add file handlers
logger.add(
    "logs/error.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="ERROR",
    rotation="5 MB",
    retention="1 week",
)

logger.add(
    "logs/info.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="INFO",
    rotation="5 MB",
    retention="1 week",
)

# Export logger
__all__ = ["logger"] 