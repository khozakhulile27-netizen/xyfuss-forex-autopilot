from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from xyfuss_forex_autopilot.models import EvidenceRecord, TradeIdea


class HistoricalTradeInvestigator:
    """Analyze historical wins and losses to find recurring patterns."""

    def investigate(self, history: Iterable[dict]) -> dict:
        trades = list(history)
        if not trades:
            return {"wins": 0, "losses": 0, "win_rate": 0.0, "patterns": [], "summary": "No historical trade data."}

        wins = [trade for trade in trades if trade.get("outcome") == "win"]
        losses = [trade for trade in trades if trade.get("outcome") == "loss"]
        win_rate = (len(wins) / len(trades)) * 100.0 if trades else 0.0

        patterns: list[str] = []
        if wins:
            directions = [trade.get("direction", "") for trade in wins]
            if directions:
                top_direction = max(set(directions), key=directions.count)
                patterns.append(f"Most wins favored {top_direction} trades.")
        if losses:
            risk_contexts = [trade.get("risk_context", "") for trade in losses if trade.get("risk_context")]
            if risk_contexts:
                patterns.append("Losses clustered around elevated risk or weak confirmation.")

        return {
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(win_rate, 2),
            "patterns": patterns,
            "summary": f"Historical review found {len(wins)} wins and {len(losses)} losses.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


class TradeIdeaBuilder:
    def build(self, symbol: str, direction: str, score: float, confidence: float, evidence: list[dict], rationale: str) -> TradeIdea:
        evidence_records = [
            EvidenceRecord(
                source=item.get("source", "unknown"),
                signal=item.get("signal", direction),
                score=float(item.get("score", 0.0)),
                detail=item.get("detail", rationale),
                confidence=float(item.get("confidence", confidence)),
            )
            for item in evidence
        ]
        return TradeIdea(
            symbol=symbol,
            direction=direction,
            score=score,
            confidence=confidence,
            risk=max(0.0, 1.0 - confidence),
            rationale=rationale,
            evidence=evidence_records,
        )
