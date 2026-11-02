from __future__ import annotations


from dataclasses import dataclass, field
from datetime import datetime, timezone
from math import isfinite


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

    def open_trade(self, trade_id: str, symbol: str, direction: str, lot_size: float, entry_price: float, stop_loss: float, take_profit: float, spread: float = 0.0, slippage: float = 0.0) -> PaperTrade:
        entry = float(entry_price)
        stop = float(stop_loss)
        target = float(take_profit)
        direction = direction.lower()
        if not all(isfinite(price) and price > 0 for price in (entry, stop, target)):
            raise ValueError("Stop-loss validation failed; paper order rejected.")
        if direction == "buy":
            stop_valid = stop < entry - spread - slippage and target > entry + spread + slippage
        elif direction == "sell":
            stop_valid = stop > entry + spread + slippage and target < entry - spread - slippage
        else:
            stop_valid = False
        if not stop_valid:
            raise ValueError("Stop-loss validation failed; paper order rejected.")
        trade = PaperTrade(trade_id, symbol, direction, lot_size, entry, stop, target)
        self.trades.append(trade)
        return trade

    def close_trade(self, trade_id: str, close_price: float) -> dict:
        for trade in self.trades:
            if trade.trade_id == trade_id:
                if trade.status != "open":
                    return {"trade_id": trade_id, "status": "duplicate_close", "pnl": 0.0}
                pnl = ((close_price - trade.entry_price) if trade.direction == "buy" else (trade.entry_price - close_price)) * trade.lot_size
                trade.status = "closed"
                return {"trade_id": trade_id, "pnl": round(pnl, 2), "closed_at": datetime.now(timezone.utc).isoformat()}
        raise KeyError(f"Trade {trade_id} not found.")


class Backtester:
    """Simple historical simulation engine used for development testing."""

    def run(self, trades: list[dict], starting_balance: float = 10000.0) -> dict:
        balance = starting_balance
        net_profit = 0.0
        wins = 0
        losses = 0
        for trade in trades:
            pnl = float(trade.get("pnl", 0.0))
            if trade.get("outcome", "loss") == "win":
                wins += 1
            else:
                losses += 1
            balance += pnl
            net_profit += pnl
        return {"starting_balance": starting_balance, "final_balance": round(balance, 2), "net_profit": round(net_profit, 2), "wins": wins, "losses": losses, "win_rate": round(wins / len(trades) * 100.0, 2) if trades else 0.0}
