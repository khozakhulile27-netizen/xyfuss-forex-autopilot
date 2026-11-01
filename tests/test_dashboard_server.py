from xyfuss_forex_autopilot.core import XyFussForexAutopilot


def test_backtester_simulation_returns_summary():
    autopilot = XyFussForexAutopilot()
    trades = [
        {"outcome": "win", "pnl": 100.0},
        {"outcome": "loss", "pnl": -40.0},
        {"outcome": "win", "pnl": 85.0},
    ]
    result = autopilot.run_backtest(trades)
    assert result["wins"] == 2
    assert result["losses"] == 1
    assert result["final_balance"] > 10000.0
