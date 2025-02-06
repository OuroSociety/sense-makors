import pytest
from decimal import Decimal
from trading.risk_manager import RiskManager
from trading.position_tracker import PositionTracker

@pytest.fixture
def risk_manager():
    position_tracker = PositionTracker()
    return RiskManager(position_tracker)

def test_risk_limits():
    position_tracker = PositionTracker()
    risk_manager = RiskManager(position_tracker)
    
    symbol = "TEST-USDT"
    risk_manager.set_limits(symbol, Decimal('100'), Decimal('10'))
    
    # Test within limits
    assert risk_manager.check_order(symbol, Decimal('50'), Decimal('1.0'), True)
    
    # Test exceeding position limit
    assert not risk_manager.check_order(symbol, Decimal('150'), Decimal('1.0'), True) 