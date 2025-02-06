import requests
import json
from datetime import datetime
import time
import logging
import os
from dotenv import load_dotenv

def setup_logging():
    """Setup logging configuration"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    log_file = os.path.join(log_dir, f"szar_test_{timestamp}.log")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()  # Also print to console
        ]
    )
    logger = logging.getLogger()
    logger.info(f"Logging to: {log_file}")
    return logger

def test_token_pairs(base_url, api_key, api_secret, logger):
    """Test token pairs using FameEX API v1"""
    
    # Test exact trading pairs (lowercase as per API docs)
    token_pairs = [
            'kangousdt',
        'kyrousdt',
        'kroakusdt',
        'keirousdt',
        'szarusdt'
    ]
    
    # Log test configuration
    logger.info("\n=== Test Configuration ===")
    logger.info(f"Testing Trading Pairs")
    logger.info(f"Pairs: {', '.join(token_pairs)}\n")
    
    overall_results = {}
    
    for pair in token_pairs:
        logger.info(f"\n\n=== Testing Trading Pair: {pair} ===")
        logger.info("=" * 50)
        
        # Define core endpoints to test
        endpoints = {
            'depth': {
                'url': 'https://openapi.fameex.net/sapi/v1/depth',
                'params': {'symbol': pair, 'limit': 100},
                'expected_fields': ['bids', 'asks']
            },
            'trades': {
                'url': 'https://openapi.fameex.net/sapi/v1/trades',
                'params': {'symbol': pair, 'limit': 100},
                'expected_fields': ['side', 'price', 'qty', 'time']
            },
            'ticker': {
                'url': 'https://openapi.fameex.net/sapi/v1/ticker',
                'params': {'symbol': pair},
                'expected_fields': ['vol', 'last', 'buy', 'sell', 'time']
            },
            'klines': {
                'url': 'https://openapi.fameex.net/sapi/v1/klines',
                'params': {'symbol': pair, 'interval': '1min', 'limit': 100},
                'expected_fields': ['high', 'low', 'open', 'close', 'vol']
            }
        }
        
        results = {'success': 0, 'failed': 0, 'details': []}
        
        for endpoint_name, endpoint_info in endpoints.items():
            try:
                url = endpoint_info['url']
                params = endpoint_info['params']
                
                logger.info(f"\nTesting {endpoint_name}:")
                logger.info(f"URL: {url}")
                logger.info(f"Params: {params}")
                
                response = requests.get(url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    logger.debug(f"Response: {json.dumps(data, indent=2)}")
                    
                    if endpoint_name == 'depth':
                        if data.get('bids') or data.get('asks'):
                            results['success'] += 1
                            results['details'].append(f"{endpoint_name}: Active - Has order book data")
                            if data.get('bids'):
                                logger.info(f"First bid: {data['bids'][0]}")
                            if data.get('asks'):
                                logger.info(f"First ask: {data['asks'][0]}")
                        else:
                            results['failed'] += 1
                            results['details'].append(f"{endpoint_name}: Inactive - No order book data")
                    
                    elif endpoint_name == 'trades':
                        if isinstance(data, list) and len(data) > 0:
                            results['success'] += 1
                            results['details'].append(f"{endpoint_name}: Active - Has recent trades")
                            logger.info(f"Latest trade: {data[0]}")
                            else:
                            results['failed'] += 1
                            results['details'].append(f"{endpoint_name}: Inactive - No trades")
                    
                    elif endpoint_name == 'ticker':
                        if data.get('vol') is not None:
                            results['success'] += 1
                            results['details'].append(f"{endpoint_name}: Active - Has ticker data")
                            logger.info(f"Ticker: {data}")
                        else:
                            results['failed'] += 1
                            results['details'].append(f"{endpoint_name}: Inactive - No ticker data")
                            
                    elif endpoint_name == 'klines':
                        if isinstance(data, list) and len(data) > 0:
                            results['success'] += 1
                            results['details'].append(f"{endpoint_name}: Active - Has kline data")
                            logger.info(f"Latest kline: {data[0]}")
                            else:
                            results['failed'] += 1
                            results['details'].append(f"{endpoint_name}: Inactive - No kline data")
                                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    results['failed'] += 1
                    results['details'].append(f"{endpoint_name}: Failed - {error_msg}")
                    
                except Exception as e:
                error_msg = f"Error: {str(e)}"
                results['failed'] += 1
                results['details'].append(f"{endpoint_name}: Failed - {error_msg}")
            
            time.sleep(0.5)  # Rate limiting
        
        # Store and log results
        overall_results[pair] = results
        
        total = results['success'] + results['failed']
        success_rate = (results['success'] / total * 100) if total > 0 else 0
        logger.info(f"\nResults for {pair}:")
        logger.info(f"Active Endpoints: {results['success']}")
        logger.info(f"Inactive/Failed: {results['failed']}")
        logger.info(f"Activity Rate: {success_rate:.2f}%")
        logger.info("\nEndpoint Details:")
        for detail in results['details']:
            logger.info(f"  {detail}")
    
    # Log final summary
    logger.info("\n\n=== Final Summary ===")
    logger.info("=" * 50)
    
    for pair, results in overall_results.items():
        total = results['success'] + results['failed']
        success_rate = (results['success'] / total * 100) if total > 0 else 0
        logger.info(f"\n{pair}:")
        logger.info(f"Active Endpoints: {results['success']}")
        logger.info(f"Inactive/Failed: {results['failed']}")
        logger.info(f"Activity Rate: {success_rate:.2f}%")
        
        active_endpoints = [d.split(':')[0] for d in results['details'] if 'Active' in d]
        if active_endpoints:
            logger.info(f"Active Markets: {', '.join(active_endpoints)}")

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    BASE_URL = "https://api.fameex.com"
    API_KEY = os.getenv('FAMEEX_API_KEY')
    API_SECRET = os.getenv('FAMEEX_API_SECRET')
    
    if not API_KEY or not API_SECRET:
        print("Error: API credentials not found in .env file")
        exit(1)
    
    # Setup logging
    logger = setup_logging()
    
    # Run tests
    test_token_pairs(BASE_URL, API_KEY, API_SECRET, logger)
    
    logger.info("Testing completed. Log file has been saved.") 