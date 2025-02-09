from typing import Dict, List, Optional
import time
from decimal import Decimal
from config.base_client import ExchangeClient
from config.config import (
    SYMBOL, ORDER_BOOK_DEPTH, SPREAD_PERCENTAGE,
    MIN_ORDER_SIZE, MAX_ORDER_SIZE
)
from trading.position_tracker import PositionTracker
from trading.risk_manager import RiskManager
from utils.logger import setup_logger
from trading.wallet_manager import WalletManager
import statistics
import uuid
import asyncio

logger = setup_logger("market_maker")

__all__ = ['MarketMaker']

class MarketMaker:
    def __init__(self, client: ExchangeClient):
        self.client = client
        self.active_orders: Dict[str, Dict] = {}
        self.position_tracker = PositionTracker()
        self.wallet_manager = WalletManager()
        self.risk_manager = RiskManager(self.position_tracker, self.wallet_manager)
        self.logger = logger
        self.price_history = []
        self.running = False
        self.job_id = str(uuid.uuid4())
        self.last_update = time.time()
        self.status = "initialized"
        
        # Set initial risk limits with minimum spread
        self.risk_manager.set_limits(
            symbol=SYMBOL,
            max_position=Decimal('1000'),
            max_order_size=Decimal('100'),
            min_spread=Decimal('0.02')
        )
        
    def calculate_volatility(self) -> Decimal:
        """Calculate recent market volatility"""
        if len(self.price_history) < 2:
            return Decimal('0.01')
            
        returns = []
        for i in range(1, len(self.price_history)):
            prev_price = self.price_history[i-1]
            curr_price = self.price_history[i]
            returns.append((curr_price - prev_price) / prev_price)
            
        return Decimal(str(statistics.stdev(returns))) if returns else Decimal('0.01')

    def calculate_new_orders(self, order_book: Dict) -> List[Dict]:
        """Calculate new orders based on the current order book"""
        try:
            if not order_book or 'bids' not in order_book or 'asks' not in order_book:
                self.logger.warning("Invalid order book data")
                return []
                
            bids = order_book['bids']
            asks = order_book['asks']
            
            if not bids or not asks:
                self.logger.warning("Empty order book")
                return []
                
            # Get best bid and ask
            best_bid = Decimal(bids[0][0])
            best_ask = Decimal(asks[0][0])
            
            # Update price history for volatility calculation
            mid_price = (best_bid + best_ask) / 2
            self.price_history.append(float(mid_price))
            if len(self.price_history) > 100:  # Keep last 100 prices
                self.price_history.pop(0)
                
            # Calculate volatility
            volatility = self.calculate_volatility()
            
            # Get recommended spread based on market conditions
            spread_percentage = self.risk_manager.get_recommended_spread(SYMBOL, volatility)
            
            # Calculate our order prices
            spread = mid_price * spread_percentage
            our_bid = mid_price - spread
            our_ask = mid_price + spread
            
            # Generate orders
            orders = []
            
            # Check risk limits for buy order
            if self.risk_manager.check_order(SYMBOL, Decimal(MIN_ORDER_SIZE), our_bid, True):
                orders.append({
                    "symbol": SYMBOL,
                    "side": 1,  # Buy
                    "orderType": 1,  # Limit
                    "price": str(our_bid),
                    "amount": str(MIN_ORDER_SIZE)
                })
            
            # Check risk limits for sell order
            if self.risk_manager.check_order(SYMBOL, Decimal(MIN_ORDER_SIZE), our_ask, False):
                orders.append({
                    "symbol": SYMBOL,
                    "side": 2,  # Sell
                    "orderType": 1,  # Limit
                    "price": str(our_ask),
                    "amount": str(MIN_ORDER_SIZE)
                })
            
            # Check wallet balances before returning orders
            filtered_orders = []
            for order in orders:
                if self.wallet_manager.can_place_order(
                    order["side"],
                    order["symbol"],
                    Decimal(order["amount"]),
                    Decimal(order["price"])
                ):
                    filtered_orders.append(order)
                else:
                    self.logger.warning(f"Insufficient balance for order: {order}")
                    
            return filtered_orders
            
        except Exception as e:
            self.logger.error(f"Error calculating orders: {str(e)}", exc_info=True)
            return []
        
    async def process_agent_intelligence(self, agent_data: Dict) -> Dict:
        """Process intelligence from AI agents"""
        
        # Verify agent on specified chain
        if not await self.agent_verifier.verify_agent(
            address=agent_data['address'],
            signed_message=agent_data['signature'],
            nonce=agent_data['nonce'],
            chain=agent_data['chain']  # 'KASPA' or 'ECASH'
        ):
            return {'status': 'rejected', 'reason': 'verification_failed'}
            
        # Continue with intelligence processing...

    def stop(self):
        """Stop the market maker"""
        self.running = False
        # Cancel all active orders
        for order_id in list(self.active_orders.keys()):
            try:
                self.client.cancel_order(SYMBOL, order_id)
                del self.active_orders[order_id]
            except Exception as e:
                self.logger.error(f"Error canceling order {order_id}: {e}")

    async def run_async(self):
        """Async market making loop"""
        self.running = True
        self.status = "running"
        
        while self.running:
            try:
                # Get current order book
                order_book = self.client.get_order_book(SYMBOL, ORDER_BOOK_DEPTH)
                
                # Calculate and place new orders
                new_orders = self.calculate_new_orders(order_book)
                
                for order in new_orders:
                    result = self.client.place_order(**order)
                    if result and result.get('code') == 200:
                        order_id = result['data']['orderId']
                        self.active_orders[order_id] = order
                
                self.last_update = time.time()
                await asyncio.sleep(0.1)  # Use async sleep
                
            except Exception as e:
                self.logger.error(f"Error in market making loop: {e}")
                self.status = f"error: {str(e)}"
                await asyncio.sleep(1)
    
    def get_status(self) -> Dict:
        """Get current market maker status"""
        return {
            "job_id": self.job_id,
            "running": self.running,
            "status": self.status,
            "last_update": self.last_update,
            "active_orders": len(self.active_orders),
            "spread": str(getattr(self, 'spread', None))
        } 