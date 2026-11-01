from __future__ import annotations

from xyfuss_forex_autopilot.models import TradeIdea


class RecommendationEngine:
    """Rank trade ideas according to score and evidence quality."""

    def rank(self, ideas: list[TradeIdea]) -> list[TradeIdea]:
        return sorted(ideas, key=lambda item: (item.score * item.confidence, item.score), reverse=True)

    def select_best(self, ideas: list[TradeIdea]) -> TradeIdea | None:
        ranked = self.rank(ideas)
        return ranked[0] if ranked else None
