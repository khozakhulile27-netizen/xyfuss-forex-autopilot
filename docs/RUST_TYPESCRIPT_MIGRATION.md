# XYFUSS Rust + TypeScript migration

## Target architecture
- Rust workspace: deterministic market-data validation, evidence scoring, strategy evaluation, portfolio/risk controls, order lifecycle state machine, broker adapters, persistence and audit.
- TypeScript: dashboard, operator controls, monitoring, reporting and typed API client.
- Python is not part of the target runtime. Existing Python remains untouched during migration as the reference implementation until each capability has a tested Rust replacement.

## Non-negotiable trading safety
- Default mode is research/backtest/paper; live trading remains disabled.
- No system can guarantee winning trades, detect every opportunity first, or guarantee capital protection.
- Missing, stale, contradictory, malformed or unverified data => NO_TRADE.
- Every order proposal requires validated stop-loss, take-profit, position sizing, spread/slippage checks, daily loss and drawdown checks, idempotency, broker-side protection confirmation and an audit record.
- A strategy passing the risk gate is approved for simulation only. This first Rust crate cannot place orders.
- Live trading requires separate human authorization, a verified regulated broker connection, independent security review and extensive demo/forward testing. Do not store credentials in source control.

## Migration phases
1. Establish Rust workspace and strict TypeScript contracts (this commit).
2. Port and test market data, indicators, freshness checks and evidence verification.
3. Port strategy competition, walk-forward backtesting, transaction costs and out-of-sample evaluation.
4. Port portfolio sizing, correlated exposure, daily loss/drawdown limits, kill switch and durable state.
5. Implement official broker demo adapters with reconciliation, idempotency and broker-side SL/TP verification.
6. Build TypeScript operator dashboard and alerting; test authentication and remote access.
7. Run full parity tests against the old implementation, fault injection, replay tests and long-duration demo trading.
8. Remove Python only after all required capabilities have Rust replacements, test parity is demonstrated, and the operator approves the migration. Never enable live trading as part of a code migration.

## Current status
This is a migration foundation, not a complete or trading-ready autopilot. No market feed, profitable strategy, broker execution or live trading is implemented by this commit.
