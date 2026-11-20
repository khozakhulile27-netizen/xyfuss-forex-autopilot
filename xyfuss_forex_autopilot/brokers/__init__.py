from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Mapping


@dataclass
class PaperTrade:
    trade_id: str
    symbol: str
    direction: str
    lot_size: float
    entry_price: float
    stop_loss: float
    take_profit: float
    status: str = "open"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class PaperTradingEngine:
    """Place and monitor simulated orders without broker access."""

    def __init__(self):
        self.trades: list[PaperTrade] = []

    def open_trade(self, trade_id: str, symbol: str, direction: str, lot_size: float, entry_price: float, stop_loss: float, take_profit: float) -> PaperTrade:
        trade = PaperTrade(
            trade_id=trade_id,
            symbol=symbol,
            direction=direction,
            lot_size=lot_size,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )
        self.trades.append(trade)
        return trade

    def close_trade(self, trade_id: str, close_price: float) -> dict:
        for trade in self.trades:
            if trade.trade_id == trade_id:
                if trade.direction == "buy":
                    pnl = (close_price - trade.entry_price) * trade.lot_size
                else:
                    pnl = (trade.entry_price - close_price) * trade.lot_size
                trade.status = "closed"
                return {"trade_id": trade_id, "pnl": round(pnl, 2), "closed_at": datetime.now(timezone.utc).isoformat()}
        raise KeyError(f"Trade {trade_id} not found.")

    def list_trades(self) -> list[dict]:
        return [
            {
                "trade_id": trade.trade_id,
                "symbol": trade.symbol,
                "direction": trade.direction,
                "lot_size": trade.lot_size,
                "entry_price": trade.entry_price,
                "status": trade.status,
            }
            for trade in self.trades
        ]


class PaperBrokerAdapter:
    """Explicitly paper-only broker adapter."""

    name = "paper"

    def open_trade(self, trade_id: str, symbol: str, direction: str, lot_size: float, entry_price: float, stop_loss: float, take_profit: float) -> PaperTrade:
        return PaperTrade(trade_id=trade_id, symbol=symbol, direction=direction, lot_size=lot_size, entry_price=entry_price, stop_loss=stop_loss, take_profit=take_profit)

    def close_trade(self, trade_id: str, close_price: float) -> dict:
        return {"trade_id": trade_id, "close_price": close_price, "mode": "paper", "status": "closed"}


@dataclass(frozen=True)
class BrokerCapabilities:
    platform: str
    supports_market_orders: bool = True
    supports_stop_loss: bool = True
    supports_take_profit: bool = True
    supports_positions: bool = True
    supports_modifications: bool = True
    supports_official_api: bool = False
    minimum_lot: float = 0.01
    lot_step: float = 0.01
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class BrokerOrder:
    client_order_id: str
    symbol: str
    direction: str
    lot_size: float
    stop_loss: float | None = None
    take_profit: float | None = None
    price: float | None = None


class BrokerExecutionError(RuntimeError):
    pass


class IdempotentOrderGate:
    """Keep submitted client IDs so retries cannot create duplicate orders."""

    def __init__(self):
        self._submitted: dict[str, dict] = {}
        self._lock = Lock()

    def submit(self, client_order_id: str, submitter, *args, **kwargs) -> dict:
        with self._lock:
            existing = self._submitted.get(client_order_id)
            if existing is not None:
                return {**existing, "duplicate": True}
            result = submitter(*args, **kwargs)
            self._submitted[client_order_id] = dict(result)
            return {**result, "duplicate": False}

    def restore(self, submitted: Mapping[str, Mapping[str, object]]) -> None:
        with self._lock:
            self._submitted.update({key: dict(value) for key, value in submitted.items()})

    def snapshot(self) -> dict[str, dict]:
        with self._lock:
            return {key: dict(value) for key, value in self._submitted.items()}


class LiveAdapterBase:
    def __init__(self, credentials: Mapping[str, str] | None = None, live_trading_enabled: bool = False, demo_execution_enabled: bool = False):
        self.credentials = dict(credentials or {})
        self.live_trading_enabled = live_trading_enabled
        self.demo_execution_enabled = demo_execution_enabled
        self.order_gate = IdempotentOrderGate()

    def connect(self) -> bool:
        return False  # Official SDK/API integration must be verified separately.

    def get_account_info(self) -> dict:
        return {"status": "disabled", "balance": None, "connected": False}

    def get_positions(self) -> list[dict]:
        return []

    def validate_lot_size(self, symbol: str, lot_size: float) -> dict:
        minimum = self.get_capabilities().minimum_lot
        step = self.get_capabilities().lot_step
        if lot_size < minimum:
            return {"valid": False, "reason": f"Minimum lot size is {minimum}."}
        if abs(round(lot_size / step) * step - lot_size) > max(step * 0.001, 1e-8):
            return {"valid": False, "reason": f"Lot size must be in increments of {step}."}
        return {"valid": True, "reason": "Lot size is valid.", "minimum_lot": minimum, "lot_step": step}

    def place_order(self, symbol: str, direction: str, lot_size: float, price: float) -> dict:
        raise BrokerExecutionError(
            "Live execution is disabled until an official integration test is verified."
        )


class MT5Adapter(LiveAdapterBase):
    name = "mt5"

    def validate_credentials(self) -> bool:
        return bool(self.credentials.get("login") and self.credentials.get("password") and self.credentials.get("server"))

    def get_capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(platform="MT5", supports_official_api=True, metadata={"protocol": "official MetaTrader 5 integration"})


class MT5IntegrationError(BrokerExecutionError):
    pass


class MetaTrader5DemoAdapter(LiveAdapterBase):
    """Official MetaTrader 5 demo adapter.

    Real-money servers are rejected. The adapter is also fail-closed unless
    demo credentials and execution enabling are both explicitly present.
    """

    name = "mt5-demo"

    def __init__(self, credentials=None, live_trading_enabled=False, demo_execution_enabled=False, backend=None):
        super().__init__(credentials=credentials, live_trading_enabled=live_trading_enabled, demo_execution_enabled=demo_execution_enabled)
        self.backend = backend
        self._connected = False
        self._emergency_stopped = False

    def _get_backend(self):
        if self.backend is not None:
            return self.backend
        try:
            import MetaTrader5 as mt5
        except ImportError as exc:
            raise MT5IntegrationError(
                "MetaTrader5 is unavailable. Run this integration on Windows with MT5 installed."
            ) from exc
        return mt5

    def _is_demo_server(self) -> bool:
        server = str(self.credentials.get("server", "")).lower()
        return "demo" in server or "trial" in server

    def validate_credentials(self) -> bool:
        if self.credentials.get("environment", "demo").lower() != "demo":
            return False
        return bool(self.credentials.get("login") and self.credentials.get("password") and self._is_demo_server())

    def get_capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(
            platform="MT5",
            supports_official_api=True,
            metadata={"protocol": "official MetaTrader 5 Python integration", "account": "demo-only"},
        )

    def connect(self, retries: int = 2) -> bool:
        if self.live_trading_enabled:
            raise MT5IntegrationError("Live trading is not supported by the MT5 demo adapter.")
        if self._emergency_stopped:
            return False
        if not self.validate_credentials():
            raise MT5IntegrationError("Valid MT5 demo credentials are required; real-money servers are blocked.")
        mt5 = self._get_backend()
        login = int(self.credentials["login"])
        for attempt in range(retries + 1):
            try:
                initialized = mt5.initialize(
                    login=login,
                    password=self.credentials["password"],
                    server=self.credentials["server"],
                )
                if not initialized:
                    last_error = mt5.last_error() if hasattr(mt5, "last_error") else ("initialize failed", None)
                    if attempt == retries:
                        raise MT5IntegrationError(
                            "MT5 initialization failed. Details were withheld to avoid credential disclosure."
                            if last_error
                            else "MT5 initialization failed."
                        )
                    continue
                account = mt5.account_info()
                self._connected = bool(account is not None and int(getattr(account, "login", login)) == login)
                if self._connected and hasattr(account, "trade_mode"):
                    demo_mode = getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", 0)
                    if int(account.trade_mode) != int(demo_mode):
                        self._connected = False
                        mt5.shutdown()
                        raise MT5IntegrationError("The connected account is not a demo account.")
                return self._connected
            except MT5IntegrationError:
                raise
            except Exception as exc:
                if attempt == retries:
                    from xyfuss_forex_autopilot.auth import redact_secrets
                    raise MT5IntegrationError(redact_secrets(
                        f"MT5 connection failed: {type(exc).__name__}",
                        self.credentials,
                    )) from exc
        return False

    def health_check(self) -> dict[str, object]:
        try:
            if self._emergency_stopped:
                return {"connected": False, "healthy": False, "emergency_stop": True}
            if not self._connected:
                return {"connected": False, "healthy": False, "emergency_stop": False}
            mt5 = self._get_backend()
            terminal = mt5.terminal_info() if hasattr(mt5, "terminal_info") else None
            terminal_connected = getattr(terminal, "connected", True)
            account = mt5.account_info()
            healthy = bool(terminal_connected and account is not None)
            return {
                "connected": healthy,
                "healthy": healthy,
                "emergency_stop": False,
            }
        except Exception as exc:
            return {"connected": False, "healthy": False, "emergency_stop": False, "error": type(exc).__name__}

    def reconnect(self, retries: int = 2) -> bool:
        self.disconnect()
        self._connected = False
        return self.connect(retries=retries)

    def ensure_connected(self) -> None:
        if self._emergency_stopped:
            raise MT5IntegrationError("Emergency stop is active.")
        if not self._connected:
            if not self.connect():
                raise MT5IntegrationError("MT5 is not connected.")

    def disconnect(self) -> None:
        self._connected = False
        if hasattr(self.backend, "shutdown"):
            self.backend.shutdown()
        elif self.backend is None:
            try:
                self._get_backend().shutdown()
            except MT5IntegrationError:
                pass

    def get_account_info(self) -> dict:
        self.ensure_connected()
        account = self._get_backend().account_info()
        if account is None:
            raise MT5IntegrationError("MT5 account information is unavailable.")
        return {
            "connected": True,
            "login": getattr(account, "login", None),
            "balance": getattr(account, "balance", None),
            "equity": getattr(account, "equity", None),
            "margin": getattr(account, "margin", None),
            "currency": getattr(account, "currency", None),
        }

    def get_market_prices(self, symbols: list[str] | str) -> list[dict] | dict:
        self.ensure_connected()
        mt5 = self._get_backend()
        single = isinstance(symbols, str)
        requested = [symbols] if single else symbols
        prices = []
        for symbol in requested:
            normalized = symbol.replace("/", "").upper()
            tick = mt5.symbol_info_tick(normalized)
            if tick is None:
                raise MT5IntegrationError(f"MT5 returned no live price for {symbol}.")
            prices.append({
                "symbol": normalized,
                "bid": getattr(tick, "bid", None),
                "ask": getattr(tick, "ask", None),
                "time": getattr(tick, "time", None),
            })
        return prices[0] if single else prices

    def get_positions(self) -> list[dict]:
        self.ensure_connected()
        positions = self._get_backend().positions_get()
        if positions is None:
            return []
        return [
            {
                "ticket": getattr(position, "ticket", None),
                "symbol": getattr(position, "symbol", None),
                "type": getattr(position, "type", None),
                "volume": getattr(position, "volume", None),
                "price_open": getattr(position, "price_open", None),
            }
            for position in positions
        ]

    def place_order(self, symbol: str, direction: str, lot_size: float, price: float,
                    stop_loss: float | None = None, take_profit: float | None = None,
                    client_order_id: str | None = None, **kwargs) -> dict:
        if self.live_trading_enabled or not self.demo_execution_enabled:
            raise MT5IntegrationError("Demo order execution is disabled; explicitly enable demo execution while live trading remains off.")
        if stop_loss is None or take_profit is None:
            raise MT5IntegrationError("Every demo order requires stop-loss and take-profit.")
        if not self._is_demo_server() or self.credentials.get("environment", "demo").lower() != "demo":
            raise MT5IntegrationError("Real-money servers are blocked.")
        return self.order_gate.submit(
            client_order_id or f"{symbol}-{direction}-{lot_size}-{price}-{stop_loss}-{take_profit}",
            self._submit_order,
            symbol,
            direction,
            lot_size,
            price,
            stop_loss,
            take_profit,
        )

    def _submit_order(self, symbol: str, direction: str, lot_size: float, price: float,
                      stop_loss: float, take_profit: float) -> dict:
        self.ensure_connected()
        mt5 = self._get_backend()
        normalized = symbol.replace("/", "").upper()
        buy = direction.lower() == "buy"
        if direction.lower() not in ("buy", "sell"):
            raise MT5IntegrationError("Direction must be buy or sell.")
        tick = mt5.symbol_info_tick(normalized)
        if tick is None:
            raise MT5IntegrationError(f"MT5 returned no live price for {symbol}.")
        mt5_type = getattr(mt5, "ORDER_TYPE_BUY" if buy else "ORDER_TYPE_SELL")
        request = {
            "action": getattr(mt5, "TRADE_ACTION_DEAL"),
            "symbol": normalized,
            "volume": lot_size,
            "type": mt5_type,
            "price": getattr(tick, "ask" if buy else "bid"),
            "sl": stop_loss,
            "tp": take_profit,
            "deviation": 20,
            "magic": 20261101,
            "comment": "XYFUSS-DEMO",
            "type_time": getattr(mt5, "ORDER_TIME_GTC"),
            "type_filling": getattr(mt5, "ORDER_FILLING_IOC"),
        }
        result = mt5.order_send(request)
        if result is None or getattr(result, "retcode", None) != getattr(mt5, "TRADE_RETCODE_DONE", 10009):
            raise MT5IntegrationError(f"MT5 order rejected: {result}")
        return {"status": "accepted", "broker_order_id": getattr(result, "order", None)}

    def close_position(self, ticket: int) -> dict:
        self.ensure_connected()
        mt5 = self._get_backend()
        positions = mt5.positions_get(ticket=ticket) or []
        if not positions:
            raise MT5IntegrationError(f"Demo position {ticket} was not found.")
        position = positions[0]
        symbol = getattr(position, "symbol")
        volume = getattr(position, "volume")
        tick = mt5.symbol_info_tick(symbol)
        position_type = getattr(position, "type", 0)
        close_type = getattr(mt5, "ORDER_TYPE_SELL" if position_type == getattr(mt5, "POSITION_TYPE_BUY", 0) else "ORDER_TYPE_BUY", None)
        request = {
            "action": getattr(mt5, "TRADE_ACTION_DEAL"),
            "symbol": symbol,
            "volume": volume,
            "type": close_type,
            "position": ticket,
            "price": getattr(tick, "bid" if position_type == getattr(mt5, "POSITION_TYPE_BUY", 0) else "ask"),
            "deviation": 20,
            "magic": 20261101,
            "comment": "XYFUSS-DEMO-CLOSE",
            "type_time": getattr(mt5, "ORDER_TIME_GTC"),
            "type_filling": getattr(mt5, "ORDER_FILLING_IOC"),
        }
        result = mt5.order_send(request)
        if result is None or getattr(result, "retcode", None) != getattr(mt5, "TRADE_RETCODE_DONE", 10009):
            raise MT5IntegrationError(f"MT5 position close rejected: {result}")
        return {"status": "closed", "ticket": ticket}

    def emergency_stop(self) -> None:
        self._emergency_stopped = True
        self.disconnect()


class CTraderAdapter(LiveAdapterBase):
    name = "ctrader"

    def validate_credentials(self) -> bool:
        return bool(self.credentials.get("client_id") and self.credentials.get("client_secret") and self.credentials.get("access_token"))

    def get_capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(platform="cTrader", supports_official_api=True, metadata={"protocol": "official cTrader Open API"})


class DirectBrokerAdapter(LiveAdapterBase):
    name = "direct-api"

    def validate_credentials(self) -> bool:
        return bool(self.credentials.get("api_key"))

    def get_capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(platform="direct-api", supports_official_api=True, metadata={"protocol": "broker-specific official API"})


def create_broker_adapter(name: str, credentials: Mapping[str, str] | None = None, live_trading_enabled: bool = False, demo_execution_enabled: bool = False):
    adapters = {
        "paper": PaperBrokerAdapter,
        "mt5": MT5Adapter,
        "mt5-demo": MetaTrader5DemoAdapter,
        "ctrader": CTraderAdapter,
        "ctrader-demo": None,
        "direct-api": DirectBrokerAdapter,
    }
    try:
        adapter_type = adapters[name.lower()]
    except KeyError as exc:
        raise ValueError(f"Unsupported broker adapter: {name}") from exc
    if adapter_type is PaperBrokerAdapter:
        return adapter_type()
    if name.lower() == "ctrader-demo":
        from xyfuss_forex_autopilot.brokers.ctrader import CTraderDemoAdapter
        return CTraderDemoAdapter(credentials=credentials, live_trading_enabled=live_trading_enabled, demo_execution_enabled=demo_execution_enabled)
    return adapter_type(credentials=credentials, live_trading_enabled=live_trading_enabled, demo_execution_enabled=demo_execution_enabled)
