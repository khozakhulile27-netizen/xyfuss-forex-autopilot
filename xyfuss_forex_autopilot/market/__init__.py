from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable


class MarketInvestigator:
    """Collect market evidence using simple deterministic indicators."""

    def investigate(self, symbol: str, candles: Iterable[dict]) -> dict:
        bars = list(candles)
        if not bars:
            return {
                "symbol": symbol,
                "summary": "No market data available",
                "trend": "neutral",
                "confidence": 0.0,
                "evidence": [],
                "signal": "NO_TRADE",
            }

        closes = [float(item["close"]) for item in bars]
        highs = [float(item["high"]) for item in bars]
        lows = [float(item["low"]) for item in bars]
        volumes = [float(item.get("volume", 0.0)) for item in bars]
        recent = bars[-1]
        previous = bars[-2] if len(bars) > 1 else bars[0]

        momentum = closes[-1] - closes[-2] if len(closes) > 1 else 0.0
        volatility = max(highs) - min(lows)
        avg_volume = sum(volumes) / len(volumes)
        support = min(lows)
        resistance = max(highs)
        close_vs_open = recent["close"] - recent["open"]

        trend = "bullish" if closes[-1] > closes[0] else "bearish" if closes[-1] < closes[0] else "neutral"
        evidence = []

        if momentum > 0:
            evidence.append({"source": "momentum", "signal": "bullish", "score": min(1.0, abs(momentum) / 100.0), "detail": "Recent close is above prior close", "confidence": 0.7})
        elif momentum < 0:
            evidence.append({"source": "momentum", "signal": "bearish", "score": min(1.0, abs(momentum) / 100.0), "detail": "Recent close is below prior close", "confidence": 0.7})

        if close_vs_open > 0:
            evidence.append({"source": "candlestick", "signal": "bullish", "score": min(1.0, abs(close_vs_open) / 50.0), "detail": "Current candle closed above open", "confidence": 0.6})
        elif close_vs_open < 0:
            evidence.append({"source": "candlestick", "signal": "bearish", "score": min(1.0, abs(close_vs_open) / 50.0), "detail": "Current candle closed below open", "confidence": 0.6})

        if recent["close"] >= resistance * 0.98:
            evidence.append({"source": "resistance", "signal": "bullish", "score": 0.5, "detail": "Price is near resistance zone", "confidence": 0.5})
        if recent["close"] <= support * 1.02:
            evidence.append({"source": "support", "signal": "bearish", "score": 0.5, "detail": "Price is near support zone", "confidence": 0.5})

        if avg_volume > 0:
            evidence.append({"source": "volume", "signal": "trend-confirmed", "score": min(1.0, avg_volume / 1000000.0), "detail": f"Average volume is {avg_volume:.2f}", "confidence": 0.5})

        net_score = sum(item["score"] for item in evidence) / max(len(evidence), 1)
        confidence = min(0.99, max(0.05, net_score * 0.8 + 0.2))

        if trend == "bullish" and confidence > 0.55:
            signal = "BUY"
        elif trend == "bearish" and confidence > 0.55:
            signal = "SELL"
        else:
            signal = "NO_TRADE"

        return {
            "symbol": symbol,
            "summary": f"Market investigation for {symbol} using {len(bars)} candles",
            "trend": trend,
            "confidence": round(confidence, 4),
            "evidence": evidence,
            "signal": signal,
            "support": support,
            "resistance": resistance,
            "volatility": volatility,
            "last_close": closes[-1],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "previous_close": previous["close"],
        }

    def validate_freshness(self, candles: Iterable[dict], max_age_seconds: float = 300.0, now: datetime | None = None) -> dict:
        bars = list(candles)
        if not bars:
            return {"fresh": False, "reason": "No market data is available."}
        raw_timestamp = bars[-1].get("timestamp")
        if raw_timestamp is None:
            return {"fresh": False, "reason": "Latest candle has no timestamp."}
        try:
            timestamp = raw_timestamp
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            return {"fresh": False, "reason": "Latest candle timestamp is invalid."}
        current = now or datetime.now(timezone.utc)
        age_seconds = (current.astimezone(timezone.utc) - timestamp.astimezone(timezone.utc)).total_seconds()
        if age_seconds < 0:
            return {"fresh": False, "reason": "Latest candle timestamp is in the future."}
        if age_seconds > max_age_seconds:
            return {"fresh": False, "reason": "Market data is stale.", "age_seconds": age_seconds}
        return {"fresh": True, "reason": "Market data is current.", "age_seconds": age_seconds}


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
    def build(self, symbol: str, direction: str, score: float, confidence: float, evidence: list[dict], rationale: str):
        return {
            "symbol": symbol,
            "direction": direction,
            "score": score,
            "confidence": confidence,
            "rationale": rationale,
            "evidence": evidence,
        }


class MarketUniverseScanner:
    """Scan an explicit broker-symbol allowlist and rank evidence-backed candidates.

    This component never submits, modifies, or closes broker orders.
    """

    def __init__(
        self,
        market_investigator: MarketInvestigator | None = None,
        strategy_engine=None,
        evidence_verifier=None,
        no_trade_engine=None,
    ):
        from xyfuss_forex_autopilot.backtesting import NoTradeDecisionEngine
        from xyfuss_forex_autopilot.recommendations import EvidenceVerifier
        from xyfuss_forex_autopilot.strategies import StrategyCompetitionEngine

        self.market_investigator = market_investigator or MarketInvestigator()
        self.strategy_engine = strategy_engine or StrategyCompetitionEngine()
        self.evidence_verifier = evidence_verifier or EvidenceVerifier()
        self.no_trade_engine = no_trade_engine or NoTradeDecisionEngine()

    @staticmethod
    def _normalise_symbol(symbol: str) -> str:
        return str(symbol).upper().replace("/", "").replace("_", "").replace("-", "").strip()

    def scan(
        self,
        broker,
        allowed_symbols: Iterable[str],
        period: str = "M5",
        weeks: int = 1,
        count: int = 500,
        max_age_seconds: float = 900.0,
        minimum_candles: int = 30,
    ) -> dict:
        requested = []
        seen = set()
        for item in allowed_symbols:
            symbol = str(item).strip()
            key = self._normalise_symbol(symbol)
            if key and key not in seen:
                requested.append((symbol, key))
                seen.add(key)

        if not requested:
            return {
                "status": "blocked",
                "reason": "An explicit non-empty market symbol allowlist is required.",
                "scanned": 0,
                "candidates": [],
                "best_candidate": None,
                "no_trade": [],
            }

        available = broker.get_market_data()
        by_name = {
            self._normalise_symbol(item.get("name", "")): item
            for item in available
            if item.get("name")
        }
        results = []
        candidates = []

        for requested_name, key in requested:
            metadata = by_name.get(key)
            if metadata is None:
                results.append({
                    "symbol": requested_name,
                    "decision": "NO_TRADE",
                    "reason": "Symbol is not available on the authorised broker account.",
                })
                continue

            try:
                candles = broker.get_historical_bars(
                    symbol_id=int(metadata["symbol_id"]),
                    period=period,
                    weeks=weeks,
                    count=count,
                )
                if len(candles) < minimum_candles:
                    results.append({
                        "symbol": requested_name,
                        "decision": "NO_TRADE",
                        "reason": "Insufficient historical candles for investigation.",
                        "candle_count": len(candles),
                    })
                    continue

                freshness = self.market_investigator.validate_freshness(
                    candles,
                    max_age_seconds=max_age_seconds,
                )
                if not freshness["fresh"]:
                    results.append({
                        "symbol": requested_name,
                        "decision": "NO_TRADE",
                        "reason": freshness["reason"],
                        "freshness": freshness,
                    })
                    continue

                market = self.market_investigator.investigate(requested_name, candles)
                strategies = self.strategy_engine.run(requested_name, market)
                directional = [
                    item for item in strategies
                    if str(getattr(item, "direction", "")).lower() in {"buy", "sell"}
                ]
                if not directional:
                    results.append({
                        "symbol": requested_name,
                        "decision": "NO_TRADE",
                        "reason": "No strategy produced a directional candidate.",
                        "market": market,
                    })
                    continue

                best = max(directional, key=lambda item: float(item.score))
                evidence = self.evidence_verifier.verify(
                    market.get("evidence", []),
                    threshold=0.55,
                )
                decision = self.no_trade_engine.decide(
                    market,
                    evidence,
                    float(best.score),
                )
                if decision["no_trade"]:
                    results.append({
                        "symbol": requested_name,
                        "decision": "NO_TRADE",
                        "reason": decision["reasons"],
                        "market": market,
                        "evidence": evidence,
                    })
                    continue

                candidate = {
                    "symbol": requested_name,
                    "decision": "CANDIDATE_FOR_RISK_ASSESSMENT",
                    "direction": str(best.direction).lower(),
                    "strategy": str(best.strategy_name),
                    "score": float(best.score),
                    "confidence": float(best.confidence),
                    "rationale": str(best.rationale),
                    "market": market,
                    "evidence": evidence,
                    "freshness": freshness,
                }
                candidates.append(candidate)
                results.append(candidate)
            except Exception as exc:
                results.append({
                    "symbol": requested_name,
                    "decision": "NO_TRADE",
                    "reason": "Market investigation failed; the symbol was rejected.",
                    "error_type": type(exc).__name__,
                })

        candidates.sort(
            key=lambda item: (item["score"], item["confidence"]),
            reverse=True,
        )
        return {
            "status": "complete",
            "period": period,
            "scanned": len(requested),
            "candidate_count": len(candidates),
            "candidates": candidates,
            "best_candidate": candidates[0] if candidates else None,
            "no_trade": [item for item in results if item["decision"] == "NO_TRADE"],
            "results": results,
        }
