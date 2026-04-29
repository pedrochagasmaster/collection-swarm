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
        tied = "yes" if any(comparison.tied for comparison in ranking.comparisons) else "no"
        needs_more = ", ".join(ranking.needs_more_data) if ranking.needs_more_data else "none"
        lines.extend(
            [
                f"### Recommended Strategy: `{best.strategy_id}`",
                f"**Payment Probability:** {best.mean_payment_probability:.0%} "
                f"(95% CI: {best.payment_probability_ci_low:.0%}-{best.payment_probability_ci_high:.0%})",
                f"**Statistically tied top strategies:** {tied}",
                f"**Needs more data:** {needs_more}",
                "",
                "### Strategy Ranking",
                "| Strategy | Simulations | Payment Probability | 95% CI | Compliance | Escalation Risk |",
                "|---|---:|---:|---:|---:|---:|",
            ]
        )
        for stat in ranking.strategies:
            lines.append(
                f"| `{stat.strategy_id}` | {stat.simulation_count} | "
                f"{stat.mean_payment_probability:.0%} | "
                f"{stat.payment_probability_ci_low:.0%}-{stat.payment_probability_ci_high:.0%} | "
                f"{stat.mean_compliance_score:.0%} | "
                f"{stat.mean_escalation_risk:.0%} |"
            )

        objection_report = extract_objections(store.get_all_transcripts(ranking.profile_id, best.strategy_id))
        if objection_report.objections:
            lines.extend(["", "### Objection Playbook"])
            for category, count in sorted(objection_report.objections.items()):
                response = next(iter(objection_report.responses.get(category, [])), "No collector response captured.")
                lines.append(
                    f"- **{category}:** observed {count} time(s). "
                    f"Example response: \"{response}\""
                )

        transcript = store.get_best_transcript(ranking.profile_id, best.strategy_id)
        if transcript:
            lines.extend(["", "### Example Transcript"])
            for turn in transcript:
                lines.append(f"> **{turn.role.title()}:** {turn.content}")

    lines.append("")
    return "\n".join(lines)
