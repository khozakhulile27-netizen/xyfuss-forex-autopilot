from xyfuss_forex_autopilot.risk import RiskManager


def test_risk_manager_rejects_overrisk_trade():
    manager = RiskManager()
    approved = manager.assess_trade(balance=10000.0, stop_distance_pct=0.08, recommendation_score=0.9)
    assert approved["approved"] is True

    strict_result = manager.assess_trade(balance=1000.0, stop_distance_pct=0.25, recommendation_score=0.9)
    assert strict_result["approved"] is False
