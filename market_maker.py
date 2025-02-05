from typing import Dict, List, Optional
import time
from decimal import Decimal
from api_client import FameexClient
from config import (
    SYMBOL, ORDER_BOOK_DEPTH, SPREAD_PERCENTAGE,
    MIN_ORDER_SIZE, MAX_ORDER_SIZE
)
from trading.position_tracker import PositionTracker
from trading.risk_manager import RiskManager
from utils.logger import setup_logger

logger = setup_logger("market_maker")

class MarketMaker:
    def __init__(self, client: FameexClient):
        self.client = client
        self.active_orders: Dict[str, Dict] = {}
        self.position_tracker = PositionTracker()
        self.risk_manager = RiskManager(self.position_tracker)
        self.logger = logger
        
        # Set initial risk limits
        self.risk_manager.set_limits(
            SYMBOL,
            max_position=Decimal('1000'),  # Adjust these values
            max_drawdown=Decimal('100')
        )
        
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
            
            # Calculate our spread
            mid_price = (best_bid + best_ask) / 2
            spread = mid_price * Decimal(SPREAD_PERCENTAGE)
            
            # Calculate our order prices
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
            
            return orders
            
        except Exception as e:
            self.logger.error(f"Error calculating orders: {str(e)}", exc_info=True)
            return []
        
    def run(self):
        """Main market making loop"""
        while True:
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
                        
                # Sleep to respect rate limits
                time.sleep(0.1)  # Adjust as needed
                
            except Exception as e:
                print(f"Error in market making loop: {e}")
                time.sleep(1) 