# XYFUSS Rust + TypeScript migration

## Target architecture
- Rust workspace: deterministic market-data validation, evidence scoring, strategy evaluation, portfolio/risk controls, order lifecycle state machine, broker adapters, persistence and audit.
- TypeScript: responsive operator dashboard, operator controls, monitoring, reporting and typed API client.
- Dashboard frontend: Vite-powered mobile-first preview with Overview, Markets, Strategies, Risk & Safety, Activity and Settings sections. It is intentionally disconnected until a secured backend API is implemented.
- Python is not part of the target runtime. Existing Python remains untouched during migration as the reference implementation until each capability has a tested Rust replacement.

## Non-negotiable trading safety
- Default mode is research/backtest/paper; live trading remains disabled.
- No system can guarantee winning trades, detect every opportunity first, or guarantee capital protection.
- Missing, stale, contradictory, malformed or unverified data => NO_TRADE.
- Every order proposal requires validated stop-loss, take-profit, position sizing, spread/slippage checks, daily loss and drawdown checks, idempotency, broker-side protection confirmation and an audit record.
- A strategy passing the risk gate is approved for simulation only. This first Rust crate cannot place orders.
- Live trading requires separate human authorization, a verified regulated broker connection, independent security review and extensive demo/forward testing. Do not store credentials in source control.

## Migration phases
1. Establish Rust workspace and strict TypeScript contracts (started).
   - Implemented: deterministic pre-trade risk gate; invalid risk configuration fails closed.
   - Implemented: independent eligibility gate; empty allowlists, untrusted/stale data, insufficient evidence, unapproved account/instrument, unvalidated strategy, closed session and active halt all block progression.
   - Not yet verified: compilation, formatting, Clippy, and CI execution. These are explicit release blockers.
2. Build and test the secure dashboard API boundary, authentication, authorization and health/status endpoints. The current frontend is preview-only and has no broker or engine connection.
3. Port and test market data, indicators, freshness checks and evidence verification.
4. Port strategy competition, walk-forward backtesting, transaction costs and out-of-sample evaluation.
5. Port portfolio sizing, correlated exposure, daily loss/drawdown limits, kill switch and durable state.
6. Implement official broker demo adapters with reconciliation, idempotency and broker-side SL/TP verification.
7. Connect the TypeScript operator dashboard and alerting to the authenticated API; test access control and remote access.
8. Run full parity tests against the old implementation, fault injection, replay tests and long-duration demo trading.
9. Remove Python only after all required capabilities have Rust replacements, test parity is demonstrated, and the operator approves the migration. Never enable live trading as part of a code migration.

## Current status
This is a migration foundation, not a complete or trading-ready autopilot. The dashboard is a responsive frontend preview only: it has no backend API, authentication, broker connection or live telemetry. The eligibility and risk gates are isolated decision modules, not connected to a market feed, portfolio state, or broker. No market feed, validated strategy, broker execution, or live trading is implemented. CI has not yet been confirmed green; no readiness claim is permitted.
