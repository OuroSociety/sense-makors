# ourOS Market Maker

A professional-grade market making system designed for the FameX exchange, specializing in SZAR, cUSD, and KAS liquidity management.

## Overview

ourOS Market Maker is a high-performance automated market making system that helps maintain liquidity and tight spreads for digital assets on the FameX exchange. Built with Python, it features robust risk management, position tracking, and comprehensive testing.

bash
Clone the repository
git clone https://github.com/ouros/market-maker.git
cd market-maker
Create and activate virtual environment using uv
uv venv
source .venv/bin/activate # On Unix/MacOS
or
.venv\Scripts\activate # On Windows
Install dependencies
uv pip install -r requirements.txt
:
env
FAMEEX_API_KEY=your_api_key_here
FAMEEX_API_SECRET=your_api_secret_here
:
python
SYMBOL = "KAS-USDT" # Trading pair
SPREAD_PERCENTAGE = 0.02 # 2% spread
MIN_ORDER_SIZE = 100
MAX_ORDER_SIZE = 1000
bash
Run the market maker
python main.py
Run tests
pytest tests/ -v
market-maker/
├── trading/
│ ├── position_tracker.py
│ └── risk_manager.py
├── utils/
│ └── logger.py
├── tests/
│ ├── test_smoke.py
│ ├── test_position_tracker.py
│ └── test_risk_manager.py
├── api_client.py
├── config.py
├── main.py
└── market_maker.py
bash
Run all tests with coverage report
pytest --cov=trading --cov=utils --cov-report=term-missing
Run specific test categories
pytest tests/test_smoke.py -v -k "risk_management"
.
This README provides:
Clear overview of the system
Installation instructions
Configuration details
Usage examples
Project structure
Testing information
Risk management details
Contributing guidelines
Would you like me to expand any section or add additional information?
please update the README to have this information

Here's the updated README with the project's current structure and information:
*

```bash
Clone the repository
git clone https://github.com/ouros/market-maker.git
cd market-maker
Create and activate virtual environment using uv
uv venv
source .venv/bin/activate # On Unix/MacOS
or
.venv\Scripts\activate # On Windows
Install dependencies
uv pip install -r requirements.txt
```

2. **Configuration**

Create a `.env` file:
```env
FAMEEX_API_KEY=your_api_key_here
FAMEEX_API_SECRET=your_api_secret_here
```
3. **Run the Market Maker**
```bash
python main.py

```
## Project Structure

market-maker/
├── trading/ # Core trading components
│ ├── position_tracker.py # Position management
│ └── risk_manager.py # Risk controls
├── utils/
│ └── logger.py # Logging configuration
├── tests/
│ ├── test_smoke.py # Integration tests
│ ├── test_position_tracker.py
│ └── test_risk_manager.py
├── logs/ # Log files directory
├── api_client.py # FameX API client
├── config.py # Configuration settings
├── main.py # Entry point
├── market_maker.py # Market making logic
├── requirements.txt # Dependencies
└── .env # API credentials

## Configuration

Key settings in `config.py`:
python
SYMBOL = "KAS-USDT" # Trading pair
SPREAD_PERCENTAGE = 0.02 # 2% spread
MIN_ORDER_SIZE = 100 # Minimum order size
MAX_ORDER_SIZE = 1000 # Maximum order size
ORDER_RATE_LIMIT = 100 # Orders per 2 seconds
ORDER_BOOK_RATE_LIMIT = 20 # Orderbook requests per 2 seconds

## Testing

The project includes comprehensive test coverage with table-driven tests:


```bash
Run all tests with coverage
pytest --cov=trading --cov=utils --cov-report=term-missing
Run smoke tests
pytest tests/test_smoke.py -v
Run specific test scenarios
pytest tests/test_smoke.py -v -k "risk_management"
```


### Test Categories:
- **Market Making Scenarios**
  - Normal market conditions
  - Tight spread conditions
  - Empty order book handling
- **Risk Management Tests**
  - Position limit compliance
  - Order size validation
  - Maximum exposure checks
- **Position Tracking Tests**
  - Position updates
  - Trade history
  - State validation

## Logging

The system uses a rotating log system:
- Console output for critical events
- File logging with 10MB size limit and 5 backup files
- Separate logs for different components
- JSON-formatted trade history

## Risk Management

The risk management system provides:

### Position Limits
- Configurable maximum position size per symbol
- Real-time position monitoring
- Automated order rejection when limits exceeded

### Drawdown Protection
- Maximum drawdown limits
- Position rebalancing triggers

### Order Validation
- Size limits
- Price reasonability checks
- Rate limiting compliance

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Disclaimer

This software is for professional use only. Trading cryptocurrencies carries significant risk. Always test thoroughly in a sandbox environment first.

## Support

For support:
1. Check the documentation
2. Review the test cases for usage examples
3. Open an issue in the GitHub repository
4. Contact the development team

---
Built with ❤️ by the ourOS team