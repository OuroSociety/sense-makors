from dataclasses import dataclass
from typing import Dict, List, Optional
from decimal import Decimal
import time
import json
from utils.logger import setup_logger

logger = setup_logger("knowledge_processor")

@dataclass
class MarketKnowledge:
    agent_id: str
    timestamp: int
    symbol: str
    prediction_type: str  # 'price_movement', 'volatility', 'liquidity'
    time_horizon: int  # in seconds
    confidence: Decimal
    predicted_value: Decimal
    supporting_data: Dict
    
    def to_dict(self) -> Dict:
        return {
            'agent_id': self.agent_id,
            'timestamp': self.timestamp,
            'symbol': self.symbol,
            'prediction_type': self.prediction_type,
            'time_horizon': self.time_horizon,
            'confidence': str(self.confidence),
            'predicted_value': str(self.predicted_value),
            'supporting_data': self.supporting_data
        }

class KnowledgeProcessor:
    def __init__(self, position_tracker, risk_manager):
        self.position_tracker = position_tracker
        self.risk_manager = risk_manager
        self.knowledge_history: Dict[str, List[MarketKnowledge]] = {}
        self.agent_performance: Dict[str, Decimal] = {}
        self.logger = logger
        
    def _validate_knowledge(self, knowledge: MarketKnowledge) -> bool:
        """Validate knowledge data"""
        try:
            if not all([
                knowledge.agent_id,
                knowledge.timestamp > 0,
                knowledge.symbol,
                knowledge.prediction_type in ['price_movement', 'volatility', 'liquidity'],
                knowledge.time_horizon > 0,
                0 <= knowledge.confidence <= 1,
                knowledge.predicted_value > 0
            ]):
                return False
            return True
        except Exception:
            return False
            
    async def _update_risk_parameters(self, knowledge: MarketKnowledge) -> Decimal:
        """Update risk parameters based on knowledge"""
        impact_score = Decimal('0')
        
        try:
            if knowledge.prediction_type == 'price_movement':
                impact_score = await self._handle_price_movement(knowledge)
            elif knowledge.prediction_type == 'volatility':
                impact_score = await self._handle_volatility(knowledge)
            elif knowledge.prediction_type == 'liquidity':
                impact_score = await self._handle_liquidity(knowledge)
                
        except Exception as e:
            self.logger.error(f"Failed to update risk parameters: {str(e)}")
            
        return impact_score
        
    async def _handle_price_movement(self, knowledge: MarketKnowledge) -> Decimal:
        """Handle price movement predictions"""
        try:
            # Get current position
            current_position = self.position_tracker.get_position(knowledge.symbol)
            
            # Calculate impact score based on prediction confidence and size
            impact = Decimal('0')
            
            # If predicting price increase
            if knowledge.predicted_value > 1:
                # Increase impact if we're short
                if current_position < 0:
                    impact = knowledge.confidence * Decimal('2.0')
                # Smaller impact if we're already long
                elif current_position > 0:
                    impact = knowledge.confidence * Decimal('0.5')
                else:
                    impact = knowledge.confidence
                    
            # If predicting price decrease
            else:
                # Increase impact if we're long
                if current_position > 0:
                    impact = knowledge.confidence * Decimal('2.0')
                # Smaller impact if we're already short
                elif current_position < 0:
                    impact = knowledge.confidence * Decimal('0.5')
                else:
                    impact = knowledge.confidence
                    
            # Update risk parameters
            await self.risk_manager.update_dynamic_limits(
                symbol=knowledge.symbol,
                confidence=knowledge.confidence,
                predicted_move=knowledge.predicted_value
            )
            
            return impact
            
        except Exception as e:
            self.logger.error(f"Failed to handle price movement: {str(e)}")
            return Decimal('0')
            
    async def _handle_volatility(self, knowledge: MarketKnowledge) -> Decimal:
        """Handle volatility predictions"""
        try:
            # Update position limits based on predicted volatility
            current_limits = self.risk_manager.get_limits(knowledge.symbol)
            
            # If high volatility predicted, reduce position limits
            if knowledge.predicted_value > Decimal('0.5'):
                new_limit = current_limits['max_position'] * Decimal('0.7')
                await self.risk_manager.set_limits(
                    symbol=knowledge.symbol,
                    max_position=new_limit
                )
                return knowledge.confidence * Decimal('1.5')
                
            # If low volatility predicted, can increase limits
            else:
                new_limit = current_limits['max_position'] * Decimal('1.2')
                await self.risk_manager.set_limits(
                    symbol=knowledge.symbol,
                    max_position=new_limit
                )
                return knowledge.confidence
                
        except Exception as e:
            self.logger.error(f"Failed to handle volatility: {str(e)}")
            return Decimal('0')
            
    async def _handle_liquidity(self, knowledge: MarketKnowledge) -> Decimal:
        """Handle liquidity predictions"""
        try:
            # Update position limits based on predicted liquidity
            current_limits = self.risk_manager.get_limits(knowledge.symbol)
            
            # If high liquidity predicted, can increase limits
            if knowledge.predicted_value > Decimal('0.5'):
                new_limit = current_limits['max_position'] * Decimal('1.3')
                await self.risk_manager.set_limits(
                    symbol=knowledge.symbol,
                    max_position=new_limit
                )
                return knowledge.confidence * Decimal('1.2')
                
            # If low liquidity predicted, reduce limits
            else:
                new_limit = current_limits['max_position'] * Decimal('0.6')
                await self.risk_manager.set_limits(
                    symbol=knowledge.symbol,
                    max_position=new_limit
                )
                return knowledge.confidence * Decimal('0.8')
                
        except Exception as e:
            self.logger.error(f"Failed to handle liquidity: {str(e)}")
            return Decimal('0')

    async def process_knowledge(self, knowledge: MarketKnowledge) -> Dict:
        """Process and score market knowledge"""
        try:
            if not self._validate_knowledge(knowledge):
                return {'status': 'rejected', 'reason': 'invalid_data'}
                
            # Store knowledge (create a new instance to avoid reference issues)
            if knowledge.agent_id not in self.knowledge_history:
                self.knowledge_history[knowledge.agent_id] = []
            
            # Create a new instance of MarketKnowledge
            stored_knowledge = MarketKnowledge(
                agent_id=knowledge.agent_id,
                timestamp=knowledge.timestamp,
                symbol=knowledge.symbol,
                prediction_type=knowledge.prediction_type,
                time_horizon=knowledge.time_horizon,
                confidence=knowledge.confidence,
                predicted_value=knowledge.predicted_value,
                supporting_data=dict(knowledge.supporting_data)
            )
            self.knowledge_history[knowledge.agent_id].append(stored_knowledge)
            
            # Update risk parameters based on knowledge
            impact_score = await self._update_risk_parameters(knowledge)
            
            knowledge_id = f"{knowledge.agent_id}_{knowledge.timestamp}"
            
            self.logger.info(f"Processed knowledge {knowledge_id} with impact {impact_score}")
            
            return {
                'status': 'accepted',
                'knowledge_id': knowledge_id,
                'impact_score': impact_score,
                'evaluation_time': knowledge.timestamp + knowledge.time_horizon
            }
            
        except Exception as e:
            self.logger.error(f"Failed to process knowledge: {str(e)}")
            return {'status': 'error', 'reason': str(e)} 