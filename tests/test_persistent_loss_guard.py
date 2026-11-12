from datetime import datetime, timezone

from xyfuss_forex_autopilot.core import XyFussForexAutopilot
from xyfuss_forex_autopilot.runtime import PersistentTradingState


def test_equity_tracker_persists_daily_loss_and_peak_drawdown(tmp_path):
    path = tmp_path / "trading-state.json"
    first = PersistentTradingState(str(path))
    first.record_equity(10000.0)
    first.record_equity(11000.0)
    snapshot = first.record_equity(10800.0)

    assert snapshot["daily_loss"] == 0.0
    assert snapshot["peak_equity"] == 11000.0
    assert snapshot["drawdown"] == 200.0

    restarted = PersistentTradingState(str(path))
    after_restart = restarted.record_equity(10750.0)
    assert after_restart["peak_equity"] == 11000.0
    assert after_restart["drawdown"] == 250.0


def test_equity_tracker_resets_daily_baseline_but_keeps_peak(tmp_path):
    state = PersistentTradingState(str(tmp_path / "trading-state.json"))
    day_one = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)
    day_two = datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc)

    state.record_equity(10000.0, day_one)
    state.record_equity(10500.0, day_one)
    next_day = state.record_equity(10400.0, day_two)

    assert next_day["daily_start_equity"] == 10500.0
    assert next_day["daily_loss"] == 100.0
    assert next_day["peak_equity"] == 10500.0
    assert next_day["drawdown"] == 100.0


def test_corrupt_state_fails_closed(tmp_path):
    path = tmp_path / "trading-state.json"
    path.write_text("{not valid json", encoding="utf-8")

    state = PersistentTradingState(str(path))
    loaded = state.load()

    assert loaded["emergency_stop"] is True
    assert "recovery_warning" in loaded


def test_invalid_equity_is_rejected(tmp_path):
    state = PersistentTradingState(str(tmp_path / "trading-state.json"))

    for value in (0, -1, float("nan"), float("inf")):
        try:
            state.record_equity(value)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected invalid equity to be rejected: {value}")


def test_daily_loss_limit_persistently_stops_new_trades(tmp_path):
    state_path = str(tmp_path / "trading-state.json")
    autopilot = XyFussForexAutopilot({"trading_state_path": state_path})

    # First observation establishes the account's daily starting equity.
    autopilot.decide_trade("EUR/USD", [], balance=10000.0, equity=10000.0)
    result = autopilot.decide_trade("EUR/USD", [], balance=10000.0, equity=9840.0)

    assert result["decision"] == "NO_TRADE"
    assert "Daily loss limit" in result["reason"]
    assert PersistentTradingState(state_path).load()["emergency_stop"] is True

    restarted = XyFussForexAutopilot({"trading_state_path": state_path})
    blocked = restarted.decide_trade("EUR/USD", [], balance=9840.0, equity=9840.0)
    assert blocked["decision"] == "NO_TRADE"
    assert "emergency stop" in blocked["reason"].lower()


def test_maximum_drawdown_persistently_stops_new_trades(tmp_path):
    state_path = str(tmp_path / "trading-state.json")
    autopilot = XyFussForexAutopilot({"trading_state_path": state_path})

    autopilot.decide_trade("EUR/USD", [], balance=10000.0, equity=10000.0)
    autopilot.decide_trade("EUR/USD", [], balance=10000.0, equity=11000.0)
    result = autopilot.decide_trade("EUR/USD", [], balance=10000.0, equity=8900.0)

    assert result["decision"] == "NO_TRADE"
    assert "drawdown" in result["reason"].lower()
    assert PersistentTradingState(state_path).load()["emergency_stop"] is True


def test_manual_emergency_stop_survives_autopilot_restart(tmp_path):
    state_path = str(tmp_path / "trading-state.json")
    autopilot = XyFussForexAutopilot({"trading_state_path": state_path})
    assert autopilot.activate_emergency_stop()["persistent"] is True

    restarted = XyFussForexAutopilot({"trading_state_path": state_path})
    result = restarted.decide_trade("EUR/USD", [], balance=10000.0)

    assert result["decision"] == "NO_TRADE"
    assert "manual review" in result["reason"]


def test_autopilot_blocks_when_persisted_state_is_corrupt(tmp_path):
    state_path = tmp_path / "trading-state.json"
    state_path.write_text("broken", encoding="utf-8")

    autopilot = XyFussForexAutopilot({"trading_state_path": str(state_path)})
    result = autopilot.decide_trade("EUR/USD", [], balance=10000.0)

    assert result["decision"] == "NO_TRADE"
    assert "manual review" in result["reason"]
