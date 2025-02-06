import pytest
from decimal import Decimal
from typing import Dict, Any

def create_mock_order_book(base_price: Decimal, spread: Decimal, depth: int) -> Dict[str, Any]:
    """Create a realistic mock order book"""
    bids = []
    asks = []
    
    for i in range(depth):
        bid_price = base_price - (spread * (i + 1))
        ask_price = base_price + (spread * (i + 1))
        
        bids.append([str(bid_price), "1.0"])
        asks.append([str(ask_price), "1.0"])
    
    return {
        "bids": bids,
        "asks": asks
    }

def validate_order(order: Dict[str, Any]) -> bool:
    """Validate order structure and values"""
    required_fields = {"symbol", "side", "orderType", "price", "amount"}
    
    # Check all required fields exist
    if not all(field in order for field in required_fields):
        return False
    
    # Validate field types and values
    try:
        assert isinstance(order["symbol"], str)
        assert order["side"] in {1, 2}  # 1 for buy, 2 for sell
        assert order["orderType"] in {1, 2}  # 1 for limit, 2 for market
        assert Decimal(order["price"]) > 0
        assert Decimal(order["amount"]) > 0
    except (AssertionError, ValueError, TypeError):
        return False
    
    return True 