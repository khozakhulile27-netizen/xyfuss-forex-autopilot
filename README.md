# XYFUSS Forex Autopilot

Independent, evidence-driven Forex research and automation project. The target deployment is a dedicated cloud server; the Android phone is an operator/control device and is not required to remain awake.

## Mission

Build an autonomous FX system that discovers market opportunities, evaluates competing strategies, rejects weak or unsafe setups, protects account equity, and reports its decisions. It must be able to choose **NO_TRADE**. No system can guarantee monthly profit.

## Current architecture

- **Rust workspace (crates/xyfuss-core)**: deterministic, fail-closed eligibility and pre-trade risk gates. A passing proposal is approved for simulation only; this crate does not submit broker orders.
- **TypeScript dashboard (apps/dashboard)**: mobile-first operator-interface preview. It is not yet connected to an authenticated backend, broker or live telemetry.
- **Python reference implementation (xyfuss_forex_autopilot/)**: retained during the migration so each capability can be ported and tested before Python is removed. It includes market investigation, strategy competition, paper execution, broker adapter interfaces and tests.

## Python reference capabilities

- Historical cTrader demo candles can be requested and normalised into timestamped OHLCV records; historical requests are rate-limited and the authenticated connection sends periodic heartbeats.
- The market-universe scanner checks an explicit symbol allowlist, candle freshness and minimum history, compares strategy candidates, and ranks only candidates that pass its evidence and NO_TRADE checks.
- The autonomous scheduler invokes the scan cycle repeatedly, records failures and continues after a failed cycle.
- The scanner never places, modifies or closes orders. A candidate is labelled CANDIDATE_FOR_RISK_ASSESSMENT, not an execution approval.
- cTrader adapter remains demo-only. It verifies the selected account is included in the token grant and blocks order submission for view-only permission scopes.

A scan requires an authenticated broker adapter to be supplied by the control plane and a non-empty market_watchlist. The example configuration deliberately has an empty watchlist, so it fails closed until explicitly configured.

## Important unfinished work

- Secure cTrader OAuth/account connection from the Copilot control centre.
- A production market-data service with live spot subscriptions, multi-timeframe data validation and reconnect/reconciliation.
- Porting market feed, scanner, strategy competition and historical testing into the Rust runtime.
- Secure authenticated backend API between the Rust engine and TypeScript dashboard.
- Persistent portfolio state, position sizing, correlated exposure, daily loss/drawdown enforcement and broker-side protective-order verification in the Rust runtime.
- Demo forward testing, fault injection, restart recovery and long-duration operation.
- Independent security review and broker/account-specific regulatory checks before any live-trading decision.

## Safety boundaries

- Live trading remains disabled in the Rust runtime and is not enabled by this branch.
- No credentials, access tokens or account identifiers belong in source control.
- Missing, stale, malformed, contradictory or unverified market/account data must result in NO_TRADE.
- A one-month operating period is a measurement window, not a promise of profit.
- The system must stop opening new risk when a configured loss, drawdown, data-integrity or connectivity limit is reached.
- No real-money order should be enabled as part of a code migration or ordinary deployment.

## Configuration

Copy config.example.yaml to config.yaml. Set an explicit market_watchlist only after the authenticated broker adapter is configured. Keep secrets in the secure runtime/control-plane secret store, never in YAML committed to Git.

## Development checks

Python reference tests:

    python -m pip install pytest PyYAML cryptography
    python -m compileall -q xyfuss_forex_autopilot tests scripts
    python -m pytest -q

Rust checks:

    cargo fmt --all -- --check
    cargo test --workspace --all-targets
    cargo clippy --workspace --all-targets -- -D warnings

Dashboard checks:

    cd apps/dashboard
    npm ci
    npm run build

The repository is a development project, not a trading-ready product. The cTrader account connection currently requests view-only access and is not an order-execution feature. Do not infer readiness from successful compilation or a successful network connection.
