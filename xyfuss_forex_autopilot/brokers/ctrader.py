from __future__ import annotations

import importlib
import threading
from collections.abc import Mapping
from concurrent.futures import Future, TimeoutError as FutureTimeoutError

from xyfuss_forex_autopilot.brokers import IdempotentOrderGate, LiveAdapterBase


class CTraderIntegrationError(RuntimeError):
    pass


class OfficialCTraderBackend:
    """Official Spotware OpenApiPy transport, with demo endpoint enforced."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        access_token: str,
        ctid_trader_account_id: int,
        environment: str = "demo",
    ):
        if environment.lower() != "demo":
            raise CTraderIntegrationError("Only the cTrader demo environment is permitted.")
        self.credentials = {
            "client_id": client_id,
            "client_secret": client_secret,
            "access_token": access_token,
            "ctid_trader_account_id": ctid_trader_account_id,
        }
        self._client = None
        self._connected = threading.Event()
        self._disconnected = threading.Event()

    def connect(self) -> bool:
        try:
            api = importlib.import_module("ctrader_open_api")
            messages = importlib.import_module("ctrader_open_api.messages.OpenApiMessages_pb2")
        except ImportError as exc:
            raise CTraderIntegrationError(
                "Install ctrader-open-api and Twisted from requirements.txt."
            ) from exc

        self._client = api.Client(
            api.EndPoints.PROTOBUF_DEMO_HOST,
            api.EndPoints.PROTOBUF_PORT,
            api.TcpProtocol,
        )
        self._client.setConnectedCallback(lambda _client: self._connected.set())
        self._client.setDisconnectedCallback(lambda _client, _reason: self._disconnected.set())
        self._client.startService()
        from twisted.internet import reactor
        threading.Thread(
            target=lambda: reactor.run(installSignalHandlers=False),
            name="xyfuss-ctrader-reactor",
            daemon=True,
        ).start()
        if not self._connected.wait(timeout=15):
            return False

        application = messages.ProtoOAApplicationAuthReq()
        application.clientId = self.credentials["client_id"]
        application.clientSecret = self.credentials["client_secret"]
        self._wait(self._client.send(application))

        account = messages.ProtoOAAccountAuthReq()
        account.ctidTraderAccountId = self.credentials["ctid_trader_account_id"]
        account.accessToken = self.credentials["access_token"]
        self._wait(self._client.send(account))
        return True

    def _wait(self, deferred, timeout: float = 15.0):
        future = Future()
        deferred.addCallbacks(future.set_result, lambda failure: future.set_exception(CTraderIntegrationError(str(failure))))
        try:
            return future.result(timeout=timeout)
        except FutureTimeoutError as exc:
            raise CTraderIntegrationError("cTrader request timed out.") from exc

    def _request(self, request, timeout: float = 15.0):
        if self._client is None:
            raise CTraderIntegrationError("cTrader is not connected.")
        return self._wait(self._client.send(request), timeout=timeout)

    def disconnect(self) -> None:
        if self._client is not None:
            self._client.stopService()

    def symbols(self) -> list[dict]:
        messages = importlib.import_module("ctrader_open_api.messages.OpenApiMessages_pb2")
        request = messages.ProtoOASymbolsListReq()
        request.ctidTraderAccountId = self.credentials["ctid_trader_account_id"]
        response = self._request(request)
        return [
            {"symbol_id": symbol.symbolId, "name": getattr(symbol, "symbolName", "")}
            for symbol in getattr(response, "symbol", [])
        ]

    def trader(self) -> dict:
        messages = importlib.import_module("ctrader_open_api.messages.OpenApiMessages_pb2")
        request = messages.ProtoOATraderReq()
        request.ctidTraderAccountId = self.credentials["ctid_trader_account_id"]
        response = self._request(request)
        return {
            "balance": getattr(response.trader, "balance", 0) / 100.0,
            "currency": getattr(response.trader, "depositAssetId", ""),
        }

    def reconcile(self) -> list[dict]:
        messages = importlib.import_module("ctrader_open_api.messages.OpenApiMessages_pb2")
        request = messages.ProtoOAReconcileReq()
        request.ctidTraderAccountId = self.credentials["ctid_trader_account_id"]
        response = self._request(request)
        from google.protobuf.json_format import MessageToDict
        return [MessageToDict(item) for item in getattr(response, "position", [])]

    def place_order(
        self,
        symbol_id: int,
        trade_side: int,
        volume: int,
        stop_loss: float | None = None,
        take_profit: float | None = None,
        broker_client_order_id: str | None = None,
    ) -> dict:
        messages = importlib.import_module("ctrader_open_api.messages.OpenApiMessages_pb2")
        model = importlib.import_module("ctrader_open_api.messages.OpenApiModelMessages_pb2")
        request = messages.ProtoOANewOrderReq()
        request.ctidTraderAccountId = self.credentials["ctid_trader_account_id"]
        request.symbolId = symbol_id
        request.orderType = model.MARKET
        request.tradeSide = trade_side
        request.volume = volume
        request.timeInForce = model.GOOD_TILL_CANCEL
        if stop_loss is not None:
            request.stopLoss = stop_loss
        if take_profit is not None:
            request.takeProfit = take_profit
        if broker_client_order_id:
            request.clientOrderId = broker_client_order_id
        response = self._request(request)
        return {"status": "submitted", "response": str(response)}

    def interrupted(self) -> bool:
        return self._disconnected.is_set()


class CTraderDemoAdapter(LiveAdapterBase):
    name = "ctrader-demo"

    def __init__(
        self,
        credentials: Mapping[str, object] | None = None,
        live_trading_enabled: bool = False,
        demo_execution_enabled: bool = False,
        backend=None,
    ):
        super().__init__(credentials=credentials, live_trading_enabled=live_trading_enabled, demo_execution_enabled=demo_execution_enabled)
        self.backend = backend
        self.order_gate = IdempotentOrderGate()
        self._emergency_stop = False

    def validate_credentials(self) -> bool:
        return all(
            str(self.credentials.get(key, "")).strip()
            for key in ("client_id", "client_secret", "access_token", "ctid_trader_account_id")
        )

    def connect(self) -> bool:
        if self.live_trading_enabled or self._emergency_stop:
            return False
        if self.backend is None:
            if not self.validate_credentials():
                return False
            self.backend = OfficialCTraderBackend(
                client_id=str(self.credentials["client_id"]),
                client_secret=str(self.credentials["client_secret"]),
                access_token=str(self.credentials["access_token"]),
                ctid_trader_account_id=int(self.credentials["ctid_trader_account_id"]),
                environment="demo",
            )
        return self.backend.connect()

    def get_market_data(self) -> list[dict]:
        if self.backend is None or not self.connect():
            raise CTraderIntegrationError("cTrader demo connection is unavailable.")
        return self.backend.symbols()

    def get_account_info(self) -> dict:
        if self.backend is None or not self.connect():
            return {"status": "disconnected", "connected": False}
        return {**self.backend.trader(), "status": "connected", "connected": True, "environment": "demo"}

    def get_positions(self) -> list[dict]:
        if self.backend is None or not self.connect():
            return []
        return self.backend.reconcile()

    def place_order(
        self,
        symbol: str,
        direction: str,
        lot_size: float,
        price: float,
        stop_loss: float | None = None,
        take_profit: float | None = None,
        client_order_id: str | None = None,
        symbol_id: int | None = None,
    ) -> dict:
        if self.live_trading_enabled or not self.demo_execution_enabled or self._emergency_stop:
            raise CTraderIntegrationError("Demo order execution is disabled, live mode is requested, or emergency stop is active.")
        if stop_loss is None or take_profit is None:
            raise CTraderIntegrationError("Every cTrader demo order requires stop-loss and take-profit.")
        if not self.connect() or self.backend is None:
            raise CTraderIntegrationError("cTrader demo connection is unavailable.")
        if direction.lower() not in {"buy", "sell"}:
            raise CTraderIntegrationError("direction must be buy or sell")
        if lot_size <= 0:
            raise CTraderIntegrationError("lot_size must be positive")
        if not client_order_id:
            raise CTraderIntegrationError("client_order_id is required")
        if symbol_id is None:
            raise CTraderIntegrationError("symbol_id is required for cTrader order submission")

        trade_side = 1 if direction.lower() == "buy" else 2
        volume = int(round(lot_size * 100000))
        return self.order_gate.submit(
            client_order_id,
            self.backend.place_order,
            symbol_id=symbol_id,
            trade_side=trade_side,
            volume=volume,
            stop_loss=stop_loss,
            take_profit=take_profit,
            broker_client_order_id=client_order_id,
        )

    def emergency_stop(self) -> None:
        self._emergency_stop = True
        if self.backend is not None:
            self.backend.disconnect()
