import pytest
from decimal import Decimal
from trading.wallet_manager import WalletManager

class TestWalletManager:
    @pytest.fixture
    def wallet_manager(self):
        return WalletManager()
        
    def test_balance_reservation(self, wallet_manager):
        # Setup
        wallet_manager.update_balance('KAS', Decimal('100'))
        
        # Test reserve
        assert wallet_manager.reserve_balance('KAS', Decimal('50'))
        assert wallet_manager.get_available_balance('KAS') == Decimal('50')
        
        # Test release
        wallet_manager.release_reserved_balance('KAS', Decimal('30'))
        assert wallet_manager.get_available_balance('KAS') == Decimal('80')
        
    def test_order_placement_checks(self, wallet_manager):
        # Setup
        wallet_manager.update_balance('KAS', Decimal('100'))
        wallet_manager.update_balance('USDC', Decimal('1000'))
        
        # Test buy order
        assert wallet_manager.can_place_order(
            1, 'KAS-USDC',
            Decimal('10'),  # amount
            Decimal('50')   # price
        )
        
        # Test insufficient balance
        assert not wallet_manager.can_place_order(
            1, 'KAS-USDC',
            Decimal('100'),
            Decimal('50')
        ) 