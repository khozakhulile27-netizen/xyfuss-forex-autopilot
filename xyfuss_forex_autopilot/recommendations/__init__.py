from __future__ import annotations

from typing import Iterable


class EvidenceVerifier:
    """Independently validate whether the evidence supports a trade idea."""

    def verify(self, evidence: Iterable[dict], threshold: float = 0.55) -> dict:
        items = list(evidence)
        if not items:
            return {"passed": False, "score": 0.0, "reason": "No evidence collected."}

        weighted = sum(float(item.get("score", 0.0)) * float(item.get("confidence", 0.0)) for item in items)
        total = max(1.0, sum(float(item.get("confidence", 0.0)) for item in items))
        final_score = weighted / total

        passed = final_score >= threshold
        reason = "Evidence supports trade execution." if passed else "Evidence is insufficient or inconsistent."
        return {"passed": passed, "score": round(final_score, 4), "reason": reason}


class RecommendationEngine:
    """Rank trade ideas by direction, confidence, and supporting evidence."""

    def rank(self, ideas: Iterable[dict]) -> list[dict]:
        ranked = sorted((dict(idea) for idea in ideas), key=lambda idea: float(idea.get("confidence", 0.0)), reverse=True)
        return ranked
