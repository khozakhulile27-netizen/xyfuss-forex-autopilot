from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Settings:
    project_name: str = "xyfuss-forex-autopilot"
    trading_mode: str = "paper"
    live_trading_enabled: bool = False
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


def load_settings(path: str | None = None) -> Settings:
    settings = Settings()
    if not path:
        return settings

    config_file = Path(path)
    if not config_file.exists():
        return settings

    try:
        import yaml  # type: ignore
    except ImportError:
        return settings

    with config_file.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    for key, value in raw.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
    return settings
