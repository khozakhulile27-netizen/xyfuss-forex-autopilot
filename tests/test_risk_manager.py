from xyfuss_forex_autopilot.evidence import EvidenceVerifier


def test_evidence_verification_accepts_strong_evidence():
    evidence = [
        {"score": 0.95, "confidence": 0.9, "detail": "Strong follow-through"},
        {"score": 0.8, "confidence": 0.8, "detail": "Trend confirms"},
    ]
    result = EvidenceVerifier().verify(evidence, threshold=0.55)
    assert result["passed"] is True
    assert result["score"] >= 0.55


def test_evidence_verification_rejects_weak_evidence():
    evidence = [
        {"score": 0.1, "confidence": 0.1, "detail": "Weak signal"},
        {"score": 0.2, "confidence": 0.1, "detail": "Minimal confirmation"},
    ]
    result = EvidenceVerifier().verify(evidence, threshold=0.55)
    assert result["passed"] is False
