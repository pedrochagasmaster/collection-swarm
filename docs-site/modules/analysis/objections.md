# `analysis/objections.py` — objection extraction

<span class="cs-kicker">collection_swarm/analysis/objections.py</span>

Counts how often each objection category appears in a list of
transcripts. Tiny, deterministic, and intentionally simple — the
sophisticated alternative would be an LLM-based classifier, which is
overkill for a per-Profile sanity check.

<dl class="cs-summary">
  <dt>Imports</dt><dd><code>collections.Counter</code>, Pydantic, domain models</dd>
  <dt>Side effects</dt><dd>None</dd>
</dl>

## Built-in keyword set

```python
KEYWORDS = {
    "inability_to_pay": ["can't afford", "cannot pay", "hardship", "tough spot"],
    "disputes_debt":    ["not mine", "dispute", "don't owe"],
    "wants_written_proof": ["written proof", "written validation", "validate"],
    "avoidance":        ["call back", "not now", "later"],
    "emotional_distress": ["tired", "angry", "stress"],
}
```

Every keyword is checked case-insensitively against the concatenation
of every Debtor turn in a transcript. A transcript counts at most once
per category, regardless of how many times the keywords appear.

## `extract_objections(transcripts, taxonomy=None)`

```python
def extract_objections(transcripts: list[list[Message]], taxonomy: list[str] | None = None) -> ObjectionReport:
    allowed = set(taxonomy or KEYWORDS)
    counts: Counter[str] = Counter()
    for transcript in transcripts:
        debtor_text = " ".join(turn.content.lower() for turn in transcript if turn.role == "debtor")
        for objection, keywords in KEYWORDS.items():
            if objection in allowed and any(keyword in debtor_text for keyword in keywords):
                counts[objection] += 1
    return ObjectionReport(objections=dict(counts))
```

The `taxonomy` argument is the allow-list. The CLI and dashboard pass
`config.simulation.objection_taxonomy` (loaded from
`simulation.yaml`). Categories outside the allow-list are silently
ignored, even if their keywords match.

## `ObjectionReport`

```python
class ObjectionReport(BaseModel):
    objections: dict[str, int]
```

A Pydantic shell so the dict ends up JSON-serializable through
`model_dump_jsonable`.

## Where it shows up

- **Playbook.** For each Profile's recommended Strategy, the Playbook
  appends an Objection Playbook section listing every observed category
  with its transcript count.
- **Dashboard.** `GET /api/profiles/{profile_id}/objections` returns
  the same data for the recommended (or explicitly chosen) Strategy.

## When you need real classification

Switch the keyword loop for an LLM call (or a dedicated classifier).
The function signature is stable enough that the rest of the system
won't notice. The return shape — `ObjectionReport` with a
`{category: count}` dict — is what every downstream caller depends on.
