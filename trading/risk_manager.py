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
        
    def set_limits(self, symbol: str, max_position: Decimal, max_order_size: Decimal, min_spread: Decimal) -> None:
        """Set risk limits for a symbol
        
        Args:
            symbol: Trading pair symbol
            max_position: Maximum allowed position size
            max_order_size: Maximum allowed order size
            min_spread: Minimum required spread between orders
        """
        self.max_position_size[symbol] = max_position
        self.max_drawdown[symbol] = Decimal('1.0')  # Assuming max_drawdown is set to 100%
        self.min_spread[symbol] = min_spread
        self.target_balance_ratio[symbol] = Decimal('1.0')  # Assuming target_ratio is set to 100%
        self.logger.info(f"Risk limits set for {symbol}: max_position={max_position}, "
                        f"max_drawdown={self.max_drawdown[symbol]}, min_spread={min_spread}, "
                        f"target_ratio={self.target_balance_ratio[symbol]}")

    def get_dynamic_position_limit(self, symbol: str, price: Decimal) -> Decimal:
        """Calculate dynamic position limit based on current portfolio value"""
        # Handle both formats: SZARUSDT and SZAR-USDT
        if '-' in symbol:
            base_asset, quote_asset = symbol.split('-')
        else:
            # Extract base and quote assets from combined symbol
            # Assuming common quote assets are USDT, USDC, etc. (3-4 chars)
            quote_asset = symbol[-4:]  # Get last 4 chars for quote asset
            base_asset = symbol[:-4]   # Get remaining chars for base asset
            
            # Handle 3-char quote assets like BTC
            if quote_asset.startswith('U'):
                quote_asset = symbol[-4:]  # USDT, USDC
                base_asset = symbol[:-4]
            else:
                quote_asset = symbol[-3:]  # BTC, ETH
                base_asset = symbol[:-3]
        
        self.logger.debug(f"Split symbol {symbol} into base={base_asset}, quote={quote_asset}")
        
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

    def _improves_balance_ratio(self, symbol: str, amount: Decimal, price: Decimal, is_buy: bool) -> bool:
        """Check if the order improves the balance ratio between assets"""
        # Handle both formats: SZARUSDT and SZAR-USDT
        if '-' in symbol:
            base_asset, quote_asset = symbol.split('-')
        else:
            # Extract base and quote assets from combined symbol
            quote_asset = symbol[-4:]  # Get last 4 chars for quote asset
            base_asset = symbol[:-4]   # Get remaining chars for base asset
            
            # Handle 3-char quote assets like BTC
            if quote_asset.startswith('U'):
                quote_asset = symbol[-4:]  # USDT, USDC
                base_asset = symbol[:-4]
            else:
                quote_asset = symbol[-3:]  # BTC, ETH
                base_asset = symbol[:-3]
        
        self.logger.debug(f"Checking balance ratio for {base_asset}/{quote_asset}")
        
        # Get current balances
        base_balance = self.wallet_manager.get_available_balance(base_asset)
        quote_balance = self.wallet_manager.get_available_balance(quote_asset)
        
        # Calculate current ratio
        current_ratio = (base_balance * price) / quote_balance if quote_balance else Decimal('0')
        target_ratio = self.target_balance_ratio.get(symbol, Decimal('1.0'))
        
        # Calculate new balances after potential trade
        if is_buy:
            new_base_balance = base_balance + amount
            new_quote_balance = quote_balance - (amount * price)
        else:
            new_base_balance = base_balance - amount
            new_quote_balance = quote_balance + (amount * price)
        
        # Calculate new ratio
        new_ratio = (new_base_balance * price) / new_quote_balance if new_quote_balance else Decimal('0')
        
        # Check if new ratio is closer to target
        current_diff = abs(current_ratio - target_ratio)
        new_diff = abs(new_ratio - target_ratio)
        
        self.logger.debug(f"Balance ratios - Current: {current_ratio:.4f}, New: {new_ratio:.4f}, Target: {target_ratio:.4f}")
        
        return new_diff <= current_diff

    def check_order(self, symbol: str, amount: Decimal, price: Decimal, is_buy: bool) -> bool:
        """Check if an order meets all risk criteria"""
        try:
            # Get current position
            current_position = self.position_tracker.get_position(symbol)
            
            # Check position limits
            if is_buy:
                new_position = current_position + amount
            else:
                new_position = current_position - amount
            
            max_allowed = self.max_position_size.get(symbol, Decimal('0'))
            if abs(new_position) > max_allowed:
                self.logger.warning(f"Order would exceed position limit of {max_allowed}")
                return False
            
            # Check dynamic position limit
            dynamic_limit = self.get_dynamic_position_limit(symbol, price)
            if abs(new_position) > dynamic_limit:
                self.logger.warning(f"Order would exceed dynamic position limit of {dynamic_limit}")
                return False
            
            # Check balance ratio improvement
            if not self._improves_balance_ratio(symbol, amount, price, is_buy):
                self.logger.warning("Order would worsen balance ratio")
                return False
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error in risk check: {str(e)}")
            return False 