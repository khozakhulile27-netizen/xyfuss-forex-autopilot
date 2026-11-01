from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RiskProfile:
    daily_risk_limit_pct: float = 1.5
    max_drawdown_pct: float = 10.0
    position_risk_pct: float = 0.5
    max_positions: int = 3
    account_balance: float = 10000.0
    correlated_pair_exposure_limit: float = 0.65


class RiskManager:
    """Protect capital with strict risk thresholds and independent stop validation."""

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

    def enforce_daily_loss_limit(self, balance: float, daily_loss_so_far: float) -> dict:
        limit = balance * (self.profile.daily_risk_limit_pct / 100.0)
        if daily_loss_so_far >= limit:
            return {"allowed": False, "reason": "Daily loss limit reached."}
        return {"allowed": True, "reason": "Daily loss limit is not breached."}

    def enforce_drawdown_limit(self, balance: float, drawdown_so_far: float) -> dict:
        limit = balance * (self.profile.max_drawdown_pct / 100.0)
        if drawdown_so_far >= limit:
            return {"allowed": False, "reason": "Maximum drawdown reached."}
        return {"allowed": True, "reason": "Drawdown is within limit."}

    def enforce_correlated_exposure(self, open_positions: list[dict], new_symbol: str, exposure_limit: float | None = None) -> dict:
        limit = exposure_limit if exposure_limit is not None else self.profile.correlated_pair_exposure_limit
        correlated = 0.0
        for position in open_positions:
            if position.get("symbol") == new_symbol:
                correlated += 1.0
        if correlated >= limit:
            return {"allowed": False, "reason": "Correlated exposure limit would be exceeded."}
        return {"allowed": True, "reason": "Correlated exposure remains within limits."}

    def verify_trade_risk(self, balance: float, stop_distance_pct: float, recommendation_score: float, daily_loss_so_far: float, drawdown_so_far: float, open_positions: list[dict], risk_pct: float | None = None) -> dict:
        result = self.assess_trade(balance, stop_distance_pct, risk_pct=risk_pct, recommendation_score=recommendation_score)
        if not result["approved"]:
            return {"allowed": False, "reason": result["reason"], "risk": result}

        daily_result = self.enforce_daily_loss_limit(balance, daily_loss_so_far)
        drawdown_result = self.enforce_drawdown_limit(balance, drawdown_so_far)
        if not daily_result["allowed"]:
            return {"allowed": False, "reason": daily_result["reason"], "risk": result}
        if not drawdown_result["allowed"]:
            return {"allowed": False, "reason": drawdown_result["reason"], "risk": result}

        exposure_result = self.enforce_correlated_exposure(open_positions, "", exposure_limit=self.profile.correlated_pair_exposure_limit)
        if not exposure_result["allowed"]:
            return {"allowed": False, "reason": exposure_result["reason"], "risk": result}

        return {"allowed": True, "reason": "Risk checks passed.", "risk": result}
