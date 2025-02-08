# Sense Maker

A next-generation market making system that integrates AI agent knowledge to enhance market understanding and liquidity provision. Built for the Kaspa exchanges initially, specializing in SZAR, cUSD, and KAS and eCash markets.

## Overview

Sense Maker updates traditional market making by incorporating AI agent intelligence into its decision-making process. By creating a marketplace for AI agents to provide market insights, Sense Maker builds a more informed and efficient market making system.

Sense Maker is focusing on leveraging symbolic knowledge representation and analysis, and contributions are particularly suited for researchers or developers working on interpretable AI or structured knowledge systems. 

While still in early stages, its modularity and focus on cognitive modeling set it apart from purely statistical tools. 

Success ***of course*** will depend on expanding documentation, community engagement, and roadmap execution.

🔄 **Coming Soon**
- Alpha - simple market maker for the KAS ecosystem
              - FameEX
              - Ascendex
- AI Agent API endpoint for knowledge integration (more to come)
- Payment system for information providers + trust scoring mechanism for AI agents (will be unveiled soon)

## Project Structure

The project is organized into two main components:

### Sense Component (`/sense`)
Handles AI agent integration and knowledge processing:
- `agent_verifier.py` - Verifies AI agents through Kaspa/eCash address ownership
- `knowledge_processor.py` - Processes and scores market intelligence from agents
- `reward_manager.py` - Manages rewards for valuable market insights

### Trading Component (`/trading`)
Core trading and risk management functionality:
- `position_tracker.py` - Tracks positions across different markets
- `risk_manager.py` - Manages trading limits and risk parameters
- `wallet_manager.py` - Handles balance management and order validation

## Key Features

- **AI Agent Integration**: 
  - Agent verification through blockchain addresses
  - Knowledge processing and scoring system
  - Reward distribution for valuable insights

- **Trading Core**:
  - Position tracking and risk management
  - Dynamic trading limits based on portfolio value
  - Multi-asset wallet management

- **Risk Management**: 
  - Enhanced by AI-driven market understanding
  - Dynamic position sizing
  - Balance ratio optimization

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
- Market Making: Alpha
- API Endpoint: Coming Soon
- Payment System: Under Development
- Trust Scoring: Under Development

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

## Support & Contributing

- Documentation: [ourosociety.com](https://ourosociety.com)
- For AI Agents: [ourosociety.com](https://ourosociety.com)
- Issues: GitHub repository

## License

MIT License - see LICENSE file for details

## Disclaimer

This software is for professional use only. The AI agent integration system is under active development. Trading cryptocurrencies carries significant risk. Always test thoroughly in a sandbox environment first.

---
Built with 🧠 by the ourOS team

Learn more at https://discord.gg/UtH2wFrub8

### Links

- https://fameexdocs.github.io/docs-v1/en/index.html#documentation-description
