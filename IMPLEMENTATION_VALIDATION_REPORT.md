# XYFUSS Multi-Broker Implementation and Validation Report

## Status

Implementation is currently **paper-only / fail closed**. MT5, cTrader, and direct-broker
adapters define the supported integration boundaries, but they do not contain a verified
SDK/API implementation and cannot place orders. No cloud deployment, real broker account,
or live connection has been claimed or performed.

## Implemented architecture

- Independent MT5, cTrader, direct-API, and paper adapters behind the broker factory.
- Shared capabilities, standardized order data, account information, positions, and lot
  validation interfaces.
- Client-order identity storage for duplicate suppression.
- Atomic JSON state persistence for submitted client IDs and emergency stop state.
- Recoverable broker-operation wrapper and health-failure counter.
- Remote dashboard emergency-stop control with remote access-token enforcement.
- Docker and systemd restart supervision templates.
- Existing evidence, risk, stop-loss, paper execution, profit allocation, audit, and
  learning paths are preserved.

## Live and withdrawal safeguards

`live_trading_enabled` remains false by default. Live adapter methods fail closed even if
credentials are provided. Withdrawal support remains separate from order execution; no
withdrawal is attempted and no broker withdrawal bypass is implemented. Any future real
withdrawal must use that broker's documented official process and an explicit human
authorisation flow.

The R3,000 profit rule remains represented by the existing allocation implementation:
R1,500 is personal withdrawal allocation and R1,500 is trading capital growth.

## Official integration requirements

The broker-specific implementation must use only the broker/platform's official,
documented SDK, Open API, or trading API. Website automation, credential sharing, token
interception, and security bypasses are prohibited. Platform availability must be
discovered per broker; no broker must be assumed to support MT5 or cTrader.

Before enabling live trading, each adapter requires:

1. A controlled integration environment.
2. Official SDK/API credentials in secret storage.
3. A verified symbol, tick, account, order, and position integration test.
4. Broker-specific symbol constraints, volume constraints, and market restrictions.
5. Idempotency and duplicate-order integration tests.
6. Explicit human approval after independent security review.

## Validation

Automated validation completed in the workspace:

- 30 tests passed.
- MT5, cTrader, and direct adapter fail-open/fail-close behaviour tested.
- Broker capabilities and minimum lot validation tested.
- Duplicate client-order suppression tested.
- Restart-state persistence and emergency stop persistence tested.
- Broker disconnection fail-safe and recoverable operation tested.
- Existing risk, stop-loss, dashboard, paper execution, profit allocation, and full-cycle
  tests remain passing.

## Not yet validated

The following require an actual server, credentials, and authorised broker environment:

- Cloud deployment and public network reachability.
- Real MT5 connection or an official MT5 integration test.
- Real cTrader connection or an official cTrader Open API integration test.
- Direct broker API connection and broker capability discovery.
- Real broker order acknowledgement, position modification, stop management, and recovery.
- Phone-off operation.
- Remote emergency shutdown from a networked phone and TLS-protected reverse proxy.
- Real withdrawal processing.

## cTrader first-integration assessment

Spotware's cTrader Open API provides a Linux/Python integration through the official
`ctrader-open-api` SDK and a dedicated demo host. A demo-only adapter now exists in
`xyfuss_forex_autopilot/brokers/ctrader.py`. It uses the official demo endpoint, requires
application credentials, account access token, and account ID, and is fail closed unless
demo credentials are supplied.

Actual credentials were not provided. As a result, the workspace did not and could not
open a real demo session. `scripts/verify_ctrader_demo.py` reports `NOT_RUN` in that case;
mocked SDK-boundary tests cover the adapter contract and passed 32 total workspace tests.

The deployment templates are validation starting points, not evidence of a deployed
service. Cloud deployment and live broker claims must remain disabled until those tests
produce verified broker confirmations.
