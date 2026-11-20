from __future__ import annotations

import importlib
import threading
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from concurrent.futures import Future, TimeoutError as FutureTimeoutError

from xyfuss_forex_autopilot.brokers import IdempotentOrderGate, LiveAdapterBase


class CTraderIntegrationError(RuntimeError):
    pass


class OfficialCTraderBackend:
    """Official Spotware OpenApiPy transport, with demo endpoint enforced."""

    # Values defined by ProtoOAClientPermissionScope in Spotware's protocol.
    SCOPE_VIEW = 0
    SCOPE_TRADE = 1

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
            "ctid_trader_account_id": int(ctid_trader_account_id),
        }
        self.permission_scope: int | None = None
        self._authenticated = False
        self._client = None
        self._connected = threading.Event()
        self._disconnected = threading.Event()

    def _validate_account_grant(self, response) -> int:
        """Confirm the token grants the exact account selected by the operator."""
        granted_accounts = getattr(response, "ctidTraderAccount", None)
        if not granted_accounts:
            raise CTraderIntegrationError("The cTrader access token has no authorised accounts.")

        requested_id = self.credentials["ctid_trader_account_id"]
        granted_ids = {
            int(getattr(account, "ctidTraderAccountId", 0))
            for account in granted_accounts
        }
        if requested_id not in granted_ids:
            raise CTraderIntegrationError(
                "The selected cTrader account is not authorised by this access token."
            )

        scope = int(getattr(response, "permissionScope", self.SCOPE_VIEW))
        if scope not in (self.SCOPE_VIEW, self.SCOPE_TRADE):
            raise CTraderIntegrationError("cTrader returned an unknown account permission scope.")
        self.permission_scope = scope
        return scope

    def _require_trading_permission(self) -> None:
        if self.permission_scope != self.SCOPE_TRADE:
            raise CTraderIntegrationError(
                "This cTrader token is view-only; trading permission was not granted."
            )

    def connect(self) -> bool:
        if self._authenticated and not self._disconnected.is_set():
            return True
        self._connected.clear()
        self._disconnected.clear()
        self._authenticated = False
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
        from twisted.internet import reactor
        self._client.startService()
        if not reactor.running:
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

        # Spotware requires account discovery after application authorisation.
        # Do not authorise an account merely because its ID was supplied locally.
        account_list = messages.ProtoOAGetAccountListByAccessTokenReq()
        account_list.accessToken = self.credentials["access_token"]
        granted_accounts = self._wait(self._client.send(account_list))
        self._validate_account_grant(granted_accounts)

        account = messages.ProtoOAAccountAuthReq()
        account.ctidTraderAccountId = self.credentials["ctid_trader_account_id"]
        account.accessToken = self.credentials["access_token"]
        account_response = self._wait(self._client.send(account))
        authorised_id = int(getattr(account_response, "ctidTraderAccountId", 0))
        if authorised_id != self.credentials["ctid_trader_account_id"]:
            raise CTraderIntegrationError("cTrader did not confirm authorisation for the selected account.")
        self._authenticated = True
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
        self._authenticated = False
        if self._client is not None:
            self._client.stopService()
            self._client = None

    def symbols(self) -> list[dict]:
        messages = importlib.import_module("ctrader_open_api.messages.OpenApiMessages_pb2")
        request = messages.ProtoOASymbolsListReq()
        request.ctidTraderAccountId = self.credentials["ctid_trader_account_id"]
        response = self._request(request)
        return [
            {
                "symbol_id": symbol.symbolId,
                "name": getattr(symbol, "symbolName", ""),
                "digits": int(getattr(symbol, "digits", 5)),
            }
            for symbol in getattr(response, "symbol", [])
        ]

    @staticmethod
    def _normalise_trendbars(trendbars, digits: int) -> list[dict]:
        """Convert cTrader's relative OHLC values into actual prices."""
        if not 0 <= int(digits) <= 10:
            raise CTraderIntegrationError("cTrader returned invalid symbol price precision.")

        normalised = []
        for bar in trendbars:
            required_fields = ("low", "deltaOpen", "deltaClose", "deltaHigh", "utcTimestampInMinutes")
            if hasattr(bar, "HasField"):
                missing = [field for field in required_fields if not bar.HasField(field)]
                if missing:
                    raise CTraderIntegrationError(
                        "cTrader returned an incomplete trend bar: " + ", ".join(missing)
                    )

            low_raw = int(getattr(bar, "low", 0))
            open_raw = low_raw + int(getattr(bar, "deltaOpen", 0))
            close_raw = low_raw + int(getattr(bar, "deltaClose", 0))
            high_raw = low_raw + int(getattr(bar, "deltaHigh", 0))
            if low_raw <= 0 or not (low_raw <= open_raw <= high_raw) or not (low_raw <= close_raw <= high_raw):
                raise CTraderIntegrationError("cTrader returned inconsistent OHLC values.")

            timestamp_minutes = int(getattr(bar, "utcTimestampInMinutes", 0))
            if timestamp_minutes <= 0:
                raise CTraderIntegrationError("cTrader trend bar has no valid timestamp.")

            price = lambda raw: round(raw / 100000.0, int(digits))
            normalised.append({
                "timestamp": datetime.fromtimestamp(
                    timestamp_minutes * 60, tz=timezone.utc
                ).isoformat(),
                "open": price(open_raw),
                "high": price(high_raw),
                "low": price(low_raw),
                "close": price(close_raw),
                "volume": int(getattr(bar, "volume", 0)),
            })

        normalised.sort(key=lambda item: item["timestamp"])
        return normalised

    def historical_bars(
        self,
        symbol_id: int,
        period: str = "M5",
        weeks: int = 1,
        count: int = 500,
    ) -> list[dict]:
        """Fetch timestamped historical candles for one cTrader demo symbol."""
        if int(symbol_id) <= 0:
            raise CTraderIntegrationError("symbol_id must be a positive cTrader symbol ID.")
        if not 1 <= int(weeks) <= 52:
            raise CTraderIntegrationError("weeks must be between 1 and 52.")
        if not 1 <= int(count) <= 1000:
            raise CTraderIntegrationError("count must be between 1 and 1000.")

        messages = importlib.import_module("ctrader_open_api.messages.OpenApiMessages_pb2")
        model = importlib.import_module("ctrader_open_api.messages.OpenApiModelMessages_pb2")
        try:
            period_value = model.ProtoOATrendbarPeriod.Value(str(period).upper())
        except (AttributeError, ValueError) as exc:
            raise CTraderIntegrationError("Unsupported cTrader trend-bar period.") from exc

        symbol = next(
            (item for item in self.symbols() if int(item["symbol_id"]) == int(symbol_id)),
            None,
        )
        if symbol is None:
            raise CTraderIntegrationError("The selected symbol ID is not available on this account.")

        now = datetime.now(timezone.utc)
        request = messages.ProtoOAGetTrendbarsReq()
        request.ctidTraderAccountId = self.credentials["ctid_trader_account_id"]
        request.symbolId = int(symbol_id)
        request.period = period_value
        request.fromTimestamp = int((now - timedelta(weeks=int(weeks))).timestamp() * 1000)
        request.toTimestamp = int(now.timestamp() * 1000)
        request.count = int(count)
        response = self._request(request, timeout=30.0)
        return self._normalise_trendbars(
            getattr(response, "trendbar", []),
            digits=int(symbol["digits"]),
        )

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
        self._require_trading_permission()
        if stop_loss is None or take_profit is None:
            raise CTraderIntegrationError("Every cTrader demo order requires broker-side stop-loss and take-profit.")
        messages = importlib.import_module("ctrader_open_api.messages.OpenApiMessages_pb2")
        model = importlib.import_module("ctrader_open_api.messages.OpenApiModelMessages_pb2")
        request = messages.ProtoOANewOrderReq()
        request.ctidTraderAccountId = self.credentials["ctid_trader_account_id"]
        request.symbolId = symbol_id
        request.orderType = model.MARKET
        request.tradeSide = trade_side
        request.volume = volume
        request.timeInForce = model.GOOD_TILL_CANCEL
        request.stopLoss = stop_loss
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
        backend=None,
    ):
        super().__init__(credentials=credentials, live_trading_enabled=live_trading_enabled)
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

    def get_historical_bars(
        self,
        symbol_id: int,
        period: str = "M5",
        weeks: int = 1,
        count: int = 500,
    ) -> list[dict]:
        if self.backend is None or not self.connect():
            raise CTraderIntegrationError("cTrader demo connection is unavailable.")
        if not hasattr(self.backend, "historical_bars"):
            raise CTraderIntegrationError("The configured cTrader backend does not provide historical candles.")
        return self.backend.historical_bars(
            symbol_id=symbol_id,
            period=period,
            weeks=weeks,
            count=count,
        )

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
        if self.live_trading_enabled or self._emergency_stop:
            raise CTraderIntegrationError("Demo execution is disabled while emergency stop is active or live mode is requested.")
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
        if stop_loss is None or take_profit is None:
            raise CTraderIntegrationError("Every cTrader demo order requires stop-loss and take-profit.")

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
