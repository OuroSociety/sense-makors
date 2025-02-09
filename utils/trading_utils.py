from decimal import Decimal
from config.api_client import FameexClient
from config.config import API_KEY, API_SECRET
from utils.logger import setup_logger

logger = setup_logger("trading_utils")

def create_exchange_client(exchange_type: str, api_key: str, api_secret: str, test_mode: bool = False):
    """Factory function to create exchange clients"""
    if exchange_type.lower() == 'fameex':
        from config.api_client import FameexClient
        return FameexClient(api_key, api_secret, test_mode=test_mode)
    else:
        raise ValueError(f"Unsupported exchange type: {exchange_type}")

def run_market_maker(client: FameexClient, spread: Decimal = None):
    """Run the market maker"""
    from market_maker import MarketMaker
    market_maker = MarketMaker(client)
    if spread is not None:
        market_maker.spread = spread
    market_maker.run()

def test_trading_system(client, symbol: str, duration: int = 300):
    """Wrapper for trading system test"""
    from main import test_trading_system as _test_trading_system
    return _test_trading_system(client, symbol, duration)

def test_famex_connection(client, continuous: bool = False, symbol: str = None, full_test: bool = False):
    """Wrapper for FameEX connection test"""
    from tests.test_famex import test_famex_connection as _test_famex
    return _test_famex(client, continuous, symbol, full_test)

def get_market_summary(client, filter_kas: bool = True):
    """Wrapper for market summary"""
    from main import get_market_summary as _get_market_summary
    return _get_market_summary(client, filter_kas) 