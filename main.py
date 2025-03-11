import argparse
from decimal import Decimal
import sys
import time
import logging
from pathlib import Path

# Add the project root to Python path
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Local imports
from config.api_client import FameexClient
from market_maker import MarketMaker
from config.config import (
    API_KEY, API_SECRET, SYMBOL, 
    ORDER_BOOK_DEPTH, SPREAD_PERCENTAGE,
    MIN_ORDER_SIZE
)
from utils.logger import setup_logger
from tests.test_famex import test_famex_connection, test_market_making
from tests.utils.test_helpers import (
    setup_test_loggers,
    save_test_results,
    test_api_endpoint,
    generate_test_summary
)
from config.test_cli import run_api_tests
from config.base_client import ExchangeClient
from trading import PositionTracker, RiskManager, WalletManager  # Updated import

# Setup main logger and test results logger
logger = setup_logger("main")
test_logger = setup_logger("test_results", log_to_console=False)

def run_market_maker(client: FameexClient, spread: Decimal = None):
    """
    Run the market maker with the specified client and spread.
    
    Args:
        client: The exchange client to use
        spread: Optional spread to use (overrides config)
    """
    logger.info(f"Starting market maker for {SYMBOL}")
    
    # Create and run the market maker
    market_maker = MarketMaker(
        client=client,
        symbol=SYMBOL,
        order_book_depth=ORDER_BOOK_DEPTH,
        spread_percentage=spread or SPREAD_PERCENTAGE,
        min_order_size=MIN_ORDER_SIZE
    )
    
    try:
    market_maker.run()
    except KeyboardInterrupt:
        logger.info("Market maker stopped by user")
    except Exception as e:
        logger.error(f"Error in market maker: {e}")
        raise

def print_kas_pairs(summary_data: dict) -> None:
    """
    Print KAS trading pairs from the market summary.
    
    Args:
        summary_data: Market summary data
    """
    kas_pairs = []
    
    # Extract KAS pairs
    for symbol, data in summary_data.items():
        if "KAS" in symbol:
            kas_pairs.append({
                "symbol": symbol,
                "last_price": data["last_price"],
                "volume_24h": data["volume_24h"],
                "price_change_24h": data["price_change_24h"]
            })
    
    # Sort by volume
    kas_pairs.sort(key=lambda x: float(x["volume_24h"]), reverse=True)
    
    # Print the pairs
    print("\nKAS Trading Pairs:")
    print(f"{'Symbol':<10} {'Last Price':<15} {'24h Volume':<15} {'24h Change':<10}")
    print("-" * 50)
    
    for pair in kas_pairs:
        print(f"{pair['symbol']:<10} {pair['last_price']:<15} {pair['volume_24h']:<15} {pair['price_change_24h']:<10}")

def get_market_summary(client: FameexClient, filter_kas: bool = True):
    """
    Get and print the market summary.
    
    Args:
        client: The exchange client to use
        filter_kas: Whether to filter for KAS pairs
    """
    logger.info("Getting market summary")
    
    # Get the market summary
    summary = client.get_market_summary()
    
            if filter_kas:
                print_kas_pairs(summary)
            else:
        print(summary)

def init_loggers(symbol: str = None):
    """
    Initialize loggers for the application.
    
    Args:
        symbol: Optional symbol to include in log filenames
    """
    # Setup loggers for different components
    setup_logger("market_maker")
    setup_logger("api_client")
    setup_logger("order_book")
    setup_logger("trading")

def create_exchange_client(exchange_type: str, api_key: str, api_secret: str, test_mode: bool = False) -> ExchangeClient:
    """Create an exchange client based on the specified type."""
    if exchange_type.lower() == "fameex":
        return FameexClient(api_key, api_secret, test_mode)
    else:
        raise ValueError(f"Unsupported exchange type: {exchange_type}")

def test_trading_system(client: ExchangeClient, symbol: str, duration: int = 300):
    """
    Run a test of the trading system.
    
    Args:
        client: The exchange client to use
        symbol: The trading symbol to test
        duration: Test duration in seconds
    """
    logger.info(f"Testing trading system for {symbol} (duration: {duration}s)")
    
    # Run the test
    test_market_making(client, symbol, duration)
    
    logger.info("Trading system test completed")

def run_solid_server():
    """
    Run the Solid Pod server.
    """
    try:
        # Initialize logging for the Solid server
        from solid.src.utils.logger import logger as solid_logger
        solid_logger.info("Starting Solid Pod server")
        
        # Import the server module
        try:
            from solid.src.main import start as start_solid_server
            
            # Start the server
            solid_logger.info("Initializing Solid Pod server")
            start_solid_server()
        except ImportError as e:
            logger.error(f"Failed to import Solid server module: {e}")
            print(f"Error: Failed to import Solid server module: {e}")
            print("Make sure the Solid server is properly installed.")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error starting Solid server: {e}")
            print(f"Error starting Solid server: {e}")
            sys.exit(1)
    except ImportError:
        logger.error("Failed to import Solid logger")
        print("Error: Failed to import Solid logger")
        print("Make sure the Solid server is properly installed.")
        sys.exit(1)

def run_solid_client(args=None):
    """
    Run the Solid client CLI.
    
    Args:
        args: Command line arguments
    """
    try:
        # Import the client CLI
        try:
            from solid.src.cli import main as solid_cli_main
            
            # Run the CLI
            solid_cli_main()
        except ImportError as e:
            logger.error(f"Failed to import Solid client module: {e}")
            print(f"Error: Failed to import Solid client module: {e}")
            print("Make sure the Solid client is properly installed.")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error running Solid client: {e}")
            print(f"Error running Solid client: {e}")
            sys.exit(1)
    except ImportError:
        logger.error("Failed to import Solid client")
        print("Error: Failed to import Solid client")
        print("Make sure the Solid client is properly installed.")
        sys.exit(1)

def main():
    """Main entry point for the application."""
    # Create the argument parser
    parser = argparse.ArgumentParser(description="Market Maker and Solid Pod Server")
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Market maker command
    mm_parser = subparsers.add_parser("market-maker", help="Run the market maker")
    mm_parser.add_argument("--spread", type=float, help="Spread percentage")
    mm_parser.add_argument("--test", action="store_true", help="Run in test mode")
    mm_parser.add_argument("--exchange", default="fameex", help="Exchange to use")
    mm_parser.add_argument("--api-key", help="API key")
    mm_parser.add_argument("--api-secret", help="API secret")
    
    # Market summary command
    summary_parser = subparsers.add_parser("summary", help="Get market summary")
    summary_parser.add_argument("--all", action="store_true", help="Show all pairs")
    summary_parser.add_argument("--test", action="store_true", help="Run in test mode")
    summary_parser.add_argument("--exchange", default="fameex", help="Exchange to use")
    summary_parser.add_argument("--api-key", help="API key")
    summary_parser.add_argument("--api-secret", help="API secret")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Test the trading system")
    test_parser.add_argument("--duration", type=int, default=300, help="Test duration in seconds")
    test_parser.add_argument("--symbol", default=SYMBOL, help="Symbol to test")
    test_parser.add_argument("--exchange", default="fameex", help="Exchange to use")
    test_parser.add_argument("--api-key", help="API key")
    test_parser.add_argument("--api-secret", help="API secret")
    
    # Solid server command
    solid_parser = subparsers.add_parser("solid", help="Run the Solid Pod server")
    solid_parser.add_argument("--test", action="store_true", help="Run in test mode")
    
    # Solid client command
    solid_client_parser = subparsers.add_parser("solid-client", help="Run the Solid client CLI")
    
    # Parse the arguments
    args = parser.parse_args()
    
    # Initialize loggers
    init_loggers()
    
    # Handle the command
    if args.command == "market-maker":
        # Get API credentials
        api_key = args.api_key or API_KEY
        api_secret = args.api_secret or API_SECRET
        
        # Create the client
        client = create_exchange_client(args.exchange, api_key, api_secret, args.test)
        
        # Run the market maker
        spread = Decimal(str(args.spread)) if args.spread else None
        run_market_maker(client, spread)
    elif args.command == "summary":
        # Get API credentials
        api_key = args.api_key or API_KEY
        api_secret = args.api_secret or API_SECRET
        
        # Create the client
        client = create_exchange_client(args.exchange, api_key, api_secret, args.test)
        
        # Get the market summary
        get_market_summary(client, not args.all)
    elif args.command == "test":
        # Get API credentials
        api_key = args.api_key or API_KEY
        api_secret = args.api_secret or API_SECRET
        
        # Create the client
        client = create_exchange_client(args.exchange, api_key, api_secret, True)
        
        # Run the test
        test_trading_system(client, args.symbol, args.duration)
    elif args.command == "solid":
        # Run the Solid server
        run_solid_server()
    elif args.command == "solid-client":
        # Run the Solid client CLI
        run_solid_client()
    else:
        # Print help if no command is specified
        parser.print_help()

if __name__ == "__main__":
    main()
