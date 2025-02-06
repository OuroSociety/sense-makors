import pytest
from decimal import Decimal
from trading.position_tracker import PositionTracker

@pytest.fixture
def position_tracker():
    return PositionTracker()

def test_position_tracking():
    tracker = PositionTracker()
    symbol = "TEST-USDT"
    
    # Test initial position
    assert tracker.get_position(symbol) == Decimal('0')
    
    # Test buy
    tracker.update_position(symbol, Decimal('10'), Decimal('100'), True)
    assert tracker.get_position(symbol) == Decimal('10')
    
    # Test sell
    tracker.update_position(symbol, Decimal('5'), Decimal('110'), False)
    assert tracker.get_position(symbol) == Decimal('5') 