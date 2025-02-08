from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union
import requests
import logging

logger = logging.getLogger(__name__)

class ExchangeClient(ABC):
    def __init__(self, api_key: str, api_secret: str, base_url: str, test_mode: bool = False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.session = requests.Session()
        self.test_mode = test_mode

    @abstractmethod
    def _generate_signature(self, *args, **kwargs) -> str:
        """Generate signature for API request"""
        pass

    @abstractmethod
    def _request(self, method: str, endpoint: str, 
                params: Dict = None, signed: bool = False) -> Optional[Dict]:
        """Make API request with optional signing"""
        pass

    @abstractmethod
    def get_order_book(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        """Get the order book for a symbol"""
        pass

    @abstractmethod
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get ticker information"""
        pass

    @abstractmethod
    def place_order(self, symbol: str, side: Union[str, int], order_type: Union[str, int],
                   volume: str, price: str = None) -> Dict[str, Any]:
        """Place a new order"""
        pass

    @abstractmethod
    def cancel_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """Cancel an existing order"""
        pass

    @abstractmethod
    def get_open_orders(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        """Get current open orders"""
        pass

    @abstractmethod
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        pass 