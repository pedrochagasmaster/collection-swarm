"""Simple objection extraction from transcripts."""

from __future__ import annotations

from collections import Counter, defaultdict

from pydantic import BaseModel

from collection_swarm.models import Message


class ObjectionReport(BaseModel):
    objections: dict[str, int]
    responses: dict[str, list[str]] = {}


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
    responses: dict[str, list[str]] = defaultdict(list)
    for transcript in transcripts:
        debtor_turns = [turn for turn in transcript if turn.role == "debtor"]
        debtor_text = " ".join(turn.content.lower() for turn in debtor_turns)
        for objection, keywords in KEYWORDS.items():
            if objection in allowed and any(keyword in debtor_text for keyword in keywords):
                counts[objection] += 1
                response = _collector_response_after_objection(transcript, objection)
                if response and response not in responses[objection]:
                    responses[objection].append(response)
    return ObjectionReport(objections=dict(counts), responses=dict(responses))


def _collector_response_after_objection(transcript: list[Message], objection: str) -> str | None:
    keywords = KEYWORDS[objection]
    for index, turn in enumerate(transcript):
        if turn.role == "debtor" and any(keyword in turn.content.lower() for keyword in keywords):
            for follow_up in transcript[index + 1 :]:
                if follow_up.role == "collector":
                    return follow_up.content
    return None
