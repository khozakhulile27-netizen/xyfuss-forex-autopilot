from xyfuss_forex_autopilot.core import XyFussForexAutopilot


def test_full_cycle_runs_without_live_trade():
    autopilot = XyFussForexAutopilot()
    candles = [
        {"open": 1.1000, "high": 1.1030, "low": 1.0990, "close": 1.1015, "volume": 120000},
        {"open": 1.1015, "high": 1.1060, "low": 1.1005, "close": 1.1040, "volume": 130000},
        {"open": 1.1040, "high": 1.1090, "low": 1.1038, "close": 1.1078, "volume": 140000},
        {"open": 1.1078, "high": 1.1120, "low": 1.1060, "close": 1.1105, "volume": 150000},
        {"open": 1.1105, "high": 1.1160, "low": 1.1085, "close": 1.1138, "volume": 170000},
    ]

    decision = autopilot.decide_trade("EUR/USD", candles, balance=10000.0)
    assert decision["decision"] in {"TRADE_ALLOWED", "NO_TRADE"}
    assert "reason" in decision or "market" in decision
