"""Compliance exclusion logic."""

from __future__ import annotations

from dataclasses import dataclass

from collection_swarm.store import SimulationStore


@dataclass(frozen=True)
class ComplianceExclusion:
    profile_id: str
    strategy_id: str
    compliance_score: float
    escalation_risk: float
    reason: str


def check_exclusions(
    store: SimulationStore,
    profile_ids: list[str],
    strategy_ids: list[str],
    min_compliance_score: float = 0.8,
    max_escalation_risk: float = 0.3,
) -> list[ComplianceExclusion]:
    exclusions: list[ComplianceExclusion] = []
    for profile_id in profile_ids:
        for strategy_id in strategy_ids:
            summary = store.get_compliance_summary(profile_id, strategy_id)
            compliance_score = summary["compliance_score"]
            escalation_risk = summary["escalation_risk"]
            if compliance_score == 0.0 and escalation_risk == 0.0:
                continue
            reasons = []
            if compliance_score < min_compliance_score:
                reasons.append(f"compliance_score {compliance_score:.2f} below {min_compliance_score:.2f}")
            if escalation_risk > max_escalation_risk:
                reasons.append(f"escalation_risk {escalation_risk:.2f} above {max_escalation_risk:.2f}")
            if reasons:
                exclusions.append(
                    ComplianceExclusion(
                        profile_id=profile_id,
                        strategy_id=strategy_id,
                        compliance_score=compliance_score,
                        escalation_risk=escalation_risk,
                        reason="; ".join(reasons),
                    )
                )
    return exclusions
