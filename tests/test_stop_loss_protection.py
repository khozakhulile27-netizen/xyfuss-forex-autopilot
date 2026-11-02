import pytest

from xyfuss_forex_autopilot.paper_trading import PaperTradingEngine
from xyfuss_forex_autopilot.risk import RiskManager, StopLossEngine


CANDLES = [
    {"high": 1.1100, "low": 1.1060, "close": 1.1080},
    {"high": 1.1120, "low": 1.1070, "close": 1.1100},
    {"high": 1.1130, "low": 1.1080, "close": 1.1110},
]


def test_atr_stop_support_resistance_and_costs():
    engine = StopLossEngine()
    atr = engine.calculate_atr(CANDLES)
    plan = engine.calculate_stop(1.1110, "buy", CANDLES, support=1.1085, spread=0.0002, slippage=0.0001)
    take_profit = engine.calculate_take_profit(1.1110, plan["stop_loss"], "buy")

    assert atr > 0
    assert plan["stop_loss"] < 1.1110
    assert take_profit > 1.1110
    assert plan["transaction_cost"] == pytest.approx(0.0003)


def test_trailing_and_cost_buffered_breakeven_protection():
    engine = StopLossEngine()
    trailing = engine.update_trailing_stop(1.1000, 1.1150, 1.0900, "buy", atr=0.0020, multiplier=1.5)
    breakeven = engine.update_breakeven(1.1000, 1.1004, 1.0950, "buy", spread=0.0002, slippage=0.0001)

    assert trailing == pytest.approx(1.1120)
    assert breakeven == pytest.approx(1.1003)


def test_daily_drawdown_and_correlated_currency_protection():
    manager = RiskManager()
    assert manager.enforce_daily_loss_limit(10000, 149.0)["allowed"] is True
    assert manager.enforce_daily_loss_limit(10000, 150.0)["allowed"] is False
    assert manager.enforce_drawdown_limit(10000, 999.0)["allowed"] is True
    assert manager.enforce_drawdown_limit(10000, 1000.0)["allowed"] is False
    assert manager.enforce_correlated_exposure([], "EUR/USD")["allowed"] is True
    assert manager.enforce_correlated_exposure([{"symbol": "EUR/GBP"}], "EUR/USD", exposure_limit=0.2)["allowed"] is False


def test_paper_execution_requires_valid_stop_loss():
    engine = PaperTradingEngine()
    with pytest.raises(ValueError, match="Stop-loss validation failed"):
        engine.open_trade("bad", "EUR/USD", "buy", 0.01, 1.1000, 1.1010, 1.1020)
