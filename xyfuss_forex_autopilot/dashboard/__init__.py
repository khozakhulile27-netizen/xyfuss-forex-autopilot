from __future__ import annotations

from dataclasses import dataclass

from xyfuss_forex_autopilot.scheduler import DashboardServer


@dataclass
class TradeOutcome:
    trade_id: str
    symbol: str
    signal: str
    result: str
    notes: str = ""


class LearningEngine:
    """Continuously record outcomes and build a historical lesson database."""

    def __init__(self):
        self.history: list[TradeOutcome] = []

    def add_outcome(self, trade_id: str, symbol: str, signal: str, result: str, notes: str = "") -> TradeOutcome:
        outcome = TradeOutcome(trade_id=trade_id, symbol=symbol, signal=signal, result=result, notes=notes)
        self.history.append(outcome)
        return outcome

    def summary(self) -> dict:
        wins = sum(1 for item in self.history if item.result == "win")
        losses = sum(1 for item in self.history if item.result == "loss")
        return {"total": len(self.history), "wins": wins, "losses": losses, "win_rate": round((wins / len(self.history)) * 100.0, 2) if self.history else 0.0}
