from decimal import Decimal
from typing import Dict, Any, Optional, TypedDict

class MarketCondition(TypedDict):
    """Type definition for market condition test cases"""
    description: str
    input: Dict[str, Any]
    expected: Dict[str, Any]

def create_test_order_book(
    base_price: Decimal,
    spread_percentage: Decimal,
    depth: int,
    volume: Decimal,
    condition: str = "normal"
) -> Dict[str, Any]:
    """
    Create a realistic test order book based on market condition.
    
    Args:
        base_price: Center price for the order book
        spread_percentage: Percentage difference between bid and ask
        depth: Number of price levels
        volume: Base volume at each level
        condition: Market condition ("normal", "tight", "wide", "empty")
    
    Returns:
        Dict containing bids and asks structured for test cases
    """
    if condition == "empty":
        return {"bids": [], "asks": []}

    spread = base_price * spread_percentage
    if condition == "tight":
        spread = spread * Decimal("0.1")
    elif condition == "wide":
        spread = spread * Decimal("2.0")

    bids = []
    asks = []
    
    for i in range(depth):
        bid_price = base_price - spread * (i + 1)
        ask_price = base_price + spread * (i + 1)
        level_volume = volume / (i + 1)  # Decrease volume at each level
        
        bids.append([str(bid_price), str(level_volume)])
        asks.append([str(ask_price), str(level_volume)])
    
    return {
        "bids": bids,
        "asks": asks
    }

def validate_test_results(
    test_case: MarketCondition,
    actual_result: Any,
    context: str = ""
) -> None:
    """
    Validate test results against expected outcomes.
    
    Args:
        test_case: The test case definition
        actual_result: The actual result from the test
        context: Additional context for error messages
    
    Raises:
        AssertionError: If validation fails
    """
    expected = test_case["expected"]
    
    for key, expected_value in expected.items():
        if key not in actual_result:
            raise AssertionError(
                f"{context}: Missing expected key '{key}' in actual result"
            )
        
        actual_value = actual_result[key]
        assert actual_value == expected_value, \
            f"{context}: Expected {key}={expected_value}, got {actual_value}"

def validate_market_maker_state(
    market_maker: Any,
    min_orders: int = 0,
    max_position: Optional[Decimal] = None
) -> bool:
    """
    Validate the state of a market maker instance.
    
    Args:
        market_maker: MarketMaker instance to validate
        min_orders: Minimum number of active orders expected
        max_position: Maximum allowed position size
    
    Returns:
        bool: True if state is valid
    """
    # Check active orders
    if len(market_maker.active_orders) < min_orders:
        return False
    
    # Check position limits
    if max_position is not None:
        for symbol, position in market_maker.position_tracker.positions.items():
            if abs(position) > max_position:
                return False
    
    return True 