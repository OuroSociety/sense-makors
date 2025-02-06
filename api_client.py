import requests
import time
import hmac
import hashlib
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
            'Content-Type': 'application/json'
        }
        
        if signed:
            timestamp = str(int(time.time()))
            signature = self._generate_signature(timestamp, method, endpoint, params)
            headers.update({
                'X-CH-APIKEY': self.api_key,
                'X-CH-SIGN': signature, 
                'X-CH-TS': timestamp
            })
            
        try:
            if method == 'GET':
                response = self.session.get(url, params=params, headers=headers)
            else:
                response = self.session.post(url, json=params, headers=headers)
                
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"API request error: {str(e)}")
            return None
            
    def get_order_book(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        """Get the order book for a symbol"""
        endpoint = "/sapi/v1/depth"
        params = {
            "symbol": symbol.upper(),
            "limit": limit
        }
        return self._request('GET', endpoint, params)
        
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get 24hr ticker information"""
        endpoint = "/sapi/v1/ticker"
        params = {"symbol": symbol.upper()}
        return self._request('GET', endpoint, params)
        
    def get_trades(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        """Get recent trades"""
        endpoint = "/sapi/v1/trades"
        params = {
            "symbol": symbol.upper(),
            "limit": limit
        }
        return self._request('GET', endpoint, params)
        
    def get_klines(self, symbol: str, interval: str = "1min", 
                   limit: int = 100) -> Dict[str, Any]:
        """Get kline/candlestick data"""
        endpoint = "/sapi/v1/klines"
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": limit
        }
        return self._request('GET', endpoint, params)
        
    def place_order(self, symbol: str, side: str, order_type: str,
                    volume: str, price: str = None) -> Dict[str, Any]:
        """Place a new order"""
        endpoint = "/sapi/v1/order"
        params = {
            "symbol": symbol.upper(),
            "volume": volume,
            "side": side.upper(),
            "type": order_type.upper()
        }
        if price:
            params["price"] = price
            
        return self._request('POST', endpoint, params, signed=True)
        
    def cancel_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """Cancel an existing order"""
        endpoint = "/sapi/v1/cancel"
        params = {
            "symbol": symbol.lower(),
            "orderId": order_id
        }
        return self._request('POST', endpoint, params, signed=True)
        
    def get_open_orders(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        """Get current open orders"""
        endpoint = "/sapi/v1/openOrders"
        params = {
            "symbol": symbol.lower(),
            "limit": limit
        }
        return self._request('GET', endpoint, params, signed=True)
        
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        endpoint = "/sapi/v1/account"
        return self._request('GET', endpoint, signed=True)
        
    def get_my_trades(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        """Get user's trade history"""
        endpoint = "/sapi/v1/myTrades"
        params = {
            "symbol": symbol.upper(),
            "limit": limit
        }
        return self._request('GET', endpoint, params, signed=True) 