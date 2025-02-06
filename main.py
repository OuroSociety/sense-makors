import argparse
from decimal import Decimal
import sys
import json
import time
from typing import Optional, Dict, Any
from pathlib import Path
import datetime
from api_client import FameexClient
from market_maker import MarketMaker
from config import (
    API_KEY, API_SECRET, SYMBOL, 
    ORDER_BOOK_DEPTH, SPREAD_PERCENTAGE,
    MIN_ORDER_SIZE
)
from utils.logger import setup_logger

# Setup main logger and test results logger
logger = setup_logger("main")
test_logger = setup_logger("test_results", log_to_console=False)

def get_log_filename(base_name: str, symbol: str) -> str:
    """Generate log filename with timestamp and symbol"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    symbol_clean = symbol.replace('-', '_').lower()
    return f"{base_name}_{symbol_clean}_{timestamp}.log"

def setup_test_loggers(symbol: str):
    """Setup loggers with symbol-specific filenames"""
    global logger, test_logger
    
    # Main logger
    main_log_file = get_log_filename("main", symbol)
    logger = setup_logger("main", log_file=main_log_file)
    
    # Test results logger
    test_log_file = get_log_filename("test_results", symbol)
    test_logger = setup_logger("test_results", log_file=test_log_file, log_to_console=False)
    
    return logger, test_logger

def save_test_results(test_name: str, success: bool, response: Any, error: Optional[str] = None):
    """Save detailed test results to log file"""
    timestamp = datetime.datetime.now().isoformat()
    result = {
        "timestamp": timestamp,
        "test": test_name,
        "success": success,
        "response": response,
        "error": error
    }
    test_logger.info(json.dumps(result, indent=2))

def test_api_endpoint(name: str, func, *args) -> bool:
    """Generic API endpoint test function with detailed logging"""
    try:
        result = func(*args)
        if result:
            logger.info(f"✓ {name} API test successful")
            save_test_results(name, True, result)
            return True
        logger.error(f"✗ {name} API test failed - empty response")
        save_test_results(name, False, None, "Empty response")
        return False
    except Exception as e:
        logger.error(f"✗ {name} API test failed: {str(e)}")
        save_test_results(name, False, None, str(e))
        return False

def run_api_tests(client: FameexClient, symbol: str, full_test: bool = False) -> Dict[str, Dict[str, Any]]:
    """Run comprehensive API tests with detailed market data logging"""
    results = {}
    
    try:
        # First verify the trading pair exists
        logger.info(f"\nVerifying trading pair {symbol}...")
        summary_response = client._request('GET', "/v2/public/summary")
        if summary_response and isinstance(summary_response, dict) and 'data' in summary_response:
            trading_pairs = [pair['trading_pairs'] for pair in summary_response['data']]
            normalized_symbol = symbol.replace('-', '').lower()
            
            if normalized_symbol not in [p.lower() for p in trading_pairs]:
                logger.error(f"Trading pair {symbol} not found!")
                logger.info("Available pairs:")
                for pair in trading_pairs:
                    logger.info(f"  - {pair}")
                return {
                    'pair_check': {
                        'success': False,
                        'error': f"Trading pair {symbol} not available",
                        'response': trading_pairs
                    }
                }
            else:
                logger.info(f"✓ Trading pair {symbol} is available")
        else:
            logger.warning("Could not verify trading pairs - continuing anyway")
    
        # Test order book
        logger.info(f"\nTesting order book API for {symbol}...")
        order_book = client.get_order_book(symbol, ORDER_BOOK_DEPTH)
        if order_book and isinstance(order_book, dict):
            data = order_book.get('data', {})
            if not data:
                logger.error("Order book response missing 'data' field")
                logger.debug(f"Full response: {order_book}")
                results['order_book'] = {
                    'success': False,
                    'response': order_book,
                    'error': 'Missing data field'
                }
            else:
                # Extract timestamp and format it
                timestamp = order_book.get('timestamp')
                if timestamp:
                    dt = datetime.datetime.fromtimestamp(int(timestamp))
                    logger.info(f"\nOrder Book Snapshot (as of {dt.isoformat()}):")
                else:
                    logger.info("\nOrder Book Snapshot:")
                logger.info("------------------------")
                
                # Show top 5 bids
                bids = data.get('bids', [])
                logger.info("\nTop 5 Bids:")
                logger.info("Price (SZAR)\tAmount (KAS)")
                logger.info("------------------------")
                for bid in bids[:5]:
                    price, amount = bid
                    logger.info(f"{price}\t\t{amount}")
                    
                # Show top 5 asks
                asks = data.get('asks', [])
                logger.info("\nTop 5 Asks:")
                logger.info("Price (SZAR)\tAmount (KAS)")
                logger.info("------------------------")
                for ask in asks[:5]:
                    price, amount = ask
                    logger.info(f"{price}\t\t{amount}")
                    
                # Calculate and show spread
                if bids and asks:
                    best_bid = Decimal(bids[0][0])
                    best_ask = Decimal(asks[0][0])
                    spread = best_ask - best_bid
                    spread_percentage = (spread / best_bid) * 100
                    logger.info(f"\nCurrent Spread: {spread} SZAR ({spread_percentage:.2f}%)")
                    
                # Show total depth
                total_bid_volume = sum(Decimal(bid[1]) for bid in bids)
                total_ask_volume = sum(Decimal(ask[1]) for ask in asks)
                logger.info("\nOrder Book Depth:")
                logger.info(f"Total Bid Volume: {total_bid_volume:.8f} KAS")
                logger.info(f"Total Ask Volume: {total_ask_volume:.8f} KAS")
                
                results['order_book'] = {
                    'success': True,
                    'response': order_book,
                    'error': None
                }
        else:
            logger.error("Failed to fetch order book - invalid response format")
            results['order_book'] = {
                'success': False,
                'response': order_book,
                'error': 'Invalid response format'
            }

        # Test market ticker
        logger.info(f"\nTesting market ticker API for {symbol}...")
        ticker = client.get_ticker(symbol)
        if ticker and isinstance(ticker, (dict, list)):
            logger.info("\nMarket Summary:")
            logger.info("------------------------")
            if isinstance(ticker, list):
                # Find our symbol in the list
                ticker_data = next((t for t in ticker if t.get('trading_pairs') == symbol), None)
                if ticker_data:
                    logger.info(f"Last Price: {ticker_data.get('last_price')}")
                    logger.info(f"24h Volume: {ticker_data.get('base_volume')} {symbol.split('-')[0]}")
                    logger.info(f"Quote Volume: {ticker_data.get('quote_volume')} {symbol.split('-')[1]}")
                    logger.info(f"24h High: {ticker_data.get('highest_price_24h')}")
                    logger.info(f"24h Low: {ticker_data.get('lowest_price_24h')}")
                    logger.info(f"Bid/Ask Spread:")
                    logger.info(f"  Best Bid: {ticker_data.get('highest_bid')}")
                    logger.info(f"  Best Ask: {ticker_data.get('lowest_ask')}")
                    
                    # Calculate price change
                    price_change = ticker_data.get('price_change_percent_24h')
                    if price_change:
                        direction = "↑" if float(price_change) > 0 else "↓"
                        logger.info(f"24h Change: {direction} {price_change}%")
            
            results['ticker'] = {
                'success': True,
                'response': ticker,
                'error': None
            }
        else:
            logger.error("Failed to fetch ticker - invalid response format")
            results['ticker'] = {
                'success': False,
                'response': ticker,
                'error': 'Invalid response format'
            }

        # Only run authenticated tests if requested
        if full_test:
            # Test account balance
            logger.info("\nTesting account balance API...")
            try:
                balances = client.get_account_balance()
                if balances and isinstance(balances, dict):
                    logger.info("Account balances:")
                    # Look specifically for cUSD and SZAR balances
                    for asset in ['cUSD', 'SZAR']:
                        balance = balances.get(asset, 'Not available')
                        logger.info(f"{asset}: {balance}")
                    results['balance'] = {
                        'success': True,
                        'response': balances,
                        'error': None
                    }
                else:
                    logger.error("Failed to fetch account balance - invalid response format")
                    results['balance'] = {
                        'success': False,
                        'response': balances,
                        'error': 'Invalid response format'
                    }
            except Exception as e:
                logger.error(f"Balance API error: {str(e)}")
                results['balance'] = {
                    'success': False,
                    'response': None,
                    'error': str(e)
                }

    except Exception as e:
        logger.error(f"API test error: {str(e)}")
        results['error'] = {
            'success': False,
            'error': str(e),
            'response': None
        }
        
    return results

def generate_test_summary(results: Dict[str, Dict[str, Any]]) -> str:
    """Generate a detailed test summary"""
    summary = [
        "\n=== FameEX API Test Summary ===\n",
        f"Time: {datetime.datetime.now().isoformat()}",
        f"Symbol: {SYMBOL}\n"
    ]
    
    total_tests = len(results)
    successful_tests = sum(1 for r in results.values() if r['success'])
    
    summary.append(f"Overall Success Rate: {(successful_tests/total_tests)*100:.1f}%")
    summary.append(f"Tests Passed: {successful_tests}/{total_tests}\n")
    
    summary.append("Detailed Results:")
    for endpoint, result in results.items():
        status = "✓ PASS" if result['success'] else "✗ FAIL"
        summary.append(f"\n{endpoint.upper()}:")
        summary.append(f"Status: {status}")
        if not result['success'] and result['error']:
            summary.append(f"Error: {result['error']}")
            
    return "\n".join(summary)

def test_famex_connection(client: FameexClient, continuous: bool = False, symbol: str = SYMBOL, full_test: bool = False) -> bool:
    """
    Test connection to FameEX API
    Args:
        client: FameexClient instance
        continuous: If True, run tests continuously until interrupted
        symbol: Trading pair to test
        full_test: If True, run full API test suite including authenticated endpoints
    Returns:
        bool: True if all critical tests pass
    """
    try:
        if continuous:
            logger.info("Starting continuous API testing (Press Ctrl+C to stop)...")
            while True:
                results = run_api_tests(client, symbol, full_test)
                summary = generate_test_summary(results)
                logger.info(summary)
                test_logger.info(summary)
                logger.info("\nWaiting 5 seconds before next test cycle...")
                time.sleep(5)
        else:
            results = run_api_tests(client, symbol, full_test)
            summary = generate_test_summary(results)
            logger.info(summary)
            test_logger.info(summary)
            
        # Consider test successful if order book and balance APIs work
        return results.get('order_book', {}).get('success', False) and \
               results.get('balance', {}).get('success', False)
        
    except KeyboardInterrupt:
        logger.info("\nAPI testing stopped by user")
        return True
    except Exception as e:
        logger.error(f"Error during API testing: {str(e)}")
        return False

def run_market_maker(client: FameexClient, spread: Optional[Decimal] = None) -> None:
    """Run the market maker with optional custom spread"""
    try:
        market_maker = MarketMaker(client)
        if spread is not None:
            logger.info(f"Using custom spread: {spread}")
            market_maker.risk_manager.set_limits(
                SYMBOL,
                max_position=Decimal('1000'),
                max_drawdown=Decimal('100'),
                min_spread=spread,
                target_ratio=Decimal('1.0')
            )
        market_maker.run()
    except KeyboardInterrupt:
        logger.info("Shutting down market maker...")
    except Exception as e:
        logger.error(f"Fatal error in market maker: {str(e)}")
        sys.exit(1)

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

def get_market_summary(client: FameexClient, filter_kas: bool = True) -> None:
    """Get and display market summary, optionally filtering for KAS pairs"""
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

def main():
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
        default='SZAR-USDT',  # Changed back to SZAR-USDT
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
    
    # Parse arguments
    args = parser.parse_args()
    
    # Initialize API client
    if not API_KEY or not API_SECRET:
        logger.error("API credentials not found. Please check your .env file.")
        sys.exit(1)
        
    client = FameexClient(API_KEY, API_SECRET)
    
    # Handle commands
    if args.command == 'test-famex':
        # Setup loggers with symbol-specific filenames
        setup_test_loggers(args.symbol)
        
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
        
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
