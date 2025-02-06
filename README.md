# ourOS Market Maker

A professional-grade market making system designed for the FameX exchange, specializing in SZAR, cUSD, and KAS liquidity management.

## Overview

ourOS Market Maker is a high-performance automated market making system that helps maintain liquidity and tight spreads for digital assets on the FameX exchange. Built with Python, it features robust risk management, position tracking, and comprehensive testing.

## Installation

```bash
# Clone the repository
git clone https://github.com/ouros/market-maker.git
cd market-maker

# Create and activate virtual environment using uv
uv venv
source .venv/bin/activate  # On Unix/MacOS
# or
.venv\Scripts\activate    # On Windows

# Install dependencies
uv pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root:
```env
FAMEEX_API_KEY=your_api_key_here
FAMEEX_API_SECRET=your_api_secret_here
```

Key settings in `config.py`:
```python
SYMBOL = "KAS-USDT"  # Trading pair
SPREAD_PERCENTAGE = 0.02  # 2% spread
MIN_ORDER_SIZE = 100
MAX_ORDER_SIZE = 1000
```

## CLI Commands

### Testing FameEX API

```bash
# Run one-time API test
python main.py test

# Run continuous API testing (Ctrl+C to stop)
python main.py test --continuous
```

The test command will check:
- Order book API
- Account balance API
- Market ticker API
- Connection status
- API response validity

Example test output:
```
Testing FameEX API connection...

Testing order book API...
✓ Order book snapshot:
Top bid: ['50000', '1.0']
Top ask: ['50100', '1.0']

Testing account balance API...
✓ Account balances:
KAS: 1000.0
USDT: 50000.0

Testing market ticker API...
✓ Current KAS-USDT ticker:
Last price: 50050
24h volume: 1500000

API Test Success Rate: 100.0%
```

### Running the Market Maker

```bash
# Run with default spread
python main.py run

# Run with custom spread (e.g., 3%)
python main.py run --spread 0.03
```

## Project Structure

```
market-maker/
├── trading/              # Core trading components
│   ├── position_tracker.py  # Position management
│   ├── risk_manager.py     # Risk controls
│   └── wallet_manager.py   # Balance management
├── utils/
│   ├── logger.py          # Logging configuration
│   └── decimal_utils.py   # Decimal handling utilities
├── tests/                # Test suite
├── api_client.py         # FameX API client
├── config.py            # Configuration settings
├── main.py             # CLI entry point
└── market_maker.py     # Market making logic
```

## Testing

```bash
# Run all tests with coverage
pytest --cov=trading --cov=utils --cov-report=term-missing

# Run specific test categories
pytest tests/test_smoke.py -v -k "risk_management"

# Run API tests with continuous monitoring
python main.py test --continuous
```

## Logging

The system uses a rotating log system with files stored in the `logs/` directory:
- `main.log`: Main application logs
- `market_maker.log`: Market making activity
- `risk_manager.log`: Risk management decisions
- `position_tracker.log`: Position updates
- `wallet_manager.log`: Balance changes

## Risk Management

The risk management system provides:
- Dynamic position sizing based on portfolio value
- Adaptive spread calculation based on market volatility
- Balance ratio targeting between assets
- Maximum drawdown protection
- Minimum spread enforcement

## Support

For support:
1. Check the documentation
2. Review the test cases for usage examples
3. Run the API tests to verify setup
4. Open an issue in the GitHub repository

## License

MIT License - see LICENSE file for details

## Disclaimer

This software is for professional use only. Trading cryptocurrencies carries significant risk. Always test thoroughly in a sandbox environment first.

---
Built with ❤️ by the ourOS team






