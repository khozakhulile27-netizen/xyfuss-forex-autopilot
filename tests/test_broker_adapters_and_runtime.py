import pytest

from xyfuss_forex_autopilot.brokers import (
    CTraderAdapter,
    DirectBrokerAdapter,
    IdempotentOrderGate,
    MT5Adapter,
    MetaTrader5DemoAdapter,
    create_broker_adapter,
)
from xyfuss_forex_autopilot.runtime import HealthMonitor, PersistentTradingState, RecoverableProcess
from xyfuss_forex_autopilot.brokers.ctrader import CTraderDemoAdapter, CTraderIntegrationError


@pytest.mark.parametrize(
    ("name", "adapter_type"),
    [
        ("mt5", MT5Adapter),
        ("ctrader", CTraderAdapter),
        ("direct-api", DirectBrokerAdapter),
    ],
)
def test_platform_adapters_are_independent_and_fail_closed(name, adapter_type):
    adapter = create_broker_adapter(name)
    assert isinstance(adapter, adapter_type)
    assert adapter.connect() is False
    assert adapter.get_account_info()["connected"] is False
    with pytest.raises(RuntimeError):
        adapter.place_order("EUR/USD", "buy", 0.01, 1.10)


def test_capability_and_minimum_lot_validation():
    adapter = MT5Adapter()
    assert adapter.get_capabilities().platform == "MT5"
    assert adapter.validate_lot_size("EUR/USD", 0.009)["valid"] is False
    assert adapter.validate_lot_size("EUR/USD", 0.01)["valid"] is True


def test_duplicate_submission_is_suppressed():
    gate = IdempotentOrderGate()
    calls = []

    def submit():
        calls.append(True)
        return {"status": "accepted", "broker_order_id": "123"}

    first = gate.submit("client-1", submit)
    second = gate.submit("client-1", submit)
    assert len(calls) == 1
    assert first["duplicate"] is False
    assert second["duplicate"] is True


class MT5DemoBackend:
    TRADE_ACTION_DEAL = 1
    TRADE_RETCODE_DONE = 10009
    ORDER_TIME_GTC = 0
    ORDER_FILLING_IOC = 1
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    POSITION_TYPE_BUY = 0

    def __init__(self):
        self.connected = False
        self.orders = []
        self.positions = []

    def initialize(self, login, password, server):
        self.connected = True
        return True

    def last_error(self):
        return (1, "ok")

    def shutdown(self):
        self.connected = False

    def terminal_info(self):
        return type("Terminal", (), {"connected": self.connected})()

    def account_info(self):
        return type("Account", (), {"login": 123456, "balance": 10000.0, "equity": 9950.0, "margin": 50.0, "currency": "USD"})()

    def symbol_info_tick(self, symbol):
        return type("Tick", (), {"bid": 1.0990, "ask": 1.0992})()

    def positions_get(self, ticket=None):
        if ticket is None:
            return self.positions
        return [position for position in self.positions if getattr(position, "ticket") == ticket]

    def order_send(self, request):
        if request["type"] in (self.ORDER_TYPE_BUY, self.ORDER_TYPE_SELL):
            if request.get("position") is not None:
                self.positions = [position for position in self.positions if getattr(position, "ticket") != request["position"]]
            else:
                ticket = 900 + len(self.orders)
                self.positions.append(type("Position", (), {
                    "ticket": ticket,
                    "symbol": request["symbol"],
                    "type": 0 if request["type"] == self.ORDER_TYPE_BUY else 1,
                    "volume": request["volume"],
                    "price_open": request["price"],
                })())
        self.orders.append(request)
        return type("Result", (), {"retcode": self.TRADE_RETCODE_DONE, "order": 900 + len(self.orders)})()


def demo_mt5_adapter(execution=True):
    return MetaTrader5DemoAdapter(
        credentials={"login": "123456", "password": "demo-password", "server": "Exness-MT5Demo1", "environment": "demo"},
        live_trading_enabled=False,
        demo_execution_enabled=execution,
        backend=MT5DemoBackend(),
    )


def test_mt5_demo_account_market_and_duplicate_order_guards():
    adapter = demo_mt5_adapter()
    assert adapter.connect() is True
    account = adapter.get_account_info()
    assert account["balance"] == 10000.0
    assert account["equity"] == 9950.0
    assert account["margin"] == 50.0
    assert account["currency"] == "USD"
    assert adapter.get_market_prices("EUR/USD")["ask"] == 1.0992

    order = adapter.place_order("EUR/USD", "buy", 0.01, 1.0992, 1.09, 1.11, "mt5-order-1")
    duplicate = adapter.place_order("EUR/USD", "buy", 0.01, 1.0992, 1.09, 1.11, "mt5-order-1")
    assert order["duplicate"] is False
    assert duplicate["duplicate"] is True
    assert len(adapter.backend.orders) == 1
    position = adapter.get_positions()[0]
    closed = adapter.close_position(position["ticket"])
    assert closed["status"] == "closed"
    assert adapter.get_positions() == []


def test_mt5_demo_requires_sl_tp_and_rejects_real_server():
    adapter = demo_mt5_adapter()
    adapter.connect()
    with pytest.raises(RuntimeError, match="stop-loss and take-profit"):
        adapter.place_order("EUR/USD", "buy", 0.01, 1.0992, client_order_id="missing-protection")

    real_money = MetaTrader5DemoAdapter(
        credentials={"login": "123456", "password": "secret", "server": "Exness-Real1", "environment": "demo"},
        live_trading_enabled=False,
        backend=MT5DemoBackend(),
    )
    assert real_money.validate_credentials() is False
    with pytest.raises(RuntimeError, match="demo credentials"):
        real_money.connect()


def test_exness_trial_server_health_reconnect_and_read_only_mode():
    adapter = MetaTrader5DemoAdapter(
        credentials={
            "login": "123456",
            "password": "demo-password",
            "server": "Exness-MT5Trial10",
            "environment": "demo",
        },
        live_trading_enabled=False,
        backend=MT5DemoBackend(),
    )
    assert adapter.connect() is True
    assert adapter.health_check()["healthy"] is True
    assert adapter.reconnect() is True
    assert adapter.health_check()["healthy"] is True
    with pytest.raises(RuntimeError, match="Demo order execution is disabled"):
        adapter.place_order("EUR/USD", "buy", 0.01, 1.0992, 1.09, 1.11)


def test_mt5_account_trade_mode_rejects_real_account():
    class RealAccountBackend(MT5DemoBackend):
        ACCOUNT_TRADE_MODE_DEMO = 0

        def account_info(self):
            account = super().account_info()
            account.trade_mode = 2
            return account

    adapter = MetaTrader5DemoAdapter(
        credentials={
            "login": "123456",
            "password": "demo-password",
            "server": "Exness-MT5Trial10",
            "environment": "demo",
        },
        backend=RealAccountBackend(),
    )
    with pytest.raises(RuntimeError, match="not a demo account"):
        adapter.connect()


def test_state_survives_restart_and_emergency_stop(tmp_path):
    path = tmp_path / "state.json"
    state = PersistentTradingState(str(path))
    state.record_submission("order-1", {"status": "accepted"})
    state.set_emergency_stop(True)

    restarted = PersistentTradingState(str(path))
    assert restarted.load()["emergency_stop"] is True
    assert "order-1" in restarted.load()["submitted_orders"]


def test_broker_failure_is_fail_safe_and_process_recovers():
    monitor = HealthMonitor(lambda: (_ for _ in ()).throw(ConnectionError()))
    assert monitor.check()["fail_safe"] is True

    attempts = []

    def operation():
        attempts.append(True)
        if len(attempts) == 1:
            raise ConnectionError("temporary")
        return {"connected": True}

    assert RecoverableProcess(operation).run()["recovered"] is True


class DemoBackend:
    def __init__(self, interrupted=False):
        self.connected = True
        self.interrupted = interrupted
        self.orders = []

    def connect(self):
        return self.connected

    def disconnect(self):
        self.connected = False

    def symbols(self):
        return [{"symbol_id": 1, "name": "EURUSD"}]

    def trader(self):
        return {"balance": 10000.0, "currency": "USD"}

    def reconcile(self):
        return [{"positionId": "10", "symbolId": 1, "volume": 10000}]

    def place_order(self, **kwargs):
        if kwargs.get("symbol_id") == 999:
            raise CTraderIntegrationError("symbol rejected by broker")
        self.orders.append(kwargs)
        return {"status": "submitted", "broker_order_id": f"demo-{len(self.orders)}"}


def demo_adapter():
    credentials = {
        "client_id": "demo-app",
        "client_secret": "demo-secret",
        "access_token": "demo-token",
        "ctid_trader_account_id": "123",
    }
    return CTraderDemoAdapter(credentials=credentials, demo_execution_enabled=True, backend=DemoBackend())


def test_ctrader_demo_execution_is_disabled_by_default():
    credentials = {"client_id": "demo-app", "client_secret": "demo-secret", "access_token": "demo-token", "ctid_trader_account_id": "123"}
    adapter = CTraderDemoAdapter(credentials=credentials, backend=DemoBackend())
    with pytest.raises(CTraderIntegrationError, match="Demo order execution is disabled"):
        adapter.place_order("EURUSD", "buy", 0.01, 1.1, client_order_id="blocked", symbol_id=1)
    assert adapter.backend.orders == []


def test_ctrader_demo_execution_is_blocked_in_live_mode():
    credentials = {"client_id": "demo-app", "client_secret": "demo-secret", "access_token": "demo-token", "ctid_trader_account_id": "123"}
    adapter = CTraderDemoAdapter(credentials=credentials, live_trading_enabled=True, demo_execution_enabled=True, backend=DemoBackend())
    with pytest.raises(CTraderIntegrationError, match="Demo order execution is disabled"):
        adapter.place_order("EURUSD", "buy", 0.01, 1.1, client_order_id="blocked", symbol_id=1)
    assert adapter.backend.orders == []


def test_ctrader_demo_connection_market_account_and_positions():
    adapter = demo_adapter()
    assert adapter.connect() is True
    assert adapter.get_market_data() == [{"symbol_id": 1, "name": "EURUSD"}]
    assert adapter.get_account_info()["balance"] == 10000.0
    assert adapter.get_positions()[0]["positionId"] == "10"


def test_ctrader_demo_orders_require_both_protective_levels():
    adapter = demo_adapter()

    with pytest.raises(CTraderIntegrationError, match="requires stop-loss and take-profit"):
        adapter.place_order("EURUSD", "buy", 0.01, 1.1, take_profit=1.12, client_order_id="missing-sl", symbol_id=1)
    with pytest.raises(CTraderIntegrationError, match="requires stop-loss and take-profit"):
        adapter.place_order("EURUSD", "buy", 0.01, 1.1, stop_loss=1.09, client_order_id="missing-tp", symbol_id=1)

    assert adapter.backend.orders == []


def test_ctrader_demo_order_rejection_sl_tp_duplicate_and_shutdown():
    adapter = demo_adapter()
    order = adapter.place_order(
        "EURUSD", "buy", 0.01, 1.1, 1.09, 1.12, "order-1", symbol_id=1
    )
    assert order["duplicate"] is False
    duplicate = adapter.place_order(
        "EURUSD", "buy", 0.01, 1.1, 1.09, 1.12, "order-1", symbol_id=1
    )
    assert duplicate["duplicate"] is True
    assert len(adapter.backend.orders) == 1
    assert adapter.backend.orders[0]["stop_loss"] == 1.09
    assert adapter.backend.orders[0]["take_profit"] == 1.12

    with pytest.raises(CTraderIntegrationError, match="symbol rejected"):
        adapter.place_order(
            "BAD", "buy", 0.01, 1.1, 1.09, 1.12, client_order_id="order-2", symbol_id=999
        )

    adapter.emergency_stop()
    assert adapter.backend.connected is False
    with pytest.raises(CTraderIntegrationError):
        adapter.place_order(
            "EURUSD", "buy", 0.01, 1.1, client_order_id="order-3", symbol_id=1
        )
