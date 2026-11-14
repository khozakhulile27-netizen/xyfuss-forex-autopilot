from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os


@dataclass
class Settings:
    project_name: str = "xyfuss-forex-autopilot"
    trading_mode: str = "paper"
    live_trading_enabled: bool = False
    demo_execution_enabled: bool = False
    default_currency: str = "USD"
    max_daily_risk_pct: float = 1.5
    max_position_risk_pct: float = 0.5
    max_positions: int = 3
    default_pair: str = "EUR/USD"
    allowed_pairs: list[str] = field(default_factory=lambda: ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD"])
    backtest_enabled: bool = True
    paper_trade_enabled: bool = True
    telemetry_enabled: bool = True
    log_level: str = "INFO"
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    scheduler_interval_seconds: int = 300
    dashboard_access_token: str = ""
    profit_allocation_ledger: str = "data/profit_allocation.jsonl"
    trading_state_path: str = "data/trading-state.json"
    broker_adapter: str = "paper"
    broker_credentials: dict[str, str] = field(default_factory=dict)
    dashboard_password_hash: str = ""
    mt5_demo_credentials_file: str = "data/credentials/mt5-demo.json"


def load_settings(path: str | None = None) -> Settings:
    settings = Settings()
    if path:
        config_file = Path(path)
        if config_file.exists():
            try:
                import yaml  # type: ignore
            except ImportError:
                raw = {}
            else:
                with config_file.open("r", encoding="utf-8") as handle:
                    raw = yaml.safe_load(handle) or {}
            for key, value in raw.items():
                if hasattr(settings, key):
                    setattr(settings, key, value)

    environment_live_flag = os.getenv("XYFUSS_LIVE_TRADING_ENABLED", "").strip().lower() in {"1", "true", "yes"}
    human_approval = os.getenv("XYFUSS_LIVE_TRADING_APPROVAL", "") == "I_UNDERSTAND_LIVE_TRADING"
    environment_demo_flag = os.getenv("XYFUSS_DEMO_EXECUTION_ENABLED", "").strip().lower() in {"1", "true", "yes"}
    settings.dashboard_access_token = os.getenv("XYFUSS_DASHBOARD_ACCESS_TOKEN", settings.dashboard_access_token)
    settings.live_trading_enabled = bool(settings.live_trading_enabled and environment_live_flag and human_approval)
    settings.demo_execution_enabled = bool(
        settings.demo_execution_enabled and environment_demo_flag and not settings.live_trading_enabled
    )
    if settings.live_trading_enabled:
        settings.trading_mode = "live"
    else:
        settings.trading_mode = "paper"
    return settings
