export type TradingMode = "research" | "backtest" | "paper" | "demo" | "live_disabled";
export type TradeDecision = "NO_TRADE" | "APPROVE_FOR_SIMULATION";

export interface MarketEvidence {
  source: string;
  observedAt: string;
  description: string;
  confidence: number;
  verified: boolean;
}

export interface MarketAssessment {
  symbol: string;
  asOf: string;
  freshnessSeconds: number;
  regime: "trending" | "ranging" | "volatile" | "unknown";
  evidence: MarketEvidence[];
  decision: TradeDecision;
  reasons: string[];
}

export interface CapitalProtectionStatus {
  emergencyStop: boolean;
  liveTradingEnabled: false;
  dailyLossPct: number;
  drawdownPct: number;
  openPositions: number;
  lastRiskCheck: string | null;
}

export interface AutopilotStatus {
  mode: TradingMode;
  connectedBroker: "none" | "paper" | "demo";
  marketAssessments: MarketAssessment[];
  protection: CapitalProtectionStatus;
}

// UI contracts only: the dashboard cannot submit or enable live orders.
