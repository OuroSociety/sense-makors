from decimal import Decimal
from typing import Optional, Dict
from utils.logger import setup_logger
from trading.position_tracker import PositionTracker

logger = setup_logger("risk_manager")

class RiskManager:
    def __init__(self, position_tracker: PositionTracker):
        self.position_tracker = position_tracker
        self.max_position_size: Dict[str, Decimal] = {}
        self.max_drawdown: Dict[str, Decimal] = {}
        self.logger = logger
        
    def set_limits(self, symbol: str, max_position: Decimal, max_drawdown: Decimal):
        """Set risk limits for a symbol"""
        self.max_position_size[symbol] = max_position
        self.max_drawdown[symbol] = max_drawdown
        self.logger.info(f"Risk limits set for {symbol}: max_position={max_position}, max_drawdown={max_drawdown}")
        
    def check_order(self, symbol: str, amount: Decimal, price: Decimal, is_buy: bool) -> bool:
        """Check if an order meets risk management criteria"""
        current_position = self.position_tracker.get_position(symbol)
        new_position = current_position + (amount if is_buy else -amount)
        
        # Check position limits
        max_position = self.max_position_size.get(symbol)
        if max_position and abs(new_position) > max_position:
            self.logger.warning(f"Order rejected: Position size {new_position} would exceed limit {max_position}")
            return False
            
        return True 