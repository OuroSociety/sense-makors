import pytest
from decimal import Decimal
import time
from unittest.mock import AsyncMock, patch, MagicMock
from sense.agent_verifier import AgentVerifier

@pytest.fixture
def agent_verifier():
    return AgentVerifier(
        kaspa_api_url="https://api.kaspa.org",
        ecash_api_url="https://chronik.fabien.cash"
    )

@pytest.fixture
def mock_response():
    response = AsyncMock()
    response.status = 200
    response.json = AsyncMock()
    return response

@pytest.fixture
def mock_session():
    session = AsyncMock()
    
    async def mock_get(*args, **kwargs):
        response = AsyncMock()
        response.status = 200
        # Check if it's a balance request
        if '/balance' in args[0] or '/history' in args[0]:
            response.json = AsyncMock(return_value={'balance': '15000'})
        return response
        
    async def mock_post(*args, **kwargs):
        response = AsyncMock()
        response.status = 200
        # Check if it's a verification request
        if '/verify' in args[0]:
            response.json = AsyncMock(return_value={'valid': True})
        return response
    
    session.get = mock_get
    session.post = mock_post
    
    return session

@pytest.fixture
def mock_session_insufficient_balance():
    session = AsyncMock()
    
    async def mock_get(*args, **kwargs):
        response = AsyncMock()
        response.status = 200
        response.json = AsyncMock(return_value={'balance': '100'})
        return response
        
    session.get = mock_get
    return session

@pytest.fixture
def mock_session_invalid_signature():
    session = AsyncMock()
    
    async def mock_get(*args, **kwargs):
        response = AsyncMock()
        response.status = 200
        response.json = AsyncMock(return_value={'balance': '15000'})
        return response
        
    async def mock_post(*args, **kwargs):
        response = AsyncMock()
        response.status = 200
        response.json = AsyncMock(return_value={'valid': False})
        return response
    
    session.get = mock_get
    session.post = mock_post
    
    return session

@pytest.fixture
def kaspa_test_data():
    return {
        'address': 'kaspa:qzrw6gz6t00szzaas2vxe5jxu68zcuaj76304z6kjsgjpnuljvkt5m8fj394l',
        'signed_message': 'test_signature',
        'nonce': '123456',
        'balance': '15000',  # Above minimum requirement
        'chain': 'KASPA'
    }

@pytest.fixture
def ecash_test_data():
    return {
        'address': 'ecash:qrwmvtssu985aqscc4n8efkhyhn39f3pp5l5cd9z2u',
        'signed_message': 'test_signature',
        'nonce': '123456',
        'balance': '150000',  # Above minimum requirement (in sats)
        'chain': 'ECASH'
    }

class TestAgentVerifier:
    @pytest.mark.asyncio
    async def test_kaspa_verification_success(self, agent_verifier, mock_session, kaspa_test_data):
        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await agent_verifier.verify_agent(
                address=kaspa_test_data['address'],
                signed_message=kaspa_test_data['signed_message'],
                nonce=kaspa_test_data['nonce'],
                chain=kaspa_test_data['chain']
            )

            assert result is True
            assert kaspa_test_data['address'] in agent_verifier.verified_agents
            assert agent_verifier.verified_agents[kaspa_test_data['address']]['chain'] == 'KASPA'

    @pytest.mark.asyncio
    async def test_ecash_verification_success(self, agent_verifier, mock_session, ecash_test_data):
        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await agent_verifier.verify_agent(
                address=ecash_test_data['address'],
                signed_message=ecash_test_data['signed_message'],
                nonce=ecash_test_data['nonce'],
                chain=ecash_test_data['chain']
            )

            assert result is True
            assert ecash_test_data['address'] in agent_verifier.verified_agents
            assert agent_verifier.verified_agents[ecash_test_data['address']]['chain'] == 'ECASH'

    @pytest.mark.asyncio
    async def test_insufficient_balance(self, agent_verifier, mock_session_insufficient_balance, kaspa_test_data):
        with patch('aiohttp.ClientSession', return_value=mock_session_insufficient_balance):
            result = await agent_verifier.verify_agent(
                address=kaspa_test_data['address'],
                signed_message=kaspa_test_data['signed_message'],
                nonce=kaspa_test_data['nonce'],
                chain=kaspa_test_data['chain']
            )
            
            assert result is False
            assert kaspa_test_data['address'] not in agent_verifier.verified_agents

    @pytest.mark.asyncio
    async def test_invalid_signature(self, agent_verifier, mock_session_invalid_signature, kaspa_test_data):
        with patch('aiohttp.ClientSession', return_value=mock_session_invalid_signature):
            result = await agent_verifier.verify_agent(
                address=kaspa_test_data['address'],
                signed_message=kaspa_test_data['signed_message'],
                nonce=kaspa_test_data['nonce'],
                chain=kaspa_test_data['chain']
            )
            
            assert result is False
            assert kaspa_test_data['address'] not in agent_verifier.verified_agents 