import datetime
from decimal import Decimal
from typing import Dict, Any, Optional
from config.api_client import FameexClient
from config.config import ORDER_BOOK_DEPTH
from utils.logger import setup_logger
from config.base_client import ExchangeClient

logger = setup_logger("test_cli")

def run_api_tests(client: FameexClient, symbol: str, full_test: bool = False) -> Dict[str, Dict[str, Any]]:
    """Run comprehensive API tests with detailed market data logging
    
    Args:
        client: FameexClient instance
        symbol: Trading pair symbol to test
        full_test: Whether to run authenticated endpoints
        
    Returns:
        Dict containing test results for each endpoint
    """
    results = {}
    
    try:
        # First verify the trading pair exists by checking order book
        logger.info(f"\nVerifying trading pair {symbol}...")
        order_book = client.get_order_book(symbol)
        
        if order_book and isinstance(order_book, dict):
            data = order_book.get('data', {})
            bids = data.get('bids', [])
            asks = data.get('asks', [])
            
            if bids or asks:
                logger.info(f"✓ Trading pair {symbol} is available")
                if bids:
                    logger.info(f"First bid: {bids[0]}")
                if asks:
                    logger.info(f"First ask: {asks[0]}")
            else:
                logger.error(f"Trading pair {symbol} not found!")
                return {
                    'pair_check': {
                        'success': False,
                        'error': f"Trading pair {symbol} not available",
                        'response': order_book
                    }
                }
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
                _log_order_book_details(data, order_book.get('timestamp'))
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
        results.update(_test_market_ticker(client, symbol))

        # Only run authenticated tests if requested
        if full_test:
            results.update(_test_authenticated_endpoints(client))

    except Exception as e:
        logger.error(f"API test error: {str(e)}")
        results['error'] = {
            'success': False,
            'error': str(e),
            'response': None
        }
        
    return results

def _log_order_book_details(data: Dict[str, Any], timestamp: Optional[str] = None) -> None:
    """Log detailed order book information"""
    if timestamp:
        dt = datetime.datetime.fromtimestamp(int(timestamp))
        logger.info(f"\nOrder Book Snapshot (as of {dt.isoformat()}):")
    else:
        logger.info("\nOrder Book Snapshot:")
    logger.info("------------------------")
    
    # Show top 5 bids/asks and calculate metrics
    bids = data.get('bids', [])
    asks = data.get('asks', [])
    
    _log_order_levels("Bids", bids[:5])
    _log_order_levels("Asks", asks[:5])
    
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

def _log_order_levels(side: str, levels: list) -> None:
    """Log order book levels"""
    logger.info(f"\nTop 5 {side}:")
    logger.info("Price (SZAR)\tAmount (KAS)")
    logger.info("------------------------")
    for level in levels:
        price, amount = level
        logger.info(f"{price}\t\t{amount}")

def _test_market_ticker(client: FameexClient, symbol: str) -> Dict[str, Dict[str, Any]]:
    """Test market ticker endpoint"""
    logger.info(f"\nTesting market ticker API for {symbol}...")
    ticker = client.get_ticker(symbol)
    
    if not ticker or not isinstance(ticker, (dict, list)):
        return {
            'ticker': {
                'success': False,
                'response': ticker,
                'error': 'Invalid response format'
            }
        }
    
    _log_ticker_details(ticker, symbol)
    return {
        'ticker': {
            'success': True,
            'response': ticker,
            'error': None
        }
    }

def _test_authenticated_endpoints(client: FameexClient) -> Dict[str, Dict[str, Any]]:
    """Test authenticated API endpoints"""
    results = {}
    
    # Test account balance
    logger.info("\nTesting account balance API...")
    try:
        balances = client.get_account_balance()
        if balances and isinstance(balances, dict):
            logger.info("Account balances:")
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
    
    return results

def _log_ticker_details(ticker: Dict[str, Any], symbol: str) -> None:
    """Log detailed ticker information"""
    logger.info("\nMarket Summary:")
    logger.info("------------------------")
    
    if isinstance(ticker, list):
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
            
            price_change = ticker_data.get('price_change_percent_24h')
            if price_change:
                direction = "↑" if float(price_change) > 0 else "↓"
                logger.info(f"24h Change: {direction} {price_change}%")

def test_market_making(logger, test_logger, client: ExchangeClient, symbol: str) -> Dict[str, Any]:
    """Test market making functionality"""
    results = {}
    
    logger.info(f"\n=== Testing Market Making for {symbol} ===")
    
    # Test order validation
    logger.info("\nTesting order validation...")
    try:
        # Test bid order
        bid_order = {
            'symbol': symbol,
            'side': 1,  # Buy
            'order_type': 1,  # Limit
            'volume': '1.0',
            'price': '100.0'
        }
        bid_result = client.test_order(**bid_order)
        if bid_result and bid_result.get('code') == 200:
            logger.info("✓ Bid order validation passed")
            results['bid_validation'] = {'success': True}
        else:
            logger.error("✗ Bid order validation failed")
            results['bid_validation'] = {'success': False}
            
        # Test ask order
        ask_order = {
            'symbol': symbol,
            'side': 2,  # Sell
            'order_type': 1,  # Limit
            'volume': '1.0',
            'price': '100.0'
        }
        ask_result = client.test_order(**ask_order)
        if ask_result and ask_result.get('code') == 200:
            logger.info("✓ Ask order validation passed")
            results['ask_validation'] = {'success': True}
        else:
            logger.error("✗ Ask order validation failed")
            results['ask_validation'] = {'success': False}
            
    except Exception as e:
        logger.error(f"Order validation error: {str(e)}")
        results['validation_error'] = {'success': False, 'error': str(e)}

    # Check open orders (real API call)
    logger.info("\nChecking open orders...")
    try:
        open_orders = client.get_open_orders(symbol)
        if open_orders is not None:
            logger.info(f"✓ Successfully fetched open orders")
            if isinstance(open_orders, list):
                logger.info(f"Current open orders: {len(open_orders)}")
                for order in open_orders[:5]:  # Show first 5 orders
                    logger.info(f"Order: {order}")
            results['open_orders'] = {'success': True}
        else:
            logger.error("✗ Failed to fetch open orders")
            results['open_orders'] = {'success': False}
    except Exception as e:
        logger.error(f"Open orders error: {str(e)}")
        results['open_orders'] = {'success': False, 'error': str(e)}

    # Check trading history (real API call)
    logger.info("\nChecking trading history...")
    try:
        trade_history = client.get_my_trades(symbol)
        if trade_history is not None:
            logger.info(f"✓ Successfully fetched trading history")
            if isinstance(trade_history, list):
                logger.info(f"Number of trades: {len(trade_history)}")
                for trade in trade_history[:5]:  # Show first 5 trades
                    logger.info(f"Trade: {trade}")
            results['trade_history'] = {'success': True}
        else:
            logger.error("✗ Failed to fetch trading history")
            results['trade_history'] = {'success': False}
    except Exception as e:
        logger.error(f"Trade history error: {str(e)}")
        results['trade_history'] = {'success': False, 'error': str(e)}

    # Print test summary
    logger.info("\n=== Market Making Test Summary ===")
    success_count = sum(1 for r in results.values() if r.get('success', False))
    total_tests = len(results)
    success_rate = (success_count / total_tests) * 100 if total_tests > 0 else 0
    logger.info(f"Success Rate: {success_rate:.1f}%")
    logger.info(f"Tests Passed: {success_count}/{total_tests}")
    
    return results
