from __future__ import annotations

from xyfuss_forex_autopilot.audit import AuditReporter
from xyfuss_forex_autopilot.backtesting import Backtester
from xyfuss_forex_autopilot.brokers import PaperBrokerAdapter
from xyfuss_forex_autopilot.dashboard import DashboardServer
from xyfuss_forex_autopilot.evidence import EvidenceVerifier
from xyfuss_forex_autopilot.learning import LearningEngine
from xyfuss_forex_autopilot.market import HistoricalTradeInvestigator, MarketInvestigator, TradeIdeaBuilder
from xyfuss_forex_autopilot.monitoring import TradeMonitor
from xyfuss_forex_autopilot.no_trade import NoTradeDecisionEngine
from xyfuss_forex_autopilot.paper_trading import PaperTradingEngine
from xyfuss_forex_autopilot.recommendations import RecommendationEngine
from xyfuss_forex_autopilot.risk import RiskManager
from xyfuss_forex_autopilot.scheduler import AutonomousScheduler
from xyfuss_forex_autopilot.strategies import StrategyCompetitionEngine


class XyFussForexAutopilot:
    """Main orchestration layer for the independent Forex autopilot."""

    def __init__(self, settings: dict | None = None):
        self.settings = settings or {}
        self.market_investigator = MarketInvestigator()
        self.historical_investigator = HistoricalTradeInvestigator()
        self.idea_builder = TradeIdeaBuilder()
        self.strategy_engine = StrategyCompetitionEngine()
        self.evidence_verifier = EvidenceVerifier()
        self.recommendation_engine = RecommendationEngine()
        self.no_trade_engine = NoTradeDecisionEngine()
        self.risk_manager = RiskManager()
        self.backtester = Backtester()
        self.paper_trading = PaperTradingEngine()
        self.broker = PaperBrokerAdapter()
        self.monitor = TradeMonitor()
        self.learning = LearningEngine()
        self.audit = AuditReporter()
        self.dashboard = DashboardServer(host=self.settings.get("server_host", "0.0.0.0"), port=self.settings.get("server_port", 8000))
        self.scheduler = AutonomousScheduler(interval_seconds=self.settings.get("scheduler_interval_seconds", 300))

    def investigate_market(self, symbol: str, candles: list[dict]) -> dict:
        return self.market_investigator.investigate(symbol, candles)

    def compare_strategies(self, symbol: str, market_data: dict) -> list:
        return self.strategy_engine.run(symbol, market_data)

    def build_recommendations(self, symbol: str, market_data: dict) -> list:
        strategy_results = self.compare_strategies(symbol, market_data)
        ideas = []
        for result in strategy_results:
            idea = self.idea_builder.build(
                symbol=symbol,
                direction=result.direction,
                score=result.score,
                confidence=result.confidence,
                evidence=market_data.get("evidence", []),
                rationale=result.rationale,
            )
            ideas.append(idea)
        return self.recommendation_engine.rank(ideas)

    def decide_trade(self, symbol: str, candles: list[dict], balance: float = 10000.0, max_risk_pct: float = 0.5) -> dict:
        market_data = self.investigate_market(symbol, candles)
        strategy_results = self.compare_strategies(symbol, market_data)
        if not strategy_results:
            return {"decision": "NO_TRADE", "reason": "No strategy results were produced.", "market": market_data}

        evidence_verification = self.evidence_verifier.verify(market_data.get("evidence", []), threshold=0.55)
        best = max(strategy_results, key=lambda item: item.score)
        recommendation_score = best.score
        no_trade = self.no_trade_engine.decide(market_data, evidence_verification, recommendation_score)

        if no_trade["no_trade"]:
            return {"decision": "NO_TRADE", "reason": no_trade["reasons"], "market": market_data}

        risk_assessment = self.risk_manager.assess_trade(balance, 0.01, recommendation_score=recommendation_score)
        if not risk_assessment["approved"]:
            return {"decision": "NO_TRADE", "reason": risk_assessment["reason"], "market": market_data}

        trade_id = f"{symbol}-{best.strategy_name}-{abs(hash(str(market_data.get('timestamp'))))}"
        if self.monitor.is_duplicate(trade_id):
            return {"decision": "NO_TRADE", "reason": "Duplicate order prevented.", "trade_id": trade_id}

        trade = self.paper_trading.open_trade(
            trade_id=trade_id,
            symbol=symbol,
            direction=best.direction,
            lot_size=max(0.01, risk_assessment["position_size"] / 1000.0),
            entry_price=float(market_data.get("last_close", 1.0)),
            stop_loss=float(market_data.get("last_close", 1.0)) * 0.995,
            take_profit=float(market_data.get("last_close", 1.0)) * 1.01,
        )

        self.audit.record("trade_opened", {"trade_id": trade_id, "symbol": symbol, "direction": best.direction})
        return {"decision": "TRADE_ALLOWED", "trade_id": trade_id, "trade": trade, "market": market_data, "risk": risk_assessment}

    def run_backtest(self, trades: list[dict]) -> dict:
        return self.backtester.run(trades)

    def run_dashboard(self, host: str = "0.0.0.0", port: int = 8000):
        self.dashboard = DashboardServer(host=host, port=port)
        self.dashboard.start()
        return self.dashboard

    def run_scheduler(self, interval_seconds: int | None = None):
        self.scheduler = AutonomousScheduler(interval_seconds=interval_seconds or self.settings.get("scheduler_interval_seconds", 300), callback=lambda: self.audit.record("scheduler_tick", {"status": "cycle"}))
        self.scheduler.start()
        return self.scheduler
