from typing import Dict, Optional
from decimal import Decimal
import time
import hmac
import hashlib
import base64
from utils.logger import setup_logger

logger = setup_logger("reward_manager")

class RewardManager:
    def __init__(self, wallet_manager, secret_key: str):
        self.wallet_manager = wallet_manager
        self.secret_key = secret_key.encode()
        self.reward_config = {
            'base_reward': Decimal('100'),  # Base KAS reward
            'accuracy_multiplier': Decimal('2'),
            'impact_multiplier': Decimal('1.5'),
            'min_accuracy_threshold': Decimal('0.7')
        }
        self.logger = logger
        
    async def process_reward(self, 
                           agent_address: str,
                           intel_id: str,
                           accuracy: Decimal,
                           impact_score: Decimal) -> Optional[Dict]:
        """Calculate and process reward for valuable intelligence"""
        try:
            if accuracy < self.reward_config['min_accuracy_threshold']:
                self.logger.info(f"Intelligence {intel_id} below accuracy threshold")
                return None
                
            # Calculate reward amount
            base_reward = self.reward_config['base_reward']
            accuracy_bonus = accuracy * self.reward_config['accuracy_multiplier']
            impact_bonus = impact_score * self.reward_config['impact_multiplier']
            
            total_reward = base_reward + accuracy_bonus + impact_bonus
            
            # Generate reward token
            reward_token = self._generate_reward_token(
                agent_address,
                intel_id,
                accuracy,
                impact_score,
                total_reward
            )
            
            # Process KAS payment
            tx_hash = await self.wallet_manager.send_reward(agent_address, total_reward)
            
            if not tx_hash:
                raise Exception("Reward payment failed")
                
            self.logger.info(
                f"Processed reward for {agent_address}: "
                f"amount={total_reward} KAS, accuracy={accuracy}, impact={impact_score}"
            )
            
            return {
                'reward_amount': total_reward,
                'reward_token': reward_token,
                'accuracy_score': accuracy,
                'impact_score': impact_score,
                'tx_hash': tx_hash
            }
            
        except Exception as e:
            self.logger.error(f"Failed to process reward: {str(e)}")
            return None
            
    def _generate_reward_token(self, agent_id: str, intel_id: str, accuracy: Decimal, 
                             impact_score: Decimal, reward_amount: Decimal) -> str:
        """Generate HMAC-based reward token"""
        try:
            timestamp = int(time.time())
            expiry = timestamp + 86400  # 24 hours
            
            # Create token payload with fixed order and format
            # Use | as separator instead of : since Kaspa addresses contain :
            payload = (
                f"{agent_id}|{intel_id}|{str(accuracy)}|{str(impact_score)}|"
                f"{str(reward_amount)}|{str(timestamp)}|{str(expiry)}"
            ).encode()
            
            # Encode the payload first
            payload_b64 = base64.b64encode(payload).decode()
            
            # Generate HMAC using the original payload
            h = hmac.new(self.secret_key, payload, hashlib.sha256)
            signature = base64.b64encode(h.digest()).decode()
            
            return f"{payload_b64}.{signature}"
            
        except Exception as e:
            self.logger.error(f"Failed to generate reward token: {str(e)}")
            return "" 