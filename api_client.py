import requests
import time
import hmac
import hashlib
import base64
from typing import Dict, Any, Optional
from config import API_BASE_URL

class FameexClient:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = requests.Session()
        
    def _generate_signature(self, timestamp: str, method: str, 
                          endpoint: str, params: Dict = None) -> str:
        """Generate signature for API request"""
        params_str = '&'.join([f"{k}={v}" for k, v in sorted(params.items())]) if params else ''
        message = f"{timestamp}{method}{endpoint}{params_str}"
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
        
    def _request(self, method: str, endpoint: str, 
                 params: Dict = None, signed: bool = False) -> Optional[Dict]:
        """Make API request with optional signing"""
        url = f"{API_BASE_URL}{endpoint}"
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        if signed:
            timestamp = str(int(time.time()))
            signature = self._generate_signature(timestamp, method, endpoint, params)
            headers.update({
                'FX-ACCESS-KEY': self.api_key,
                'FX-ACCESS-SIGN': signature,
                'FX-ACCESS-TIMESTAMP': timestamp,
                'FX-ACCESS-VERSION': 'v1.0'
            })
            
        try:
            if method == 'GET':
                response = self.session.get(url, params=params, headers=headers)
            else:
                response = self.session.post(url, json=params, headers=headers)
            
            print(f"Request URL: {response.url}")
            print(f"Response Status: {response.status_code}")
            print(f"Response Text: {response.text}")
                
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"API request error: {str(e)}")
            return None
            
    def get_order_book(self, symbol: str, limit: int = 5) -> Dict[str, Any]:
        """Get the order book for a specific symbol"""
        # First check if the trading pair exists
        try:
            # Get all available pairs
            summary_endpoint = "/v2/public/summary"
            summary = self._request('GET', summary_endpoint)
            
            if summary and isinstance(summary, dict) and 'data' in summary:
                # Check if our pair exists
                trading_pairs = [pair['trading_pairs'] for pair in summary['data']]
                normalized_symbol = symbol.replace('-', '').lower()  # Convert SZAR-cUSD to szarcusd
                
                if normalized_symbol not in [p.lower() for p in trading_pairs]:
                    print(f"Warning: Trading pair {symbol} not found in available pairs:")
                    print("Available pairs:", trading_pairs)
                    return None
            
            # If pair exists or we couldn't verify, try to get order book
            market_pair = symbol.replace('-', '_')
            endpoint = "/v2/public/orderbook/market_pair"
            params = {
                "market_pair": market_pair,
                "level": 3,
                "depth": limit
            }
            response = self._request('GET', endpoint, params)
            
            if response is None:
                print(f"Error: No response from order book API for {symbol}")
                return None
                
            if isinstance(response, dict) and 'code' in response:
                if response['code'] != '0':
                    print(f"API Error: {response.get('message', 'Unknown error')}")
                    return None
                    
            return response
            
        except Exception as e:
            print(f"Error fetching order book: {str(e)}")
            return None
        
    def get_account_balance(self) -> Dict[str, Any]:
        """Get account balances"""
        endpoint = "/v1/api/account/wallet"
        return self._request('GET', endpoint, signed=True)
        
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get ticker information for a symbol"""
        endpoint = "/api/v2/ticker/24hr"
        params = {"symbol": symbol} if symbol else {}
        return self._request('GET', endpoint, params)
        
    def place_order(self, symbol: str, side: int, order_type: int, 
                   price: str, amount: str) -> Dict[str, Any]:
        """Place a new order"""
        endpoint = "/spot/trade/orders"
        params = {
            "symbol": symbol,
            "side": side,
            "orderType": order_type,
            "price": price,
            "amount": amount
        }
        return self._request('POST', endpoint, params, signed=True) 