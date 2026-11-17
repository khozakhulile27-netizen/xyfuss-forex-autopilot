pub mod eligibility;

//! XYFUSS deterministic pre-trade safety gate.
//! This crate does not place orders. It rejects unsafe or incomplete proposals.

#[derive(Debug, Clone, PartialEq)]
pub struct RiskLimits {
    pub max_position_risk_pct: f64,
    pub max_daily_loss_pct: f64,
    pub max_drawdown_pct: f64,
    pub max_spread_pct: f64,
    pub max_open_positions: usize,
    pub max_market_age_seconds: u64,
}

impl Default for RiskLimits {
    fn default() -> Self {
        Self {
            max_position_risk_pct: 0.5,
            max_daily_loss_pct: 1.5,
            max_drawdown_pct: 5.0,
            max_spread_pct: 0.05,
            max_open_positions: 3,
            max_market_age_seconds: 30,
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct TradeProposal {
    pub symbol: String,
    pub direction: Direction,
    pub entry: f64,
    pub stop_loss: f64,
    pub take_profit: f64,
    pub account_equity: f64,
    pub proposed_risk_pct: f64,
    pub spread_pct: f64,
    pub market_age_seconds: u64,
    pub daily_loss_pct: f64,
    pub drawdown_pct: f64,
    pub open_positions: usize,
    pub evidence_score: f64,
    pub evidence_count: usize,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Direction { Long, Short }

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Decision { ApproveForSimulation, NoTrade }

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RiskVerdict {
    pub decision: Decision,
    pub reasons: Vec<String>,
}

pub fn evaluate(proposal: &TradeProposal, limits: &RiskLimits) -> RiskVerdict {
    let mut reasons = Vec::new();
    let valid_limits = limits.max_position_risk_pct.is_finite()
        && limits.max_position_risk_pct > 0.0
        && limits.max_position_risk_pct <= 100.0
        && limits.max_daily_loss_pct.is_finite()
        && limits.max_daily_loss_pct > 0.0
        && limits.max_daily_loss_pct <= 100.0
        && limits.max_drawdown_pct.is_finite()
        && limits.max_drawdown_pct > 0.0
        && limits.max_drawdown_pct <= 100.0
        && limits.max_spread_pct.is_finite()
        && (0.0..=100.0).contains(&limits.max_spread_pct)
        && limits.max_open_positions > 0;
    if !valid_limits {
        reasons.push("invalid_risk_configuration".into());
    }
    let finite = [proposal.entry, proposal.stop_loss, proposal.take_profit,
        proposal.account_equity, proposal.proposed_risk_pct, proposal.spread_pct,
        proposal.daily_loss_pct, proposal.drawdown_pct, proposal.evidence_score]
        .iter().all(|v| v.is_finite());

    if proposal.symbol.trim().is_empty() { reasons.push("missing_symbol".into()); }
    if !finite { reasons.push("non_finite_numeric_input".into()); }
    if proposal.entry <= 0.0 || proposal.account_equity <= 0.0 { reasons.push("invalid_price_or_equity".into()); }
    if proposal.evidence_count == 0 || !(0.0..=1.0).contains(&proposal.evidence_score) || proposal.evidence_score < 0.70 {
        reasons.push("insufficient_verified_evidence".into());
    }
    if proposal.market_age_seconds > limits.max_market_age_seconds { reasons.push("stale_market_data".into()); }
    if proposal.proposed_risk_pct <= 0.0 || proposal.proposed_risk_pct > limits.max_position_risk_pct { reasons.push("position_risk_limit_exceeded".into()); }
    if proposal.spread_pct < 0.0 || proposal.spread_pct > limits.max_spread_pct { reasons.push("spread_limit_exceeded".into()); }
    if proposal.daily_loss_pct < 0.0 || proposal.daily_loss_pct >= limits.max_daily_loss_pct { reasons.push("daily_loss_limit_reached".into()); }
    if proposal.drawdown_pct < 0.0 || proposal.drawdown_pct >= limits.max_drawdown_pct { reasons.push("drawdown_limit_reached".into()); }
    if proposal.open_positions >= limits.max_open_positions { reasons.push("open_position_limit_reached".into()); }

    let protective = match proposal.direction {
        Direction::Long => proposal.stop_loss > 0.0 && proposal.stop_loss < proposal.entry && proposal.take_profit > proposal.entry,
        Direction::Short => proposal.stop_loss > proposal.entry && proposal.take_profit > 0.0 && proposal.take_profit < proposal.entry,
    };
    if !protective { reasons.push("invalid_protective_levels".into()); }

    let decision = if reasons.is_empty() { Decision::ApproveForSimulation } else { Decision::NoTrade };
    RiskVerdict { decision, reasons }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn valid() -> TradeProposal {
        TradeProposal { symbol: "EURUSD".into(), direction: Direction::Long, entry: 1.10,
            stop_loss: 1.095, take_profit: 1.11, account_equity: 10_000.0,
            proposed_risk_pct: 0.25, spread_pct: 0.01, market_age_seconds: 2,
            daily_loss_pct: 0.2, drawdown_pct: 0.5, open_positions: 0,
            evidence_score: 0.85, evidence_count: 4 }
    }

    #[test]
    fn valid_proposal_only_passes_to_simulation() {
        assert_eq!(evaluate(&valid(), &RiskLimits::default()).decision, Decision::ApproveForSimulation);
    }

    #[test]
    fn stale_data_is_no_trade() {
        let mut p = valid(); p.market_age_seconds = 31;
        assert!(evaluate(&p, &RiskLimits::default()).reasons.contains(&"stale_market_data".into()));
    }

    #[test]
    fn missing_evidence_is_no_trade() {
        let mut p = valid(); p.evidence_count = 0;
        assert_eq!(evaluate(&p, &RiskLimits::default()).decision, Decision::NoTrade);
    }

    #[test]
    fn invalid_stop_is_no_trade() {
        let mut p = valid(); p.stop_loss = 1.105;
        assert!(evaluate(&p, &RiskLimits::default()).reasons.contains(&"invalid_protective_levels".into()));
    }

    #[test]
    fn non_finite_input_is_no_trade() {
        let mut p = valid(); p.entry = f64::NAN;
        assert_eq!(evaluate(&p, &RiskLimits::default()).decision, Decision::NoTrade);
    }

    #[test]
    fn invalid_risk_configuration_is_no_trade() {
        let mut limits = RiskLimits::default();
        limits.max_position_risk_pct = f64::NAN;
        assert!(evaluate(&valid(), &limits).reasons.contains(&"invalid_risk_configuration".into()));
    }
}
