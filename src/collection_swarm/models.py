"""Domain models for Collection Swarm."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PaymentOutcome(StrEnum):
    FULL_PAYMENT = "full_payment"
    PARTIAL_PAYMENT = "partial_payment"
    PAYMENT_PLAN = "payment_plan"
    PROMISE_TO_PAY = "promise_to_pay"
    NO_COMMITMENT = "no_commitment"
    REFUSAL = "refusal"
    HANG_UP = "hang_up"


class EndedBy(StrEnum):
    COLLECTOR = "collector"
    DEBTOR = "debtor"
    STALEMATE = "stalemate"
    TURN_LIMIT = "turn_limit"


class ConstraintRule(BaseModel):
    """Machine-readable profile invariant used by the Judge.

    Supported `action` values for ``type == "required_action"``:

    - ``demand_written_proof`` — debtor must mention written proof / fatura
      detalhada / contrato before discussing payment.
    - ``cite_liquidator_and_official_channel`` — collector must reference the
      liquidator (EFB Regimes Especiais de Empresas) or an official channel
      (willbank.com.br, bcb.gov.br, Banco Central) before requesting payment.
    - ``provide_official_boleto_path`` / ``verify_official_channel`` —
      collector must mention an official boleto, liquidator, or validation
      channel before the debtor is expected to engage.
    """

    type: Literal["max_payment", "required_action"]
    amount: float | None = None
    frequency: str | None = None
    action: str | None = None

    @model_validator(mode="after")
    def validate_required_fields(self) -> "ConstraintRule":
        if self.type == "max_payment" and self.amount is None:
            raise ValueError("max_payment constraint rules require amount")
        if self.type == "required_action" and not self.action:
            raise ValueError("required_action constraint rules require action")
        return self


class Constraint(BaseModel):
    text: str
    rule: ConstraintRule | None = None


class AccountData(BaseModel):
    debt_amount: float = Field(gt=0)
    debt_age_days: int = Field(ge=0)
    debt_type: str
    prior_contact_count: int = Field(ge=0)


class Profile(BaseModel):
    id: str
    archetype: str
    financial_situation: str
    debt_amount: float = Field(gt=0)
    debt_age_days: int = Field(ge=0)
    debt_type: str
    prior_contact_count: int = Field(ge=0)
    emotional_state: str
    primary_objection: str
    responsiveness: str
    demographics: str
    backstory: str
    constraints: list[Constraint] = Field(default_factory=list)

    @property
    def account_data(self) -> AccountData:
        return AccountData(
            debt_amount=self.debt_amount,
            debt_age_days=self.debt_age_days,
            debt_type=self.debt_type,
            prior_contact_count=self.prior_contact_count,
        )


class Strategy(BaseModel):
    """Behavioral configuration for the Collector participant.

    The first eight fields are required and define the core behavioral knobs
    used by every strategy. The remaining optional fields are descriptive
    refinements introduced for the Will Bank / Brazilian context (see
    docs/willbank-research-dossier.md). They are surfaced to the LLM and to
    analysis when present, but legacy strategies that omit them keep working
    unchanged.
    """

    model_config = ConfigDict(extra="ignore")

    id: str
    tone: str
    opening_approach: str
    negotiation_tactic: str
    escalation_style: str
    concession_willingness: str
    compliance_adherence: str
    follow_up_strategy: str
    payment_channel: str | None = None
    primary_anchor: str | None = None
    discovery_questions: str | None = None
    framing: str | None = None
    discount_authority: str | None = None
    liquidation_disclosure: str | None = None
    cultural_register: str | None = None
    rationale: str | None = None


class Message(BaseModel):
    role: Literal["collector", "debtor", "system", "judge"]
    content: str


class LLMMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class CollectorPromptConfig(BaseModel):
    system: str
    history_empty: str
    history: str


class DebtorPromptConfig(BaseModel):
    system: str
    constraints_empty: str = "- None"
    history_message: str


class JudgePromptConfig(BaseModel):
    system: str
    transcript: str


class CursorSdkPromptConfig(BaseModel):
    preamble: str


class PromptConfig(BaseModel):
    collector: CollectorPromptConfig
    debtor: DebtorPromptConfig
    judge: JudgePromptConfig
    cursor_sdk: CursorSdkPromptConfig


class ModelConfig(BaseModel):
    id: str
    backend: str
    provider: str = "local"
    input_cost_per_m: float = 0.0
    output_cost_per_m: float = 0.0
    model_name: str | None = None

    @property
    def litellm_model(self) -> str:
        return self.model_name or self.id


class ConversationSettings(BaseModel):
    max_turns: int = Field(default=20, ge=2)
    end_signal: str = "[END_CONVERSATION]"
    stalemate_window: int = Field(default=3, ge=1)
    stalemate_similarity_threshold: float = Field(default=0.6, ge=0.0, le=1.0)


class ArenaSettings(BaseModel):
    default_format: Literal["swiss", "round_robin"] = "swiss"
    default_rounds: int = Field(default=4, ge=1)
    k_factor_initial: float = 32.0
    k_factor_stable: float = 16.0
    k_factor_threshold: int = 30
    scoring: Literal["payment_x_compliance", "payment_only"] = "payment_x_compliance"


class SimulationSettings(BaseModel):
    conversation: ConversationSettings = Field(default_factory=ConversationSettings)
    default_repetitions: int = Field(default=1, ge=1)
    min_compliance_score: float = Field(default=0.8, ge=0.0, le=1.0)
    max_escalation_risk: float = Field(default=0.3, ge=0.0, le=1.0)
    objection_taxonomy: list[str] = Field(default_factory=list)
    arena: ArenaSettings = Field(default_factory=ArenaSettings)


class Judgment(BaseModel):
    reasoning: str
    payment_outcome: PaymentOutcome = PaymentOutcome.NO_COMMITMENT
    payment_probability: float = Field(ge=0.0, le=1.0)
    debtor_satisfaction: float = Field(ge=0.0, le=1.0)
    compliance_score: float = Field(ge=0.0, le=1.0)
    conversation_efficiency: int = Field(ge=0)
    rapport_built: float = Field(ge=0.0, le=1.0)
    escalation_risk: float = Field(ge=0.0, le=1.0)
    end_reason: str = "no_resolution"
    constraint_violations: list[str] = Field(default_factory=list)


class SimulationResult(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=lambda: f"sim_{uuid4().hex[:12]}")
    status: Literal["completed", "failed", "running"] = "completed"
    error_message: str | None = None
    profile_id: str
    strategy_id: str
    conversation_model: str
    judge_model: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: datetime | None = None
    turn_count: int = 0
    ended_by: EndedBy | None = None
    transcript: list[Message] = Field(default_factory=list)
    judgment: Judgment | None = None
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    estimated_cost_usd: float = 0.0

    @field_validator("started_at", "ended_at", mode="before")
    @classmethod
    def parse_datetime(cls, value: Any) -> Any:
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        return value

    @field_validator("started_at", "ended_at")
    @classmethod
    def ensure_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class StrategyStats(BaseModel):
    profile_id: str
    strategy_id: str
    simulation_count: int
    mean_payment_probability: float
    mean_compliance_score: float
    mean_escalation_risk: float


class MatrixCell(BaseModel, frozen=True):
    profile_id: str
    strategy_id: str
    conversation_model: str
    judge_model: str


DRAW_THRESHOLD = 0.05


class EloRating(BaseModel):
    entity_type: Literal["strategy", "profile"]
    entity_id: str
    rating: float = 1500.0
    games_played: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0


class EloUpdate(BaseModel):
    entity_type: Literal["strategy", "profile"]
    entity_id: str
    opponent_id: str
    simulation_id: str
    rating_before: float
    rating_after: float
    effective_score: float
    expected_score: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TournamentConfig(BaseModel):
    format: Literal["round_robin", "swiss"] = "swiss"
    rounds: int = Field(default=4, ge=1)
    reps_per_pairing: int = Field(default=1, ge=1)
    k_factor_initial: float = 32.0
    k_factor_stable: float = 16.0
    k_factor_threshold: int = 30
    scoring: Literal["payment_x_compliance", "payment_only"] = "payment_x_compliance"


class TournamentResult(BaseModel):
    id: str = Field(default_factory=lambda: f"tourn_{uuid4().hex[:10]}")
    config: TournamentConfig
    rounds_completed: int = 0
    total_games: int = 0
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    total_cost_usd: float = 0.0


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def model_dump_jsonable(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json")
