from types import SimpleNamespace

import pytest

from xyfuss_forex_autopilot.brokers.ctrader import (
    CTraderIntegrationError,
    OfficialCTraderBackend,
)


def make_backend(account_id=123):
    return OfficialCTraderBackend(
        client_id="test-client",
        client_secret="test-secret",
        access_token="test-token",
        ctid_trader_account_id=account_id,
        environment="demo",
    )


def grant(account_id=123, permission_scope=0):
    return SimpleNamespace(
        ctidTraderAccount=[
            SimpleNamespace(ctidTraderAccountId=account_id),
        ],
        permissionScope=permission_scope,
    )


def test_account_grant_must_contain_the_selected_account():
    backend = make_backend(account_id=123)

    assert backend._validate_account_grant(grant(account_id=123)) == backend.SCOPE_VIEW

    with pytest.raises(CTraderIntegrationError, match="not authorised"):
        backend._validate_account_grant(grant(account_id=456))


def test_empty_or_missing_account_grants_fail_closed():
    backend = make_backend()

    with pytest.raises(CTraderIntegrationError, match="no authorised accounts"):
        backend._validate_account_grant(SimpleNamespace(ctidTraderAccount=[]))

    with pytest.raises(CTraderIntegrationError, match="no authorised accounts"):
        backend._validate_account_grant(SimpleNamespace())


def test_view_only_scope_cannot_submit_orders():
    backend = make_backend()
    backend._validate_account_grant(grant(permission_scope=backend.SCOPE_VIEW))

    with pytest.raises(CTraderIntegrationError, match="view-only"):
        backend._require_trading_permission()


def test_trade_scope_is_required_before_order_payload_is_built():
    backend = make_backend()
    backend._validate_account_grant(grant(permission_scope=backend.SCOPE_TRADE))

    with pytest.raises(CTraderIntegrationError, match="requires broker-side"):
        backend.place_order(
            symbol_id=1,
            trade_side=1,
            volume=1000,
            stop_loss=None,
            take_profit=1.2,
        )


def test_cTrader_requests_require_an_authenticated_account_session():
    backend = make_backend()

    with pytest.raises(CTraderIntegrationError, match="account session is not authenticated"):
        backend._request(object())


def test_heartbeat_failure_marks_connection_unusable_and_stops_loop():
    class FakeLoop:
        running = True

        def stop(self):
            self.running = False

    backend = make_backend()
    backend._authenticated = True
    backend._heartbeat = FakeLoop()

    backend._heartbeat_failed(RuntimeError("simulated heartbeat failure"))

    assert backend._authenticated is False
    assert backend._disconnected.is_set()
    assert backend._heartbeat.running is False


def test_heartbeat_uses_spotware_common_message_module(monkeypatch):
    import importlib

    sent = []

    class Heartbeat:
        pass

    class Deferred:
        def addErrback(self, callback):
            self.errback = callback

    class Client:
        def send(self, message):
            sent.append(message)
            return Deferred()

    class CommonMessages:
        ProtoHeartbeatEvent = Heartbeat

    backend = make_backend()
    backend._client = Client()
    backend._authenticated = True
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name: CommonMessages
        if name == "ctrader_open_api.messages.OpenApiCommonMessages_pb2"
        else None,
    )

    backend._send_heartbeat()

    assert len(sent) == 1
    assert isinstance(sent[0], Heartbeat)
