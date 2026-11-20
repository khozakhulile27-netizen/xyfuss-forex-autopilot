from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from xyfuss_forex_autopilot.market import MarketUniverseScanner


class FakeBroker:
    def __init__(self, symbols=None, candles=None):
        self.symbols = symbols or [
            {"symbol_id": 1, "name": "EURUSD", "digits": 5},
            {"symbol_id": 2, "name": "GBPUSD", "digits": 5},
        ]
        self.candles = candles or [
            {"timestamp": (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()}
            for _ in range(30)
        ]
        self.requested = []
        self.order_calls = 0

    def get_market_data(self):
        return self.symbols

    def get_historical_bars(self, **kwargs):
        self.requested.append(kwargs)
        return self.candles

    def place_order(self, *_args, **_kwargs):
        self.order_calls += 1
        raise AssertionError("The market scanner must never submit orders.")


class FreshInvestigator:
    def validate_freshness(self, candles, max_age_seconds):
        return {"fresh": True, "reason": "fresh"}

    def investigate(self, symbol, candles):
        return {
            "symbol": symbol,
            "signal": "BUY",
            "confidence": 0.9,
            "evidence": [{"source": "test", "score": 0.9, "confidence": 0.9}],
        }


class RankingStrategies:
    def run(self, symbol, market):
        score = 0.9 if symbol == "GBPUSD" else 0.8
        return [
            SimpleNamespace(
                direction="buy",
                score=score,
                confidence=0.85,
                strategy_name="test-strategy",
                rationale="test-only candidate",
            )
        ]


class PassingVerifier:
    def verify(self, evidence, threshold):
        return {"passed": True, "score": 0.9, "reason": "test evidence"}


class PassingNoTradeGate:
    def decide(self, market, evidence, recommendation_score):
        return {"no_trade": False, "reasons": []}


def scanner():
    return MarketUniverseScanner(
        market_investigator=FreshInvestigator(),
        strategy_engine=RankingStrategies(),
        evidence_verifier=PassingVerifier(),
        no_trade_engine=PassingNoTradeGate(),
    )


def test_scanner_requires_explicit_allowlist():
    broker = FakeBroker()

    result = scanner().scan(broker, allowed_symbols=[])

    assert result["status"] == "blocked"
    assert result["best_candidate"] is None
    assert broker.requested == []


def test_scanner_ranks_candidates_without_submitting_orders():
    broker = FakeBroker()

    result = scanner().scan(
        broker,
        allowed_symbols=["EUR/USD", "GBPUSD"],
        period="M5",
        weeks=1,
        count=100,
    )

    assert result["status"] == "complete"
    assert result["scanned"] == 2
    assert result["candidate_count"] == 2
    assert result["best_candidate"]["symbol"] == "GBPUSD"
    assert all(item["decision"] == "CANDIDATE_FOR_RISK_ASSESSMENT" for item in result["candidates"])
    assert broker.order_calls == 0
    assert len(broker.requested) == 2


def test_scanner_rejects_symbols_not_available_on_account():
    broker = FakeBroker(symbols=[{"symbol_id": 1, "name": "EURUSD", "digits": 5}])

    result = scanner().scan(broker, allowed_symbols=["USDJPY"])

    assert result["candidate_count"] == 0
    assert result["best_candidate"] is None
    assert result["no_trade"][0]["decision"] == "NO_TRADE"
