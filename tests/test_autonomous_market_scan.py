import threading
from datetime import datetime, timedelta, timezone

from xyfuss_forex_autopilot.core import XyFussForexAutopilot
from xyfuss_forex_autopilot.scheduler import AutonomousScheduler


class ReadOnlyMarketBroker:
    def get_market_data(self):
        return [{"symbol_id": 1, "name": "EURUSD", "digits": 5}]

    def get_historical_bars(self, **_kwargs):
        timestamp = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
        return [
            {
                "timestamp": timestamp,
                "open": 1.10 + index * 0.00001,
                "high": 1.101 + index * 0.00001,
                "low": 1.099 + index * 0.00001,
                "close": 1.1005 + index * 0.00001,
                "volume": 100,
            }
            for index in range(40)
        ]


def test_core_autonomous_cycle_runs_market_scan_without_order_execution():
    broker = ReadOnlyMarketBroker()
    autopilot = XyFussForexAutopilot(
        settings={"market_watchlist": ["EURUSD"]},
        broker=broker,
    )

    result = autopilot.run_autonomous_cycle()

    assert result["status"] == "complete"
    assert result["scanned"] == 1
    assert result["best_candidate"] is None or result["best_candidate"]["decision"] == "CANDIDATE_FOR_RISK_ASSESSMENT"


def test_core_autonomous_cycle_stops_when_emergency_stop_is_active():
    autopilot = XyFussForexAutopilot()
    autopilot.emergency_stop = True

    result = autopilot.run_autonomous_cycle()

    assert result["status"] == "stopped"
    assert result["scanned"] == 0


def test_scheduler_records_failure_and_recovers_on_next_cycle():
    first_cycle = threading.Event()
    recovered_cycle = threading.Event()
    calls = []

    def callback():
        calls.append(len(calls) + 1)
        if len(calls) == 1:
            first_cycle.set()
            raise RuntimeError("simulated temporary scan failure")
        recovered_cycle.set()
        return {"status": "complete"}

    scheduler = AutonomousScheduler(interval_seconds=1, callback=callback).start()
    try:
        assert first_cycle.wait(timeout=3)
        assert recovered_cycle.wait(timeout=3)
        status = scheduler.status()
        for _ in range(100):
            if status["cycles"] >= 2:
                break
            threading.Event().wait(0.01)
            status = scheduler.status()
        assert status["cycles"] >= 2
        assert status["last_error"] is None
        assert status["last_result"] == {"status": "complete"}
    finally:
        scheduler.stop()
