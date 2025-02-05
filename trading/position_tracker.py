from typing import Dict, Optional
from decimal import Decimal
import json
from utils.logger import setup_logger

logger = setup_logger("position_tracker")

class PositionTracker:
    def __init__(self):
        self.positions: Dict[str, Decimal] = {}
        self.trades: list = []
        self.logger = logger
        
    def update_position(self, symbol: str, amount: Decimal, price: Decimal, is_buy: bool):
        """Update position after a trade"""
        if symbol not in self.positions:
            self.positions[symbol] = Decimal('0')
            
        delta = amount if is_buy else -amount
        self.positions[symbol] += delta
        
        trade = {
            'symbol': symbol,
            'amount': str(amount),
            'price': str(price),
            'side': 'buy' if is_buy else 'sell',
            'position_after': str(self.positions[symbol])
        }
        self.trades.append(trade)
        self.logger.info(f"Position updated: {json.dumps(trade)}")
        
    def get_position(self, symbol: str) -> Decimal:
        """Get current position for a symbol"""
        return self.positions.get(symbol, Decimal('0')) 