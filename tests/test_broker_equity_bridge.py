from xyfuss_forex_autopilot.core import XyFussForexAutopilot
from xyfuss_forex_autopilot.runtime import PersistentTradingState


class ReadOnlyBroker:
    def __init__(self, account):
        self.account = account
        self.reads = 0
        self.order_calls = 0

    def get_account_info(self):
        self.reads += 1
        return self.account

    def place_order(self, *args, **kwargs):
        self.order_calls += 1
        raise AssertionError("The equity monitor must never place broker orders.")


def test_broker_equity_is_recorded_from_read_only_account_snapshot(tmp_path):
    state_path = str(tmp_path / "trading-state.json")
    autopilot = XyFussForexAutopilot({"trading_state_path": state_path})
    broker = ReadOnlyBroker({
        "connected": True,
        "balance": 10000.0,
        "equity": 9875.0,
        "currency": "USD",
    })

    result = autopilot.decide_trade_from_broker("EUR/USD", [], broker)

    assert result["decision"] == "NO_TRADE"
    assert result["account_monitoring"]["source"] == "broker_read_only"
    assert result["account_monitoring"]["equity_checked"] is True
    assert broker.reads == 1
    assert broker.order_calls == 0
    assert PersistentTradingState(state_path).load()["risk"]["last_equity"] == 9875.0


def test_disconnected_broker_activates_persistent_emergency_stop(tmp_path):
    state_path = str(tmp_path / "trading-state.json")
    autopilot = XyFussForexAutopilot({"trading_state_path": state_path})
    broker = ReadOnlyBroker({"connected": False, "balance": None, "equity": None})

    result = autopilot.decide_trade_from_broker("EUR/USD", [], broker)

    assert result["decision"] == "NO_TRADE"
    assert result["account_monitoring"]["connected"] is False
    assert "emergency stop activated" in result["reason"].lower()
    assert PersistentTradingState(state_path).load()["emergency_stop"] is True
    assert broker.order_calls == 0


def test_missing_broker_equity_fails_closed(tmp_path):
    state_path = str(tmp_path / "trading-state.json")
    autopilot = XyFussForexAutopilot({"trading_state_path": state_path})
    broker = ReadOnlyBroker({"connected": True, "balance": 10000.0})

    result = autopilot.decide_trade_from_broker("EUR/USD", [], broker)

    assert result["decision"] == "NO_TRADE"
    assert PersistentTradingState(state_path).load()["emergency_stop"] is True
    assert broker.order_calls == 0


def test_existing_emergency_stop_prevents_broker_access(tmp_path):
    state_path = str(tmp_path / "trading-state.json")
    autopilot = XyFussForexAutopilot({"trading_state_path": state_path})
    autopilot.activate_emergency_stop()
    broker = ReadOnlyBroker({
        "connected": True,
        "balance": 10000.0,
        "equity": 10000.0,
        "currency": "USD",
    })

    result = autopilot.decide_trade_from_broker("EUR/USD", [], broker)

    assert result["decision"] == "NO_TRADE"
    assert broker.reads == 0
    assert broker.order_calls == 0
