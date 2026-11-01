# xyfuss-forex-autopilot

Independent, evidence-driven Forex trading system designed to run on a dedicated computer or cloud server without requiring a mobile device to remain open.

This project is intentionally separated from the existing `xyfuss-god-mode` repository and is fully self-contained.

## Mission
Build an autonomous FX intelligence engine that:
- investigates market conditions
- gathers evidence before making recommendations
- compares multiple strategies
- verifies risk and execution safety
- runs in paper-trading mode by default
- blocks live trading unless explicitly enabled and securely configured

## Core principles
- Evidence before action
- Independent investigation separate from strategy logic
- No fabricated broker confirmations
- No duplicate orders
- Strict risk limits
- Paper trading only during development
- Live trading disabled by default

## Features implemented
- Market investigation engine
- Historical winner/loser analysis
- Multiple strategy competition engine
- Independent evidence verification
- Recommendation and ranking engine
- NO TRADE decision engine
- Capital protection and risk management
- Backtesting engine
- Paper trading engine
- Broker adapter framework
- Autonomous monitoring
- Trade history and learning loop
- Mobile-friendly dashboard
- Autonomous scheduler
- Audit and reporting

## Project structure
```text
xyfuss_forex_autopilot/
    __init__.py
    __main__.py
    main.py
    cli.py
    config.py
    models.py
    core.py
    market/
    strategies/
    evidence/
    recommendations/
    risk/
    no_trade/
    backtesting/
    paper_trading/
    brokers/
    monitoring/
    learning/
    dashboard/
    scheduler/
    audit/
```

## Quick start
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m xyfuss_forex_autopilot --help
```

## Commands
```bash
python -m xyfuss_forex_autopilot status
python -m xyfuss_forex_autopilot simulate
python -m xyfuss_forex_autopilot paper-trade
python -m xyfuss_forex_autopilot dashboard
python -m xyfuss_forex_autopilot audit
```

## Configuration
Copy the configuration example and adjust to your environment:
```bash
cp config.example.yaml config.yaml
```

## Safety notes
- Live trading is disabled by default.
- Broker integrations are abstracted behind adapters.
- Every trade candidate must pass evidence, strategy, and risk checks.
- Duplicate orders are blocked by the monitoring layer.

## Development note
This release focuses on a working, installable, independent project with real Python logic, tests, and a local dashboard. Live trading remains intentionally disabled.
