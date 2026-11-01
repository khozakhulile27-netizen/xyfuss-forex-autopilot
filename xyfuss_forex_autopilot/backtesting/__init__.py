from __future__ import annotations


class NoTradeDecisionEngine:
    """Prevents trading under weak or unsafe conditions."""

    def decide(self, market_data: dict, evidence_verification: dict, recommendation_score: float) -> dict:
        reasons: list[str] = []
        if market_data.get("signal") == "NO_TRADE":
            reasons.append("No valid trend signal.")
        if not evidence_verification.get("passed", False):
            reasons.append("Evidence verification failed.")
        if recommendation_score < 0.55:
            reasons.append("Recommendation score below threshold.")
        if market_data.get("confidence", 0.0) < 0.5:
            reasons.append("Market confidence is weak.")

        return {
            "no_trade": bool(reasons),
            "reasons": reasons,
            "decision": "NO_TRADE" if reasons else "TRADE_ALLOWED",
        }
