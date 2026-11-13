from __future__ import annotations

from math import isfinite

from xyfuss_forex_autopilot.audit import AuditReporter
from xyfuss_forex_autopilot.paper_trading import Backtester, PaperTradingEngine
from xyfuss_forex_autopilot.brokers import PaperBrokerAdapter
from xyfuss_forex_autopilot.scheduler import DashboardServer
from xyfuss_forex_autopilot.recommendations import EvidenceVerifier, RecommendationEngine
from xyfuss_forex_autopilot.dashboard import LearningEngine
from xyfuss_forex_autopilot.market import HistoricalTradeInvestigator, MarketInvestigator, TradeIdeaBuilder
from xyfuss_forex_autopilot.learning import TradeMonitor
from xyfuss_forex_autopilot.backtesting import NoTradeDecisionEngine
from xyfuss_forex_autopilot.risk import RiskManager, StopLossEngine
from xyfuss_forex_autopilot.scheduler import AutonomousScheduler
from xyfuss_forex_autopilot.strategies import StrategyCompetitionEngine
from xyfuss_forex_autopilot.profit_allocation import ProfitAllocationManager
from xyfuss_forex_autopilot.runtime import PersistentTradingState


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
        self.stop_loss_engine = StopLossEngine()
        self.backtester = Backtester()
        self.paper_trading = PaperTradingEngine()
        self.broker = PaperBrokerAdapter()
        self.monitor = TradeMonitor()
        self.learning = LearningEngine()
        self.audit = AuditReporter()
        self.profit_allocation = ProfitAllocationManager(
            ledger_path=self.settings.get("profit_allocation_ledger", "data/profit_allocation.jsonl"),
        )
        self.trading_state = PersistentTradingState(
            self.settings.get("trading_state_path", "data/trading-state.json"),
        )
        persisted_state = self.trading_state.load()
        self.emergency_stop = bool(
            persisted_state.get("emergency_stop") or persisted_state.get("recovery_warning")
        )
        self.dashboard = DashboardServer(
            host=self.settings.get("server_host", "0.0.0.0"),
            port=self.settings.get("server_port", 8000),
        )
        self.scheduler = AutonomousScheduler(
            interval_seconds=self.settings.get("scheduler_interval_seconds", 300),
        )

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

    def decide_trade(
        self,
        symbol: str,
        candles: list[dict],
        balance: float = 10000.0,
        max_risk_pct: float = 0.5,
        equity: float | None = None,
    ) -> dict:
        if self.settings.get("live_trading_enabled", False) or self.settings.get("trading_mode", "paper") != "paper":
            return {"decision": "NO_TRADE", "reason": "Live execution is disabled; only the paper-trading engine may execute orders.", "market": {}}

        persisted_state = self.trading_state.load()
        if self.emergency_stop or persisted_state.get("emergency_stop") or persisted_state.get("recovery_warning"):
            self.emergency_stop = True
            return {"decision": "NO_TRADE", "reason": "Persistent emergency stop is active; manual review is required before reset.", "market": {}}

        try:
            risk_balance = float(balance)
            current_equity = float(equity if equity is not None else balance)
            if not isfinite(risk_balance) or risk_balance <= 0:
                raise ValueError("Account balance must be finite and positive.")
            risk_snapshot = self.trading_state.record_equity(current_equity)
        except (TypeError, ValueError, RuntimeError, OSError) as exc:
            self.activate_emergency_stop()
            return {"decision": "NO_TRADE", "reason": f"Account risk state unavailable; emergency stop activated ({type(exc).__name__}).", "market": {}}

        daily_loss_limit = risk_balance * self.risk_manager.profile.daily_risk_limit_pct / 100.0
        drawdown_limit = risk_balance * self.risk_manager.profile.max_drawdown_pct / 100.0
        if risk_snapshot["daily_loss"] >= daily_loss_limit:
            self.activate_emergency_stop()
            return {"decision": "NO_TRADE", "reason": "Daily loss limit reached; persistent emergency stop activated.", "market": {"risk": risk_snapshot}}
        if risk_snapshot["drawdown"] >= drawdown_limit:
            self.activate_emergency_stop()
            return {"decision": "NO_TRADE", "reason": "Maximum account drawdown reached; persistent emergency stop activated.", "market": {"risk": risk_snapshot}}
        freshness = self.market_investigator.validate_freshness(candles)
        if not freshness["fresh"]:
            return {"decision": "NO_TRADE", "reason": freshness["reason"], "market": {"freshness": freshness}}
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

        entry_price = float(market_data.get("last_close", 1.0))
        spread = float(self.settings.get("spread", 0.0002))
        slippage = float(self.settings.get("slippage", 0.0001))
        stop_plan = self.stop_loss_engine.calculate_stop(
            entry_price,
            best.direction,
            candles,
            support=market_data.get("support"),
            resistance=market_data.get("resistance"),
            spread=spread,
            slippage=slippage,
        )
        stop_distance = abs(entry_price - stop_plan["stop_loss"])
        risk_assessment = self.risk_manager.verify_trade_risk(
            balance=balance,
            stop_distance_pct=stop_distance / entry_price,
            recommendation_score=recommendation_score,
            daily_loss_so_far=risk_snapshot["daily_loss"],
            drawdown_so_far=risk_snapshot["drawdown"],
            open_positions=[trade.__dict__ for trade in self.paper_trading.trades if trade.status == "open"],
            risk_pct=max_risk_pct,
            new_symbol=symbol,
        )
        if not risk_assessment["allowed"]:
            self.audit.record("trade_rejected", {"symbol": symbol, "reason": risk_assessment["reason"]})
            return {"decision": "NO_TRADE", "reason": risk_assessment["reason"], "market": market_data}

        take_profit = self.stop_loss_engine.calculate_take_profit(
            entry_price, stop_plan["stop_loss"], best.direction, spread=spread, slippage=slippage
        )
        validation = self.stop_loss_engine.validate_stop(entry_price, stop_plan["stop_loss"], take_profit, best.direction, spread, slippage)
        if not validation["valid"]:
            self.audit.record("stop_validation_failed", {"symbol": symbol, "reason": validation["reason"]})
            return {"decision": "NO_TRADE", "reason": validation["reason"], "market": market_data}

        trade_id = f"{symbol}-{best.strategy_name}-{abs(hash(str(market_data.get('timestamp'))))}"
        if self.monitor.is_duplicate(trade_id):
            return {"decision": "NO_TRADE", "reason": "Duplicate order prevented.", "trade_id": trade_id}

        trade = self.paper_trading.open_trade(
            trade_id=trade_id,
            symbol=symbol,
            direction=best.direction,
            lot_size=max(0.01, risk_assessment["position_size"] / 1000.0),
            entry_price=entry_price,
            stop_loss=stop_plan["stop_loss"],
            take_profit=take_profit,
            spread=spread,
            slippage=slippage,
        )

        self.audit.record("trade_opened", {"trade_id": trade_id, "symbol": symbol, "direction": best.direction, "stop_loss": stop_plan["stop_loss"], "take_profit": take_profit, "atr": stop_plan["atr"], "spread": spread, "slippage": slippage, "mode": "paper"})
        return {"decision": "TRADE_ALLOWED", "trade_id": trade_id, "trade": trade, "market": market_data, "risk": risk_assessment}

    def decide_trade_from_broker(
        self,
        symbol: str,
        candles: list[dict],
        broker_adapter,
        max_risk_pct: float = 0.5,
    ) -> dict:
        """Use a fresh, read-only broker account snapshot for the persistent risk guard.

        This method never submits, modifies, or closes broker orders. It only
        reads account balance/equity, then delegates to the paper-only decision
        pipeline. Any missing or disconnected account snapshot fails closed.
        """
        persisted_state = self.trading_state.load()
        if self.emergency_stop or persisted_state.get("emergency_stop") or persisted_state.get("recovery_warning"):
            self.emergency_stop = True
            return {
                "decision": "NO_TRADE",
                "reason": "Persistent emergency stop is active; broker monitoring is blocked pending manual review.",
                "market": {},
            }

        try:
            account = broker_adapter.get_account_info()
            if not isinstance(account, dict) or account.get("connected") is not True:
                raise RuntimeError("Broker account connection is not verified.")
            if account.get("balance") is None or account.get("equity") is None:
                raise ValueError("Broker account snapshot must include balance and equity.")

            result = self.decide_trade(
                symbol,
                candles,
                balance=account["balance"],
                max_risk_pct=max_risk_pct,
                equity=account["equity"],
            )
            result["account_monitoring"] = {
                "source": "broker_read_only",
                "connected": True,
                "currency": account.get("currency"),
                "equity_checked": True,
            }
            return result
        except Exception as exc:
            try:
                self.activate_emergency_stop()
            except Exception:
                self.emergency_stop = True
            return {
                "decision": "NO_TRADE",
                "reason": f"Broker account snapshot unavailable; emergency stop activated ({type(exc).__name__}).",
                "market": {},
                "account_monitoring": {"source": "broker_read_only", "connected": False},
            }

    def run_backtest(self, trades: list[dict]) -> dict:
        return self.backtester.run(trades)

    def run_dashboard(self, host: str = "0.0.0.0", port: int = 8000):
        if host not in {"127.0.0.1", "localhost", "::1"} and not (
            self.settings.get("dashboard_access_token") or self.settings.get("dashboard_password_hash")
        ):
            raise ValueError("A dashboard access token is required for remote dashboard access.")
        self.dashboard = DashboardServer(
            host=host,
            port=port,
            access_token=self.settings.get("dashboard_access_token"),
            password_hash=self.settings.get("dashboard_password_hash") or None,
            on_emergency_stop=self.activate_emergency_stop,
        )
        self.dashboard.start()
        return self.dashboard

    def activate_emergency_stop(self) -> dict:
        self.emergency_stop = True
        self.trading_state.set_emergency_stop(True)
        self.audit.record("emergency_stop", {"status": "active", "persistence": "saved"})
        return {"status": "stopped", "live_trading_enabled": False, "persistent": True}

    def run_scheduler(self, interval_seconds: int | None = None):
        self.scheduler = AutonomousScheduler(
            interval_seconds=interval_seconds or self.settings.get("scheduler_interval_seconds", 300),
            callback=lambda: self.audit.record("scheduler_tick", {"status": "cycle"}),
        )
        self.scheduler.start()
        return self.scheduler
