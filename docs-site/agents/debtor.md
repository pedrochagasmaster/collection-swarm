# Debtor Agent

**Module:** `src/collection_swarm/agents/debtor.py`

The `DebtorAgent` is the **debtor-side participant** in the simulated conversation. It receives a behavioral `Profile` (including constraints that define hard behavioral boundaries) and generates dialogue turns that realistically portray a specific debtor archetype.

---

## Class: `DebtorAgent`

### Constructor

```python
class DebtorAgent:
    def __init__(
        self,
        router: LLMRouter,
        model_id: str,
        prompts: DebtorPromptConfig,
    ) -> None
```

| Parameter | Type | Description |
|---|---|---|
| `router` | `LLMRouter` | Backend dispatcher — routes completions to the configured LLM backend |
| `model_id` | `str` | Identifier for the model to use (must exist in the router's model registry) |
| `prompts` | `DebtorPromptConfig` | Prompt templates for system message, constraints, and history formatting |

### `DebtorPromptConfig`

Defined in `models.py`:

```python
class DebtorPromptConfig(BaseModel):
    system: str               # System prompt template — interpolated with {profile} and {constraints}
    constraints_empty: str    # Fallback text when a profile has no constraints (default: "- None")
    history_message: str      # Template for individual history messages — {role} and {content}
```

---

## Method: `generate_turn`

```python
async def generate_turn(
    self,
    profile: Profile,
    history: list[Message],
) -> LLMResponse
```

Generates a single debtor turn by constructing a system message plus alternating history messages, then sending them to the LLM.

| Parameter | Type | Description |
|---|---|---|
| `profile` | `Profile` | Full debtor profile including archetype, backstory, emotional state, and constraints |
| `history` | `list[Message]` | Conversation transcript so far (may be empty for the first debtor turn) |

**Returns:** `LLMResponse` containing the generated text, token counts, and cost estimate.

---

## Message Construction

Unlike the Collector (which uses two messages), the Debtor agent constructs a **variable-length message list**: one system message followed by alternating user/assistant messages representing the conversation history.

```
┌──────────────────────────────────────┐
│ Message 1: system                    │
│   Profile attributes + constraints   │
├──────────────────────────────────────┤
│ Message 2: user     (collector #1)   │
├──────────────────────────────────────┤
│ Message 3: assistant (debtor #1)     │
├──────────────────────────────────────┤
│ Message 4: user     (collector #2)   │
├──────────────────────────────────────┤
│ ...alternating until current turn    │
└──────────────────────────────────────┘
```

### System Prompt Construction

```python
def _system_message(prompts, profile) -> LLMMessage:
    constraints = "\n".join(
        f"- {constraint.text}" for constraint in profile.constraints
    ) or prompts.constraints_empty
    content = prompts.system.format(
        profile=profile,
        constraints=constraints,
    ).strip()
    return LLMMessage(role="system", content=content)
```

The system prompt receives the full `Profile` object and a pre-formatted constraint list. Inside the template, any profile attribute can be referenced:

```yaml
# Example prompt template (config/prompts.yaml)
system: |
  You are the debtor in a debt collection conversation.

  Your profile:
    Archetype: {profile.archetype}
    Financial situation: {profile.financial_situation}
    Emotional state: {profile.emotional_state}
    Primary objection: {profile.primary_objection}
    Backstory: {profile.backstory}

  Your constraints (you MUST follow these):
  {constraints}
```

!!! info "Constraint formatting"
    Constraints are formatted as a bulleted list. If the profile has no constraints, the `constraints_empty` fallback (default `"- None"`) is used instead, keeping the template structure consistent.

#### Constraint Examples

Each constraint has a human-readable `text` field and an optional machine-readable `rule`:

```python
Constraint(
    text="Never agree to pay more than R$ 150 per month",
    rule=ConstraintRule(type="max_payment", amount=150.0, frequency="monthly"),
)

Constraint(
    text="Demand written proof before discussing any payment",
    rule=ConstraintRule(type="required_action", action="demand_written_proof"),
)
```

The `text` is what the LLM sees in the system prompt; the `rule` is used by the Judge for deterministic verification.

### History Message Mapping

```python
def _history_messages(prompts, history) -> list[LLMMessage]:
    messages: list[LLMMessage] = []
    for turn in history:
        role = "assistant" if turn.role == "debtor" else "user"
        content = prompts.history_message.format(
            role=turn.role.title(),
            content=turn.content,
        )
        messages.append(LLMMessage(role=role, content=content))
    return messages
```

The domain roles are mapped to LLM chat roles so the model understands which utterances are "its own":

| Domain Role | LLM Role | Rationale |
|---|---|---|
| `debtor` | `assistant` | The debtor's own prior messages — presented as the model's own output |
| `collector` | `user` | The collector's messages — presented as incoming user messages |

!!! tip "Why this mapping matters"
    By mapping debtor messages to `assistant` and collector messages to `user`, the LLM naturally continues the conversation in the debtor's voice. Each turn's content is additionally wrapped via `prompts.history_message.format(role=..., content=...)`, allowing the prompt author to add role labels or formatting.

---

## Information Boundaries

The Debtor agent has the **richest information context** of all three agents:

| Data | Access |
|---|---|
| Full `Profile` (archetype, backstory, emotional state, demographics, etc.) | ✅ Yes |
| `Constraints` (behavioral rules) | ✅ Yes |
| `AccountData` (debt amount, age, type) | ✅ Yes (embedded in Profile) |
| Collector's `Strategy` | ❌ No |
| Judge's evaluation criteria | ❌ No |

!!! warning "The Debtor never sees the collection strategy"
    The debtor has no knowledge of the collector's tone settings, negotiation tactics, escalation style, or concession parameters. It must react naturally to whatever approach the collector takes.

---

## Profile Model

The `Profile` model provides the debtor's complete behavioral specification:

```python
class Profile(BaseModel):
    id: str
    archetype: str              # e.g., "disputer", "hardship", "scam_suspect"
    financial_situation: str
    debt_amount: float
    debt_age_days: int
    debt_type: str
    prior_contact_count: int
    emotional_state: str        # e.g., "angry", "confused", "cooperative"
    primary_objection: str
    responsiveness: str
    demographics: str
    backstory: str              # Rich narrative context for the LLM
    constraints: list[Constraint]
```

The `account_data` property extracts `AccountData` for the Collector agent, but the Debtor receives the full profile including backstory and emotional state.

---

## Related

- [Agent Architecture Overview](overview.md)
- [Collector Agent](collector.md) — the other participant
- [Judge](judge.md) — evaluates the final transcript and verifies constraints
- [LLM Router](../backends/router.md) — how `router.complete` dispatches to backends
