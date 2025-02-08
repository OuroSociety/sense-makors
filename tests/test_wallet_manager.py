import pytest
from decimal import Decimal
from trading.wallet_manager import WalletManager

class TestWalletManager:
    @pytest.fixture
    def wallet_manager(self):
        """Create a fresh wallet manager for each test"""
        return WalletManager()
        
    def test_initial_balances(self, wallet_manager):
        """Test initial wallet balances"""
        # Check default assets
        assert wallet_manager.get_available_balance('KAS') == Decimal('0')
        assert wallet_manager.get_available_balance('USDC') == Decimal('0')
        assert wallet_manager.get_available_balance('SZAR') == Decimal('0')
        
        # Check non-existent asset
        assert wallet_manager.get_available_balance('NONEXISTENT') == Decimal('0')
        
    def test_balance_updates(self, wallet_manager):
        """Test basic balance updates"""
        # Update KAS balance
        wallet_manager.update_balance('KAS', Decimal('100'))
        assert wallet_manager.get_available_balance('KAS') == Decimal('100')
        
        # Update again
        wallet_manager.update_balance('KAS', Decimal('150'))
        assert wallet_manager.get_available_balance('KAS') == Decimal('150')
        
        # Update new asset
        wallet_manager.update_balance('ETH', Decimal('10'))
        assert wallet_manager.get_available_balance('ETH') == Decimal('10')
        
    def test_balance_reservation(self, wallet_manager):
        """Test balance reservation functionality"""
        # Setup initial balance
        wallet_manager.update_balance('USDC', Decimal('1000'))
        
        # Test successful reservation
        assert wallet_manager.reserve_balance('USDC', Decimal('500'))
        assert wallet_manager.get_available_balance('USDC') == Decimal('500')
        
        # Test reservation with insufficient balance
        assert not wallet_manager.reserve_balance('USDC', Decimal('600'))
        assert wallet_manager.get_available_balance('USDC') == Decimal('500')
        
        # Release partial reservation
        wallet_manager.release_reserved_balance('USDC', Decimal('200'))
        assert wallet_manager.get_available_balance('USDC') == Decimal('700')
        
        # Release remaining reservation
        wallet_manager.release_reserved_balance('USDC', Decimal('300'))
        assert wallet_manager.get_available_balance('USDC') == Decimal('1000')
        
    def test_order_placement_checks(self, wallet_manager):
        """Test order placement balance checks"""
        # Setup initial balances
        wallet_manager.update_balance('KAS', Decimal('10'))  # For gas
        wallet_manager.update_balance('SZAR', Decimal('1000'))
        wallet_manager.update_balance('USDT', Decimal('10000'))
        
        # Test buy order
        assert wallet_manager.can_place_order(
            side=1,  # Buy
            symbol='SZAR-USDT',
            amount=Decimal('100'),
            price=Decimal('1.0')
        )
        
        # Test sell order
        assert wallet_manager.can_place_order(
            side=2,  # Sell
            symbol='SZAR-USDT',
            amount=Decimal('100'),
            price=Decimal('1.0')
        )
        
        # Test insufficient quote balance for buy
        assert not wallet_manager.can_place_order(
            side=1,
            symbol='SZAR-USDT',
            amount=Decimal('20000'),
            price=Decimal('1.0')
        )
        
        # Test insufficient base balance for sell
        assert not wallet_manager.can_place_order(
            side=2,
            symbol='SZAR-USDT',
            amount=Decimal('2000'),
            price=Decimal('1.0')
        )
        
    def test_insufficient_gas_checks(self, wallet_manager):
        """Test gas balance requirements"""
        # Setup balances without KAS
        wallet_manager.update_balance('SZAR', Decimal('1000'))
        wallet_manager.update_balance('USDT', Decimal('10000'))
        
        # Should fail due to insufficient KAS
        assert not wallet_manager.can_place_order(
            side=1,
            symbol='SZAR-USDT',
            amount=Decimal('100'),
            price=Decimal('1.0')
        )
        
        # Add minimum KAS
        wallet_manager.update_balance('KAS', wallet_manager.min_kas_reserve)
        
        # Should now succeed
        assert wallet_manager.can_place_order(
            side=1,
            symbol='SZAR-USDT',
            amount=Decimal('100'),
            price=Decimal('1.0')
        )
        
    def test_balance_precision(self, wallet_manager):
        """Test balance handling with different decimal precisions"""
        # Test small amounts
        wallet_manager.update_balance('USDT', Decimal('0.00000001'))
        assert wallet_manager.get_available_balance('USDT') == Decimal('0.00000001')
        
        # Test large amounts
        wallet_manager.update_balance('SZAR', Decimal('1000000.00000000'))
        assert wallet_manager.get_available_balance('SZAR') == Decimal('1000000.00000000')
        
    def test_multiple_reservations(self, wallet_manager):
        """Test multiple concurrent reservations"""
        wallet_manager.update_balance('USDT', Decimal('1000'))
        
        # Make multiple reservations
        assert wallet_manager.reserve_balance('USDT', Decimal('200'))
        assert wallet_manager.reserve_balance('USDT', Decimal('300'))
        assert wallet_manager.get_available_balance('USDT') == Decimal('500')
        
        # Release in different order
        wallet_manager.release_reserved_balance('USDT', Decimal('300'))
        assert wallet_manager.get_available_balance('USDT') == Decimal('800')
        wallet_manager.release_reserved_balance('USDT', Decimal('200'))
        assert wallet_manager.get_available_balance('USDT') == Decimal('1000')
        
    def test_negative_balance_prevention(self, wallet_manager):
        """Test prevention of negative balances"""
        wallet_manager.update_balance('USDT', Decimal('100'))
        
        # Try to reserve more than available
        assert not wallet_manager.reserve_balance('USDT', Decimal('150'))
        assert wallet_manager.get_available_balance('USDT') == Decimal('100')
        
        # Try to release more than reserved
        wallet_manager.reserve_balance('USDT', Decimal('50'))
        wallet_manager.release_reserved_balance('USDT', Decimal('100'))
        assert wallet_manager.get_available_balance('USDT') == Decimal('100') 