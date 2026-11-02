# GitHub Readiness Report

**Assessment date:** 2026-11-02 UTC
**Repository mode:** DEMO/PAPER
**Live trading, real deposits, and real withdrawals:** Disabled

## Validation

- Full test suite: **56 passed**
- Python compilation: passed
- Patch whitespace check: passed
- Git history credential-pattern scan: no private-key or credential assignment matches found
- Private credential files currently in the worktree: none found

## Sensitive worktree areas

The following paths are excluded from Git and require attention before any commit:

- `.env`, `.env.*`
- `data/`
- `backups/`
- `credentials/` and credential-named directories/files
- `*.key`, `*.pem`
- credential JSON files

Existing backups are historical snapshots and must not be committed. In particular, backup patches and account-adapter snapshots may contain sensitive testing context.

## Credential handling

Broker credentials are environment-only:

| Variable |
|---|
| `MT5_DEMO_LOGIN` |
| `MT5_DEMO_PASSWORD` |
| `MT5_DEMO_SERVER` |
| `CTRADER_DEMO_CLIENT_ID` |
| `CTRADER_DEMO_CLIENT_SECRET` |
| `CTRADER_DEMO_ACCESS_TOKEN` |
| `CTRADER_DEMO_ACCOUNT_ID` |

GitHub Codespaces Secrets may provide these environment variables. Example configuration contains no real credentials.

## Recommended commit classification

### Safe without further secret review

- Application source files under `xyfuss_forex_autopilot/`
- Test files under `tests/`
- `.gitignore`
- `config.example.yaml`
- Deployment metadata that contains no credentials
- Documentation describing validated behavior without secret values

### Requires attention

- Any untracked backup directory
- Any locally generated `data/` file
- Any generated credential vault, private key, certificate, or account export
- Reports that contain real account numbers, login IDs, server names tied to a private account, or broker tokens

## Git history finding

A repository-wide scan across available commits found no private-key blocks or explicit credential assignments in tracked files. This is evidence, not a guarantee that credentials were obfuscated or stored in another encoding.

Git history was not rewritten.

## Broker and safety status

- Demo/paper is the default.
- Real-money MT5 servers are rejected.
- Live execution requires explicit configuration and human approval.
- Automatic live switching is disabled.
- Missing credentials fail closed.
- Duplicate broker submissions are suppressed.
- Stop-loss, take-profit, emergency-stop, and recovery behavior are tested.

No real-money order was executed.
