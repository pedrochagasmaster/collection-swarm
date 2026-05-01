"""Generate seed simulation data for demo purposes."""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from collection_swarm.models import (
    EndedBy,
    Judgment,
    Message,
    PaymentOutcome,
    SimulationResult,
)
from collection_swarm.store import SimulationStore

PROFILE_IDS = [
    "cooperative_hardship",
    "written_proof_disputer",
    "hostile_avoidant",
    "liquidation_confused_cardholder",
    "overindebted_northeast_worker",
    "fraud_and_scam_sensitive",
    "reputationally_angry_former_customer",
]
STRATEGY_IDS = [
    "empathetic_payment_plan",
    "assertive_settlement",
    "neutral_reminder",
    "problem_solving_callback",
    "liquidation_clarity_validation",
    "low_income_budget_fit_plan",
    "scam_sensitive_self_service",
    "complaint_deescalation_review",
]

SAMPLE_CONVERSATIONS: dict[tuple[str, str], list[dict]] = {
    ("cooperative_hardship", "empathetic_payment_plan"): [
        {"role": "collector", "content": "Hello, this is Sarah from Meridian Financial Services. I'm calling regarding an outstanding medical balance of $1,250. I understand these situations can be stressful, and I'd like to help find a solution that works for you."},
        {"role": "debtor", "content": "Hi... yeah, I know about the bill. I've been really stressed about it. My hours got cut at work a few months ago and I'm barely keeping up with rent right now."},
        {"role": "collector", "content": "I'm sorry to hear about the reduced hours \u2014 that's a tough situation. I want you to know we have flexible options available. Would it help if we looked at a monthly payment plan that fits within your current budget?"},
        {"role": "debtor", "content": "I mean, maybe? I just can't do anything big right now. What kind of amounts are we talking about?"},
        {"role": "collector", "content": "I completely understand. How about we start with something manageable \u2014 say $75 per month? That would help you make progress on the balance without putting too much pressure on your budget."},
        {"role": "debtor", "content": "Seventy-five... I think I could probably do that. Could I start next month so I have time to adjust some other payments?"},
        {"role": "collector", "content": "Absolutely, we can set the first payment for next month. I'll send you a written agreement with all the details \u2014 the monthly amount, due dates, and total remaining balance. Does that sound good?"},
        {"role": "debtor", "content": "Yeah, that actually sounds really reasonable. Thank you for being understanding about this. I really do want to take care of it."},
        {"role": "collector", "content": "Of course. I appreciate your willingness to work on this. I'll have that agreement in your hands within a couple of days. If anything changes with your situation, don't hesitate to call us. We're here to help. [END_CONVERSATION]"},
    ],
    ("cooperative_hardship", "assertive_settlement"): [
        {"role": "collector", "content": "Good afternoon, this is Mike from Meridian Financial. I'm calling about your medical debt of $1,250 that's 75 days past due. We need to discuss resolution options today."},
        {"role": "debtor", "content": "Oh... okay. I know I owe it, I just haven't been able to pay. Things have been really tight since my hours got cut."},
        {"role": "collector", "content": "I understand times are tough. Here's what I can offer \u2014 if you can make a one-time settlement payment of $875, we'll consider the full balance resolved. That's a 30% reduction."},
        {"role": "debtor", "content": "I can't come up with $875 all at once. That's just not possible right now. I'm already worried about making rent."},
        {"role": "collector", "content": "I hear you. What if we split that settlement into two payments \u2014 $440 now and $435 in 30 days? It would still save you significantly on the total balance."},
        {"role": "debtor", "content": "Two payments is better but $440 is still a lot for me right now. Could we do smaller amounts over a longer time?"},
        {"role": "collector", "content": "I can do a three-month plan at $100 per month as a starting point, with a review after three months. Would that be manageable?"},
        {"role": "debtor", "content": "A hundred a month... that's tight but I think I could manage it if I cut some things. Yeah, let's try that."},
        {"role": "collector", "content": "Good. I'll set that up starting next month. You'll receive confirmation by mail. [END_CONVERSATION]"},
    ],
    ("written_proof_disputer", "empathetic_payment_plan"): [
        {"role": "collector", "content": "Hello, this is Sarah from Meridian Financial Services. I'm reaching out regarding a credit card balance of $780. I'd like to discuss this with you and see how we can help resolve it."},
        {"role": "debtor", "content": "Before we go any further, I need to see written proof of this debt. I don't recognize some of the charges and I'm not discussing payment until I get documentation."},
        {"role": "collector", "content": "That's completely fair, and you have every right to request validation. I can have a detailed statement sent to you showing the original charges, any fees, and the payment history. Would you prefer mail or email?"},
        {"role": "debtor", "content": "Email is fine. But I want itemized charges, not just a total. I think there might be fees on there that shouldn't be."},
        {"role": "collector", "content": "Absolutely. I'll request an itemized breakdown showing each charge and when it was applied. You should receive it within 5 business days. Once you've had a chance to review, would you be open to discussing next steps?"},
        {"role": "debtor", "content": "If everything checks out, sure. But I'm not committing to anything until I see the numbers. I've dealt with incorrect bills before."},
        {"role": "collector", "content": "Completely understood. We want to make sure everything is accurate too. I'll get that documentation sent out today and follow up with you next week. Does that timeline work?"},
        {"role": "debtor", "content": "Yeah, that works. Thanks for not pushing me on this \u2014 the last person who called was a lot more aggressive."},
        {"role": "collector", "content": "Of course. We want to resolve this in a way that feels fair to everyone. I'll send that over today. Talk to you next week. [END_CONVERSATION]"},
    ],
    ("written_proof_disputer", "assertive_settlement"): [
        {"role": "collector", "content": "Good afternoon. This is Mike from Meridian Financial regarding your credit card balance of $780. I'd like to discuss settlement options with you today."},
        {"role": "debtor", "content": "Hold on \u2014 I've asked for written validation of this debt multiple times. I'm not discussing any payment until I receive proper documentation."},
        {"role": "collector", "content": "I can certainly arrange for that documentation. In the meantime, I wanted to let you know we could offer a settlement of $550, which would close this account entirely."},
        {"role": "debtor", "content": "Did you not hear me? I want to see the charges first. Some of these fees don't look right. Send me the validation and then we'll talk."},
        {"role": "collector", "content": "I understand your position. I'll expedite the written validation. Once you've reviewed it, the settlement offer will still be available. Can I have your preferred email address?"},
        {"role": "debtor", "content": "Fine, send it to my email. But I'm going to review everything carefully before I agree to anything. And if there are incorrect charges, I expect them removed."},
        {"role": "collector", "content": "That's fair. If there are any discrepancies, we'll work to resolve them. I'll send the full documentation today and follow up in a week. [END_CONVERSATION]"},
    ],
    ("hostile_avoidant", "empathetic_payment_plan"): [
        {"role": "collector", "content": "Hello, this is Sarah from Meridian Financial Services. I'm calling about your utility account balance. I know you've received several calls and I don't want to add to your frustration \u2014 I'm hoping we can find a quick solution."},
        {"role": "debtor", "content": "Another call? I've told you people to stop calling me. I don't have time for this."},
        {"role": "collector", "content": "I completely understand your frustration, and I apologize for the frequency of contacts. I'll keep this very brief. I just want to let you know about a payment plan option that could help get this resolved so the calls stop."},
        {"role": "debtor", "content": "I'm tired of talking about this. I know I owe it but I can't deal with it right now. Every time you call it just makes things worse."},
        {"role": "collector", "content": "I hear you, and I respect that. If you'd prefer, I can send all the details in writing \u2014 no more phone calls needed. Would a payment plan around $100 per month be something you'd consider if you could set it up online instead?"},
        {"role": "debtor", "content": "... Online? You mean I wouldn't have to talk to anyone?"},
        {"role": "collector", "content": "Exactly. I can send you a link where you can review the balance and set up automatic payments at whatever amount works for you. The minimum would be $85 per month. No more calls once a plan is active."},
        {"role": "debtor", "content": "Fine. Send me the link. But I'm not giving card details over the phone, got it?"},
        {"role": "collector", "content": "Absolutely, no phone payments. I'll send the online portal link to your address on file today. Once you set up the plan, the account will be marked active and the outreach stops. Thank you for your time. [END_CONVERSATION]"},
    ],
    ("hostile_avoidant", "neutral_reminder"): [
        {"role": "collector", "content": "Good afternoon. This is a courtesy call from Meridian Financial regarding your utility account balance of $3,400. I wanted to provide a brief update on your account status."},
        {"role": "debtor", "content": "Courtesy? There's nothing courteous about calling me for the sixth time. I told the last person I'd handle it when I can."},
        {"role": "collector", "content": "I understand, and I'll be brief. I'm calling because the account has reached 220 days and there are resolution options I want to make sure you're aware of before any further action is taken."},
        {"role": "debtor", "content": "What do you mean 'further action'? Are you threatening me?"},
        {"role": "collector", "content": "Not at all \u2014 I'm simply letting you know where things stand. We'd much prefer to work with you directly. Would you be open to a quick conversation about payment options, or would you prefer I send the information in writing?"},
        {"role": "debtor", "content": "Send it in writing. I'm done with phone calls. And don't call again."},
        {"role": "collector", "content": "Understood. I'll send the account summary and available options by mail. If you have questions after reviewing, you can reach us at the number on the letter. Have a good day. [END_CONVERSATION]"},
    ],
}

OUTCOMES_BY_COMBO: dict[tuple[str, str], tuple[str, float, float, float, float, float, str]] = {
    ("cooperative_hardship", "empathetic_payment_plan"): ("payment_plan", 0.82, 0.88, 0.95, 0.85, 0.08, "agreement_reached"),
    ("cooperative_hardship", "assertive_settlement"): ("promise_to_pay", 0.58, 0.62, 0.88, 0.55, 0.22, "partial_agreement"),
    ("cooperative_hardship", "neutral_reminder"): ("promise_to_pay", 0.52, 0.70, 0.92, 0.60, 0.12, "callback_scheduled"),
    ("cooperative_hardship", "problem_solving_callback"): ("payment_plan", 0.75, 0.85, 0.94, 0.82, 0.06, "agreement_reached"),
    ("written_proof_disputer", "empathetic_payment_plan"): ("no_commitment", 0.35, 0.72, 0.96, 0.58, 0.10, "validation_requested"),
    ("written_proof_disputer", "assertive_settlement"): ("no_commitment", 0.22, 0.42, 0.78, 0.28, 0.45, "validation_requested"),
    ("written_proof_disputer", "neutral_reminder"): ("no_commitment", 0.30, 0.60, 0.90, 0.42, 0.18, "callback_scheduled"),
    ("written_proof_disputer", "problem_solving_callback"): ("partial_payment", 0.45, 0.78, 0.95, 0.65, 0.08, "documentation_sent"),
    ("hostile_avoidant", "empathetic_payment_plan"): ("promise_to_pay", 0.40, 0.55, 0.92, 0.48, 0.18, "online_setup_offered"),
    ("hostile_avoidant", "assertive_settlement"): ("refusal", 0.10, 0.18, 0.72, 0.10, 0.68, "debtor_ended_call"),
    ("hostile_avoidant", "neutral_reminder"): ("no_commitment", 0.20, 0.35, 0.88, 0.22, 0.32, "written_followup"),
    ("hostile_avoidant", "problem_solving_callback"): ("promise_to_pay", 0.38, 0.52, 0.90, 0.45, 0.20, "callback_scheduled"),
    ("liquidation_confused_cardholder", "liquidation_clarity_validation"): ("promise_to_pay", 0.62, 0.82, 0.96, 0.72, 0.08, "liquidation_context_explained"),
    ("overindebted_northeast_worker", "low_income_budget_fit_plan"): ("payment_plan", 0.76, 0.86, 0.95, 0.80, 0.07, "cash_flow_plan_agreed"),
    ("fraud_and_scam_sensitive", "scam_sensitive_self_service"): ("full_payment", 0.84, 0.80, 0.96, 0.68, 0.06, "official_channel_payment"),
    ("reputationally_angry_former_customer", "complaint_deescalation_review"): ("no_commitment", 0.38, 0.70, 0.94, 0.58, 0.12, "complaint_acknowledged_review_scheduled"),
}


def _make_transcript(profile_id: str, strategy_id: str) -> list[Message]:
    key = (profile_id, strategy_id)
    if key in SAMPLE_CONVERSATIONS:
        return [Message(**m) for m in SAMPLE_CONVERSATIONS[key]]
    return _generate_generic_transcript(profile_id, strategy_id)


def _generate_generic_transcript(profile_id: str, strategy_id: str) -> list[Message]:
    return [
        Message(role="collector", content=f"Hello, I'm calling from Meridian Financial Services regarding your account. I'd like to discuss resolution options with you using our {strategy_id.replace('_', ' ')} approach."),
        Message(role="debtor", content="Okay, I'm listening. What are my options?"),
        Message(role="collector", content="We have several flexible options available. Based on your account, I'd recommend we find something that works for your current situation. What does your budget look like?"),
        Message(role="debtor", content="Things are tight right now but I want to get this resolved. What's the minimum you can work with?"),
        Message(role="collector", content="I understand. We can work with smaller amounts to get started. Let me put together some options and send them to you in writing so you can review at your convenience."),
        Message(role="debtor", content="That sounds fair. Go ahead and send it over."),
        Message(role="collector", content="I'll get that out to you today. Thank you for taking the time to speak with me. [END_CONVERSATION]"),
    ]


def generate_seed_data(
    db_path: Path = Path("output/collection_swarm.sqlite"),
    num_runs: int = 24,
) -> int:
    store = SimulationStore(db_path)
    results: list[SimulationResult] = []
    base_time = datetime.now(timezone.utc) - timedelta(hours=num_runs)

    combos = [(p, s) for p in PROFILE_IDS for s in STRATEGY_IDS]
    reps_per_combo = max(1, num_runs // len(combos))

    for combo_idx, (profile_id, strategy_id) in enumerate(combos):
        if len(results) >= num_runs:
            break
        for rep in range(reps_per_combo):
            if len(results) >= num_runs:
                break
            idx = combo_idx * reps_per_combo + rep
            started = base_time + timedelta(hours=idx * 0.5)
            transcript = _make_transcript(profile_id, strategy_id)
            duration_minutes = random.uniform(3, 12)
            ended = started + timedelta(minutes=duration_minutes)

            key = (profile_id, strategy_id)
            base_vals = OUTCOMES_BY_COMBO.get(
                key,
                ("no_commitment", 0.30, 0.50, 0.85, 0.40, 0.20, "no_resolution"),
            )
            outcome_str, pp, ds, cs, rb, er, end_reason = base_vals
            jitter = lambda v: max(0.0, min(1.0, v + random.uniform(-0.08, 0.08)))

            judgment = Judgment(
                reasoning=f"The collector used a {strategy_id.replace('_', ' ')} approach with the {profile_id.replace('_', ' ')} profile. "
                f"The conversation {'showed good rapport and progress toward resolution' if pp > 0.5 else 'had limited progress toward payment commitment'}. "
                f"{'Compliance was well maintained throughout.' if cs > 0.85 else 'Some compliance concerns were noted.'}",
                payment_outcome=PaymentOutcome(outcome_str),
                payment_probability=jitter(pp),
                debtor_satisfaction=jitter(ds),
                compliance_score=jitter(cs),
                conversation_efficiency=len(transcript),
                rapport_built=jitter(rb),
                escalation_risk=jitter(er),
                end_reason=end_reason,
                constraint_violations=(
                    ["excessive_pressure"]
                    if er > 0.5 and random.random() < 0.4
                    else []
                ),
            )

            result = SimulationResult(
                status="completed",
                profile_id=profile_id,
                strategy_id=strategy_id,
                conversation_model="scripted_echo",
                judge_model="heuristic_judge",
                started_at=started,
                ended_at=ended,
                turn_count=len([m for m in transcript if m.role == "collector"]),
                ended_by=EndedBy.COLLECTOR,
                transcript=transcript,
                judgment=judgment,
                total_input_tokens=random.randint(800, 2500),
                total_output_tokens=random.randint(600, 1800),
                estimated_cost_usd=round(random.uniform(0.001, 0.015), 4),
            )
            results.append(result)

    store.save_runs(results)
    return len(results)
