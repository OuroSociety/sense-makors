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
from utils.trading_utils import create_exchange_client

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

def test_trading_system(client: ExchangeClient, symbol: str, duration: int = 300):
    """Test the complete trading system including position tracking and risk management"""
    logger = setup_logger("system_test", debug=True)  # Enable debug logging
    logger.info(f"\n=== Starting Trading System Test for {symbol} ===")
    logger.info(f"Test duration: {duration} seconds")
    
    # Initialize start_time at the beginning
    start_time = time.time()
    results = {
        "orders_tested": 0,
        "orders_accepted": 0,
        "orders_rejected": 0,
        "position_updates": 0,
        "risk_checks": 0
    }
    
    try:
        # Initialize components
        logger.info("Initializing trading components...")
        position_tracker = PositionTracker()
        wallet_manager = WalletManager()
        
        # Extract base and quote assets from symbol
        if '-' in symbol:
            base_asset, quote_asset = symbol.split('-')
        else:
            quote_asset = symbol[-4:]  # Assuming USDT
            base_asset = symbol[:-4]   # Rest is base asset
            
        logger.info(f"Trading {base_asset}/{quote_asset}")
        
        # Initialize wallet with some test balances
        wallet_manager.update_balance(quote_asset, Decimal('10000'))
        wallet_manager.update_balance(base_asset, Decimal('10000'))
        
        risk_manager = RiskManager(position_tracker, wallet_manager)
        
        # Set risk limits
        max_position = Decimal("1000")  # Maximum position size
        max_order_size = Decimal("100")  # Maximum single order size
        min_spread = Decimal("0.001")    # Minimum spread (0.1%)
        
        risk_manager.set_limits(
            symbol=symbol,
            max_position=max_position,
            max_order_size=max_order_size,
            min_spread=min_spread
        )
        
        logger.info(f"Risk limits set:")
        logger.info(f"- Max position: {max_position}")
        logger.info(f"- Max order size: {max_order_size}")
        logger.info(f"- Min spread: {min_spread * 100}%")
        
        test_orders = [
            {"side": 1, "volume": "50", "price": "1.0", "desc": "Small buy"},
            {"side": 2, "volume": "30", "price": "1.1", "desc": "Small sell"},
            {"side": 1, "volume": "150", "price": "1.0", "desc": "Exceeds order size"},
            {"side": 1, "volume": "90", "price": "1.0", "desc": "Near limit buy"},
        ]
        
        cycle = 0
        while time.time() - start_time < duration:
            cycle += 1
            logger.info(f"\n=== Testing Order Cycle {cycle} ===")
            
            # Test order placement with risk checks
            for order in test_orders:
                results["orders_tested"] += 1
                order_size = Decimal(order["volume"])
                order_price = Decimal(order["price"])
                is_buy = order["side"] == 1
                
                logger.info(f"\nTesting {order['desc']}: {order_size} @ {order_price}")
                
                # Risk check
                results["risk_checks"] += 1
                if risk_manager.check_order(symbol, order_size, order_price, is_buy):
                    logger.info(f"✓ Risk check passed")
                    results["orders_accepted"] += 1
                    
                    # Update position
                    position_tracker.update_position(
                        symbol, 
                        order_size, 
                        order_price, 
                        is_buy
                    )
                    results["position_updates"] += 1
                    
                    # Update wallet balances
                    if is_buy:
                        wallet_manager.update_balance(quote_asset, 
                            wallet_manager.get_available_balance(quote_asset) - (order_size * order_price))
                        wallet_manager.update_balance(base_asset,
                            wallet_manager.get_available_balance(base_asset) + order_size)
                    else:
                        wallet_manager.update_balance(quote_asset,
                            wallet_manager.get_available_balance(quote_asset) + (order_size * order_price))
                        wallet_manager.update_balance(base_asset,
                            wallet_manager.get_available_balance(base_asset) - order_size)
                    
                    current_position = position_tracker.get_position(symbol)
                    logger.info(f"Position updated: {current_position}")
                else:
                    logger.warning(f"✗ Risk check failed - would exceed limits")
                    results["orders_rejected"] += 1
            
            # Position and wallet status
            current_position = position_tracker.get_position(symbol)
            logger.info(f"\nPosition Status:")
            logger.info(f"Current position: {current_position}")
            logger.info(f"Position limit: {max_position}")
            logger.info(f"Position utilization: {(abs(current_position) / max_position) * 100:.1f}%")
            
            logger.info(f"\nWallet Status:")
            logger.info(f"{quote_asset} Balance: {wallet_manager.get_available_balance(quote_asset)}")
            logger.info(f"{base_asset} Balance: {wallet_manager.get_available_balance(base_asset)}")
            
            # Mock order execution check
            if hasattr(client, 'test_mode') and client.test_mode:
                open_orders = client.get_open_orders(symbol)
                trades = client.get_my_trades(symbol)
                logger.info(f"\nMock Exchange Status:")
                logger.info(f"Open orders: {len(open_orders) if open_orders else 0}")
                logger.info(f"Recent trades: {len(trades) if trades else 0}")
            
            time.sleep(10)  # Wait between cycles
            
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
    except Exception as e:
        logger.error(f"Test error: {str(e)}")
        raise  # Re-raise to see full traceback
    finally:
        # Print test summary
        logger.info("\n=== Trading System Test Summary ===")
        logger.info(f"Test duration: {int(time.time() - start_time)} seconds")
        logger.info(f"Orders tested: {results['orders_tested']}")
        logger.info(f"Orders accepted: {results['orders_accepted']}")
        logger.info(f"Orders rejected: {results['orders_rejected']}")
        logger.info(f"Position updates: {results['position_updates']}")
        logger.info(f"Risk checks performed: {results['risk_checks']}")
        logger.info(f"Final position: {position_tracker.get_position(symbol)}")
        logger.info(f"Final {quote_asset} balance: {wallet_manager.get_available_balance(quote_asset)}")
        logger.info(f"Final {base_asset} balance: {wallet_manager.get_available_balance(base_asset)}")
        
    return results

def main():
    parser = argparse.ArgumentParser(description='Market Making Bot')
    parser.add_argument('command', choices=['run', 'test-famex', 'test-mm', 'test-system', 'api'], 
                       help='Command to execute')
    parser.add_argument('--symbol', default='SZARUSDT', help='Trading pair symbol')
    parser.add_argument('--spread', type=float, help='Custom spread percentage')
    parser.add_argument('--duration', type=int, default=300, 
                       help='Test duration in seconds (default: 300)')
    parser.add_argument('--continuous', action='store_true', 
                       help='Run tests continuously')
    parser.add_argument('--full', action='store_true', 
                       help='Run full test suite')
    args = parser.parse_args()
    
    # Initialize default loggers
    logger, test_logger = init_loggers()
    
    # Initialize API client
    if not API_KEY or not API_SECRET:
        logger.error("API credentials not found. Please check your .env file.")
        sys.exit(1)
        
    try:
        # Enable test mode for test-mm command
        test_mode = args.command == 'test-mm'
        client = create_exchange_client('fameex', API_KEY, API_SECRET, test_mode=test_mode)
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
        get_market_summary(client, filter_kas=not args.full)
        
    elif args.command == 'test-mm':
        # Reinitialize loggers with symbol and enable debug
        logger, test_logger = init_loggers(args.symbol)
        logger.setLevel(logging.DEBUG)  # Enable debug logging
        logging.getLogger('urllib3').setLevel(logging.DEBUG)  # Enable HTTP request logging
        logger.info(f"Testing market making functionality for {args.symbol}...")
        results = test_market_making(logger, test_logger, client, args.symbol)
        success = any(r.get('success', False) for r in results.values())
        sys.exit(0 if success else 1)
        
    elif args.command == 'test-system':
        logger.info(f"Starting trading system test for {args.symbol}...")
        results = test_trading_system(client, args.symbol, args.duration)
        success = results['orders_accepted'] > 0 and results['position_updates'] > 0
        sys.exit(0 if success else 1)
        
    elif args.command == 'api':
        logger.info("Starting API server...")
        from api.server import start_api
        start_api()
        return
        
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
