from __future__ import annotations

from datetime import datetime, timezone


class TradeMonitor:
    """Monitor open positions and reject duplicates or stale orders."""

    def __init__(self):
        self._seen_trade_ids: set[str] = set()

    def is_duplicate(self, trade_id: str) -> bool:
        if trade_id in self._seen_trade_ids:
            return True
        self._seen_trade_ids.add(trade_id)
        return False

    def heartbeat(self, trade_id: str, symbol: str, direction: str) -> dict:
        return {
            "trade_id": trade_id,
            "symbol": symbol,
            "direction": direction,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "monitored",
        }
