from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict
from decimal import Decimal
import uvicorn
import sys
from pathlib import Path
from uuid import UUID
import asyncio

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from config.config import API_KEY, API_SECRET
from utils.logger import setup_logger
from market_maker import MarketMaker
from utils.trading_utils import (
    create_exchange_client,
    test_trading_system,
    test_famex_connection,
    get_market_summary
)

app = FastAPI(title="Market Maker API", version="1.0.0")
logger = setup_logger("api")

# Store running market makers
market_makers: Dict[str, MarketMaker] = {}

class MarketMakerConfig(BaseModel):
    symbol: str = "SZARUSDT"
    spread: Optional[float] = None
    
class TestConfig(BaseModel):
    symbol: str = "SZARUSDT"
    duration: Optional[int] = 300
    continuous: bool = False
    full: bool = False

@app.get("/")
async def root():
    return {"status": "ok", "service": "Market Maker API"}

@app.post("/market-maker/start")
async def start_market_maker(config: MarketMakerConfig, background_tasks: BackgroundTasks):
    """Start a market maker instance"""
    try:
        client = create_exchange_client('fameex', API_KEY, API_SECRET)
        market_maker = MarketMaker(client)
        
        if config.spread is not None:
            market_maker.spread = Decimal(str(config.spread))
        
        # Store market maker with its job ID
        market_makers[market_maker.job_id] = market_maker
        
        # Start the market maker in the background
        background_tasks.add_task(market_maker.run_async)
        
        return {
            "status": "started",
            "job_id": market_maker.job_id,
            "symbol": config.symbol,
            "spread": str(config.spread) if config.spread else None
        }
    except Exception as e:
        logger.error(f"Failed to start market maker: {str(e)}")
        raise HTTPException(500, str(e))

@app.get("/market-maker/status/{job_id}")
async def get_market_maker_status(job_id: str):
    """Get status of a specific market maker"""
    try:
        UUID(job_id)  # Validate UUID format
    except ValueError:
        raise HTTPException(400, "Invalid job ID format")
        
    if job_id not in market_makers:
        raise HTTPException(404, "Market maker not found")
        
    return market_makers[job_id].get_status()

@app.get("/market-maker/status")
async def get_all_market_makers_status():
    """Get status of all running market makers"""
    return {
        job_id: mm.get_status()
        for job_id, mm in market_makers.items()
    }

@app.post("/market-maker/stop/{job_id}")
async def stop_market_maker(job_id: str):
    """Stop a specific market maker"""
    try:
        UUID(job_id)  # Validate UUID format
    except ValueError:
        raise HTTPException(400, "Invalid job ID format")
        
    if job_id not in market_makers:
        raise HTTPException(404, "Market maker not found")
        
    try:
        market_maker = market_makers[job_id]
        market_maker.running = False
        await asyncio.sleep(0.5)  # Give it time to stop
        del market_makers[job_id]
        return {"status": "stopped", "job_id": job_id}
    except Exception as e:
        logger.error(f"Failed to stop market maker: {str(e)}")
        raise HTTPException(500, str(e))

@app.post("/market-maker/stop-all")
async def stop_all_market_makers():
    """Stop all running market makers"""
    stopped_jobs = []
    errors = []
    
    for job_id in list(market_makers.keys()):
        try:
            market_maker = market_makers[job_id]
            market_maker.running = False
            await asyncio.sleep(0.5)  # Give it time to stop
            del market_makers[job_id]
            stopped_jobs.append(job_id)
        except Exception as e:
            errors.append({"job_id": job_id, "error": str(e)})
    
    return {
        "status": "completed",
        "stopped_jobs": stopped_jobs,
        "errors": errors
    }

@app.post("/test/trading-system")
async def test_trading(config: TestConfig):
    """Run trading system test"""
    try:
        client = create_exchange_client('fameex', API_KEY, API_SECRET, test_mode=True)
        results = test_trading_system(client, config.symbol, config.duration)
        return results
    except Exception as e:
        logger.error(f"Trading system test failed: {str(e)}")
        raise HTTPException(500, str(e))

@app.post("/test/famex")
async def test_famex(config: TestConfig):
    """Test FameEX connection"""
    try:
        client = create_exchange_client('fameex', API_KEY, API_SECRET)
        success = test_famex_connection(
            client,
            continuous=config.continuous,
            symbol=config.symbol,
            full_test=config.full
        )
        return {"success": success}
    except Exception as e:
        logger.error(f"FameEX test failed: {str(e)}")
        raise HTTPException(500, str(e))

@app.get("/market/summary")
async def market_summary(filter_kas: bool = True):
    """Get market summary"""
    try:
        client = create_exchange_client('fameex', API_KEY, API_SECRET)
        return get_market_summary(client, filter_kas)
    except Exception as e:
        logger.error(f"Failed to get market summary: {str(e)}")
        raise HTTPException(500, str(e)) 