"""Markdown playbook generation."""

from __future__ import annotations

from datetime import datetime, timezone

from collection_swarm.analysis.compliance import ComplianceExclusion
from collection_swarm.analysis.objections import extract_objections
from collection_swarm.analysis.statistics import StrategyRanking
from collection_swarm.store import SimulationStore


def generate_playbook(
    rankings: list[StrategyRanking],
    exclusions: list[ComplianceExclusion],
    store: SimulationStore,
) -> str:
    total = len(store.list_runs(status="completed"))
    lines = [
        "# Collection Playbook",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()} | Simulations analyzed: {total}",
        "",
        "## Compliance Notice",
    ]
    if exclusions:
        for exclusion in exclusions:
            lines.append(
                f"- Exclude `{exclusion.strategy_id}` for `{exclusion.profile_id}`: "
                f"compliance={exclusion.compliance_score:.2f}, escalation_risk={exclusion.escalation_risk:.2f}"
            )
    else:
        lines.append("- No compliance exclusions detected.")

    for ranking in rankings:
        lines.extend(["", f"## Profile: {ranking.profile_id}"])
        if not ranking.strategies:
            lines.append("No completed simulations.")
            continue
        best = ranking.strategies[0]
        lines.extend(
            [
                f"### Recommended Strategy: `{best.strategy_id}`",
                f"**Payment Probability:** {best.mean_payment_probability:.0%}",
                "",
                "### Strategy Ranking",
                "| Strategy | Simulations | Payment Probability | Compliance | Escalation Risk |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for stat in ranking.strategies:
            lines.append(
                f"| `{stat.strategy_id}` | {stat.simulation_count} | "
                f"{stat.mean_payment_probability:.0%} | {stat.mean_compliance_score:.0%} | "
                f"{stat.mean_escalation_risk:.0%} |"
            )

        objection_report = extract_objections(store.get_all_transcripts(ranking.profile_id, best.strategy_id))
        if objection_report.objections:
            lines.extend(["", "### Objection Playbook"])
            for category, count in sorted(objection_report.objections.items()):
                lines.append(f"- **{category}:** observed in {count} transcript(s).")

        transcript = store.get_best_transcript(ranking.profile_id, best.strategy_id)
        if transcript:
            lines.extend(["", "### Example Transcript"])
            for turn in transcript:
                lines.append(f"> **{turn.role.title()}:** {turn.content}")

    lines.append("")
    return "\n".join(lines)
