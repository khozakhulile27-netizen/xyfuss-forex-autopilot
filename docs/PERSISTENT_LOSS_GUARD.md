# Persistent Equity Loss Guard

## Purpose

The persistent loss guard prevents new Autopilot trade decisions after the configured daily-loss or maximum-drawdown threshold is reached. It also keeps the emergency-stop state across process restarts.

## Equity input

`XyFussForexAutopilot.decide_trade(..., equity=...)` accepts the latest account equity. A broker-connected caller must supply the broker-reported equity on every decision cycle. If `equity` is omitted, the method uses the `balance` argument as a compatibility fallback for paper-mode callers; this is not a substitute for live broker equity.

MetaTrader 5 exposes account balance and equity through its official `account_info()` result. The account snapshot must be obtained from the connected terminal and passed into the decision layer by a separately verified integration.

For a read-only integration, call `decide_trade_from_broker(symbol, candles, broker_adapter)`. The adapter must return a connected account snapshot containing both `balance` and `equity`. A disconnected, incomplete, or invalid snapshot activates the persistent emergency stop. This method never submits or closes broker orders; the strategy decision pipeline remains paper-only.

## Thresholds

The current default risk profile uses:
- Daily loss stop: 1.5% of the supplied account balance.
- Maximum drawdown stop: 10% of the supplied account balance.
- At a UTC date change, daily loss is measured from the last equity snapshot recorded before the boundary. This conservatively counts any equity gap while the process was offline.
- Drawdown is measured from the persisted all-time equity high-water mark.

The thresholds are configurable through the existing `RiskProfile`. They are protective limits, not a guarantee against losses or execution slippage.

## Persistence and recovery

The state file defaults to `data/trading-state.json` and can be changed with `trading_state_path`. It stores submitted-order IDs, the daily starting equity, the equity high-water mark, and emergency-stop status.

A missing state file is treated as a first run. An unreadable, malformed, or structurally invalid existing state file activates a fail-closed emergency stop. The system requires manual review before an operator clears a stop.

## Important limitations

- This guard blocks new trade decisions. It does **not** automatically close existing broker positions, cancel pending orders, or guarantee that a broker-side stop-loss will execute.
- The main Autopilot orchestration remains paper-only. This change does not enable live trading or connect the main decision loop to the MT5 demo adapter.
- The caller must supply fresh, trustworthy broker equity for the guard to measure actual account losses. A stale or hard-coded value cannot protect an account.
- A separate, tested broker-side position-management and liquidation workflow is required before any real-money use.
