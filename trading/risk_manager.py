from decimal import Decimal
from typing import Optional, Dict
from utils.logger import setup_logger
from trading.position_tracker import PositionTracker
from trading.wallet_manager import WalletManager

logger = setup_logger("risk_manager")

class RiskManager:
    def __init__(self, position_tracker: PositionTracker, wallet_manager: WalletManager):
        self.position_tracker = position_tracker
        self.wallet_manager = wallet_manager
        self.max_position_size: Dict[str, Decimal] = {}
        self.max_drawdown: Dict[str, Decimal] = {}
        self.min_spread: Dict[str, Decimal] = {}
        self.target_balance_ratio: Dict[str, Decimal] = {}
        self.logger = logger
        
    def set_limits(self, symbol: str, max_position: Decimal, max_drawdown: Decimal, 
                  min_spread: Decimal, target_ratio: Decimal = Decimal('1.0')):
        """
        Set risk limits for a symbol
        target_ratio: target ratio of base asset to quote asset value (e.g., 1.0 for equal value)
        """
        self.max_position_size[symbol] = max_position
        self.max_drawdown[symbol] = max_drawdown
        self.min_spread[symbol] = min_spread
        self.target_balance_ratio[symbol] = target_ratio
        self.logger.info(f"Risk limits set for {symbol}: max_position={max_position}, "
                        f"max_drawdown={max_drawdown}, min_spread={min_spread}, "
                        f"target_ratio={target_ratio}")

    def get_dynamic_position_limit(self, symbol: str, price: Decimal) -> Decimal:
        """Calculate dynamic position limit based on current portfolio value"""
        base_asset, quote_asset = symbol.split('-')
        
        # Get total portfolio value in quote asset
        base_balance = self.wallet_manager.get_available_balance(base_asset)
        quote_balance = self.wallet_manager.get_available_balance(quote_asset)
        total_value_in_quote = (base_balance * price) + quote_balance
        
        # Adjust max position based on total portfolio value
        # Use a percentage of total portfolio value (e.g., 20%)
        return total_value_in_quote * Decimal('0.20')

    def get_recommended_spread(self, symbol: str, market_volatility: Decimal) -> Decimal:
        """Calculate recommended spread based on market conditions"""
        base_spread = self.min_spread[symbol]
        
        # Increase spread with volatility
        volatility_adjustment = market_volatility * Decimal('2.0')
        
        # Increase spread if position is imbalanced
        imbalance_factor = self.calculate_position_imbalance(symbol)
        imbalance_adjustment = base_spread * imbalance_factor
        
        return max(base_spread, base_spread + volatility_adjustment + imbalance_adjustment)

    def calculate_position_imbalance(self, symbol: str) -> Decimal:
        """Calculate how far current position is from target ratio"""
        base_asset, quote_asset = symbol.split('-')
        current_position = self.position_tracker.get_position(symbol)
        target_ratio = self.target_balance_ratio[symbol]
        
        base_balance = self.wallet_manager.get_available_balance(base_asset)
        quote_balance = self.wallet_manager.get_available_balance(quote_asset)
        
        if quote_balance == 0:
            return Decimal('1.0')
            
        current_ratio = base_balance / quote_balance
        imbalance = abs(current_ratio - target_ratio) / target_ratio
        return Decimal('1.0') + imbalance

    def check_order(self, symbol: str, amount: Decimal, price: Decimal, is_buy: bool) -> bool:
        """Check if an order meets risk management criteria"""
        current_position = self.position_tracker.get_position(symbol)
        new_position = current_position + (amount if is_buy else -amount)
        
        # Get dynamic position limit
        dynamic_limit = self.get_dynamic_position_limit(symbol, price)
        max_position = min(self.max_position_size[symbol], dynamic_limit)
        
        # Check position limits
        if abs(new_position) > max_position:
            self.logger.warning(f"Order rejected: Position size {new_position} would exceed limit {max_position}")
            return False
            
        # Check if order would improve balance ratio
        if not self._improves_balance_ratio(symbol, amount, price, is_buy):
            self.logger.warning("Order rejected: Would worsen asset balance ratio")
            return False
            
        return True
        
    def _improves_balance_ratio(self, symbol: str, amount: Decimal, price: Decimal, is_buy: bool) -> bool:
        """Check if order would move us closer to target balance ratio"""
        base_asset, quote_asset = symbol.split('-')
        target_ratio = self.target_balance_ratio[symbol]
        
        base_balance = self.wallet_manager.get_available_balance(base_asset)
        quote_balance = self.wallet_manager.get_available_balance(quote_asset)
        
        # Calculate current ratio
        current_ratio = base_balance / quote_balance if quote_balance else Decimal('inf')
        
        # Calculate new balances after trade
        quote_delta = amount * price
        if is_buy:
            new_base = base_balance + amount
            new_quote = quote_balance - quote_delta
        else:
            new_base = base_balance - amount
            new_quote = quote_balance + quote_delta
            
        # Calculate new ratio
        new_ratio = new_base / new_quote if new_quote else Decimal('inf')
        
        # Check if new ratio is closer to target
        current_diff = abs(current_ratio - target_ratio)
        new_diff = abs(new_ratio - target_ratio)
        
        # Allow some tolerance for small deviations
        tolerance = Decimal('0.1')
        return new_diff <= current_diff * (1 + tolerance) 