import pytest
from decimal import Decimal
import time
from unittest.mock import AsyncMock, MagicMock
from sense.knowledge_processor import KnowledgeProcessor, MarketKnowledge

@pytest.fixture
def position_tracker():
    tracker = MagicMock()
    tracker.get_position = MagicMock(return_value=Decimal('0'))
    return tracker

@pytest.fixture
def risk_manager():
    manager = MagicMock()
    manager.get_limits = MagicMock(return_value={'max_position': Decimal('1000')})
    manager.set_limits = AsyncMock()
    manager.update_dynamic_limits = AsyncMock()
    return manager

@pytest.fixture
def knowledge_processor(position_tracker, risk_manager):
    return KnowledgeProcessor(position_tracker, risk_manager)

@pytest.fixture
def valid_knowledge():
    return MarketKnowledge(
        agent_id="test_agent",
        timestamp=int(time.time()),
        symbol="KAS/USD",
        prediction_type="price_movement",
        time_horizon=3600,  # 1 hour
        confidence=Decimal('0.8'),
        predicted_value=Decimal('1.2'),  # 20% increase predicted
        supporting_data={"analysis": "technical"}
    )

class TestKnowledgeProcessor:
    @pytest.mark.asyncio
    async def test_process_valid_knowledge(self, knowledge_processor, valid_knowledge):
        result = await knowledge_processor.process_knowledge(valid_knowledge)
        
        assert result['status'] == 'accepted'
        assert 'knowledge_id' in result
        assert 'impact_score' in result
        assert result['evaluation_time'] == valid_knowledge.timestamp + valid_knowledge.time_horizon
        assert valid_knowledge.agent_id in knowledge_processor.knowledge_history

    @pytest.mark.asyncio
    async def test_process_invalid_knowledge(self, knowledge_processor):
        invalid_knowledge = MarketKnowledge(
            agent_id="",  # Invalid: empty agent_id
            timestamp=int(time.time()),
            symbol="KAS/USD",
            prediction_type="invalid_type",  # Invalid prediction type
            time_horizon=3600,
            confidence=Decimal('2.0'),  # Invalid: confidence > 1
            predicted_value=Decimal('-1'),  # Invalid: negative value
            supporting_data={}
        )
        
        result = await knowledge_processor.process_knowledge(invalid_knowledge)
        assert result['status'] == 'rejected'
        assert result['reason'] == 'invalid_data'
        assert invalid_knowledge.agent_id not in knowledge_processor.knowledge_history

    @pytest.mark.asyncio
    async def test_price_movement_impact(self, knowledge_processor, valid_knowledge, position_tracker):
        # Test long position impact
        position_tracker.get_position.return_value = Decimal('100')
        result = await knowledge_processor.process_knowledge(valid_knowledge)
        assert result['status'] == 'accepted'
        assert Decimal(result['impact_score']) < valid_knowledge.confidence

        # Test short position impact
        position_tracker.get_position.return_value = Decimal('-100')
        result = await knowledge_processor.process_knowledge(valid_knowledge)
        assert result['status'] == 'accepted'
        assert Decimal(result['impact_score']) > valid_knowledge.confidence

    @pytest.mark.asyncio
    async def test_volatility_impact(self, knowledge_processor, valid_knowledge):
        # Test high volatility prediction
        valid_knowledge.prediction_type = 'volatility'
        valid_knowledge.predicted_value = Decimal('0.8')  # High volatility
        
        result = await knowledge_processor.process_knowledge(valid_knowledge)
        assert result['status'] == 'accepted'
        assert Decimal(result['impact_score']) > Decimal('0')

    @pytest.mark.asyncio
    async def test_historical_tracking(self, knowledge_processor, valid_knowledge):
        # Process first prediction
        result1 = await knowledge_processor.process_knowledge(valid_knowledge)
        assert result1['status'] == 'accepted'

        # Create new prediction with different timestamp
        new_knowledge = MarketKnowledge(
            agent_id=valid_knowledge.agent_id,
            timestamp=valid_knowledge.timestamp + 3600,
            symbol=valid_knowledge.symbol,
            prediction_type=valid_knowledge.prediction_type,
            time_horizon=valid_knowledge.time_horizon,
            confidence=valid_knowledge.confidence,
            predicted_value=valid_knowledge.predicted_value,
            supporting_data=dict(valid_knowledge.supporting_data)
        )

        # Process second prediction
        result2 = await knowledge_processor.process_knowledge(new_knowledge)
        assert result2['status'] == 'accepted'

        # Verify history
        history = knowledge_processor.knowledge_history[valid_knowledge.agent_id]
        assert len(history) == 2
        assert history[0].timestamp < history[1].timestamp
        
        # Verify they are different objects
        assert id(history[0]) != id(history[1])
        assert history[0].timestamp == valid_knowledge.timestamp
        assert history[1].timestamp == valid_knowledge.timestamp + 3600 