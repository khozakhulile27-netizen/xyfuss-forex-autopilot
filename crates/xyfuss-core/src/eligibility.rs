//! Independent fail-closed eligibility gate.
//! Eligibility answers whether a candidate may proceed to risk assessment.
//! It never authorizes an order or overrides the capital-protection gate.

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DataIntegrity {
    Verified,
    Missing,
    Stale,
    Contradictory,
    Malformed,
    Unverified,
}

#[derive(Debug, Clone, PartialEq)]
pub struct EligibilityPolicy {
    pub allowed_symbols: Vec<String>,
    pub allowed_strategies: Vec<String>,
    pub minimum_verified_sources: usize,
    pub minimum_evidence_score: f64,
    pub maximum_market_age_seconds: u64,
}

impl Default for EligibilityPolicy {
    fn default() -> Self {
        Self {
            allowed_symbols: Vec::new(),
            allowed_strategies: Vec::new(),
            minimum_verified_sources: 2,
            minimum_evidence_score: 0.70,
            maximum_market_age_seconds: 30,
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct EligibilityInput {
    pub symbol: String,
    pub strategy_id: String,
    pub data_integrity: DataIntegrity,
    pub market_age_seconds: u64,
    pub verified_source_count: usize,
    pub evidence_score: f64,
    pub instrument_enabled: bool,
    pub broker_connected: bool,
    pub account_permitted: bool,
    pub trading_session_open: bool,
    pub strategy_validated: bool,
    pub trading_halt_active: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum EligibilityDecision {
    EligibleForRiskAssessment,
    Ineligible,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EligibilityVerdict {
    pub decision: EligibilityDecision,
    pub reasons: Vec<String>,
}

pub fn evaluate_eligibility(
    input: &EligibilityInput,
    policy: &EligibilityPolicy,
) -> EligibilityVerdict {
    let mut reasons = Vec::new();

    if input.symbol.trim().is_empty() {
        reasons.push("missing_symbol".to_owned());
    } else if policy.allowed_symbols.is_empty() {
        reasons.push("symbol_allowlist_not_configured".to_owned());
    } else if !policy.allowed_symbols.iter().any(|item| item.eq_ignore_ascii_case(&input.symbol)) {
        reasons.push("symbol_not_allowlisted".to_owned());
    }

    if input.strategy_id.trim().is_empty() {
        reasons.push("missing_strategy".to_owned());
    } else if policy.allowed_strategies.is_empty() {
        reasons.push("strategy_allowlist_not_configured".to_owned());
    } else if !policy.allowed_strategies.iter().any(|item| item == &input.strategy_id) {
        reasons.push("strategy_not_allowlisted".to_owned());
    }

    if !policy.minimum_evidence_score.is_finite()
        || !(0.0..=1.0).contains(&policy.minimum_evidence_score)
        || policy.minimum_verified_sources == 0
    {
        reasons.push("invalid_eligibility_policy".to_owned());
    }

    if input.data_integrity != DataIntegrity::Verified {
        reasons.push(match input.data_integrity {
            DataIntegrity::Missing => "market_data_missing",
            DataIntegrity::Stale => "market_data_stale",
            DataIntegrity::Contradictory => "market_data_contradictory",
            DataIntegrity::Malformed => "market_data_malformed",
            DataIntegrity::Unverified => "market_data_unverified",
            DataIntegrity::Verified => unreachable!(),
        }.to_owned());
    }

    if input.market_age_seconds > policy.maximum_market_age_seconds {
        reasons.push("market_data_too_old".to_owned());
    }
    if input.verified_source_count < policy.minimum_verified_sources {
        reasons.push("insufficient_independent_sources".to_owned());
    }
    if !input.evidence_score.is_finite()
        || !(0.0..=1.0).contains(&input.evidence_score)
        || input.evidence_score < policy.minimum_evidence_score
    {
        reasons.push("evidence_threshold_not_met".to_owned());
    }
    if !input.instrument_enabled {
        reasons.push("instrument_not_enabled".to_owned());
    }
    if !input.broker_connected {
        reasons.push("broker_not_connected".to_owned());
    }
    if !input.account_permitted {
        reasons.push("account_not_permitted".to_owned());
    }
    if !input.trading_session_open {
        reasons.push("trading_session_closed".to_owned());
    }
    if !input.strategy_validated {
        reasons.push("strategy_not_validated".to_owned());
    }
    if input.trading_halt_active {
        reasons.push("trading_halt_active".to_owned());
    }

    let decision = if reasons.is_empty() {
        EligibilityDecision::EligibleForRiskAssessment
    } else {
        EligibilityDecision::Ineligible
    };

    EligibilityVerdict { decision, reasons }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn valid_policy() -> EligibilityPolicy {
        EligibilityPolicy {
            allowed_symbols: vec!["EURUSD".to_owned()],
            allowed_strategies: vec!["trend-follow-v1".to_owned()],
            ..EligibilityPolicy::default()
        }
    }

    fn valid_input() -> EligibilityInput {
        EligibilityInput {
            symbol: "EURUSD".to_owned(),
            strategy_id: "trend-follow-v1".to_owned(),
            data_integrity: DataIntegrity::Verified,
            market_age_seconds: 2,
            verified_source_count: 3,
            evidence_score: 0.85,
            instrument_enabled: true,
            broker_connected: true,
            account_permitted: true,
            trading_session_open: true,
            strategy_validated: true,
            trading_halt_active: false,
        }
    }

    #[test]
    fn valid_candidate_only_proceeds_to_risk_assessment() {
        assert_eq!(
            evaluate_eligibility(&valid_input(), &valid_policy()).decision,
            EligibilityDecision::EligibleForRiskAssessment
        );
    }

    #[test]
    fn empty_default_allowlists_fail_closed() {
        let verdict = evaluate_eligibility(&valid_input(), &EligibilityPolicy::default());
        assert!(verdict.reasons.contains(&"symbol_allowlist_not_configured".to_owned()));
        assert!(verdict.reasons.contains(&"strategy_allowlist_not_configured".to_owned()));
    }

    #[test]
    fn every_untrusted_data_state_is_rejected() {
        for state in [
            DataIntegrity::Missing,
            DataIntegrity::Stale,
            DataIntegrity::Contradictory,
            DataIntegrity::Malformed,
            DataIntegrity::Unverified,
        ] {
            let mut input = valid_input();
            input.data_integrity = state;
            assert_eq!(
                evaluate_eligibility(&input, &EligibilityPolicy::default()).decision,
                EligibilityDecision::Ineligible
            );
        }
    }

    #[test]
    fn allowlists_are_enforced() {
        let policy = EligibilityPolicy {
            allowed_symbols: vec!["GBPUSD".to_owned()],
            allowed_strategies: vec!["breakout-v2".to_owned()],
            ..EligibilityPolicy::default()
        };
        let verdict = evaluate_eligibility(&valid_input(), &policy);
        assert!(verdict.reasons.contains(&"symbol_not_allowlisted".to_owned()));
        assert!(verdict.reasons.contains(&"strategy_not_allowlisted".to_owned()));
    }

    #[test]
    fn missing_broker_or_account_permission_blocks_candidate() {
        let mut input = valid_input();
        input.broker_connected = false;
        input.account_permitted = false;
        let verdict = evaluate_eligibility(&input, &EligibilityPolicy::default());
        assert!(verdict.reasons.contains(&"broker_not_connected".to_owned()));
        assert!(verdict.reasons.contains(&"account_not_permitted".to_owned()));
    }

    #[test]
    fn unvalidated_strategy_and_active_halt_block_candidate() {
        let mut input = valid_input();
        input.strategy_validated = false;
        input.trading_halt_active = true;
        let verdict = evaluate_eligibility(&input, &EligibilityPolicy::default());
        assert!(verdict.reasons.contains(&"strategy_not_validated".to_owned()));
        assert!(verdict.reasons.contains(&"trading_halt_active".to_owned()));
    }

    #[test]
    fn invalid_or_low_evidence_blocks_candidate() {
        for score in [f64::NAN, f64::INFINITY, -0.1, 1.1, 0.69] {
            let mut input = valid_input();
            input.evidence_score = score;
            assert_eq!(
                evaluate_eligibility(&input, &EligibilityPolicy::default()).decision,
                EligibilityDecision::Ineligible
            );
        }
    }
}
