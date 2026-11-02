from __future__ import annotations

from xyfuss_forex_autopilot.brokers import (
    BrokerCapabilities,
    BrokerOrder,
    DirectBrokerAdapter,
    MT5Adapter,
    CTraderAdapter,
)


class BrokerAdapter:
    """Compatibility base for older monitoring imports."""

    name = "base"


class PaperBrokerAdapter(BrokerAdapter):
    name = "paper"

    def connect(self) -> bool:
        return True

    def get_account_info(self) -> dict:
        return {"balance": 10000.0, "status": "paper"}

    def place_order(self, symbol: str, direction: str, lot_size: float, price: float) -> dict:
        return {
            "status": "paper-only",
            "symbol": symbol,
            "direction": direction,
            "lot_size": lot_size,
            "price": price,
            "confirmation": "No real broker confirmation generated.",
        }

    def get_positions(self) -> list[dict]:
        return []


def connect_broker_safely(adapter: BrokerAdapter) -> dict:
    try:
        connected = bool(adapter.connect())
    except Exception as exc:
        return {"connected": False, "reason": f"Broker connection failed: {type(exc).__name__}"}
    return {"connected": connected, "reason": "Connected." if connected else "Broker connection was rejected."}


def place_paper_order_safely(adapter: BrokerAdapter, *args, **kwargs) -> dict:
    if adapter.name != "paper":
        return {"status": "rejected", "reason": "Live execution is disabled."}
    connection = connect_broker_safely(adapter)
    if not connection["connected"]:
        return {"status": "rejected", "reason": connection["reason"]}
    return adapter.place_order(*args, **kwargs)
