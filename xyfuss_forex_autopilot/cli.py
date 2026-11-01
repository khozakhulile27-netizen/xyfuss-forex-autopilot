from __future__ import annotations

import argparse
from pathlib import Path

from xyfuss_forex_autopilot.config import load_settings
from xyfuss_forex_autopilot.core import XyFussForexAutopilot


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="XYFUSS Forex Autopilot")
    parser.add_argument(
        "command",
        choices=["status", "simulate", "paper-trade", "dashboard", "audit"],
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
    autopilot = XyFussForexAutopilot(
        settings={
            "server_host": args.host,
            "server_port": args.port,
            "scheduler_interval_seconds": settings.scheduler_interval_seconds,
        }
    )

    if args.command == "status":
        print("XYFUSS Forex Autopilot is ready.")
        print(f"Mode: {settings.trading_mode}")
        print(f"Live trading enabled: {settings.live_trading_enabled}")
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
