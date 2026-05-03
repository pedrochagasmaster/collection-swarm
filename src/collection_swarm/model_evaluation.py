"""Model-role evaluation utilities for Collection Swarm.

The functions in this module turn model probe output into a reusable report.
They are intentionally independent from the web UI so the same logic can power
CLI reports, CI checks, and future dashboard views.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from collection_swarm.agents.collector import CollectorAgent
from collection_swarm.agents.debtor import DebtorAgent
from collection_swarm.agents.judge import Judge
from collection_swarm.backends.router import LLMRouter
from collection_swarm.config import AppConfig
from collection_swarm.credentials import CredentialResolver
from collection_swarm.models import Judgment, Message, ModelConfig, model_dump_jsonable

EvaluationRole = Literal["collector", "debtor", "judge"]
ReportFormat = Literal["markdown", "json"]

DEFAULT_CURSOR_SDK_MODEL_IDS = (
    "default",
    "composer-2",
    "composer-1.5",
    "gpt-5.5",
    "gpt-5.3-codex",
    "claude-sonnet-4-6",
    "claude-opus-4-7",
    "gpt-5.4",
    "claude-opus-4-6",
    "claude-opus-4-5",
    "gpt-5.2",
    "gemini-3.1-pro",
    "gpt-5.4-mini",
    "gpt-5.4-nano",
    "claude-haiku-4-5",
    "gpt-5.3-codex-spark",
)

DEFAULT_CURSOR_PROBE_MODELS = (
    "composer-2",
    "gpt-5.5",
    "gpt-5.4",
    "gpt-5.3-codex",
    "claude-sonnet-4-6",
    "claude-opus-4-7",
    "gemini-3.1-pro",
    "gpt-5.4-mini",
    "claude-haiku-4-5",
)

MODEL_NAME_REPLACEMENTS = {
    "gpt-5.5-medium": "gpt-5.5",
    "gpt-5.4-high": "gpt-5.4",
    "gpt-5.4-high-fast": "gpt-5.4-mini",
    "gpt-5.3-codex-high": "gpt-5.3-codex",
    "gpt-5.3-codex-high-fast": "gpt-5.3-codex-spark",
    "claude-4.6-opus-high-thinking": "claude-opus-4-6",
    "claude-4.6-opus-high-thinking-fast": "claude-sonnet-4-6",
    "claude-opus-4-7-thinking-high": "claude-opus-4-7",
}

BASELINE_PROBES: tuple[dict[str, Any], ...] = (
    {
        "model_name": "composer-2",
        "role": "collector",
        "status": "ok",
        "elapsed_s": 4.72,
        "content": "Hello, this is [Agency name] calling about a medical balance of $1,250.00 on your account. I know these bills can be stressful, so I am reaching out to see if we can find a way forward that works for you. If you would like, we can talk about a payment plan or other options.",
    },
    {
        "model_name": "composer-2",
        "role": "debtor",
        "status": "ok",
        "elapsed_s": 4.84,
        "content": "I am really stretched right now, but I could manage about $100 a month toward this if we can set that up in writing.",
    },
    {
        "model_name": "composer-2",
        "role": "judge",
        "status": "ok",
        "elapsed_s": 4.85,
        "judgment": {
            "reasoning": "The collector opened by soliciting payment without validation, then recovered by agreeing to written validation.",
            "payment_outcome": "no_commitment",
            "payment_probability": 0.55,
            "debtor_satisfaction": 0.72,
            "compliance_score": 0.68,
            "conversation_efficiency": 4,
            "rapport_built": 0.65,
            "escalation_risk": 0.18,
            "end_reason": "agreed_to_send_validation_and_resume_after_review",
            "constraint_violations": ["initial_payment_request_before_written_proof_offer"],
        },
    },
    {
        "model_name": "gpt-5.5",
        "role": "collector",
        "status": "ok",
        "elapsed_s": 5.12,
        "content": "Hello, I am calling about a medical account with a current balance of $1,250. I understand unexpected medical bills can be stressful, and I would like to see whether we can work out a manageable payment plan that fits your situation.",
    },
    {
        "model_name": "gpt-5.5",
        "role": "debtor",
        "status": "ok",
        "elapsed_s": 5.19,
        "content": "I want to take care of it, but my work hours were cut and I am trying not to fall behind on rent for my family. Realistically, I could do about $100 a month right now.",
    },
    {
        "model_name": "gpt-5.5",
        "role": "judge",
        "status": "ok",
        "elapsed_s": 7.26,
        "judgment": {
            "reasoning": "Collector respected the debtor's written validation requirement and paused payment discussion.",
            "payment_outcome": "no_commitment",
            "payment_probability": 0.25,
            "debtor_satisfaction": 0.9,
            "compliance_score": 0.98,
            "conversation_efficiency": 4,
            "rapport_built": 0.65,
            "escalation_risk": 0.1,
            "end_reason": "written_proof_to_be_sent_before_payment_discussion",
            "constraint_violations": [],
        },
    },
    {
        "model_name": "gpt-5.4",
        "role": "collector",
        "status": "ok",
        "elapsed_s": 14.61,
        "content": "Hello, I am reaching out about your medical account balance of $1,250.00. I know these situations can be stressful, and I would like to work with you to find a manageable way to take care of it.",
    },
    {
        "model_name": "gpt-5.4",
        "role": "debtor",
        "status": "ok",
        "elapsed_s": 9.8,
        "content": "My work hours were cut, so money is really tight and I am trying to keep up with rent and groceries for my family. I could realistically manage $75 a month right now.",
    },
    {
        "model_name": "gpt-5.4",
        "role": "judge",
        "status": "ok",
        "elapsed_s": 15.73,
        "judgment": {
            "reasoning": "The collector ultimately honored the written proof request after an initial payment ask.",
            "payment_outcome": "no_commitment",
            "payment_probability": 0.17,
            "debtor_satisfaction": 0.74,
            "compliance_score": 0.81,
            "conversation_efficiency": 4,
            "rapport_built": 0.6,
            "escalation_risk": 0.14,
            "end_reason": "awaiting_written_proof_before_payment_discussion",
            "constraint_violations": ["Collector asked for payment before providing written proof/validation."],
        },
    },
    {
        "model_name": "gpt-5.3-codex",
        "role": "collector",
        "status": "ok",
        "elapsed_s": 8.88,
        "content": "Hi, this is Alex from the billing team, reaching out about your medical account balance of $1,250.00 that is currently 75 days past due. I am here to work with you on something manageable.",
    },
    {
        "model_name": "gpt-5.3-codex",
        "role": "debtor",
        "status": "ok",
        "elapsed_s": 6.46,
        "content": "I want to take care of this, but with my reduced hours and rent due, the most I can realistically manage is $100 per month right now.",
    },
    {
        "model_name": "gpt-5.3-codex",
        "role": "judge",
        "status": "ok",
        "elapsed_s": 9.13,
        "judgment": {
            "reasoning": "No payment was secured because the debtor required written validation first.",
            "payment_outcome": "no_commitment",
            "payment_probability": 0.22,
            "debtor_satisfaction": 0.74,
            "compliance_score": 0.82,
            "conversation_efficiency": 4,
            "rapport_built": 0.68,
            "escalation_risk": 0.18,
            "end_reason": "debtor_requested_written_proof_before_any_payment_discussion",
            "constraint_violations": ["collector_requested_payment_before_sending_written_proof"],
        },
    },
    {
        "model_name": "claude-sonnet-4-6",
        "role": "collector",
        "status": "ok",
        "elapsed_s": 6.78,
        "content": "Hello, my name is Alex, and I am calling on behalf of a medical billing account. I want to be upfront that this is an attempt to collect a debt. I understand that medical expenses can be unexpected and stressful.",
    },
    {
        "model_name": "claude-sonnet-4-6",
        "role": "debtor",
        "status": "ok",
        "elapsed_s": 6.4,
        "content": "Honestly, things have been really tight since my hours got cut. I think I could maybe manage around $75 to $100 a month, but I would need to make sure it does not put us in a bind.",
    },
    {
        "model_name": "claude-sonnet-4-6",
        "role": "judge",
        "status": "ok",
        "elapsed_s": 6.86,
        "judgment": {
            "reasoning": "Judge returned unparseable output; fallback heuristic used.",
            "payment_outcome": "no_commitment",
            "payment_probability": 0.0,
            "debtor_satisfaction": 0.5,
            "compliance_score": 0.5,
            "conversation_efficiency": 4,
            "rapport_built": 0.0,
            "escalation_risk": 0.5,
            "end_reason": "judge_parse_failed",
            "constraint_violations": [],
        },
    },
    {
        "model_name": "claude-opus-4-7",
        "role": "collector",
        "status": "ok",
        "elapsed_s": 5.44,
        "content": "Hi, this is calling regarding your medical account with a balance of $1,250.00 that is about 75 days past due. I understand medical bills can come at tough times.",
    },
    {
        "model_name": "claude-opus-4-7",
        "role": "debtor",
        "status": "ok",
        "elapsed_s": 4.51,
        "content": "I really want to take care of this, but my hours got cut recently and rent has to come first for my family. The most I could honestly commit to right now is around $100 a month.",
    },
    {
        "model_name": "claude-opus-4-7",
        "role": "judge",
        "status": "ok",
        "elapsed_s": 5.6,
        "judgment": {
            "reasoning": "Collector promptly honored the written validation request and paused collection.",
            "payment_outcome": "no_commitment",
            "payment_probability": 0.35,
            "debtor_satisfaction": 0.8,
            "compliance_score": 0.95,
            "conversation_efficiency": 4,
            "rapport_built": 0.7,
            "escalation_risk": 0.1,
            "end_reason": "validation_requested",
            "constraint_violations": [],
        },
    },
    {
        "model_name": "gemini-3.1-pro",
        "role": "collector",
        "status": "ok",
        "elapsed_s": 11.33,
        "content": "Hello, my name is Alex and I am calling to discuss an outstanding medical balance of $1,250.00 on your account. We completely understand that healthcare expenses can be unexpected.",
    },
    {
        "model_name": "gemini-3.1-pro",
        "role": "debtor",
        "status": "ok",
        "elapsed_s": 7.61,
        "content": "I really want to get this taken care of, but my hours at work were just cut and I am extremely stressed about making rent for my family. Would it be possible to set up a payment plan for maybe $100 a month?",
    },
    {
        "model_name": "gemini-3.1-pro",
        "role": "judge",
        "status": "ok",
        "elapsed_s": 11.16,
        "judgment": {
            "reasoning": "Judge returned unparseable output; fallback heuristic used.",
            "payment_outcome": "no_commitment",
            "payment_probability": 0.0,
            "debtor_satisfaction": 0.5,
            "compliance_score": 0.5,
            "conversation_efficiency": 4,
            "rapport_built": 0.0,
            "escalation_risk": 0.5,
            "end_reason": "judge_parse_failed",
            "constraint_violations": [],
        },
    },
    {
        "model_name": "gpt-5.4-mini",
        "role": "collector",
        "status": "ok",
        "elapsed_s": 6.06,
        "content": "Hello, this is regarding a medical account balance of $1,250.00. I understand this can be an unexpected expense, and I would like to work with you on a payment plan that fits your situation.",
    },
    {
        "model_name": "gpt-5.4-mini",
        "role": "debtor",
        "status": "ok",
        "elapsed_s": 6.52,
        "content": "I can probably do $100 a month right now, but even that is tight with my reduced hours and rent.",
    },
    {
        "model_name": "gpt-5.4-mini",
        "role": "judge",
        "status": "ok",
        "elapsed_s": 12.01,
        "judgment": {
            "reasoning": "Judge returned unparseable output; fallback heuristic used.",
            "payment_outcome": "no_commitment",
            "payment_probability": 0.0,
            "debtor_satisfaction": 0.5,
            "compliance_score": 0.5,
            "conversation_efficiency": 4,
            "rapport_built": 0.0,
            "escalation_risk": 0.5,
            "end_reason": "judge_parse_failed",
            "constraint_violations": [],
        },
    },
    {
        "model_name": "claude-haiku-4-5",
        "role": "collector",
        "status": "ok",
        "elapsed_s": 7.84,
        "content": "Hello, this is [Collector name] calling from [Collection Agency]. I am reaching out regarding a medical account that has been with us for a short time.",
    },
    {
        "model_name": "claude-haiku-4-5",
        "role": "debtor",
        "status": "ok",
        "elapsed_s": 6.21,
        "content": "Look, I want to take care of this, but I have just had my hours cut at work and I am really stretched thin right now. Honestly, I could probably manage around $75 to $100 a month.",
    },
    {
        "model_name": "claude-haiku-4-5",
        "role": "judge",
        "status": "ok",
        "elapsed_s": 11.44,
        "judgment": {
            "reasoning": "Judge returned unparseable output; fallback heuristic used.",
            "payment_outcome": "no_commitment",
            "payment_probability": 0.0,
            "debtor_satisfaction": 0.5,
            "compliance_score": 0.5,
            "conversation_efficiency": 4,
            "rapport_built": 0.0,
            "escalation_risk": 0.5,
            "end_reason": "judge_parse_failed",
            "constraint_violations": [],
        },
    },
)


@dataclass(frozen=True)
class ProbeScenario:
    """Inputs used to exercise a model for each role.

    Args:
        profile_id: Profile used for Collector and Debtor probes.
        strategy_id: Strategy used for Collector probes.
        judge_profile_id: Profile used by Judge probes. The default stresses
            written-validation compliance and parser reliability.
        debtor_prompt: Collector turn that starts the Debtor probe.
        judge_transcript: Completed transcript that starts the Judge probe.
    """

    profile_id: str = "cooperative_hardship"
    strategy_id: str = "empathetic_payment_plan"
    judge_profile_id: str = "written_proof_disputer"
    debtor_prompt: str = (
        "This is an attempt to collect a debt. I see a medical balance of $1,250. "
        "What amount could you realistically afford each month?"
    )
    judge_transcript: tuple[Message, ...] = (
        Message(
            role="collector",
            content="This is an attempt to collect a debt for a $780 credit card balance. Can you pay today?",
        ),
        Message(
            role="debtor",
            content="I am not discussing payment until you send written proof and validation of the balance.",
        ),
        Message(
            role="collector",
            content="I can send validation in writing and pause payment discussion until you review it.",
        ),
        Message(role="debtor", content="Thank you. Send the written proof first, then I will review it."),
    )


@dataclass(frozen=True)
class RoleProbe:
    """Raw output from one model-role probe."""

    model_name: str
    role: EvaluationRole
    status: Literal["ok", "error"]
    elapsed_s: float | None = None
    content: str = ""
    judgment: Judgment | None = None
    error: str | None = None


@dataclass(frozen=True)
class RoleAssessment:
    """Opinionated fit score derived from a probe."""

    model_name: str
    role: EvaluationRole
    score: int
    fit: str
    evidence: str
    caution: str


@dataclass(frozen=True)
class ConfigModelStatus:
    """Whether a configured Cursor SDK model name is currently valid."""

    configured_id: str
    model_name: str
    live_status: Literal["works", "fails", "unknown"]
    action: str


@dataclass(frozen=True)
class ModelRoleReport:
    """Complete model-role evaluation report."""

    title: str
    generated_at: datetime
    scenario: ProbeScenario
    probes: tuple[RoleProbe, ...]
    assessments: tuple[RoleAssessment, ...]
    config_statuses: tuple[ConfigModelStatus, ...]
    recommendations: dict[EvaluationRole, str]
    notes: tuple[str, ...] = field(default_factory=tuple)


def baseline_probes() -> tuple[RoleProbe, ...]:
    """Return the checked-in baseline probe data from Apr 30, 2026."""

    return tuple(_probe_from_dict(item) for item in BASELINE_PROBES)


def configured_cursor_model_statuses(
    config: AppConfig,
    available_model_ids: tuple[str, ...] | list[str] = DEFAULT_CURSOR_SDK_MODEL_IDS,
) -> tuple[ConfigModelStatus, ...]:
    """Compare configured Cursor model names against known SDK model IDs."""

    available = set(available_model_ids)
    statuses: list[ConfigModelStatus] = []
    for model in config.models.values():
        if model.backend != "cursor_sdk":
            continue
        model_name = model.model_name or model.id
        if model_name in available:
            status: Literal["works", "fails", "unknown"] = "works"
            action = "Keep"
        elif replacement := MODEL_NAME_REPLACEMENTS.get(model_name):
            status = "fails"
            action = f"Replace model_name with {replacement}"
        else:
            status = "unknown"
            action = "Verify with Cursor.models.list() before live use"
        statuses.append(ConfigModelStatus(model.id, model_name, status, action))
    return tuple(statuses)


def build_model_role_report(
    config: AppConfig,
    probes: tuple[RoleProbe, ...] | list[RoleProbe] | None = None,
    *,
    scenario: ProbeScenario | None = None,
    title: str = "Cursor Model Role Evaluation",
    generated_at: datetime | None = None,
    available_cursor_model_ids: tuple[str, ...] | list[str] = DEFAULT_CURSOR_SDK_MODEL_IDS,
) -> ModelRoleReport:
    """Build a report from probe outputs and configuration health.

    The scoring is intentionally transparent and deterministic. Live model
    calls happen only in `run_live_role_probes`; this function is pure report
    assembly, which makes it suitable for tests and repeatable docs.
    """

    scenario = scenario or ProbeScenario()
    probe_tuple = tuple(probes or baseline_probes())
    assessments = tuple(assess_probe(probe) for probe in probe_tuple)
    recommendations = recommend_models(assessments)
    notes = (
        "Scores are deterministic interpretations of probe outputs, not a statistically complete benchmark.",
        "Judge reliability carries extra weight because parse fallback corrupts saved metrics and playbook rankings.",
    )
    return ModelRoleReport(
        title=title,
        generated_at=generated_at or datetime.now(timezone.utc),
        scenario=scenario,
        probes=probe_tuple,
        assessments=assessments,
        config_statuses=configured_cursor_model_statuses(config, available_cursor_model_ids),
        recommendations=recommendations,
        notes=notes,
    )


async def run_live_role_probes(
    config: AppConfig,
    *,
    cursor_model_names: tuple[str, ...] | list[str] = DEFAULT_CURSOR_PROBE_MODELS,
    roles: tuple[EvaluationRole, ...] | list[EvaluationRole] = ("collector", "debtor", "judge"),
    scenario: ProbeScenario | None = None,
    concurrency: int = 1,
    credentials: CredentialResolver | None = None,
) -> tuple[RoleProbe, ...]:
    """Run live Cursor SDK probes for the requested models and roles.

    Args:
        config: Loaded app configuration. It is copied before temporary probe
            models are registered.
        cursor_model_names: Provider-facing Cursor SDK model IDs such as
            `gpt-5.5` or `claude-opus-4-7`.
        roles: Any subset of `collector`, `debtor`, and `judge`.
        scenario: Profile, Strategy, and prompt inputs to use.
        concurrency: Maximum concurrent role probes. Keep low for expensive
            SDK runs; the default favors reproducibility over speed.
    """

    scenario = scenario or ProbeScenario()
    models = dict(config.models)
    for model_name in cursor_model_names:
        probe_id = _probe_model_id(model_name)
        models[probe_id] = ModelConfig(
            id=probe_id,
            backend="cursor_sdk",
            provider=_provider_for_cursor_model(model_name),
            model_name=model_name,
        )
    probe_config = config.model_copy(update={"models": models})
    router = LLMRouter(
        probe_config.models,
        cursor_sdk_prompts=probe_config.prompts.cursor_sdk,
        credentials=credentials,
    )
    semaphore = asyncio.Semaphore(concurrency)

    async def run_one(model_name: str, role: EvaluationRole) -> RoleProbe:
        async with semaphore:
            return await _run_role_probe(probe_config, router, model_name, role, scenario)

    tasks = [run_one(model_name, role) for model_name in cursor_model_names for role in roles]
    return tuple(await asyncio.gather(*tasks))


def assess_probe(probe: RoleProbe) -> RoleAssessment:
    """Score one probe for its assigned role on a 1-10 fit scale."""

    if probe.status == "error":
        return RoleAssessment(
            model_name=probe.model_name,
            role=probe.role,
            score=1,
            fit="Unavailable",
            evidence="The probe failed before producing role output.",
            caution=probe.error or "Unknown probe error.",
        )
    if probe.role == "collector":
        return _assess_collector_probe(probe)
    if probe.role == "debtor":
        return _assess_debtor_probe(probe)
    return _assess_judge_probe(probe)


def recommend_models(assessments: tuple[RoleAssessment, ...]) -> dict[EvaluationRole, str]:
    """Pick the top-scoring model for each role."""

    preferred_tie_breakers: dict[EvaluationRole, tuple[str, ...]] = {
        "collector": ("gpt-5.5", "claude-sonnet-4-6", "gpt-5.3-codex", "gpt-5.4", "gemini-3.1-pro"),
        "debtor": ("gpt-5.5", "claude-sonnet-4-6", "claude-opus-4-7", "gpt-5.4", "gpt-5.3-codex"),
        "judge": ("gpt-5.5", "claude-opus-4-7", "gpt-5.4", "gpt-5.3-codex", "composer-2"),
    }
    recommendations: dict[EvaluationRole, str] = {}
    for role in ("collector", "debtor", "judge"):
        role_assessments = [item for item in assessments if item.role == role]
        if not role_assessments:
            continue
        preference = preferred_tie_breakers[role]
        best = sorted(
            role_assessments,
            key=lambda item: (
                -item.score,
                preference.index(item.model_name) if item.model_name in preference else len(preference),
                item.model_name,
            ),
        )[0]
        recommendations[role] = best.model_name
    return recommendations


def render_markdown_report(report: ModelRoleReport) -> str:
    """Render a report as Markdown suitable for docs or artifacts."""

    lines = [
        f"# {report.title}",
        "",
        f"Generated: {report.generated_at.isoformat()}",
        "",
        "## Executive Recommendation",
        "",
    ]
    for role in ("collector", "debtor", "judge"):
        model = report.recommendations.get(role, "n/a")
        lines.append(f"- **{role.title()}**: `{model}`")
    lines.extend(
        [
            "",
            "Use `gpt-5.5` as the safest default when the app uses one conversation model for both Participants. "
            "Treat `claude-opus-4-7` as the premium Judge challenger after broader calibration.",
            "",
            "## Configuration Health",
            "",
            "| Configured ID | model_name | Status | Action |",
            "| --- | --- | --- | --- |",
        ]
    )
    for status in report.config_statuses:
        lines.append(
            f"| `{status.configured_id}` | `{status.model_name}` | {status.live_status} | {status.action} |"
        )
    lines.extend(["", "## Role Assessments", ""])
    for role in ("collector", "debtor", "judge"):
        lines.extend(
            [
                f"### {role.title()}",
                "",
                "| Model | Score | Fit | Evidence | Caution |",
                "| --- | ---: | --- | --- | --- |",
            ]
        )
        for assessment in sorted(
            [item for item in report.assessments if item.role == role],
            key=lambda item: (-item.score, item.model_name),
        ):
            lines.append(
                "| "
                + " | ".join(
                    [
                        f"`{assessment.model_name}`",
                        str(assessment.score),
                        _md_cell(assessment.fit),
                        _md_cell(assessment.evidence),
                        _md_cell(assessment.caution),
                    ]
                )
                + " |"
            )
        lines.append("")
    lines.extend(
        [
            "## Probe Scenario",
            "",
            f"- Profile: `{report.scenario.profile_id}`",
            f"- Strategy: `{report.scenario.strategy_id}`",
            f"- Judge profile: `{report.scenario.judge_profile_id}`",
            "",
            "## Operational Notes",
            "",
        ]
    )
    for note in report.notes:
        lines.append(f"- {note}")
    lines.extend(
        [
            "- Run live reports with `collection-swarm model-report --live-probes` when validating new SDK model IDs.",
            "- Keep report outputs in `docs/` for checked-in snapshots or `output/` for disposable benchmark runs.",
            "",
        ]
    )
    return "\n".join(lines)


def report_to_dict(report: ModelRoleReport) -> dict[str, Any]:
    """Convert a report to plain JSON-compatible data."""

    return {
        "title": report.title,
        "generated_at": report.generated_at.isoformat(),
        "scenario": {
            "profile_id": report.scenario.profile_id,
            "strategy_id": report.scenario.strategy_id,
            "judge_profile_id": report.scenario.judge_profile_id,
            "debtor_prompt": report.scenario.debtor_prompt,
            "judge_transcript": [model_dump_jsonable(message) for message in report.scenario.judge_transcript],
        },
        "recommendations": report.recommendations,
        "config_statuses": [status.__dict__ for status in report.config_statuses],
        "assessments": [assessment.__dict__ for assessment in report.assessments],
        "probes": [_probe_to_dict(probe) for probe in report.probes],
        "notes": list(report.notes),
    }


def write_report(report: ModelRoleReport, path: Path, *, report_format: ReportFormat = "markdown") -> None:
    """Write a Markdown or JSON report to disk."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if report_format == "json":
        path.write_text(json.dumps(report_to_dict(report), indent=2), encoding="utf-8")
    else:
        path.write_text(render_markdown_report(report), encoding="utf-8")


def _probe_from_dict(data: dict[str, Any]) -> RoleProbe:
    judgment = data.get("judgment")
    return RoleProbe(
        model_name=data["model_name"],
        role=data["role"],
        status=data["status"],
        elapsed_s=data.get("elapsed_s"),
        content=data.get("content", ""),
        judgment=Judgment.model_validate(judgment) if judgment else None,
        error=data.get("error"),
    )


async def _run_role_probe(
    config: AppConfig,
    router: LLMRouter,
    model_name: str,
    role: EvaluationRole,
    scenario: ProbeScenario,
) -> RoleProbe:
    model_id = _probe_model_id(model_name)
    started = time.perf_counter()
    try:
        if role == "collector":
            response = await CollectorAgent(router, model_id, config.prompts.collector).generate_turn(
                config.strategy(scenario.strategy_id),
                config.profile(scenario.profile_id).account_data,
                [],
            )
            return RoleProbe(model_name, role, "ok", time.perf_counter() - started, response.content)
        if role == "debtor":
            response = await DebtorAgent(router, model_id, config.prompts.debtor).generate_turn(
                config.profile(scenario.profile_id),
                [Message(role="collector", content=scenario.debtor_prompt)],
            )
            return RoleProbe(model_name, role, "ok", time.perf_counter() - started, response.content)
        judgment = await Judge(router, model_id, config.prompts.judge).evaluate(
            list(scenario.judge_transcript),
            config.profile(scenario.judge_profile_id),
        )
        return RoleProbe(model_name, role, "ok", time.perf_counter() - started, judgment=judgment)
    except Exception as exc:
        return RoleProbe(model_name, role, "error", time.perf_counter() - started, error=str(exc))


def _assess_collector_probe(probe: RoleProbe) -> RoleAssessment:
    text = probe.content.lower()
    score = 5
    evidence: list[str] = []
    cautions: list[str] = []
    if any(marker in text for marker in ("attempt to collect", "outstanding", "balance", "account")):
        score += 1
        evidence.append("identified account purpose")
    else:
        cautions.append("did not clearly identify account purpose")
    if "$" in text or "balance" in text:
        score += 1
        evidence.append("included account detail")
    else:
        cautions.append("omitted concrete account detail")
    if any(marker in text for marker in ("stress", "understand", "work with", "manageable")):
        score += 1
        evidence.append("used empathetic payment-plan framing")
    if "[agency" in text or "[collector" in text:
        score -= 2
        cautions.append("leaked placeholders")
    if "this is calling" in text:
        score -= 2
        cautions.append("awkward caller identification")
    score = _clamp_score(score)
    return RoleAssessment(
        probe.model_name,
        probe.role,
        score,
        _fit_label(score),
        "; ".join(evidence) or "produced a usable Collector turn",
        "; ".join(cautions) or "no major one-shot caution observed",
    )


def _assess_debtor_probe(probe: RoleProbe) -> RoleAssessment:
    text = probe.content.lower()
    score = 6
    evidence: list[str] = []
    cautions: list[str] = []
    if any(marker in text for marker in ("rent", "hours", "family", "tight", "stretched")):
        score += 1
        evidence.append("stayed in hardship persona")
    if _has_payment_under_cap(text, max_amount=150):
        score += 1
        evidence.append("honored payment ceiling")
    elif "$" in text:
        cautions.append("payment amount needs constraint review")
    if any(marker in text for marker in ("maybe", "probably", "realistically", "honestly")):
        score += 1
        evidence.append("sounded like a realistic consumer")
    if "**" in probe.content:
        score -= 1
        cautions.append("markdown formatting leaked into dialogue")
    return RoleAssessment(
        probe.model_name,
        probe.role,
        _clamp_score(score),
        _fit_label(score),
        "; ".join(evidence) or "produced a plausible Debtor turn",
        "; ".join(cautions) or "needs broader profile coverage",
    )


def _assess_judge_probe(probe: RoleProbe) -> RoleAssessment:
    judgment = probe.judgment
    if judgment is None:
        return RoleAssessment(
            probe.model_name,
            probe.role,
            1,
            "Unavailable",
            "No Judgment was produced.",
            probe.error or "missing Judgment",
        )
    if judgment.end_reason == "judge_parse_failed":
        return RoleAssessment(
            probe.model_name,
            probe.role,
            3,
            "Unsafe without parser hardening",
            "underlying reasoning may be useful, but strict schema validation failed",
            "parser fallback corrupts saved metrics",
        )
    score = 6
    evidence: list[str] = ["returned parseable Judgment"]
    cautions: list[str] = []
    if not judgment.constraint_violations:
        score += 2
        evidence.append("did not invent profile Constraint Violations")
    else:
        score -= 1
        cautions.append("reported possible false Constraint Violations")
    if judgment.compliance_score >= 0.9 and judgment.escalation_risk <= 0.2:
        score += 1
        evidence.append("scores aligned with low-risk validation handling")
    if 0 <= judgment.payment_probability <= 0.5:
        score += 1
        evidence.append("did not overstate payment likelihood")
    score = _clamp_score(score)
    return RoleAssessment(
        probe.model_name,
        probe.role,
        score,
        _fit_label(score),
        "; ".join(evidence),
        "; ".join(cautions) or "calibrate across more transcripts before policy use",
    )


def _probe_to_dict(probe: RoleProbe) -> dict[str, Any]:
    return {
        "model_name": probe.model_name,
        "role": probe.role,
        "status": probe.status,
        "elapsed_s": probe.elapsed_s,
        "content": probe.content,
        "judgment": model_dump_jsonable(probe.judgment) if probe.judgment else None,
        "error": probe.error,
    }


def _provider_for_cursor_model(model_name: str) -> str:
    if model_name.startswith("claude"):
        return "anthropic"
    if model_name.startswith("gpt"):
        return "openai"
    if model_name.startswith("gemini"):
        return "google"
    return "cursor"


def _probe_model_id(model_name: str) -> str:
    return f"probe-{re.sub(r'[^a-zA-Z0-9_.-]+', '-', model_name)}"


def _has_payment_under_cap(text: str, *, max_amount: float) -> bool:
    amounts = [float(match.replace(",", "")) for match in re.findall(r"\$([0-9][0-9,]*(?:\.\d{1,2})?)", text)]
    return bool(amounts) and max(amounts) <= max_amount


def _fit_label(score: int) -> str:
    if score >= 9:
        return "Primary recommendation"
    if score >= 7:
        return "Strong candidate"
    if score >= 5:
        return "Usable with caution"
    return "Avoid for now"


def _clamp_score(score: int) -> int:
    return max(1, min(10, score))


def _md_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
