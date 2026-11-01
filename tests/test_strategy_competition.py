from xyfuss_forex_autopilot.market import MarketInvestigator


def test_market_investigator_builds_signal():
    candles = [
        {"open": 1.1000, "high": 1.1020, "low": 1.0990, "close": 1.1010, "volume": 120000},
        {"open": 1.1010, "high": 1.1040, "low": 1.1000, "close": 1.1030, "volume": 130000},
        {"open": 1.1030, "high": 1.1060, "low": 1.1020, "close": 1.1050, "volume": 135000},
        {"open": 1.1050, "high": 1.1080, "low": 1.1030, "close": 1.1070, "volume": 150000},
        {"open": 1.1070, "high": 1.1100, "low": 1.1050, "close": 1.1090, "volume": 145000},
    ]

    result = MarketInvestigator().investigate("EUR/USD", candles)

    assert result["symbol"] == "EUR/USD"
    assert result["signal"] in {"BUY", "SELL", "NO_TRADE"}
    assert result["confidence"] > 0.0
