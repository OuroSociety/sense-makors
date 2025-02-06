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
        
    log_file = os.path.join(log_dir, f"pair_test_{timestamp}.log")
    
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

def test_pair_formats(base_url, api_key, api_secret, logger):
    """Test different formats of SZAR-USDT, BTC-USDT, and KANGO-USDT pairs across multiple endpoints"""
    
    # Test all possible format variations
    pair_formats = {
        'SZAR': [
            'SZAR-USDT',
            'SZARUSDT',
            'SZAR_USDT',
            'szar-usdt',
            'szarusdt',
            'SZAR/USDT',
            'USDT_SZAR',
            'USDT-SZAR',
            'SZAR.USDT'  # Some APIs use dot notation
        ],
        'BTC': [
            'BTC-USDT',
            'BTCUSDT',
            'BTC_USDT',
            'btc-usdt',
            'btcusdt',
            'BTC/USDT',
            'USDT_BTC',
            'USDT-BTC'
        ],
        'KANGO': [
            'KANGO-USDT',
            'KANGOUSDT',
            'KANGO_USDT',
            'kango-usdt',
            'kangousdt',
            'KANGO/USDT',
            'USDT_KANGO',
            'USDT-KANGO'
        ]
    }
    
    # All possible endpoints to test
    endpoints = {
        'trades': '/api/v2/trades',
        'orderbook': '/api/v2/orderbook',
        'ticker': '/api/v2/ticker',
        'summary': '/v2/public/summary',
        'market_pair': '/v2/public/trades/market_pair',
        'ticker_24hr': '/api/v2/ticker/24hr',  # Added 24hr ticker endpoint
        'ticker_price': '/api/v2/ticker/price',  # Added price ticker endpoint
        'assets': '/v2/public/assets',  # Added assets endpoint
        'orderbook_market': '/v2/public/orderbook/market_pair',  # Added market orderbook endpoint
        'kline': '/v1/market/history/kline'  # Added kline/candlestick endpoint
    }
    
    headers = {
        'AccessKey': api_key,
        'Content-Type': 'application/json'
    }
    
    # Log test configuration
    logger.info("\n=== Test Configuration ===")
    logger.info(f"Base URL: {base_url}")
    logger.info(f"API Key: {api_key}")
    logger.info("Testing Pairs: SZAR-USDT, BTC-USDT, KANGO-USDT")
    logger.info(f"Endpoints: {', '.join(endpoints.keys())}\n")
    
    results_summary = {coin: {'success': 0, 'failed': 0} for coin in pair_formats.keys()}
    
    for coin in ['SZAR', 'BTC', 'KANGO']:
        logger.info(f"\n=== Testing {coin}-USDT Pair Availability ===")
        logger.info(f"Timestamp: {datetime.now().isoformat()}\n")
        
        for endpoint_name, endpoint in endpoints.items():
            logger.info(f"\nTesting {endpoint_name} endpoint:")
            logger.info("-" * 50)
            
            for pair_format in pair_formats[coin]:
                url = f"{base_url}{endpoint}"
                if endpoint_name != 'summary':
                    if endpoint_name == 'market_pair':
                        url += f"?market_pair={pair_format}"
                    elif endpoint_name == 'kline':
                        url += f"?symbol={pair_format}&period=1"  # Test with 1min candles
                    else:
                        url += f"?symbol={pair_format}"
                
                try:
                    response = requests.get(url, headers=headers)
                    
                    logger.info(f"\nTesting {pair_format} at {url}")
                    logger.info(f"Status Code: {response.status_code}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        if endpoint_name == 'summary':
                            pairs = [p for p in data.get('data', []) if coin in str(p)]
                            if pairs:
                                logger.info(f"Found {coin} pairs in summary:")
                                for pair in pairs:
                                    logger.info(json.dumps(pair, indent=2))
                                results_summary[coin]['success'] += 1
                            else:
                                logger.info(f"No {coin} pairs found in summary")
                                results_summary[coin]['failed'] += 1
                        else:
                            if isinstance(data, dict) and not any(data.values()) and coin in ['BTC', 'KANGO']:
                                logger.warning(f"Warning: Empty response for {coin} pair - possible API issue")
                                results_summary[coin]['failed'] += 1
                            elif isinstance(data, list) and not data and coin in ['BTC', 'KANGO']:
                                logger.warning(f"Warning: Empty response for {coin} pair - possible API issue")
                                results_summary[coin]['failed'] += 1
                            else:
                                logger.info("Response: " + json.dumps(data, indent=2))
                                if data:  # If we got any data back
                                    results_summary[coin]['success'] += 1
                                else:
                                    results_summary[coin]['failed'] += 1
                    else:
                        logger.error(f"Error Response: {response.text}")
                        results_summary[coin]['failed'] += 1
                    
                except Exception as e:
                    logger.error(f"Error testing {pair_format}: {str(e)}")
                    results_summary[coin]['failed'] += 1
                
                # Add small delay to avoid rate limiting
                time.sleep(0.5)
    
    # Log final summary
    logger.info("\n=== Final Test Summary ===")
    for coin, results in results_summary.items():
        total = results['success'] + results['failed']
        success_rate = (results['success'] / total * 100) if total > 0 else 0
        logger.info(f"{coin}-USDT Test Results:")
        logger.info(f"  Success: {results['success']}")
        logger.info(f"  Failed: {results['failed']}")
        logger.info(f"  Success Rate: {success_rate:.2f}%\n")

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
    test_pair_formats(BASE_URL, API_KEY, API_SECRET, logger)
    
    logger.info("Testing completed. Log file has been saved.") 