from types import SimpleNamespace

import pytest

from xyfuss_forex_autopilot.brokers.ctrader import (
    CTraderDemoAdapter,
    CTraderIntegrationError,
    OfficialCTraderBackend,
)


def test_relative_cTrader_trendbar_values_are_normalised_to_ohlc():
    bars = [
        SimpleNamespace(
            low=110000,
            deltaOpen=100,
            deltaClose=300,
            deltaHigh=500,
            utcTimestampInMinutes=29_000_001,
            volume=42,
        )
    ]

    result = OfficialCTraderBackend._normalise_trendbars(bars, digits=5)

    assert len(result) == 1
    assert result[0]["open"] == 1.101
    assert result[0]["high"] == 1.105
    assert result[0]["low"] == 1.1
    assert result[0]["close"] == 1.103
    assert result[0]["volume"] == 42
    assert result[0]["timestamp"].endswith("+00:00")


def test_trendbars_are_sorted_oldest_first():
    bars = [
        SimpleNamespace(low=110000, deltaOpen=0, deltaClose=100, deltaHigh=200,
                        utcTimestampInMinutes=29_000_002, volume=1),
        SimpleNamespace(low=109000, deltaOpen=0, deltaClose=100, deltaHigh=200,
                        utcTimestampInMinutes=29_000_001, volume=2),
    ]

    result = OfficialCTraderBackend._normalise_trendbars(bars, digits=5)

    assert [bar["volume"] for bar in result] == [2, 1]


def test_incomplete_or_inconsistent_trendbars_fail_closed():
    class IncompleteBar:
        low = 110000
        deltaOpen = 100
        deltaClose = 200
        deltaHigh = 300
        utcTimestampInMinutes = 29_000_001
        volume = 1

        def HasField(self, name):
            return name != "deltaClose"

    with pytest.raises(CTraderIntegrationError, match="incomplete trend bar"):
        OfficialCTraderBackend._normalise_trendbars([IncompleteBar()], digits=5)

    invalid = SimpleNamespace(
        low=110000,
        deltaOpen=500,
        deltaClose=200,
        deltaHigh=300,
        utcTimestampInMinutes=29_000_001,
        volume=1,
    )
    with pytest.raises(CTraderIntegrationError, match="inconsistent OHLC"):
        OfficialCTraderBackend._normalise_trendbars([invalid], digits=5)


def test_historical_candle_adapter_delegates_without_fabricating_data():
    expected = [{"timestamp": "2026-11-20T00:00:00+00:00", "open": 1.1}]
    calls = []

    class Backend:
        def connect(self):
            return True

        def historical_bars(self, **kwargs):
            calls.append(kwargs)
            return expected

        def disconnect(self):
            pass

    adapter = CTraderDemoAdapter(backend=Backend())

    assert adapter.get_historical_bars(12, period="M15", weeks=2, count=100) == expected
    assert calls == [{"symbol_id": 12, "period": "M15", "weeks": 2, "count": 100}]
