import pytest
from decimal import Decimal
import time
import hmac
import hashlib
import base64
from unittest.mock import AsyncMock, MagicMock
from sense.reward_manager import RewardManager

@pytest.fixture
def wallet_manager():
    manager = AsyncMock()
    manager.send_reward = AsyncMock(return_value="tx_hash_123")
    return manager

@pytest.fixture
def secret_key():
    return "test_secret_key_123"

@pytest.fixture
def reward_manager(wallet_manager, secret_key):
    return RewardManager(wallet_manager, secret_key)

@pytest.fixture
def reward_data():
    return {
        'agent_address': 'kaspa:test123',
        'intel_id': 'test_intel_123',
        'accuracy': Decimal('0.85'),
        'impact_score': Decimal('1.2')
    }

class TestRewardManager:
    @pytest.mark.asyncio
    async def test_successful_reward_processing(self, reward_manager, reward_data):
        result = await reward_manager.process_reward(**reward_data)
        
        assert result is not None
        assert 'reward_amount' in result
        assert 'reward_token' in result
        assert 'tx_hash' in result
        assert result['accuracy_score'] == reward_data['accuracy']
        assert result['impact_score'] == reward_data['impact_score']
        
        # Verify reward calculation
        base_reward = reward_manager.reward_config['base_reward']
        accuracy_bonus = reward_data['accuracy'] * reward_manager.reward_config['accuracy_multiplier']
        impact_bonus = reward_data['impact_score'] * reward_manager.reward_config['impact_multiplier']
        expected_reward = base_reward + accuracy_bonus + impact_bonus
        
        assert result['reward_amount'] == expected_reward

    @pytest.mark.asyncio
    async def test_below_accuracy_threshold(self, reward_manager, reward_data):
        # Set accuracy below threshold
        reward_data['accuracy'] = Decimal('0.5')  # Below min_accuracy_threshold
        
        result = await reward_manager.process_reward(**reward_data)
        assert result is None

    @pytest.mark.asyncio
    async def test_payment_failure(self, reward_manager, reward_data, wallet_manager):
        # Mock payment failure
        wallet_manager.send_reward.return_value = None
        
        result = await reward_manager.process_reward(**reward_data)
        assert result is None

    @pytest.mark.asyncio
    async def test_reward_token_validation(self, reward_manager, reward_data):
        result = await reward_manager.process_reward(**reward_data)
        assert result is not None
        
        # Verify token structure
        token = result['reward_token']
        payload_b64, signature = token.split('.')
        
        # Decode payload
        payload = base64.b64decode(payload_b64)  # Keep as bytes for HMAC
        payload_str = payload.decode()  # Decode for string operations
        payload_parts = payload_str.split('|')  # Using | as separator
        
        # Verify payload structure (agent_id|intel_id|accuracy|impact|reward|timestamp|expiry)
        assert len(payload_parts) == 7
        assert payload_parts[0] == reward_data['agent_address']
        assert payload_parts[1] == reward_data['intel_id']
        assert Decimal(payload_parts[2]) == reward_data['accuracy']
        assert Decimal(payload_parts[3]) == reward_data['impact_score']
        assert Decimal(payload_parts[4]) == result['reward_amount']
        
        # Verify timestamp and expiry are integers
        timestamp = int(payload_parts[5])
        expiry = int(payload_parts[6])
        assert expiry - timestamp == 86400  # 24 hours
        
        # Verify signature using original payload bytes
        h = hmac.new(reward_manager.secret_key, payload, hashlib.sha256)
        expected_signature = base64.b64encode(h.digest()).decode()
        assert signature == expected_signature

    @pytest.mark.asyncio
    async def test_reward_calculation(self, reward_manager, reward_data):
        # Test different accuracy and impact combinations
        test_cases = [
            (Decimal('0.9'), Decimal('1.5')),  # High accuracy, high impact
            (Decimal('0.8'), Decimal('1.0')),  # Medium accuracy, medium impact
            (Decimal('0.7'), Decimal('0.5'))   # Low accuracy, low impact
        ]
        
        for accuracy, impact in test_cases:
            reward_data['accuracy'] = accuracy
            reward_data['impact_score'] = impact
            
            result = await reward_manager.process_reward(**reward_data)
            assert result is not None
            
            # Calculate expected reward
            base_reward = reward_manager.reward_config['base_reward']
            accuracy_bonus = accuracy * reward_manager.reward_config['accuracy_multiplier']
            impact_bonus = impact * reward_manager.reward_config['impact_multiplier']
            expected_reward = base_reward + accuracy_bonus + impact_bonus
            
            assert result['reward_amount'] == expected_reward

    @pytest.mark.asyncio
    async def test_error_handling(self, reward_manager, reward_data):
        # Test with invalid data types
        invalid_data = {
            **reward_data,
            'accuracy': 'not_a_decimal'  # Invalid type
        }
        
        result = await reward_manager.process_reward(**invalid_data)
        assert result is None

    @pytest.mark.asyncio
    async def test_token_expiry(self, reward_manager, reward_data):
        result = await reward_manager.process_reward(**reward_data)
        assert result is not None
        
        # Verify token structure and expiry
        token = result['reward_token']
        payload_b64, _ = token.split('.')
        
        # Decode payload
        payload = base64.b64decode(payload_b64).decode()
        payload_parts = payload.split('|')  # Using | as separator
        
        # Verify timestamp and expiry
        timestamp = int(payload_parts[5])
        expiry = int(payload_parts[6])
        assert expiry - timestamp == 86400  # 24 hours 