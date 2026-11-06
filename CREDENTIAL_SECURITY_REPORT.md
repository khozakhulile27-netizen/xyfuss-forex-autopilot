# Credential and GitHub Readiness Report

Generated: 2026-11-02

## Trading mode

- Default configuration is `paper`.
- `live_trading_enabled` is forced to false unless both `XYFUSS_LIVE_TRADING_ENABLED` and the exact human approval value `I_UNDERSTAND_LIVE_TRADING` are supplied in the environment.
- Demo order placement has a separate `demo_execution_enabled` setting and requires `XYFUSS_DEMO_EXECUTION_ENABLED=true` as an additional environment opt-in.
- Both MT5 and cTrader demo adapters reject order placement by default and reject demo order placement when live mode is enabled.
- MT5 and cTrader demo connections may still be used for read-only account/market verification while demo order execution remains disabled.
- No live-money order path is claimed as verified.

## Credential handling

- Broker demo credentials are loaded from Codespaces/environment variables.
- No broker credential values are placed in `config.example.yaml`.
- Private credential, environment, backup, key, and account-data patterns are ignored by Git.
- Dashboard passwords are entered interactively and only a password hash is stored; passwords are not printed.
- Verification scripts output counts and connection status, not account identifiers, balances, or broker payloads.

## Git history and private files

Git history was scanned for credential-like filenames and secret assignments. This report records no confirmed credential values in tracked history at the time of review. Full Git history must be rotated by the repository owner if a secret was ever pasted outside the reviewed patterns.

The following local paths are ignored and must not be staged:

- `data/credentials/`
- `data/dashboard-auth.json`
- `backups/`
- `.env` and environment-specific `.env.*` files

## Commit-readiness review

Safe to commit after normal code review:

- `.gitignore`
- `config.example.yaml`
- `xyfuss_forex_autopilot/auth.py`
- `xyfuss_forex_autopilot/brokers/__init__.py`
- `xyfuss_forex_autopilot/brokers/ctrader.py`
- `xyfuss_forex_autopilot/cli.py`
- `xyfuss_forex_autopilot/config.py`
- `scripts/verify_mt5_demo.py`
- `scripts/verify_ctrader_demo.py`
- Focused test and report files

Requires attention before staging:

- `backups/risk_backup_before_stop_loss_upgrade.py` is already tracked despite the broader `backups/` ignore rule; decide whether to remove or sanitize it before committing repository changes.
- Any untracked private credential, account data, backup, key, or `.env` file.
- Any existing working-tree change that includes its own private values.
- No credentials or private account data should be staged; GitHub push and staging were not performed.

## Validation

- A GitHub Actions Python test workflow now runs compile checks and the test suite on supported Python versions for pushes to `main` and `fix/**` branches and pull requests to `main`.
- The new workflow has not yet completed for this branch; test success is not claimed until GitHub Actions reports a passing run.
- Live broker authentication, market execution, and order placement require separate real demo-environment credentials and evidence and are not claimed complete in this report without execution.
