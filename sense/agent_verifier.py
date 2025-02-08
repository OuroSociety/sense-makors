from typing import Dict, Optional, Literal
from decimal import Decimal
import time
import hmac
import hashlib
import aiohttp
from utils.logger import setup_logger

logger = setup_logger("agent_verifier")

ChainType = Literal['KASPA', 'ECASH']

class AgentVerifier:
    """Verifies AI agents through Kaspa or eCash address ownership and balance"""
    
    def __init__(self, 
                 kaspa_api_url: str = "https://api.kaspa.org",
                 ecash_api_url: str = "https://chronik.fabien.cash"):
        self.api_urls = {
            'KASPA': kaspa_api_url,
            'ECASH': ecash_api_url
        }
        self.verified_agents: Dict[str, Dict] = {}
        self.min_balance_requirements = {
            'KASPA': {
                'KAS': Decimal('10000')
            },
            'ECASH': {
                'XEC': Decimal('100000')  # Example minimum XEC requirement
            }
        }
        self.logger = logger
        
    async def verify_agent(self, 
                          address: str, 
                          signed_message: str, 
                          nonce: str,
                          chain: ChainType) -> bool:
        """Verify agent has required balance and signature"""
        try:
            # Verify signature matches address
            if not await self._verify_signature(address, signed_message, nonce, chain):
                self.logger.warning(f"Signature verification failed for {address} on {chain}")
                return False
                
            # Check balance
            balance = await self._get_address_balance(address, chain)
            required_balance = self.min_balance_requirements[chain][
                'KAS' if chain == 'KASPA' else 'XEC'
            ]
            
            if balance < required_balance:
                self.logger.warning(
                    f"Insufficient {chain} balance for {address}: "
                    f"{balance} < {required_balance}"
                )
                return False
                
            # Store verified agent
            timestamp = int(time.time())
            self.verified_agents[address] = {
                'verified_at': timestamp,
                'chain': chain,
                'balance': balance,
                'performance_score': Decimal('0')
            }
            
            self.logger.info(f"Agent {address} verified successfully on {chain}")
            return True
            
        except Exception as e:
            self.logger.error(f"Agent verification failed on {chain}: {str(e)}")
            return False
            
    def is_agent_verified(self, address: str) -> bool:
        """Check if agent is currently verified"""
        if address not in self.verified_agents:
            return False
            
        # Check if verification is still valid (24 hour expiry)
        verification_age = time.time() - self.verified_agents[address]['verified_at']
        return verification_age < 86400  # 24 hours
        
    async def _get_address_balance(self, address: str, chain: ChainType) -> Decimal:
        """Get balance for address using appropriate API"""
        try:
            if chain == 'KASPA':
                return await self._get_kaspa_balance(address)
            else:  # ECASH
                return await self._get_ecash_balance(address)
                
        except Exception as e:
            self.logger.error(f"Failed to get {chain} balance: {str(e)}")
            return Decimal('0')
            
    async def _get_kaspa_balance(self, address: str) -> Decimal:
        """Get KAS balance using Kaspa API"""
        try:
            async with aiohttp.ClientSession() as session:
                response = await session.get(
                    f"{self.api_urls['KASPA']}/addresses/{address}/balance"
                )
                if response.status == 200:
                    data = await response.json()
                    return Decimal(str(data.get('balance', '0')))
                return Decimal('0')
        except Exception as e:
            self.logger.error(f"Failed to get KAS balance: {str(e)}")
            return Decimal('0')
                    
    async def _get_ecash_balance(self, address: str) -> Decimal:
        """Get XEC balance using Chronik API"""
        try:
            clean_address = address.replace('ecash:', '')
            
            async with aiohttp.ClientSession() as session:
                response = await session.get(
                    f"{self.api_urls['ECASH']}/address/{clean_address}/history"
                )
                if response.status == 200:
                    data = await response.json()
                    balance_sats = Decimal(str(data.get('balance', '0')))
                    return balance_sats / Decimal('100')
                return Decimal('0')
        except Exception as e:
            self.logger.error(f"Error getting XEC balance: {str(e)}")
            return Decimal('0')
            
    async def _verify_signature(self, 
                              address: str, 
                              signed_message: str, 
                              nonce: str,
                              chain: ChainType) -> bool:
        """Verify signed message matches address using appropriate verification"""
        try:
            # Create verification message with nonce
            message = f"Verify market maker agent {nonce}"
            
            if chain == 'KASPA':
                return await self._verify_kaspa_signature(address, message, signed_message)
            else:  # ECASH
                return await self._verify_ecash_signature(address, message, signed_message)
                
        except Exception as e:
            self.logger.error(f"Signature verification failed for {chain}: {str(e)}")
            return False
            
    async def _verify_kaspa_signature(self, 
                                    address: str, 
                                    message: str, 
                                    signature: str) -> bool:
        """Verify Kaspa signature"""
        try:
            async with aiohttp.ClientSession() as session:
                response = await session.post(
                    f"{self.api_urls['KASPA']}/addresses/{address}/verify",
                    json={
                        'message': message,
                        'signature': signature
                    }
                )
                if response.status == 200:
                    data = await response.json()
                    return data.get('valid', False)
                return False
                
        except Exception as e:
            self.logger.error(f"Kaspa signature verification failed: {str(e)}")
            return False
                    
    async def _verify_ecash_signature(self, 
                                    address: str, 
                                    message: str, 
                                    signature: str) -> bool:
        """Verify eCash signature using Chronik API"""
        try:
            clean_address = address.replace('ecash:', '')
            
            async with aiohttp.ClientSession() as session:
                response = await session.post(
                    f"{self.api_urls['ECASH']}/verify",
                    json={
                        'address': clean_address,
                        'message': message,
                        'signature': signature
                    }
                )
                if response.status == 200:
                    data = await response.json()
                    return data.get('valid', False)
                return False
                
        except Exception as e:
            self.logger.error(f"eCash signature verification failed: {str(e)}")
            return False 