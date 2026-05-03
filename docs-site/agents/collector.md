# Collector Agent

**Module:** `src/collection_swarm/agents/collector.py`

The `CollectorAgent` is the **collection-side participant** in the simulated conversation. It receives a behavioral `Strategy` and `AccountData`, then generates dialogue turns that attempt to collect a debt according to the strategy's parameters.

---

## Class: `CollectorAgent`

### Constructor

```python
class CollectorAgent:
    def __init__(
        self,
        router: LLMRouter,
        model_id: str,
        prompts: CollectorPromptConfig,
    ) -> None
```

| Parameter | Type | Description |
|---|---|---|
| `router` | `LLMRouter` | Backend dispatcher — routes completions to the configured LLM backend |
| `model_id` | `str` | Identifier for the model to use (must exist in the router's model registry) |
| `prompts` | `CollectorPromptConfig` | Prompt templates for system message and history formatting |

### `CollectorPromptConfig`

Defined in `models.py`:

```python
class CollectorPromptConfig(BaseModel):
    system: str          # System prompt template — interpolated with {strategy} and {account}
    history_empty: str   # Text used when no conversation history exists yet
    history: str         # Template for history — interpolated with {transcript}
```

---

## Method: `generate_turn`

```python
async def generate_turn(
    self,
    strategy: Strategy,
    account: AccountData,
    history: list[Message],
) -> LLMResponse
```

Generates a single collector turn by constructing a two-message payload and sending it to the LLM via the router.

| Parameter | Type | Description |
|---|---|---|
| `strategy` | `Strategy` | Behavioral configuration (tone, tactics, escalation style, etc.) |
| `account` | `AccountData` | Financial data about the debt (amount, age, type, prior contacts) |
| `history` | `list[Message]` | Conversation transcript so far (may be empty for the opening turn) |

**Returns:** `LLMResponse` containing the generated text, token counts, and cost estimate.

---

## Message Construction

The agent builds exactly **two messages** for each LLM call:

```
┌─────────────────────────────────┐
│ Message 1: system               │
│ ┌─────────────────────────────┐ │
│ │ prompts.system.format(      │ │
│ │   strategy=strategy,        │ │
│ │   account=account           │ │
│ │ )                           │ │
│ └─────────────────────────────┘ │
├─────────────────────────────────┤
│ Message 2: user                 │
│ ┌─────────────────────────────┐ │
│ │ History prompt              │ │
│ │ (empty or formatted)        │ │
│ └─────────────────────────────┘ │
└─────────────────────────────────┘
```

### System Prompt Construction

```python
def _system_prompt(prompts, strategy, account) -> str:
    return prompts.system.format(strategy=strategy, account=account).strip()
```

The system prompt template receives the full `Strategy` and `AccountData` objects. Inside the template, any attribute can be referenced:

```yaml
# Example prompt template (config/prompts.yaml)
system: |
  You are a debt collection agent. Use the following strategy:
  Tone: {strategy.tone}
  Negotiation tactic: {strategy.negotiation_tactic}
  Escalation style: {strategy.escalation_style}

  Account details:
  Debt amount: R$ {account.debt_amount}
  Debt age: {account.debt_age_days} days
  Debt type: {account.debt_type}
  Prior contacts: {account.prior_contact_count}
```

### History Prompt Construction

```python
def _history_prompt(prompts, history) -> str:
    if not history:
        return prompts.history_empty.strip()
    transcript = "\n".join(
        f"{message.role.title()}: {message.content}"
        for message in history
    )
    return prompts.history.format(transcript=transcript).strip()
```

| Scenario | Template Used | Behavior |
|---|---|---|
| Empty history (opening turn) | `prompts.history_empty` | Returns the static prompt for initiating conversation |
| Populated history | `prompts.history` | Formats the transcript with `"Role: content"` lines and interpolates into the template |

The transcript is formatted as:

```
Collector: Hello, I'm calling about your account...
Debtor: What account? I don't recognize this debt.
Collector: Let me explain — your Will Bank credit card...
```

---

## Information Boundaries

!!! warning "The Collector has no access to debtor profile details"
    The `CollectorAgent` receives only `Strategy` and `AccountData`. It **never** sees:

    - The debtor's **archetype** (e.g., disputer, scam-suspect, hardship)
    - The debtor's **backstory** or **emotional state**
    - The debtor's **constraints** (max payment, required actions)
    - The debtor's **demographics** or **responsiveness** rating

    This asymmetry forces the collector LLM to read social cues from the conversation itself, mirroring real-world conditions.

### What the Collector sees

| Data Source | Available Fields |
|---|---|
| `Strategy` | `id`, `tone`, `opening_approach`, `negotiation_tactic`, `escalation_style`, `concession_willingness`, `compliance_adherence`, `follow_up_strategy`, `payment_channel`, `primary_anchor`, `discovery_questions`, `framing`, `discount_authority`, `liquidation_disclosure`, `cultural_register`, `rationale` |
| `AccountData` | `debt_amount`, `debt_age_days`, `debt_type`, `prior_contact_count` |

!!! note "AccountData is a strict subset of Profile"
    `AccountData` is derived from `Profile.account_data` — a property that extracts only the four financial fields. The engine passes this subset to the collector, not the full profile.

---

## Integration with SimulationEngine

The engine calls `generate_turn` in a loop:

```python
# Simplified from engine.py
collector_response = await self.collector.generate_turn(
    strategy=strategy,
    account=profile.account_data,  # Not the full profile!
    history=transcript,
)
transcript.append(Message(role="collector", content=collector_response.content))
```

The `profile.account_data` property ensures the collector only receives the four permitted financial fields.

---

## Related

- [Agent Architecture Overview](overview.md)
- [Debtor Agent](debtor.md) — the other participant
- [Judge](judge.md) — evaluates the final transcript
- [LLM Router](../backends/router.md) — how `router.complete` dispatches to backends
