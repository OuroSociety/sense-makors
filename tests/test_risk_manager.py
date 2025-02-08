import pytest
from decimal import Decimal
from trading.risk_manager import RiskManager
from trading.position_tracker import PositionTracker
from trading.wallet_manager import WalletManager

@pytest.fixture
def risk_manager():
    """Create a RiskManager instance with mocked dependencies"""
    position_tracker = PositionTracker()
    wallet_manager = WalletManager()
    risk_mgr = RiskManager(position_tracker, wallet_manager)
    
    # Initialize test balances
    wallet_manager.update_balance('USDT', Decimal('10000'))
    wallet_manager.update_balance('SZAR', Decimal('10000'))
    
    return risk_mgr

@pytest.fixture
def symbol():
    """Test trading pair"""
    return "SZARUSDT"

class TestRiskManager:
    def test_set_limits(self, risk_manager, symbol):
        """Test setting risk limits"""
        max_position = Decimal('1000')
        max_order_size = Decimal('100')
        min_spread = Decimal('0.001')
        
        risk_manager.set_limits(
            symbol=symbol,
            max_position=max_position,
            max_order_size=max_order_size,
            min_spread=min_spread
        )
        
        assert risk_manager.max_position_size[symbol] == max_position
        assert risk_manager.min_spread[symbol] == min_spread
        assert risk_manager.target_balance_ratio[symbol] == Decimal('1.0')

    def test_check_order_within_limits(self, risk_manager, symbol):
        """Test order checking within limits"""
        # Set limits
        risk_manager.set_limits(
            symbol=symbol,
            max_position=Decimal('1000'),
            max_order_size=Decimal('100'),
            min_spread=Decimal('0.001')
        )
        
        # Set balanced initial state
        risk_manager.wallet_manager.update_balance('USDT', Decimal('10000'))
        risk_manager.wallet_manager.update_balance('SZAR', Decimal('10000'))
        
        # Test buy order within limits
        assert risk_manager.check_order(
            symbol=symbol,
            amount=Decimal('50'),
            price=Decimal('1.0'),
            is_buy=True
        )

    def test_check_order_exceeds_limits(self, risk_manager, symbol):
        """Test order checking exceeding limits"""
        # Set limits
        risk_manager.set_limits(
            symbol=symbol,
            max_position=Decimal('1000'),
            max_order_size=Decimal('100'),
            min_spread=Decimal('0.001')
        )
        
        # Test buy order exceeding limits
        assert not risk_manager.check_order(
            symbol=symbol,
            amount=Decimal('1500'),
            price=Decimal('1.0'),
            is_buy=True
        )

    def test_dynamic_position_limit(self, risk_manager, symbol):
        """Test dynamic position limit calculation"""
        # Set initial balances and price
        price = Decimal('1.0')
        
        # Calculate dynamic limit
        limit = risk_manager.get_dynamic_position_limit(symbol, price)
        
        # Should be 20% of total portfolio value
        expected_limit = (Decimal('10000') + Decimal('10000')) * Decimal('0.20')
        assert limit == expected_limit

    def test_balance_ratio_improvement(self, risk_manager, symbol):
        """Test balance ratio improvement check"""
        # Set up initial state
        risk_manager.set_limits(
            symbol=symbol,
            max_position=Decimal('1000'),
            max_order_size=Decimal('100'),
            min_spread=Decimal('0.001')
        )
        
        # Test with imbalanced portfolio (more USDT than SZAR)
        risk_manager.wallet_manager.update_balance('USDT', Decimal('15000'))
        risk_manager.wallet_manager.update_balance('SZAR', Decimal('5000'))
        
        # Buy order should improve balance (convert USDT to SZAR)
        assert risk_manager.check_order(
            symbol=symbol,
            amount=Decimal('50'),
            price=Decimal('1.0'),
            is_buy=True
        )
        
        # Update balances to simulate executed buy order
        risk_manager.wallet_manager.update_balance('USDT', Decimal('14950'))
        risk_manager.wallet_manager.update_balance('SZAR', Decimal('5050'))
        
        # Sell order should worsen balance
        assert not risk_manager.check_order(
            symbol=symbol,
            amount=Decimal('50'),
            price=Decimal('1.0'),
            is_buy=False
        )

    def test_recommended_spread(self, risk_manager, symbol):
        """Test spread recommendation based on market conditions"""
        # Set initial spread
        risk_manager.set_limits(
            symbol=symbol,
            max_position=Decimal('1000'),
            max_order_size=Decimal('100'),
            min_spread=Decimal('0.001')
        )
        
        # Test with different volatility levels
        low_volatility = Decimal('0.001')
        high_volatility = Decimal('0.01')
        
        low_spread = risk_manager.get_recommended_spread(symbol, low_volatility)
        high_spread = risk_manager.get_recommended_spread(symbol, high_volatility)
        
        assert low_spread < high_spread
        assert low_spread >= risk_manager.min_spread[symbol]

    def test_error_handling(self, risk_manager, symbol):
        """Test error handling in risk checks"""
        # Don't set limits to trigger error
        assert not risk_manager.check_order(
            symbol=symbol,
            amount=Decimal('50'),
            price=Decimal('1.0'),
            is_buy=True
        )
        
        # Test with invalid symbol
        assert not risk_manager.check_order(
            symbol="INVALID-PAIR",
            amount=Decimal('50'),
            price=Decimal('1.0'),
            is_buy=True
        )

    def test_position_accumulation(self, risk_manager, symbol):
        """Test position accumulation checks"""
        risk_manager.set_limits(
            symbol=symbol,
            max_position=Decimal('1000'),
            max_order_size=Decimal('100'),
            min_spread=Decimal('0.001')
        )
        
        # Set initial balances to allow accumulation
        risk_manager.wallet_manager.update_balance('USDT', Decimal('20000'))
        risk_manager.wallet_manager.update_balance('SZAR', Decimal('20000'))  # Balanced initial state
        
        accumulated_position = Decimal('0')
        for i in range(9):  # Try to accumulate beyond limit
            current_order = Decimal('100')
            if accumulated_position + current_order > Decimal('1000'):
                # Should reject order that would exceed position limit
                assert not risk_manager.check_order(
                    symbol=symbol,
                    amount=current_order,
                    price=Decimal('1.0'),
                    is_buy=True
                )
                break
            
            # Should accept order within limits
            assert risk_manager.check_order(
                symbol=symbol,
                amount=current_order,
                price=Decimal('1.0'),
                is_buy=True
            )
            
            # Update position and balances
            risk_manager.position_tracker.update_position(
                symbol=symbol,
                amount=current_order,
                price=Decimal('1.0'),
                is_buy=True
            )
            accumulated_position += current_order
            
            # Update balances
            current_usdt = risk_manager.wallet_manager.get_available_balance('USDT')
            current_szar = risk_manager.wallet_manager.get_available_balance('SZAR')
            risk_manager.wallet_manager.update_balance('USDT', current_usdt - current_order)
            risk_manager.wallet_manager.update_balance('SZAR', current_szar + current_order) 