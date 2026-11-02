from __future__ import annotations

import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from xyfuss_forex_autopilot.auth import load_mt5_demo_credentials
from xyfuss_forex_autopilot.brokers import MT5IntegrationError, MetaTrader5DemoAdapter


def main() -> int:
    missing = [name for name in ("MT5_DEMO_SERVER", "MT5_DEMO_LOGIN", "MT5_DEMO_PASSWORD") if not os.environ.get(name)]
    if missing:
        print("NOT_RUN: demo credentials are not configured:", ", ".join(missing))
        return 2

    credentials = load_mt5_demo_credentials("data/credentials/mt5-demo.json")
    adapter = MetaTrader5DemoAdapter(credentials=credentials, live_trading_enabled=False)
    try:
        if not adapter.connect():
            print("FAIL: MT5 demo connection or authentication failed")
            return 1
        if not adapter.reconnect():
            print("FAIL: MT5 demo reconnection failed")
            return 1
        adapter.get_account_info()
        prices = adapter.get_market_prices(["EUR/USD", "GBP/USD"])
        health = adapter.health_check()
        if not health["healthy"]:
            print("FAIL: MT5 demo connection health check failed")
            return 1
        print("PASS: MT5 demo account, market prices, and health verified")
        print("MARKET_SYMBOL_COUNT:", len(prices))
        print("HEALTHY:", health["healthy"])
        print("RECONNECTED:", True)
        print("ORDERS_PLACED: 0")
        return 0
    except (MT5IntegrationError, OSError) as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}")
        return 1
    finally:
        adapter.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())
