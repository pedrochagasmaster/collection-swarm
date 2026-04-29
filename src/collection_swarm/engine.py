"""Conversation engine for a single Simulation."""

from __future__ import annotations

from datetime import timezone
from difflib import SequenceMatcher

from collection_swarm.agents.collector import CollectorAgent
from collection_swarm.agents.debtor import DebtorAgent
from collection_swarm.agents.judge import Judge
from collection_swarm.models import EndedBy, Message, Profile, SimulationResult, Strategy, utc_now


class SimulationEngine:
    def __init__(
        self,
        collector: CollectorAgent,
        debtor: DebtorAgent,
        judge: Judge,
        max_turns: int = 20,
        end_signal: str = "[END_CONVERSATION]",
        stalemate_window: int = 3,
        stalemate_similarity_threshold: float = 0.6,
    ) -> None:
        self.collector = collector
        self.debtor = debtor
        self.judge = judge
        self.max_turns = max_turns
        self.end_signal = end_signal
        self.stalemate_window = stalemate_window
        self.stalemate_similarity_threshold = stalemate_similarity_threshold

    async def run_simulation(self, profile: Profile, strategy: Strategy) -> SimulationResult:
        result = SimulationResult(
            profile_id=profile.id,
            strategy_id=strategy.id,
            conversation_model=self.collector.model_id,
            judge_model=self.judge.model_id,
        )
        try:
            while len(result.transcript) < self.max_turns:
                await self._add_collector_turn(result, profile, strategy)
                if result.ended_by:
                    break
                if len(result.transcript) >= self.max_turns:
                    break
                await self._add_debtor_turn(result, profile)
                if result.ended_by or self._stalemate_detected(result.transcript):
                    result.ended_by = result.ended_by or EndedBy.STALEMATE
                    break

            if result.ended_by is None:
                result.ended_by = EndedBy.TURN_LIMIT

            result.turn_count = len(result.transcript)
            result.judgment = await self.judge.evaluate(result.transcript, profile)
            if self.judge.last_response:
                result.total_input_tokens += self.judge.last_response.input_tokens
                result.total_output_tokens += self.judge.last_response.output_tokens
                result.estimated_cost_usd += self.judge.last_response.estimated_cost_usd
            result.ended_at = utc_now()
            return result
        except Exception as exc:
            result.status = "failed"
            result.error_message = str(exc)
            result.turn_count = len(result.transcript)
            result.ended_at = utc_now().astimezone(timezone.utc)
            return result

    async def _add_collector_turn(self, result: SimulationResult, profile: Profile, strategy: Strategy) -> None:
        response = await self.collector.generate_turn(strategy, profile.account_data, result.transcript)
        result.total_input_tokens += response.input_tokens
        result.total_output_tokens += response.output_tokens
        result.estimated_cost_usd += response.estimated_cost_usd
        content, ended = strip_end_signal(response.content, self.end_signal)
        result.transcript.append(Message(role="collector", content=content))
        if ended:
            result.ended_by = EndedBy.COLLECTOR

    async def _add_debtor_turn(self, result: SimulationResult, profile: Profile) -> None:
        response = await self.debtor.generate_turn(profile, result.transcript)
        result.total_input_tokens += response.input_tokens
        result.total_output_tokens += response.output_tokens
        result.estimated_cost_usd += response.estimated_cost_usd
        content, ended = strip_end_signal(response.content, self.end_signal)
        result.transcript.append(Message(role="debtor", content=content))
        if ended:
            result.ended_by = EndedBy.DEBTOR

    def _stalemate_detected(self, transcript: list[Message]) -> bool:
        return stalemate_detected(transcript, self.stalemate_window, self.stalemate_similarity_threshold)


def strip_end_signal(content: str, signal: str = "[END_CONVERSATION]") -> tuple[str, bool]:
    ended = signal in content
    cleaned = content.replace(signal, "").strip()
    return cleaned, ended


def stalemate_detected(transcript: list[Message], window: int = 3, threshold: float = 0.6) -> bool:
    pairs = [(transcript[i], transcript[i + 1]) for i in range(0, len(transcript) - 1, 2)]
    if len(pairs) < window:
        return False
    recent_pairs = pairs[-window:]
    baseline_collector = recent_pairs[0][0].content.lower()
    baseline_debtor = recent_pairs[0][1].content.lower()
    for collector_turn, debtor_turn in recent_pairs[1:]:
        collector_ratio = SequenceMatcher(None, baseline_collector, collector_turn.content.lower()).ratio()
        debtor_ratio = SequenceMatcher(None, baseline_debtor, debtor_turn.content.lower()).ratio()
        if collector_ratio < threshold or debtor_ratio < threshold:
            return False
    return True
