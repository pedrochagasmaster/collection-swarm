"""Deterministic local backend used for offline simulations and tests."""

from __future__ import annotations

import json

from collection_swarm.backends.base import LLMResponse
from collection_swarm.models import LLMMessage, ModelConfig


class ScriptedBackend:
    """A lightweight backend that makes the app usable without API credentials."""

    backend_name = "scripted"

    async def complete(self, model: ModelConfig, messages: list[LLMMessage]) -> LLMResponse:
        system = messages[0].content.lower() if messages else ""
        history = "\n".join(message.content for message in messages)
        # Role detection: judge first (most distinctive), then debtor
        # (matches "you are the debtor" / "voc\u00ea \u00e9 o devedor"), and
        # finally collector as the default. We anchor the debtor match on the
        # opening phrase so it does not get triggered by passing references
        # to "devedor" inside the collector's system prompt.
        if any(marker in system for marker in ("judge", "evaluator", "juiz avaliador")):
            content = self._judge_response(history)
        elif (
            "you are the debtor" in system
            or "voc\u00ea \u00e9 o devedor" in system
        ):
            content = self._debtor_response(system, history.lower())
        else:
            content = self._collector_response(system, history.lower())
        return LLMResponse(
            content=content,
            input_tokens=sum(len(message.content.split()) for message in messages),
            output_tokens=len(content.split()),
            estimated_cost_usd=0.0,
            model_id=model.id,
            backend=self.backend_name,
        )

    def _collector_response(self, system: str, history: str) -> str:
        if any(term in system for term in ["payment_plan", "payment plan", "parcelamento", "parcela"]):
            tactic = "combinar uma parcela que caiba no seu bolso"
        elif any(term in system for term in ["settlement", "settlement_offer", "acordo", "à vista", "a vista"]):
            tactic = "ver um acordo com desconto à vista"
        else:
            tactic = "encontrar o próximo passo de pagamento que faça sentido"

        if "debtor:" not in history:
            return (
                "Olá, aqui é Alex falando em nome do liquidante do Will Bank. "
                "Quero entender sua situação e ver se conseguimos "
                f"{tactic}, sem pressão."
            )
        if any(
            term in history
            for term in [
                "agree",
                "can do",
                "will pay",
                "plan works",
                "per month",
                "acceptable",
                "topo",
                "fechado",
                "posso pagar",
                "consigo pagar",
                "aceito",
                "por mês",
            ]
        ):
            return (
                "Combinado. Vou registrar o acordo e te enviar a confirmação por escrito. "
                "[END_CONVERSATION]"
            )
        if any(
            term in history
            for term in [
                "can't",
                "hardship",
                "afford",
                "written proof",
                "verify",
                "n\u00e3o consigo",
                "n\u00e3o posso",
                "fatura detalhada",
                "contrato",
                "golpe",
                "desconfio",
            ]
        ):
            return (
                "Entendi. Posso te enviar a fatura detalhada e o contrato pelos canais oficiais "
                "do liquidante (willbank.com.br) e voltamos a falar quando estiver tudo claro. "
                "Se ajudar, também consigo um primeiro valor menor ou um retorno em data combinada."
            )
        return (
            "Que valor ou data ficaria realista pra você pra darmos um próximo passo?"
        )

    def _debtor_response(self, system: str, history: str) -> str:
        if any(term in system for term in ["dispute", "written proof", "wants_written_proof", "disputer"]):
            if not any(
                marker in history
                for marker in ["written validation", "written proof", "fatura detalhada", "contrato"]
            ):
                return (
                    "Antes de falar de pagamento, preciso da fatura detalhada e do contrato "
                    "por escrito pra confirmar essa cobrança."
                )
            return (
                "Quando eu receber e revisar a documentação a gente fala. "
                "Hoje eu não vou me comprometer. [END_CONVERSATION]"
            )
        if any(term in system for term in ["scam", "suspects_scam", "distrustful", "skeptical"]):
            if not any(
                marker in history
                for marker in ["liquidante", "willbank.com.br", "bcb.gov.br", "banco central"]
            ):
                return (
                    "Como sei que isso não é golpe? Me passe o nome do liquidante e o canal oficial "
                    "antes de qualquer coisa."
                )
            return (
                "Vou confirmar essas informações nos canais oficiais e te retorno. [END_CONVERSATION]"
            )
        if any(term in system for term in ["hardship", "can_pay_partial"]):
            if any(marker in system for marker in ["150", "r$ 150", "r$150"]):
                return (
                    "Não consigo pagar tudo, mas R$ 100 por mês eu topo se for em boleto."
                )
            return (
                "Tô numa fase apertada, mas consigo segurar uma parcela pequena no boleto."
            )
        if any(term in system for term in ["angry", "hostile", "avoidance", "avoidant"]):
            return (
                "Cansei dessas ligações. Manda tudo por escrito. [END_CONVERSATION]"
            )
        if any(term in system for term in ["confused", "questions_validity"]):
            return (
                "Achei que com o Will tendo quebrado eu nem precisava pagar. Você pode me explicar "
                "como funciona agora?"
            )
        return (
            "Esqueci esse boleto. Se me mandarem a confirmação por escrito, "
            "eu pago essa semana."
        )

    def _judge_response(self, history: str) -> str:
        lower_history = history.lower()
        if any(
            marker in lower_history
            for marker in ["payment plan", "per month", "por m\u00eas", "parcela", "boleto registrado"]
        ):
            outcome = "payment_plan"
            probability = 0.72
        elif any(
            marker in lower_history
            for marker in ["payment this week", "will pay", "vou pagar", "pago essa semana"]
        ):
            outcome = "promise_to_pay"
            probability = 0.65
        elif any(
            marker in lower_history
            for marker in [
                "not committing",
                "send me everything in writing",
                "manda tudo por escrito",
                "n\u00e3o vou me comprometer",
            ]
        ):
            outcome = "no_commitment"
            probability = 0.25
        else:
            outcome = "no_commitment"
            probability = 0.35
        payload = {
            "reasoning": "Heuristic local judge based on the transcript outcome and tone.",
            "payment_outcome": outcome,
            "payment_probability": probability,
            "debtor_satisfaction": 0.68,
            "compliance_score": 0.95,
            "conversation_efficiency": max(1, history.count("Collector:") + history.count("Debtor:")),
            "rapport_built": 0.62,
            "escalation_risk": 0.08,
            "end_reason": "agreement_reached" if outcome in {"payment_plan", "promise_to_pay"} else "debtor_deferred",
            "constraint_violations": [],
        }
        return json.dumps(payload)
