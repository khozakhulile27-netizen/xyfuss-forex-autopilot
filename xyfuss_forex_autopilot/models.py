from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class MarketObservation:
    symbol: str
    timestamp: datetime
    open_price: float
    high: float
    low: float
    close: float
    volume: float = 0.0

    @property
    def typical_price(self) -> float:
        return (self.high + self.low + self.close) / 3.0


@dataclass
class EvidenceRecord:
    source: str
    signal: str
    score: float
    detail: str
    confidence: float


@dataclass
class StrategyResult:
    strategy_name: str
    symbol: str
    score: float
    direction: str
    confidence: float
    rationale: str


@dataclass
class TradeIdea:
    symbol: str
    direction: str
    score: float
    confidence: float
    risk: float
    rationale: str
    evidence: list[EvidenceRecord] = field(default_factory=list)


@dataclass
class TradeExecution:
    trade_id: str
    symbol: str
    direction: str
    strategy: str
    lot_size: float
    entry_price: float
    stop_loss: float
    take_profit: float
    status: str = "pending"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
