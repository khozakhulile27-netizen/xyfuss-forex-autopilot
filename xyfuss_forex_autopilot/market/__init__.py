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
