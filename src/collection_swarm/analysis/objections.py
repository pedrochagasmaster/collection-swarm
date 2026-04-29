"""Simple objection extraction from transcripts."""

from __future__ import annotations

from collections import Counter

from pydantic import BaseModel

from collection_swarm.models import Message


class ObjectionReport(BaseModel):
    objections: dict[str, int]


KEYWORDS = {
    "inability_to_pay": ["can't afford", "cannot pay", "hardship", "tough spot"],
    "disputes_debt": ["not mine", "dispute", "don't owe"],
    "wants_written_proof": ["written proof", "written validation", "validate"],
    "avoidance": ["call back", "not now", "later"],
    "emotional_distress": ["tired", "angry", "stress"],
}


def extract_objections(transcripts: list[list[Message]], taxonomy: list[str] | None = None) -> ObjectionReport:
    allowed = set(taxonomy or KEYWORDS)
    counts: Counter[str] = Counter()
    for transcript in transcripts:
        debtor_text = " ".join(turn.content.lower() for turn in transcript if turn.role == "debtor")
        for objection, keywords in KEYWORDS.items():
            if objection in allowed and any(keyword in debtor_text for keyword in keywords):
                counts[objection] += 1
    return ObjectionReport(objections=dict(counts))
