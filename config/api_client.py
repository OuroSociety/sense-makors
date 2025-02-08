import requests
import time
import hmac
import hashlib
from typing import Dict, Any, Optional, Union
from config.base_client import ExchangeClient
from config.config import API_BASE_URL
import logging

logger = logging.getLogger(__name__)

class FameexClient(ExchangeClient):
    def __init__(self, api_key: str, api_secret: str, test_mode: bool = False):
        super().__init__(api_key, api_secret, API_BASE_URL, test_mode)
        
    def _generate_signature(self, timestamp: str, method: str, 
                          endpoint: str, params: Dict = None) -> str:
        """Generate signature for API request"""
        # Sort parameters alphabetically and create parameter string
        params_list = []
        if params:
            for key in sorted(params.keys()):
                params_list.append(f"{key}={params[key]}")
        params_str = '&'.join(params_list)
        
        # Create message string
        message = f"{method.upper()}{endpoint}{timestamp}{params_str}"
        
        # Generate HMAC SHA256 signature
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        logger.debug(f"Signature message: {message}")
        logger.debug(f"Generated signature: {signature}")
        
        return signature
        
    def _request(self, method: str, endpoint: str, 
                 params: Dict = None, signed: bool = False) -> Optional[Dict]:
        """Make API request with optional signing"""
        # Only mock order-related endpoints in test mode
        if self.test_mode and endpoint in [
            "/sapi/v1/order",
            "/sapi/v1/order/test",
            "/sapi/v1/cancel"
        ]:
            return self._get_mock_response(endpoint, params)
            
        url = f"{self.base_url}{endpoint}"
        
        # Generate timestamp and signature first for all authenticated requests
        timestamp = str(int(time.time() * 1000))  # Use milliseconds timestamp
        
        headers = {
            'Content-Type': 'application/json',
            'X-CH-APIKEY': self.api_key,
            'X-CH-TS': timestamp
        }
        
        if signed:
            # Include timestamp in params for signature
            if params is None:
                params = {}
            params['timestamp'] = timestamp
            
            # Generate signature with all parameters
            signature = self._generate_signature(timestamp, method, endpoint, params)
            headers['X-CH-SIGN'] = signature
        
        try:
            if method == 'GET':
                response = self.session.get(url, params=params, headers=headers)
            else:
                response = self.session.post(url, json=params, headers=headers)
                
            # Log request details for debugging
            logger.debug(f"Request URL: {url}")
            logger.debug(f"Request Headers: {headers}")
            logger.debug(f"Request Params: {params}")
            logger.debug(f"Response Status: {response.status_code}")
            logger.debug(f"Response Text: {response.text}")
            
            response.raise_for_status()
            data = response.json()
            
            # Check for API error codes
            if isinstance(data, dict) and 'code' in data and data['code'] != 200:
                logger.error(f"API Error: {data.get('msg', 'Unknown error')}")
                return None
            
            # Handle both direct data and data within 'data' field
            if isinstance(data, dict) and 'data' in data:
                return data['data']
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"API request error: {str(e)}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response text: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return None
            
    def _get_mock_response(self, endpoint: str, params: Dict = None) -> Dict:
        """Generate mock responses for testing - only for order operations"""
        if endpoint == "/sapi/v1/order" or endpoint == "/sapi/v1/order/test":
            return {
                'code': 200,
                'data': {
                    'orderId': 'test_' + str(int(time.time())),
                    'symbol': params.get('symbol'),
                    'side': params.get('side'),
                    'type': params.get('type'),
                    'price': params.get('price'),
                    'volume': params.get('volume'),
                    'status': 'NEW'
                }
            }
        elif endpoint == "/sapi/v1/cancel":
            return {
                'code': 200,
                'data': {
                    'orderId': params.get('orderId'),
                    'status': 'CANCELED'
                }
            }
        return {'code': 200, 'data': {}}

    def _format_symbol(self, symbol: str) -> str:
        """Format symbol to match exchange requirements"""
        return symbol.lower().replace('-', '')

    def get_order_book(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        """Get the order book for a symbol"""
        endpoint = "/sapi/v1/depth"
        params = {
            "symbol": self._format_symbol(symbol),
            "limit": limit
        }
        response = self._request('GET', endpoint, params)
        
        # Transform response to expected format
        if response and isinstance(response, dict):
            return {
                'data': {
                    'bids': response.get('bids', []),
                    'asks': response.get('asks', []),
                    'timestamp': response.get('time')
                }
            }
        return response
        
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get 24hr ticker information"""
        endpoint = "/sapi/v1/ticker"
        params = {"symbol": self._format_symbol(symbol)}
        return self._request('GET', endpoint, params)
        
    def get_trades(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        """Get recent trades"""
        endpoint = "/sapi/v1/trades"
        params = {
            "symbol": self._format_symbol(symbol),
            "limit": limit
        }
        return self._request('GET', endpoint, params)
        
    def get_klines(self, symbol: str, interval: str = "1min", 
                   limit: int = 100) -> Dict[str, Any]:
        """Get kline/candlestick data"""
        endpoint = "/sapi/v1/klines"
        params = {
            "symbol": self._format_symbol(symbol),
            "interval": interval,
            "limit": limit
        }
        return self._request('GET', endpoint, params)
        
    def place_order(self, symbol: str, side: Union[str, int], order_type: Union[str, int],
                    volume: str, price: str = None) -> Dict[str, Any]:
        """Place a new order
        
        Args:
            symbol: Trading pair symbol
            side: 1 for BUY, 2 for SELL (or "BUY"/"SELL" strings)
            order_type: 1 for LIMIT, 2 for MARKET (or "LIMIT"/"MARKET" strings)
            volume: Order volume
            price: Order price (required for limit orders)
        """
        endpoint = "/sapi/v1/order"
        
        # Convert side to integer if it's a string
        if isinstance(side, str):
            side = 1 if side.upper() == "BUY" else 2
        
        # Convert order_type to integer if it's a string    
        if isinstance(order_type, str):
            order_type = 1 if order_type.upper() == "LIMIT" else 2
        
        params = {
            "symbol": self._format_symbol(symbol),
            "volume": volume,
            "side": side,  # Use integer directly
            "type": order_type  # Use integer directly
        }
        if price:
            params["price"] = price
            
        return self._request('POST', endpoint, params, signed=True)
        
    def cancel_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """Cancel an existing order"""
        endpoint = "/sapi/v1/cancel"
        params = {
            "symbol": self._format_symbol(symbol),
            "orderId": order_id
        }
        return self._request('POST', endpoint, params, signed=True)
        
    def get_open_orders(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        """Get current open orders"""
        endpoint = "/sapi/v1/openOrders"
        params = {
            "symbol": self._format_symbol(symbol),
            "limit": str(limit)  # Convert to string for consistent signature
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
            "symbol": self._format_symbol(symbol),
            "limit": str(limit)  # Convert to string for consistent signature
        }
        return self._request('GET', endpoint, params, signed=True)
        
    def test_order(self, symbol: str, side: Union[str, int], order_type: Union[str, int],
                   volume: str, price: str = None) -> Dict[str, Any]:
        """Test a new order without sending to matching engine"""
        endpoint = "/sapi/v1/order/test"
        
        # Convert side to integer if it's a string
        if isinstance(side, str):
            side = 1 if side.upper() == "BUY" else 2
        
        # Convert order_type to integer if it's a string    
        if isinstance(order_type, str):
            order_type = 1 if order_type.upper() == "LIMIT" else 2
        
        params = {
            "symbol": self._format_symbol(symbol),
            "volume": volume,
            "side": side,
            "type": order_type
        }
        if price:
            params["price"] = price
        
        return self._request('POST', endpoint, params, signed=True) 