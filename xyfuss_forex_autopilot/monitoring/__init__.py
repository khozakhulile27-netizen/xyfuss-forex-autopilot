from __future__ import annotations

from abc import ABC, abstractmethod


class BrokerAdapter(ABC):
    """Abstract broker adapter framework. Live trading is disabled by default."""

    name: str = "base"

    @abstractmethod
    def connect(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_account_info(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def place_order(self, symbol: str, direction: str, lot_size: float, price: float) -> dict:
        raise NotImplementedError


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
