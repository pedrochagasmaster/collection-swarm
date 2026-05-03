# Manual Human-in-the-Loop Sessions

Manual sessions let a human take the **collector** or **debtor** seat in a live conversation while an AI plays the opposite role. When the conversation ends, the Judge model evaluates the transcript and the result is persisted exactly like an automated simulation.

## Creating a Session

### Choose your role

| `human_role` | Human plays | AI plays | First turn |
|--------------|-------------|----------|------------|
| `"collector"` | Collector | Debtor | Human sends the opening message |
| `"debtor"` | Debtor | Collector | AI sends the opening message automatically |

### Request

```http
POST /api/manual-sessions
Content-Type: application/json

{
  "profile_id": "cooperative_hardship",
  "strategy_id": "empathetic_payment_plan",
  "human_role": "debtor",
  "conversation_model": "local-scripted",
  "judge_model": "local-judge"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `profile_id` | `str` | Yes | The debtor profile the AI will embody (or the human will role-play) |
| `strategy_id` | `str` | Yes | The collector strategy the AI will follow (or the human will apply) |
| `human_role` | `str` | Yes | `"collector"` or `"debtor"` |
| `conversation_model` | `str` | No | Model for AI turns. Defaults to config default. |
| `judge_model` | `str` | No | Model for judgment. Defaults to config default. |

### Response

When `human_role` is `"debtor"`, the AI collector generates the first message before the response is returned:

```json
{
  "id": "manual_a1b2c3d4e5",
  "status": "waiting_for_human",
  "human_role": "debtor",
  "message": "Waiting for human debtor turn.",
  "run": {
    "id": "sim_x1y2z3",
    "status": "running",
    "profile_id": "cooperative_hardship",
    "strategy_id": "empathetic_payment_plan",
    "transcript": [
      {
        "role": "collector",
        "content": "Hello, this is Sarah from Meridian Financial Services..."
      }
    ],
    "turn_count": 1
  },
  "ended_at": null
}
```

When `human_role` is `"collector"`, the transcript starts empty and the human sends the opening message.

## Turn-by-Turn Interaction

Each turn follows the same pattern:

1. Human submits their message via `POST /api/manual-sessions/{session_id}/turn`.
2. The server appends the human's message to the transcript.
3. The AI counterpart generates a response.
4. The server checks for end conditions.
5. If the conversation continues, the session returns to `waiting_for_human`.

### Submitting a turn

```http
POST /api/manual-sessions/{session_id}/turn
Content-Type: application/json

{
  "content": "I understand the situation. I think I can manage $75 per month."
}
```

The response is the updated session snapshot with the AI's reply appended to the transcript.

!!! tip "Viewing the AI response"
    After submitting a turn, check `run.transcript` in the response — the last message will be the AI's reply.

## Session Lifecycle

```
┌─────────────────┐
│   POST /create   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     POST /turn     ┌─────────────────┐
│ waiting_for_human│ ───────────────► │   ai_thinking    │
└────────┬────────┘                    └────────┬────────┘
         │                                      │
         │◄─────────────────────────────────────┘
         │         (AI responds, no end signal)
         │
         │  ┌── end signal detected ──┐
         │  │  turn limit reached     │
         │  │  stalemate detected     │
         │  │  POST /finish           │
         ▼  ▼                         │
┌─────────────────┐                   │
│     judging      │◄─────────────────┘
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    completed     │
└─────────────────┘
```

### States

| State | Description |
|-------|-------------|
| `waiting_for_human` | Session is waiting for the human to submit their turn |
| `ai_thinking` | The AI model is generating its response |
| `judging` | The conversation has ended and the Judge is evaluating the transcript |
| `completed` | Judgment is complete; the run has been persisted to the database |

!!! warning "Concurrent turn protection"
    Submitting a turn while the session is in `ai_thinking` state returns `409 Conflict`. Each session uses an `asyncio.Lock` to prevent race conditions.

## End Conditions

A session can end through any of the following mechanisms:

### 1. Explicit end signal

Include `[END_CONVERSATION]` anywhere in the human's message to signal the end of the conversation:

```json
{
  "content": "Thank you for your help. I'll set up that payment plan. [END_CONVERSATION]"
}
```

The end signal is stripped from the stored message content. The `ended_by` field records which role ended the conversation.

The same applies to AI-generated messages — if the AI includes `[END_CONVERSATION]`, the conversation ends after that turn.

### 2. Turn limit

When the transcript reaches the configured maximum turn count (defined in `config/simulation.yaml`), the session ends automatically with `ended_by: "turn_limit"`.

### 3. Stalemate detection

The engine monitors recent messages for semantic similarity. If consecutive turns are too similar (controlled by `stalemate_window` and `stalemate_similarity_threshold` in config), the session ends with `ended_by: "stalemate"`.

### 4. Manual finish

The human can force-finish the session at any time via the finish endpoint:

```http
POST /api/manual-sessions/{session_id}/finish
```

This triggers judgment immediately on whatever transcript exists. The session must have at least one turn — finishing an empty session returns `400 Bad Request`.

## Judgment and Persistence

When the conversation ends (by any mechanism):

1. The session transitions to the `judging` state.
2. The Judge model evaluates the full transcript against the debtor profile.
3. The `SimulationResult` is updated with:
    - `judgment` — structured scores and reasoning
    - `ended_by` — who or what ended the conversation
    - `status` — set to `"completed"`
    - `ended_at` — timestamp
4. The result is saved to the SQLite database via `SimulationStore.save_run()`.
5. The session transitions to `completed`.

The saved run is identical in structure to automated simulation results and appears in all the same views — run browser, dashboard stats, strategy comparisons, playbook generation, etc.

### Retrieving the saved run

After completion, the run is accessible through the standard runs API:

```http
GET /api/runs/{run_id}
```

The `run_id` is available in the session snapshot at `run.id`.

## Example: Complete Debtor Session

```python
import httpx

base = "http://127.0.0.1:8000"

# 1. Create session
resp = httpx.post(f"{base}/api/manual-sessions", json={
    "profile_id": "cooperative_hardship",
    "strategy_id": "empathetic_payment_plan",
    "human_role": "debtor",
    "conversation_model": "local-scripted",
    "judge_model": "local-judge",
})
session = resp.json()
session_id = session["id"]
print(f"Collector: {session['run']['transcript'][0]['content']}")

# 2. Submit turns
resp = httpx.post(f"{base}/api/manual-sessions/{session_id}/turn", json={
    "content": "I lost my job last month and I'm struggling to pay bills."
})
session = resp.json()
ai_reply = session["run"]["transcript"][-1]["content"]
print(f"Collector: {ai_reply}")

# 3. End the conversation
resp = httpx.post(f"{base}/api/manual-sessions/{session_id}/turn", json={
    "content": "Okay, $75/month works for me. Thank you. [END_CONVERSATION]"
})
session = resp.json()
assert session["status"] == "completed"
assert session["run"]["judgment"] is not None

# 4. Access the persisted run
run_id = session["run"]["id"]
run = httpx.get(f"{base}/api/runs/{run_id}").json()
print(f"Payment outcome: {run['judgment']['payment_outcome']}")
print(f"Compliance score: {run['judgment']['compliance_score']}")
```

## Example: Complete Collector Session

```python
import httpx

base = "http://127.0.0.1:8000"

# Human plays collector — no AI opening message
resp = httpx.post(f"{base}/api/manual-sessions", json={
    "profile_id": "written_proof_disputer",
    "strategy_id": "empathetic_payment_plan",
    "human_role": "collector",
    "conversation_model": "local-scripted",
    "judge_model": "local-judge",
})
session = resp.json()
session_id = session["id"]
assert session["run"]["transcript"] == []  # human goes first

# Send the opening message
resp = httpx.post(f"{base}/api/manual-sessions/{session_id}/turn", json={
    "content": "Hello, I'm calling about your Will Bank account. I'd like to help find a solution."
})
session = resp.json()
# AI debtor responds automatically
debtor_reply = session["run"]["transcript"][-1]["content"]
print(f"Debtor: {debtor_reply}")

# Continue the conversation...
resp = httpx.post(f"{base}/api/manual-sessions/{session_id}/turn", json={
    "content": "I completely understand. I'll send you the full documentation right away. [END_CONVERSATION]"
})
session = resp.json()
assert session["status"] == "completed"
```
