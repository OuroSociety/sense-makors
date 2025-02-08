import pytest
from decimal import Decimal
from trading.position_tracker import PositionTracker
import json

class TestPositionTracker:
    @pytest.fixture
    def position_tracker(self):
        """Create a fresh position tracker for each test"""
        return PositionTracker()

    @pytest.fixture
    def symbol(self):
        """Test trading pair"""
        return "SZARUSDT"

    def test_initial_position(self, position_tracker, symbol):
        """Test initial position is zero"""
        assert position_tracker.get_position(symbol) == Decimal('0')
        assert len(position_tracker.trades) == 0

    def test_single_buy(self, position_tracker, symbol):
        """Test single buy order tracking"""
        amount = Decimal('100')
        price = Decimal('1.0')
        
        position_tracker.update_position(symbol, amount, price, True)
        
        assert position_tracker.get_position(symbol) == amount
        assert len(position_tracker.trades) == 1
        
        trade = position_tracker.trades[0]
        assert trade['symbol'] == symbol
        assert trade['amount'] == str(amount)
        assert trade['price'] == str(price)
        assert trade['side'] == 'buy'
        assert trade['position_after'] == str(amount)

    def test_single_sell(self, position_tracker, symbol):
        """Test single sell order tracking"""
        amount = Decimal('100')
        price = Decimal('1.0')
        
        position_tracker.update_position(symbol, amount, price, False)
        
        assert position_tracker.get_position(symbol) == -amount
        assert len(position_tracker.trades) == 1
        
        trade = position_tracker.trades[0]
        assert trade['side'] == 'sell'
        assert trade['position_after'] == str(-amount)

    def test_multiple_trades(self, position_tracker, symbol):
        """Test multiple trades tracking"""
        trades = [
            (Decimal('100'), Decimal('1.0'), True),   # Buy 100
            (Decimal('50'), Decimal('1.1'), False),   # Sell 50
            (Decimal('75'), Decimal('0.9'), True),    # Buy 75
            (Decimal('125'), Decimal('1.2'), False),  # Sell 125
        ]
        
        expected_positions = [
            Decimal('100'),    # After first buy
            Decimal('50'),     # After first sell
            Decimal('125'),    # After second buy
            Decimal('0'),      # After final sell
        ]
        
        for i, (amount, price, is_buy) in enumerate(trades):
            position_tracker.update_position(symbol, amount, price, is_buy)
            assert position_tracker.get_position(symbol) == expected_positions[i]
            
        assert len(position_tracker.trades) == len(trades)

    def test_multiple_symbols(self, position_tracker):
        """Test tracking positions for multiple symbols"""
        symbols = ["SZARUSDT", "BTCUSDT", "ETHUSDT"]
        
        # Execute trades for each symbol
        for symbol in symbols:
            position_tracker.update_position(symbol, Decimal('100'), Decimal('1.0'), True)
            position_tracker.update_position(symbol, Decimal('50'), Decimal('1.1'), False)
            
        # Verify positions
        for symbol in symbols:
            assert position_tracker.get_position(symbol) == Decimal('50')
            
        assert len(position_tracker.trades) == len(symbols) * 2

    def test_position_flipping(self, position_tracker, symbol):
        """Test flipping from long to short position"""
        # Build long position
        position_tracker.update_position(symbol, Decimal('100'), Decimal('1.0'), True)
        assert position_tracker.get_position(symbol) > 0
        
        # Flip to short position
        position_tracker.update_position(symbol, Decimal('200'), Decimal('1.1'), False)
        assert position_tracker.get_position(symbol) < 0

    def test_trade_history(self, position_tracker, symbol):
        """Test trade history recording"""
        trades = [
            (Decimal('100'), Decimal('1.0'), True),
            (Decimal('50'), Decimal('1.1'), False),
            (Decimal('75'), Decimal('0.9'), True),
        ]
        
        for amount, price, is_buy in trades:
            position_tracker.update_position(symbol, amount, price, is_buy)
        
        # Verify trade history
        assert len(position_tracker.trades) == len(trades)
        
        # Check if trades are properly serializable
        for trade in position_tracker.trades:
            # Should not raise any JSON encoding errors
            json_str = json.dumps(trade)
            decoded = json.loads(json_str)
            assert all(key in decoded for key in ['symbol', 'amount', 'price', 'side', 'position_after'])

    def test_zero_amount_handling(self, position_tracker, symbol):
        """Test handling of zero amount trades"""
        # Initial position
        position_tracker.update_position(symbol, Decimal('100'), Decimal('1.0'), True)
        initial_position = position_tracker.get_position(symbol)
        initial_trades = len(position_tracker.trades)
        
        # Update with zero amount
        position_tracker.update_position(symbol, Decimal('0'), Decimal('1.0'), True)
        
        # Position should remain unchanged
        assert position_tracker.get_position(symbol) == initial_position
        assert len(position_tracker.trades) == initial_trades + 1  # Trade still recorded 