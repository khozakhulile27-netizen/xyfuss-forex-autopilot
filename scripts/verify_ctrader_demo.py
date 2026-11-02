from __future__ import annotations

import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from xyfuss_forex_autopilot.brokers.ctrader import CTraderDemoAdapter, CTraderIntegrationError


REQUIRED = (
    "CTRADER_DEMO_CLIENT_ID",
    "CTRADER_DEMO_CLIENT_SECRET",
    "CTRADER_DEMO_ACCESS_TOKEN",
    "CTRADER_DEMO_ACCOUNT_ID",
)


def main() -> int:
    missing = [name for name in REQUIRED if not os.environ.get(name)]
    if missing:
        print("NOT_RUN: demo credentials are not configured:", ", ".join(missing))
        return 2

    adapter = CTraderDemoAdapter(
        credentials={
            "client_id": os.environ["CTRADER_DEMO_CLIENT_ID"],
            "client_secret": os.environ["CTRADER_DEMO_CLIENT_SECRET"],
            "access_token": os.environ["CTRADER_DEMO_ACCESS_TOKEN"],
            "ctid_trader_account_id": os.environ["CTRADER_DEMO_ACCOUNT_ID"],
        }
    )
    try:
        if not adapter.connect():
            print("FAIL: cTrader demo connection or authentication failed")
            return 1
        print("PASS: demo connection and authentication")
        market_data = adapter.get_market_data()
        account = adapter.get_account_info()
        positions = adapter.get_positions()
        print("MARKET_SYMBOL_COUNT:", len(market_data))
        print("ACCOUNT_CONNECTED:", account.get("connected", False))
        print("POSITION_COUNT:", len(positions))
        print("PASS: demo account and position retrieval")
        return 0
    except (CTraderIntegrationError, ConnectionError, TimeoutError) as exc:
        print(f"FAIL: {type(exc).__name__}")
        return 1
    finally:
        adapter.emergency_stop()


if __name__ == "__main__":
    raise SystemExit(main())
