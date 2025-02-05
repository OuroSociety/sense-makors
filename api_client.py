import requests
import time
from typing import Dict, Any
from config import API_BASE_URL

class FameexClient:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = requests.Session()
        
    def get_order_book(self, symbol: str, limit: int = 5) -> Dict[str, Any]:
        """Get the order book for a specific symbol"""
        endpoint = f"{API_BASE_URL}/api/v2/orderbook"
        params = {
            "symbol": symbol,
            "limit": limit
        }
        
        try:
            response = self.session.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching order book: {e}")
            return None
            
    def place_order(self, symbol: str, side: int, order_type: int, 
                    price: str, amount: str) -> Dict[str, Any]:
        """Place a new order"""
        endpoint = f"{API_BASE_URL}/v1/api/spot/orders"
        
        data = {
            "symbol": symbol,
            "side": side,  # 1 for buy, 2 for sell
            "orderType": order_type,  # 1 for limit order
            "price": price,
            "amount": amount
        }
        
        # TODO: Add authentication headers
        try:
            response = self.session.post(endpoint, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error placing order: {e}")
            return None 