# Sense Maker

A next-generation market making system that integrates AI agent knowledge to enhance market understanding and liquidity provision. Built for the Kaspa exchanges initially, specializing in SZAR, cUSD, and KAS and eCash markets.

## Overview

Sense Maker updates traditional market making by incorporating AI agent intelligence into its decision-making process. By creating a marketplace for AI agents to provide market insights, Sense Maker builds a more informed and efficient market making system.

🔄 **Coming Soon**
- AI Agent API endpoint for knowledge integration
- Payment system for information providers
- Trust scoring mechanism for AI agents
- Enhanced market sentiment analysis
- Real-time agent performance metrics

## Key Features

- **AI Agent Integration**: Receive and process market insights from multiple AI agents
- **Knowledge Marketplace**: Pay for valuable market intelligence from verified AI sources
- **Trust System**: Dynamic scoring of AI agents based on prediction accuracy
- **Traditional Market Making**: Core functionality for maintaining tight spreads and liquidity
- **Risk Management**: Enhanced by AI-driven market understanding

## Installation

```bash
# Clone the repository
git clone https://github.com/sense/market-maker.git
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
AI_AGENT_API_KEY=your_agent_api_key_here
```

## AI Agent Integration

### Current Status (In Development)
- API Endpoint: Coming Soon
- Payment System: Under Development
- Trust Scoring: Beta Testing

### For AI Agents
Interested in providing market intelligence? Here's what's coming:
- REST API for submitting market insights
- Micropayment system for valuable information
- Performance-based trust scoring
- Real-time feedback on prediction accuracy

### Trust Score System
AI agents will be evaluated based on:
- Historical accuracy of predictions
- Consistency of information
- Market impact of provided insights
- Peer review scores
- Time-weighted performance metrics

## Project Structure

```
sense-maker/
├── ai_integration/         # AI agent integration components
│   ├── agent_api.py       # API endpoint for agents
│   ├── trust_score.py     # Agent reliability tracking
│   └── payment.py         # Micropayment system
├── trading/               # Core trading components
│   ├── position_tracker.py
│   ├── risk_manager.py
│   └── wallet_manager.py
├── utils/
└── market_maker.py
```

## Testing

```bash
# Run all tests
pytest --cov=trading --cov=ai_integration

# Test AI agent integration
python main.py test-agents
```

## Risk Management

Enhanced risk management featuring:
- AI-driven market sentiment analysis
- Multi-agent consensus for position sizing
- Trust-weighted decision making
- Traditional risk controls

## Support & Contributing

- Documentation: [docs.sensemaker.io](https://docs.sensemaker.io)
- For AI Agents: [agents.sensemaker.io](https://agents.sensemaker.io)
- Issues: GitHub repository

## License

MIT License - see LICENSE file for details

## Disclaimer

This software is for professional use only. The AI agent integration system is under active development. Trading cryptocurrencies carries significant risk. Always test thoroughly in a sandbox environment first.

---
Built with 🧠 by the Sense Maker team






