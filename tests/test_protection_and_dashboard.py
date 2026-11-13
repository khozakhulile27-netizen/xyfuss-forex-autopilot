from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen
import urllib.error
import pytest

from xyfuss_forex_autopilot.core import XyFussForexAutopilot
from xyfuss_forex_autopilot.market import MarketInvestigator
from xyfuss_forex_autopilot.paper_trading import PaperTradingEngine
from xyfuss_forex_autopilot.scheduler import DashboardServer
from xyfuss_forex_autopilot.monitoring import PaperBrokerAdapter, place_paper_order_safely


def test_fresh_market_data_and_stale_data():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    investigator = MarketInvestigator()
    current = [{"timestamp": now.isoformat(), "close": 1.0}]
    stale = [{"timestamp": (now - timedelta(minutes=10)).isoformat(), "close": 1.0}]
    assert investigator.validate_freshness(current, now=now)["fresh"] is True
    assert investigator.validate_freshness(stale, now=now)["fresh"] is False


def test_live_configuration_and_emergency_stop_never_execute(tmp_path):
    live = XyFussForexAutopilot({"live_trading_enabled": True, "trading_state_path": str(tmp_path / "live-state.json")})
    result = live.decide_trade("EUR/USD", [])
    assert result["decision"] == "NO_TRADE"
    emergency = XyFussForexAutopilot({"trading_state_path": str(tmp_path / "emergency-state.json")})
    emergency.activate_emergency_stop()
    result = emergency.decide_trade("EUR/USD", [])
    assert result["decision"] == "NO_TRADE"


def test_duplicate_paper_close_is_not_counted_twice():
    engine = PaperTradingEngine()
    engine.open_trade("trade-1", "EUR/USD", "buy", 1.0, 1.1000, 1.0900, 1.1200)
    first = engine.close_trade("trade-1", 1.1100)
    second = engine.close_trade("trade-1", 1.1100)
    assert first["pnl"] != 0
    assert second["status"] == "duplicate_close"


def test_remote_dashboard_requires_token():
    server = DashboardServer(host="0.0.0.0", port=0)
    with pytest.raises(ValueError, match="access token"):
        server.start()


def test_dashboard_emergency_stop_control():
    stopped = []
    server = DashboardServer(host="127.0.0.1", port=0, on_emergency_stop=lambda: stopped.append(True))
    server.start()
    port = server._server.server_address[1]
    request = Request(f"http://127.0.0.1:{port}/emergency-stop", data=b"", method="POST")
    with urlopen(request, timeout=2) as response:
        assert response.status == 200
    assert stopped == [True]
    server.stop()


def test_paper_broker_safely_rejects_live_adapter():
    result = place_paper_order_safely(PaperBrokerAdapter(), "EUR/USD", "buy", 0.01, 1.1)
    assert result["status"] == "paper-only"
