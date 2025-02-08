import logging
import json
import time
import datetime
from decimal import Decimal
from typing import Dict, Any, Optional
from config.api_client import FameexClient
from utils.logger import setup_logger
from tests.utils.test_helpers import (
    setup_test_loggers,
    save_test_results,
    test_api_endpoint,
    generate_test_summary
)

def get_log_filename(base_name: str, symbol: str) -> str:
    """Generate log filename with timestamp and symbol"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    symbol_clean = symbol.replace('-', '_').lower()
    return f"{base_name}_{symbol_clean}_{timestamp}.log"

def setup_test_loggers(symbol: str):
    """Setup loggers with symbol-specific filenames"""
    # Main logger
    main_log_file = get_log_filename("main", symbol)
    logger = setup_logger("main", log_file=main_log_file)
    
    # Test results logger
    test_log_file = get_log_filename("test_results", symbol)
    test_logger = setup_logger("test_results", log_file=test_log_file, log_to_console=False)
    
    return logger, test_logger

def save_test_results(test_logger: logging.Logger, test_name: str, success: bool, response: Any, error: Optional[str] = None):
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

def test_api_endpoint(logger: logging.Logger, test_logger: logging.Logger, name: str, func, *args) -> bool:
    """Generic API endpoint test function with detailed logging"""
    try:
        result = func(*args)
        if result:
            logger.info(f"✓ {name} API test successful")
            save_test_results(test_logger, name, True, result)
            return True
        logger.error(f"✗ {name} API test failed - empty response")
        save_test_results(test_logger, name, False, None, "Empty response")
        return False
    except Exception as e:
        logger.error(f"✗ {name} API test failed: {str(e)}")
        save_test_results(test_logger, name, False, None, str(e))
        return False

def test_market_making(logger: logging.Logger, test_logger: logging.Logger, client: FameexClient, symbol: str) -> Dict[str, Dict[str, Any]]:
    """Test market making functionality"""
    results = {}
    logger.info(f"\n=== Testing Market Making for {symbol} ===")
    
    try:
        # 1. Test order validation (without execution)
        logger.info("\nTesting order validation...")
        test_bid = {
            "side": 1,  # 1 for BUY
            "type": 1,  # 1 for LIMIT
            "volume": "100",
            "price": "1.0"
        }
        
        test_ask = {
            "side": 2,  # 2 for SELL
            "type": 1,  # 1 for LIMIT
            "volume": "100",
            "price": "1.1"
        }
        
        # Test bid order
        bid_test = client.test_order(
            symbol=symbol,
            side=test_bid["side"],  # Pass integer directly
            order_type=test_bid["type"],  # Pass integer directly
            volume=test_bid["volume"],
            price=test_bid["price"]
        )
        
        # Add debug logging
        logger.debug(f"Bid test response: {bid_test}")
        
        if bid_test is not None:
            logger.info("✓ Bid order validation successful")
            results['bid_test'] = {
                'success': True,
                'response': bid_test
            }
        else:
            logger.error("✗ Bid order validation failed")
            results['bid_test'] = {
                'success': False,
                'error': 'Order validation failed'
            }
            
        # Test ask order
        ask_test = client.test_order(
            symbol=symbol,
            side=test_ask["side"],  # Pass integer directly
            order_type=test_ask["type"],  # Pass integer directly
            volume=test_ask["volume"],
            price=test_ask["price"]
        )
        
        # Add debug logging
        logger.debug(f"Ask test response: {ask_test}")
        
        if ask_test is not None:
            logger.info("✓ Ask order validation successful")
            results['ask_test'] = {
                'success': True,
                'response': ask_test
            }
        else:
            logger.error("✗ Ask order validation failed")
            results['ask_test'] = {
                'success': False,
                'error': 'Order validation failed'
            }
            
        # 2. Check current open orders
        logger.info("\nChecking open orders...")
        open_orders = client.get_open_orders(symbol)
        if isinstance(open_orders, list):
            logger.info(f"Found {len(open_orders)} open orders")
            for order in open_orders[:5]:  # Show first 5 orders
                logger.info(f"Order: {order.get('orderId')} - {order.get('side')} "
                          f"{order.get('origQty')} @ {order.get('price')}")
            results['open_orders'] = {
                'success': True,
                'response': open_orders
            }
        else:
            logger.error("✗ Failed to fetch open orders")
            results['open_orders'] = {
                'success': False,
                'error': 'Failed to fetch open orders'
            }
            
        # 3. Check trading history
        logger.info("\nChecking trading history...")
        trades = client.get_my_trades(symbol)
        if isinstance(trades, list):
            logger.info(f"Found {len(trades)} trades")
            for trade in trades[:5]:  # Show last 5 trades
                logger.info(f"Trade: {trade.get('id')} - {trade.get('side')} "
                          f"{trade.get('qty')} @ {trade.get('price')}")
            results['trades'] = {
                'success': True,
                'response': trades
            }
        else:
            logger.error("✗ Failed to fetch trading history")
            results['trades'] = {
                'success': False,
                'error': 'Failed to fetch trading history'
            }
            
    except Exception as e:
        logger.error(f"Error during market making test: {str(e)}")
        results['error'] = {
            'success': False,
            'error': str(e)
        }
        
    # Generate summary
    success_count = sum(1 for r in results.values() if r.get('success', False))
    total_count = len(results)
    
    logger.info("\n=== Market Making Test Summary ===")
    logger.info(f"Success Rate: {(success_count/total_count)*100:.1f}%")
    logger.info(f"Tests Passed: {success_count}/{total_count}")
    
    return results

def test_famex_connection(client: FameexClient, continuous: bool = False, symbol: str = "SZAR-USDT", full_test: bool = False) -> bool:
    """Test FameEX API connectivity and endpoints"""
    logger, test_logger = setup_test_loggers(symbol)
    
    while True:
        try:
            # Test market data endpoints
            success = test_api_endpoint(logger, test_logger, "Order Book", client.get_order_book, symbol)
            success &= test_api_endpoint(logger, test_logger, "Recent Trades", client.get_trades, symbol)
            success &= test_api_endpoint(logger, test_logger, "Ticker", client.get_ticker, symbol)
            success &= test_api_endpoint(logger, test_logger, "Klines", client.get_klines, symbol)
            
            if full_test:
                # Test authenticated endpoints
                success &= test_api_endpoint(logger, test_logger, "Account Info", client.get_account_info)
                success &= test_api_endpoint(logger, test_logger, "Open Orders", client.get_open_orders, symbol)
                
                # Test market making functionality
                market_making_results = test_market_making(logger, test_logger, client, symbol)
                success &= any(r.get('success', False) for r in market_making_results.values())
            
            if not continuous:
                return success
                
            time.sleep(1)  # Wait before next test cycle
            
        except KeyboardInterrupt:
            logger.info("\nTest interrupted by user")
            return success
        except Exception as e:
            logger.error(f"Test failed with error: {str(e)}")
            return False 