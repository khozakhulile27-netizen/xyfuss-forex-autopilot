from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RiskProfile:
    daily_risk_limit_pct: float = 1.5
    position_risk_pct: float = 0.5
    max_positions: int = 3
    account_balance: float = 10000.0


class RiskManager:
    """Protect capital with strict risk thresholds."""

    def __init__(self, profile: RiskProfile | None = None):
        self.profile = profile or RiskProfile()

    def calculate_position_size(self, balance: float, stop_distance_pct: float, risk_pct: float | None = None) -> float:
        risk_pct = risk_pct if risk_pct is not None else self.profile.position_risk_pct
        allowed_risk = balance * (risk_pct / 100.0)
        if stop_distance_pct <= 0:
            return 0.0
        return allowed_risk / stop_distance_pct

    def assess_trade(self, balance: float, stop_distance_pct: float, risk_pct: float | None = None, recommendation_score: float = 0.0) -> dict:
        position_size = self.calculate_position_size(balance, stop_distance_pct, risk_pct)
        allowed_daily_risk = balance * (self.profile.daily_risk_limit_pct / 100.0)
        allowed_position_risk = balance * (self.profile.position_risk_pct / 100.0)

        position_risk_value = position_size * stop_distance_pct
        approved = (
            recommendation_score >= 0.55
            and position_size > 0
            and position_risk_value <= allowed_position_risk
            and position_risk_value <= allowed_daily_risk
        )

        return {
            "approved": approved,
            "position_size": position_size,
            "allowed_daily_risk": allowed_daily_risk,
            "allowed_position_risk": allowed_position_risk,
            "risk_pct": self.profile.position_risk_pct,
            "reason": "Trade passes strict risk policy." if approved else "Trade rejected by risk policy.",
        }
