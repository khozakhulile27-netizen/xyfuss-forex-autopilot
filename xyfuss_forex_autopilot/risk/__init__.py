from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable


@dataclass
class RiskProfile:
    daily_risk_limit_pct: float = 1.5
    max_drawdown_pct: float = 10.0
    position_risk_pct: float = 0.5
    max_positions: int = 3
    account_balance: float = 10000.0
    correlated_pair_exposure_limit: float = 1.0
    atr_stop_multiplier: float = 2.0
    atr_trailing_multiplier: float = 1.5
    minimum_risk_reward: float = 1.5


class StopLossEngine:
    """Calculate and protect stop-loss and take-profit levels from market data."""

    def calculate_atr(self, candles: Iterable[dict], period: int = 14) -> float:
        bars = list(candles)
        if len(bars) < 2:
            return 0.0
        true_ranges = []
        previous_close = None
        for bar in bars:
            high = float(bar["high"])
            low = float(bar["low"])
            close = float(bar["close"])
            true_range = high - low
            if previous_close is not None:
                true_range = max(true_range, abs(high - previous_close), abs(low - previous_close))
            true_ranges.append(true_range)
            previous_close = close
        sample = true_ranges[-period:] if period > 0 else true_ranges
        return sum(sample) / len(sample) if sample else 0.0

    def transaction_cost(self, entry_price: float, spread: float, slippage: float = 0.0) -> dict:
        spread = max(0.0, float(spread))
        slippage = max(0.0, float(slippage))
        total = spread + slippage
        return {"spread": spread, "slippage": slippage, "total": total, "pct": total / entry_price if entry_price else 0.0}

    def calculate_stop(self, entry_price: float, direction: str, candles: Iterable[dict], support: float | None = None, resistance: float | None = None, atr_multiplier: float = 2.0, spread: float = 0.0, slippage: float = 0.0) -> dict:
        entry = float(entry_price)
        atr = self.calculate_atr(candles)
        if atr <= 0 or not isfinite(atr):
            raise ValueError("ATR requires valid high, low, and close market data.")
        direction = direction.lower()
        costs = self.transaction_cost(entry, spread, slippage)["total"]
        if direction == "buy":
            technical_stop = entry - atr * atr_multiplier
            if support is not None:
                technical_stop = min(technical_stop, float(support) - costs)
            stop_loss = technical_stop - costs
        elif direction == "sell":
            technical_stop = entry + atr * atr_multiplier
            if resistance is not None:
                technical_stop = max(technical_stop, float(resistance) + costs)
            stop_loss = technical_stop + costs
        else:
            raise ValueError("direction must be 'buy' or 'sell'.")
        return {"stop_loss": stop_loss, "atr": atr, "transaction_cost": costs}

    def calculate_take_profit(self, entry_price: float, stop_loss: float, direction: str, risk_reward: float = 1.5, spread: float = 0.0, slippage: float = 0.0) -> float:
        entry = float(entry_price)
        stop = float(stop_loss)
        costs = spread + slippage
        if direction.lower() == "buy":
            return entry + max(risk_reward, 0.0) * (entry - stop) + costs
        if direction.lower() == "sell":
            return entry - max(risk_reward, 0.0) * (stop - entry) - costs
        raise ValueError("direction must be 'buy' or 'sell'.")

    def validate_stop(self, entry_price: float, stop_loss: float, take_profit: float, direction: str, spread: float = 0.0, slippage: float = 0.0) -> dict:
        entry = float(entry_price)
        stop = float(stop_loss)
        target = float(take_profit)
        direction = direction.lower()
        if not all(isfinite(value) for value in (entry, stop, target)) or entry <= 0:
            return {"valid": False, "reason": "Stop-loss and take-profit must be finite positive prices."}
        cost_adjustment = spread + slippage
        if direction == "buy":
            valid = stop < entry - cost_adjustment and target > entry + cost_adjustment
        elif direction == "sell":
            valid = stop > entry + cost_adjustment and target < entry - cost_adjustment
        else:
            return {"valid": False, "reason": "direction must be 'buy' or 'sell'."}
        return {"valid": valid, "reason": "Stop-loss validated." if valid else "Stop-loss is not on the protective side of entry."}

    def update_trailing_stop(self, entry_price: float, current_price: float, stop_loss: float, direction: str, atr: float, multiplier: float = 1.5) -> float:
        if direction.lower() == "buy":
            candidate = current_price - atr * multiplier
            return max(stop_loss, candidate)
        if direction.lower() == "sell":
            candidate = current_price + atr * multiplier
            return min(stop_loss, candidate)
        raise ValueError("direction must be 'buy' or 'sell'.")

    def update_breakeven(self, entry_price: float, current_price: float, stop_loss: float, direction: str, spread: float = 0.0, slippage: float = 0.0) -> float:
        cost_buffer = spread + slippage
        if direction.lower() == "buy" and current_price >= entry_price + cost_buffer:
            return max(stop_loss, entry_price + cost_buffer)
        if direction.lower() == "sell" and current_price <= entry_price - cost_buffer:
            return min(stop_loss, entry_price - cost_buffer)
        return stop_loss


class RiskManager:
    """Protect capital with strict, independently verified risk thresholds."""

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
        allowed_position_risk = balance * (self.profile.position_risk_pct / 100.0)
        allowed_daily_risk = balance * (self.profile.daily_risk_limit_pct / 100.0)
        position_risk_value = position_size * stop_distance_pct
        approved = (
            recommendation_score >= 0.55
            and position_size > 0
            and stop_distance_pct < 0.20
            and position_risk_value <= allowed_position_risk
        )
        return {"approved": approved, "position_size": position_size, "allowed_daily_risk": allowed_daily_risk, "allowed_position_risk": allowed_position_risk, "risk_pct": risk_pct or self.profile.position_risk_pct, "reason": "Trade passes strict risk policy." if approved else "Trade rejected by risk policy."}

    def enforce_daily_loss_limit(self, balance: float, daily_loss_so_far: float) -> dict:
        limit = balance * self.profile.daily_risk_limit_pct / 100.0
        allowed = daily_loss_so_far < limit
        return {"allowed": allowed, "reason": "Daily loss limit is not breached." if allowed else "Daily loss limit reached."}

    def enforce_drawdown_limit(self, balance: float, drawdown_so_far: float) -> dict:
        limit = balance * self.profile.max_drawdown_pct / 100.0
        allowed = drawdown_so_far < limit
        return {"allowed": allowed, "reason": "Drawdown is within limit." if allowed else "Maximum drawdown reached."}

    @staticmethod
    def _currencies(symbol: str) -> set[str]:
        parts = symbol.upper().replace("_", "/").replace("-", "/").split("/")
        return {part for part in parts if part}

    def enforce_correlated_exposure(self, open_positions: list[dict], new_symbol: str, exposure_limit: float | None = None) -> dict:
        limit = exposure_limit if exposure_limit is not None else self.profile.correlated_pair_exposure_limit
        new_currencies = self._currencies(new_symbol)
        correlated = sum(1 for position in open_positions if self._currencies(str(position.get("symbol", ""))) & new_currencies)
        normalized = correlated / max(1, self.profile.max_positions)
        allowed = normalized < limit
        return {"allowed": allowed, "reason": "Correlated exposure remains within limits." if allowed else "Correlated currency exposure limit would be exceeded."}

    def verify_trade_risk(self, balance: float, stop_distance_pct: float, recommendation_score: float, daily_loss_so_far: float, drawdown_so_far: float, open_positions: list[dict], risk_pct: float | None = None, new_symbol: str = "") -> dict:
        result = self.assess_trade(balance, stop_distance_pct, risk_pct=risk_pct, recommendation_score=recommendation_score)
        if not result["approved"]:
            return {"allowed": False, "reason": result["reason"], "risk": result}
        for check in (
            self.enforce_daily_loss_limit(balance, daily_loss_so_far),
            self.enforce_drawdown_limit(balance, drawdown_so_far),
            self.enforce_correlated_exposure(open_positions, new_symbol),
        ):
            if not check["allowed"]:
                return {"allowed": False, "reason": check["reason"], "risk": result}
        return {"allowed": True, "reason": "Independent risk checks passed.", "risk": result}
