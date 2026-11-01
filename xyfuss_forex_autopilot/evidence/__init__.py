from __future__ import annotations

from typing import Iterable

from xyfuss_forex_autopilot.models import StrategyResult


class StrategyBase:
    name: str = "base"

    def evaluate(self, symbol: str, market_data: dict) -> StrategyResult:
        raise NotImplementedError


class TrendFollowerStrategy(StrategyBase):
    name = "trend_follower"

    def evaluate(self, symbol: str, market_data: dict) -> StrategyResult:
        signal = market_data.get("signal", "NO_TRADE")
        confidence = float(market_data.get("confidence", 0.0))
        trend = market_data.get("trend", "neutral")

        if signal == "BUY":
            return StrategyResult(
                strategy_name=self.name,
                symbol=symbol,
                score=0.7 + confidence * 0.3,
                direction="buy",
                confidence=confidence,
                rationale="Trend and momentum favor upside continuation.",
            )
        if signal == "SELL":
            return StrategyResult(
                strategy_name=self.name,
                symbol=symbol,
                score=0.7 + confidence * 0.3,
                direction="sell",
                confidence=confidence,
                rationale="Trend and momentum favor downside continuation.",
            )
        return StrategyResult(
            strategy_name=self.name,
            symbol=symbol,
            score=0.2,
            direction="hold",
            confidence=confidence,
            rationale="Market structure is too weak for directional conviction.",
        )


class MeanReversionStrategy(StrategyBase):
    name = "mean_reversion"

    def evaluate(self, symbol: str, market_data: dict) -> StrategyResult:
        signal = market_data.get("signal", "NO_TRADE")
        confidence = float(market_data.get("confidence", 0.0))
        support = float(market_data.get("support", 0.0))
        last_close = float(market_data.get("last_close", 0.0))

        if signal in {"BUY", "SELL"} and support and last_close:
            direction = "buy" if signal == "BUY" else "sell"
            return StrategyResult(
                strategy_name=self.name,
                symbol=symbol,
                score=0.6 + confidence * 0.25,
                direction=direction,
                confidence=confidence,
                rationale="Price is returning toward support/resistance after a short directional move.",
            )
        return StrategyResult(
            strategy_name=self.name,
            symbol=symbol,
            score=0.15,
            direction="hold",
            confidence=confidence,
            rationale="No mean-reversion setup with enough conviction.",
        )


class VolatilityBreakoutStrategy(StrategyBase):
    name = "volatility_breakout"

    def evaluate(self, symbol: str, market_data: dict) -> StrategyResult:
        volatility = float(market_data.get("volatility", 0.0))
        confidence = float(market_data.get("confidence", 0.0))
        trend = market_data.get("trend", "neutral")

        if volatility > 0 and trend != "neutral":
            direction = "buy" if trend == "bullish" else "sell"
            return StrategyResult(
                strategy_name=self.name,
                symbol=symbol,
                score=0.65 + min(confidence, 0.8),
                direction=direction,
                confidence=confidence,
                rationale="Volatility expansion supports a directional breakout.",
            )
        return StrategyResult(
            strategy_name=self.name,
            symbol=symbol,
            score=0.18,
            direction="hold",
            confidence=confidence,
            rationale="Breakout conditions are not present.",
        )


class StrategyCompetitionEngine:
    def __init__(self, strategies: Iterable[StrategyBase] | None = None):
        self.strategies = list(strategies or [TrendFollowerStrategy(), MeanReversionStrategy(), VolatilityBreakoutStrategy()])

    def run(self, symbol: str, market_data: dict) -> list[StrategyResult]:
        results = [strategy.evaluate(symbol, market_data) for strategy in self.strategies]
        return sorted(results, key=lambda item: item.score, reverse=True)
