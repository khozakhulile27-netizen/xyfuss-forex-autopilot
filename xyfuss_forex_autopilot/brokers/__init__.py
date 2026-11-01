from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class PaperTrade:
    trade_id: str
    symbol: str
    direction: str
    lot_size: float
    entry_price: float
    stop_loss: float
    take_profit: float
    status: str = "open"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class PaperTradingEngine:
    """Place and monitor simulated orders without broker access."""

    def __init__(self):
        self.trades: list[PaperTrade] = []

    def open_trade(self, trade_id: str, symbol: str, direction: str, lot_size: float, entry_price: float, stop_loss: float, take_profit: float) -> PaperTrade:
        trade = PaperTrade(
            trade_id=trade_id,
            symbol=symbol,
            direction=direction,
            lot_size=lot_size,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )
        self.trades.append(trade)
        return trade

    def close_trade(self, trade_id: str, close_price: float) -> dict:
        for trade in self.trades:
            if trade.trade_id == trade_id:
                if trade.direction == "buy":
                    pnl = (close_price - trade.entry_price) * trade.lot_size
                else:
                    pnl = (trade.entry_price - close_price) * trade.lot_size
                trade.status = "closed"
                return {"trade_id": trade_id, "pnl": round(pnl, 2), "closed_at": datetime.now(timezone.utc).isoformat()}
        raise KeyError(f"Trade {trade_id} not found.")

    def list_trades(self) -> list[dict]:
        return [
            {
                "trade_id": trade.trade_id,
                "symbol": trade.symbol,
                "direction": trade.direction,
                "lot_size": trade.lot_size,
                "entry_price": trade.entry_price,
                "status": trade.status,
            }
            for trade in self.trades
        ]
