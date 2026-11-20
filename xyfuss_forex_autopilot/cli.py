from __future__ import annotations

import argparse
import os
import getpass
import hmac
import json
import time
from pathlib import Path

from xyfuss_forex_autopilot.config import load_settings
from xyfuss_forex_autopilot.core import XyFussForexAutopilot


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="XYFUSS Forex Autopilot")
    parser.add_argument(
        "command",
        choices=["status", "simulate", "paper-trade", "dashboard", "audit", "setup-dashboard", "configure-mt5-demo", "test-mt5-demo"],
        nargs="?",
        default="status",
    )
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    config_path = Path(args.config)
    settings = load_settings(str(config_path))
    dashboard_password_hash = settings.dashboard_password_hash
    auth_file = Path("data/dashboard-auth.json")
    if not dashboard_password_hash and auth_file.exists():
        try:
            dashboard_password_hash = json.loads(auth_file.read_text(encoding="utf-8")).get("password_hash", "")
        except json.JSONDecodeError:
            dashboard_password_hash = ""
    autopilot = XyFussForexAutopilot(
        settings={
            "server_host": args.host,
            "server_port": args.port,
            "scheduler_interval_seconds": settings.scheduler_interval_seconds,
            "trading_mode": settings.trading_mode,
            "live_trading_enabled": settings.live_trading_enabled,
            "demo_execution_enabled": settings.demo_execution_enabled,
            "dashboard_access_token": settings.dashboard_access_token,
            "dashboard_password_hash": dashboard_password_hash,
        }
    )

    if args.command == "setup-dashboard":
        from xyfuss_forex_autopilot.auth import generate_dashboard_password, hash_password, save_dashboard_hash

        try:
            password = getpass.getpass("New dashboard password (input will be hidden): ")
            confirmation = getpass.getpass("Confirm dashboard password: ")
        except (EOFError, KeyboardInterrupt):
            print("Dashboard setup cancelled.")
            return 1
        if not password or not hmac.compare_digest(password, confirmation):
            print("Dashboard password setup cancelled: passwords were empty or did not match.")
            return 1
        save_dashboard_hash(hash_password(password))
        print("Generated dashboard credentials were stored as a restricted password hash.")
        return 0

    if args.command == "configure-mt5-demo":
        print("MT5 demo credentials must be supplied through Codespaces or environment secrets.")
        print("Required variables: MT5_DEMO_LOGIN, MT5_DEMO_PASSWORD, MT5_DEMO_SERVER.")
        return 1

    if args.command == "test-mt5-demo":
        from xyfuss_forex_autopilot.auth import load_mt5_demo_credentials
        from xyfuss_forex_autopilot.brokers import MT5IntegrationError, create_broker_adapter

        credentials = load_mt5_demo_credentials(settings.mt5_demo_credentials_file)
        if not credentials:
            print("MT5 demo integration is not configured.")
            return 1
        try:
            adapter = create_broker_adapter(
                "mt5-demo",
                credentials=credentials,
                live_trading_enabled=False,
            )
            if not adapter.connect():
                print("MT5 demo connection failed.")
                return 1
            account = adapter.get_account_info()
            prices = adapter.get_market_prices(["EUR/USD", "GBP/USD"])
            print(
                "MT5 demo account connected; "
                f"balance_available={account.get('balance') is not None} "
                f"currency={account.get('currency', 'unknown')}"
            )
            print(f"MT5 demo prices: {prices}")
            health = adapter.health_check()
            if not health["healthy"]:
                print("MT5 demo connection health check failed.")
                return 1
            print(f"MT5 demo health: {health}")
            print("MT5 demo integration passed; all real-money order execution remains blocked; no trades placed.")
            return 0
        except (MT5IntegrationError, OSError) as exc:
            from xyfuss_forex_autopilot.auth import redact_secrets
            print(f"MT5 demo integration failed: {redact_secrets(type(exc).__name__, credentials)}")
            return 1
        finally:
            if "adapter" in locals():
                adapter.disconnect()

    if args.command == "status":
        print("XYFUSS Forex Autopilot is operational in paper-only mode.")
        print(f"Mode: {settings.trading_mode}")
        print(f"Live trading enabled: {settings.live_trading_enabled}")
        print(f"Demo order execution enabled: {settings.demo_execution_enabled}")
        return 0

    if args.command == "simulate":
        sample_data = [
            {"open": 1.1000, "high": 1.1050, "low": 1.0990, "close": 1.1030, "volume": 120000},
            {"open": 1.1030, "high": 1.1090, "low": 1.1010, "close": 1.1080, "volume": 135000},
            {"open": 1.1080, "high": 1.1120, "low": 1.1060, "close": 1.1100, "volume": 140000},
            {"open": 1.1100, "high": 1.1150, "low": 1.1080, "close": 1.1135, "volume": 155000},
            {"open": 1.1135, "high": 1.1180, "low": 1.1110, "close": 1.1160, "volume": 160000},
        ]
        market_data = autopilot.investigate_market("EUR/USD", sample_data)
        result = autopilot.decide_trade("EUR/USD", sample_data, balance=10000.0)
        print(market_data)
        print(result)
        return 0

    if args.command == "paper-trade":
        sample_data = [
            {"open": 1.0900, "high": 1.0980, "low": 1.0880, "close": 1.0940, "volume": 120000},
            {"open": 1.0940, "high": 1.1000, "low": 1.0920, "close": 1.0985, "volume": 130000},
            {"open": 1.0985, "high": 1.1010, "low": 1.0950, "close": 1.0990, "volume": 135000},
            {"open": 1.0990, "high": 1.1035, "low": 1.0960, "close": 1.1015, "volume": 140000},
            {"open": 1.1015, "high": 1.1075, "low": 1.0990, "close": 1.1055, "volume": 150000},
        ]
        result = autopilot.decide_trade("EUR/USD", sample_data, balance=10000.0)
        print(result)
        return 0

    if args.command == "dashboard":
        dashboard = autopilot.run_dashboard(host=args.host, port=args.port)
        print(f"Dashboard running at http://{args.host}:{args.port}")
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            dashboard.stop()
        return 0

    if args.command == "audit":
        print(autopilot.audit.report())
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
