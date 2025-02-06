import json
import hmac
import hashlib
import base64
from decimal import Decimal
from typing import Dict, Optional
from utils.logger import setup_logger

logger = setup_logger("wallet_manager")

class WalletManager:
    def __init__(self):
        self.balances: Dict[str, Decimal] = {
            'KAS': Decimal('0'),
            'USDC': Decimal('0'),
            'SZAR': Decimal('0')
        }
        self.reserved_balances: Dict[str, Decimal] = {
            'KAS': Decimal('0'),
            'USDC': Decimal('0'),
            'SZAR': Decimal('0')
        }
        self.min_kas_reserve = Decimal('1.0')  # Minimum KAS for gas
        self.logger = logger
        
    def update_balance(self, asset: str, amount: Decimal):
        """Update balance for an asset"""
        if asset not in self.balances:
            self.balances[asset] = Decimal('0')
        self.balances[asset] = amount
        self.logger.info(f"Balance updated for {asset}: {amount}")
        
    def get_available_balance(self, asset: str) -> Decimal:
        """Get available balance (total - reserved)"""
        return self.balances.get(asset, Decimal('0')) - self.reserved_balances.get(asset, Decimal('0'))
        
    def reserve_balance(self, asset: str, amount: Decimal) -> bool:
        """Reserve balance for pending orders"""
        available = self.get_available_balance(asset)
        if available >= amount:
            self.reserved_balances[asset] = self.reserved_balances.get(asset, Decimal('0')) + amount
            self.logger.info(f"Reserved {amount} {asset}")
            return True
        return False
        
    def release_reserved_balance(self, asset: str, amount: Decimal):
        """Release reserved balance"""
        self.reserved_balances[asset] = max(
            Decimal('0'),
            self.reserved_balances.get(asset, Decimal('0')) - amount
        )
        self.logger.info(f"Released {amount} {asset} from reserved balance")
        
    def can_place_order(self, side: int, symbol: str, amount: Decimal, price: Decimal) -> bool:
        """Check if order can be placed based on available balance"""
        base_asset, quote_asset = symbol.split('-')
        
        if side == 1:  # Buy
            required_quote = amount * price
            return (self.get_available_balance(quote_asset) >= required_quote and 
                   self.get_available_balance('KAS') >= self.min_kas_reserve)
        else:  # Sell
            return (self.get_available_balance(base_asset) >= amount and 
                   self.get_available_balance('KAS') >= self.min_kas_reserve) 