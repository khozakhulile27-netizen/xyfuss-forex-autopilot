from xyfuss_forex_autopilot.strategies import StrategyCompetitionEngine


def test_strategy_competition_ranks_best_strategy():
    market_data = {
        "signal": "BUY",
        "confidence": 0.8,
        "trend": "bullish",
        "volatility": 0.55,
        "support": 1.10,
        "last_close": 1.12,
    }

    results = StrategyCompetitionEngine().run("EUR/USD", market_data)
    assert results
    assert results[0].direction in {"buy", "sell", "hold"}
    assert max(item.score for item in results) >= 0.0
