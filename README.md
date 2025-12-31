# Orion 🏹

> **Named after the legendary hunter of Greek mythology, Orion tracks down profitable trading opportunities with precision and efficiency.**

Orion is a trading signals platform that scans the stock market to identify option trading opportunities based on configurable strategies. Like the constellation that watches over the night sky, Orion monitors the market landscape to alert you when conditions align for profitable trades.

## 🎯 What Does Orion Do?

Orion combines two powerful capabilities:

1. **Screener**: Filters tradable stocks based on fundamental criteria (revenue, market cap, volume, option liquidity)
2. **Detector**: Identifies trading opportunities using technical analysis (moving averages, RSI, pattern recognition)

## ✨ Key Features

- 📊 **Strategy-Based Screening**: Define custom strategies in simple YAML/Markdown files
- 🎯 **Option Focus**: Specialized in finding option trading opportunities (puts/calls)
- 📧 **Smart Alerts**: Email notifications when opportunities match your criteria
- ⚡ **Fast & Efficient**: Screen 500+ stocks in under 5 minutes with intelligent caching
- 🔄 **Automated Execution**: Run on-demand via CLI or scheduled in the cloud
- 📈 **Technical Analysis**: Built-in indicators (SMA, RSI, volume analysis, pattern detection)
- 💾 **Historical Tracking**: SQLite database tracks all screening results over time

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/tdu-meta/hello.git
cd hello

# Install dependencies (coming soon)
poetry install

# Configure API keys
cp .env.example .env
# Edit .env with your Alpha Vantage API key
```

### Basic Usage

```bash
# Run screening with OFI strategy
orion run --strategy ofi

# Screen specific symbols
orion run --strategy ofi --symbols AAPL,MSFT,GOOGL

# View screening history
orion history AAPL
```

## 📋 Project Status

**Current Phase**: Phase 1 Complete ✅ | Phase 2 In Progress

- ✅ System architecture designed
- ✅ Implementation plan created (7-week roadmap)
- ✅ OFI (Option for Income) strategy defined
- ✅ Phase 1: Foundation & Infrastructure (Configuration, Logging)
- ⏳ Phase 2: Data Layer (In Progress)

## 🎓 Strategies

### OFI (Option for Income)

The flagship strategy focuses on generating income by selling at-the-money (ATM) put options on high-quality stocks showing specific technical patterns.

**Entry Criteria**:
- Bull trend (20-week SMA > 60-week SMA)
- Recent oversold condition (RSI < 30)
- Bounce pattern (higher high + higher low with volume confirmation)
- Large cap stocks (>$1B revenue)

**See**: [strategies/ofi.md](strategies/ofi.md)

### Custom Strategies

Create your own strategies by adding YAML files to the `strategies/` folder. Each strategy defines:
- Stock screening criteria (fundamentals)
- Entry conditions (technical indicators)
- Option parameters (strike selection, expiration, minimum yield)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                          Orion System                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Strategy   │    │    Data      │    │  Notification │  │
│  │   Engine     │───▶│   Provider   │◀───│   Service    │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                    │                    │          │
│         ▼                    ▼                    ▼          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  Screening   │    │    Cache     │    │   Alert      │  │
│  │   Rules      │    │   Manager    │    │   Manager    │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Results Storage & History                │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         │                      │                      │
         ▼                      ▼                      ▼
  ┌──────────┐          ┌──────────┐          ┌──────────┐
  │   CLI    │          │   Cloud  │          │  Email   │
  │ Interface│          │ Scheduler│          │  Service │
  └──────────┘          └──────────┘          └──────────┘
```

## 📂 Project Structure

```
orion/
├── design/                    # System design documents
│   ├── system_design_detailed.md
│   ├── implementation_plan.md
│   └── stock_screener.md
├── strategies/                # Trading strategy definitions
│   └── ofi.md                # Option for Income strategy
├── src/orion/                # Source code (coming soon)
│   ├── core/                 # Screening orchestration
│   ├── data/                 # Data providers and models
│   ├── strategies/           # Strategy engine
│   ├── analysis/             # Technical indicators
│   └── notifications/        # Alert service
└── tests/                    # Test suite
    ├── unit/
    ├── integration/
    └── fixtures/
```

## 🔧 Technology Stack

- **Language**: Python 3.12+
- **Async Framework**: asyncio + aiohttp
- **Data Sources**: Alpha Vantage, Yahoo Finance
- **Technical Analysis**: pandas, numpy, pandas-ta
- **Database**: SQLite (local) / PostgreSQL (cloud)
- **Cloud**: AWS Lambda + EventBridge
- **Notifications**: SMTP email

## 🧪 Testing & CI/CD

### Running Tests Locally

```bash
# Run all tests
make test

# Run with coverage report
make test-cov

# Run only unit tests
make test-unit

# Run linting and formatting
make lint
make format

# Run type checking
make type-check

# Run all CI checks locally
make ci
```

### Automated Testing

Tests are automatically triggered on every push and pull request via GitHub Actions:

- ✅ **Unit Tests**: Run on Python 3.12
- ✅ **Code Coverage**: Tracked with pytest-cov
- ✅ **Linting**: Black, Ruff
- ✅ **Type Checking**: mypy

See [.github/workflows/test.yml](.github/workflows/test.yml) for the full CI configuration.

### Pre-commit Hooks (Optional)

Install pre-commit hooks to run tests before each commit:

```bash
make pre-commit
# or
pip install pre-commit
pre-commit install
```

This will automatically run:
- Code formatting (black)
- Linting (ruff)
- Type checking (mypy)
- All unit tests

## 📖 Documentation

- [Detailed System Design](design/system_design_detailed.md) - Complete architecture and component specifications
- [Implementation Plan](design/implementation_plan.md) - 7-week phased development plan with tests
- [OFI Strategy](strategies/ofi.md) - Option for Income strategy details
- [Phase 1 Complete](PHASE1_COMPLETE.md) - Summary of foundation implementation

## 🛣️ Roadmap

### Phase 1: Foundation (Week 1)
- Project setup and configuration
- Logging infrastructure
- Development environment

### Phase 2: Data Layer (Week 2)
- Data models and providers
- Alpha Vantage integration
- Caching system

### Phase 3: Technical Analysis (Week 3)
- Indicator calculations (SMA, RSI)
- Pattern detection
- Volume analysis

### Phase 4: Strategy Engine (Week 4)
- Strategy parser
- Rule evaluator
- Option analyzer

### Phase 5: Orchestration (Week 5)
- Main screener
- Notification service
- Batch processing

### Phase 6: CLI & Storage (Week 6)
- Command-line interface
- Results database
- History tracking

### Phase 7: Cloud Deployment (Week 7)
- AWS Lambda setup
- EventBridge scheduling
- Production deployment

## 🤝 Contributing

This is a personal project currently in active development. Contributions, ideas, and feedback are welcome!

## 📝 License

MIT License - see LICENSE file for details

## ⚠️ Disclaimer

This software is for educational and informational purposes only. It is not financial advice. Trading stocks and options involves risk, including the potential loss of principal. Always do your own research and consult with a licensed financial advisor before making investment decisions.

## 🌟 Why "Orion"?

In Greek mythology, Orion was a legendary hunter of great skill and precision. The Orion constellation has guided travelers for millennia, watching over the night sky. Similarly, this platform watches the market, tracking opportunities with the precision of a skilled hunter, helping you navigate the complex landscape of options trading.

---

**Built with Claude Code** | [Documentation](design/) | [Strategies](strategies/)
