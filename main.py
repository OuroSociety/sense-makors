import argparse
from decimal import Decimal
import sys
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
from config.test_cli import run_api_tests  # Import run_api_tests from test_cli
import logging
from config.base_client import ExchangeClient

# Setup main logger and test results logger
logger = setup_logger("main")
test_logger = setup_logger("test_results", log_to_console=False)

def run_market_maker(client: FameexClient, spread: Decimal = None):
    """Run the market maker"""
    market_maker = MarketMaker(client)
    if spread is not None:
        market_maker.spread = spread
    market_maker.run()

def print_kas_pairs(summary_data: dict) -> None:
    """Print all trading pairs related to KAS"""
    if not summary_data or 'data' not in summary_data:
        logger.error("Invalid summary data")
        return
        
    kas_pairs = [pair for pair in summary_data['data'] 
                 if 'KAS' in pair['trading_pairs'].upper()]
    
    if not kas_pairs:
        logger.info("No KAS trading pairs found")
        return
        
    logger.info("\nKAS Trading Pairs:")
    logger.info("=" * 80)
    logger.info(f"{'Trading Pair':<15} {'Last Price':<12} {'24h High':<12} {'24h Low':<12} {'24h Volume':<15} {'Change %':<10}")
    logger.info("-" * 80)
    
    for pair in kas_pairs:
        logger.info(
            f"{pair['trading_pairs']:<15} "
            f"{pair['last_price']:<12} "
            f"{pair['highest_price_24h']:<12} "
            f"{pair['lowest_price_24h']:<12} "
            f"{pair['base_volume']:<15} "
            f"{pair['price_change_percent_24h']:<10}"
        )

def get_market_summary(client: FameexClient, filter_kas: bool = True):
    """Get market summary"""
    try:
        summary = client._request('GET', "/v2/public/summary")
        if summary and isinstance(summary, dict) and 'data' in summary:
            if filter_kas:
                print_kas_pairs(summary)
            else:
                # Print all pairs
                logger.info("\nAll Trading Pairs:")
                logger.info("=" * 80)
                for pair in summary['data']:
                    logger.info(f"Pair: {pair['trading_pairs']}")
        else:
            logger.error("Failed to get market summary")
    except Exception as e:
        logger.error(f"Error fetching market summary: {str(e)}")

def init_loggers(symbol: str = None):
    """Initialize loggers"""
    if symbol:
        return setup_test_loggers(symbol)
    else:
        logger = setup_logger("main")
        test_logger = setup_logger("test_results", log_to_console=False)
        return logger, test_logger

def create_exchange_client(exchange_type: str, api_key: str, api_secret: str) -> ExchangeClient:
    """Factory function to create exchange clients"""
    if exchange_type.lower() == 'fameex':
        from config.api_client import FameexClient
        return FameexClient(api_key, api_secret)
    # Add more exchange types here as needed
    else:
        raise ValueError(f"Unsupported exchange type: {exchange_type}")

def main():
    # Initialize default loggers
    logger, test_logger = init_loggers()
    
    parser = argparse.ArgumentParser(description='ourOS Market Maker CLI')
    
    # Add subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Test FameEX data command
    test_parser = subparsers.add_parser('test-famex', help='Test FameEX market data and API endpoints')
    test_parser.add_argument(
        '--continuous',
        action='store_true',
        help='Run API tests continuously until stopped'
    )
    test_parser.add_argument(
        '--symbol',
        type=str,
        default='SZAR-USDT',
        help='Trading pair to test (default: SZAR-USDT)'
    )
    test_parser.add_argument(
        '--full',
        action='store_true',
        help='Run full API test suite including authenticated endpoints'
    )
    test_parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run the market maker')
    run_parser.add_argument(
        '--spread',
        type=float,
        help='Custom spread percentage (e.g., 0.02 for 2%%)',
        default=None
    )
    
    # Summary command
    summary_parser = subparsers.add_parser('summary', help='Get market summary')
    summary_parser.add_argument(
        '--all',
        action='store_true',
        help='Show all pairs (default: show only KAS pairs)'
    )
    
    # Add market making test command
    mm_test_parser = subparsers.add_parser('test-mm', help='Test market making functionality')
    mm_test_parser.add_argument(
        '--symbol',
        type=str,
        default=SYMBOL,
        help=f'Trading pair to test (default: {SYMBOL})'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Initialize API client
    if not API_KEY or not API_SECRET:
        logger.error("API credentials not found. Please check your .env file.")
        sys.exit(1)
        
    try:
        client = create_exchange_client('fameex', API_KEY, API_SECRET)
    except ValueError as e:
        logger.error(f"Error creating exchange client: {e}")
        sys.exit(1)
    
    # Handle commands
    if args.command == 'test-famex':
        # Reinitialize loggers with symbol
        logger, test_logger = init_loggers(args.symbol)
        logger.info(f"Testing FameEX market data for {args.symbol}...")
        success = test_famex_connection(
            client, 
            continuous=args.continuous,
            symbol=args.symbol,
            full_test=args.full
        )
        sys.exit(0 if success else 1)
        
    elif args.command == 'run':
        logger.info("Starting market maker...")
        spread = Decimal(str(args.spread)) if args.spread is not None else None
        run_market_maker(client, spread)
        
    elif args.command == 'summary':
        get_market_summary(client, filter_kas=not args.all)
        
    elif args.command == 'test-mm':
        # Reinitialize loggers with symbol and enable debug
        logger, test_logger = init_loggers(args.symbol)
        logger.setLevel(logging.DEBUG)  # Enable debug logging
        logger.info(f"Testing market making functionality for {args.symbol}...")
        results = test_market_making(logger, test_logger, client, args.symbol)
        success = any(r.get('success', False) for r in results.values())
        sys.exit(0 if success else 1)
        
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
