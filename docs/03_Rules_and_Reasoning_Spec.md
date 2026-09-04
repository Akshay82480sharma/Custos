# Rules & Reasoning Specification
## Custos — Autonomous Revenue Recovery Agent

**Version:** 1.0

This document specifies exactly what is decided by deterministic rules vs. what is delegated to the LLM, and exactly what the LLM is allowed to influence. This separation is the core trust mechanism of the system — write it down precisely so it can't drift during the build.

---

## 1. Division of Responsibility

| Decision | Owner | Why |
|---|---|---|
| Is this event worth looking at at all? | Rules | Cheap, high-volume, doesn't need judgment |
| What category does this event fall into? | Rules | Deterministic mapping from status fields |
| Why did this probably happen? | LLM | Requires reading context/history, genuine judgment |
| What action should be taken? | LLM (recommendation only) | Requires weighing tradeoffs |
| Is that action allowed right now? | Rules (Policy Engine) | Must be predictable and auditable, zero tolerance for LLM error here |
| Did the action actually work? | Rules (verification check against real system state) | Factual, not interpretive |

**Golden rule: the LLM proposes, the rules dispose.** No exceptions. If a demo scenario ever seems to need the LLM to directly execute something, that's a design smell — route it through the policy engine instead, even if it adds one extra hop.

## 2. Classification Rules (deterministic)

```
IF payment.status == "failed" AND payment.attempts < 3
    → category = AT_RISK_RETRIABLE

IF payment.status == "failed" AND payment.attempts >= 3
    → category = AT_RISK_EXHAUSTED  (do not auto-retry further; route to LLM for
      an alternative recommendation, e.g. alternate payment method or human contact)

IF invoice.due_date < today AND invoice.status == "unpaid"
    → days_overdue = today - due_date
    → IF days_overdue <= 7  → category = OVERDUE_EARLY
    → IF days_overdue > 7 AND <= 30 → category = OVERDUE_MID
    → IF days_overdue > 30 → category = OVERDUE_LATE

IF transaction.status == "disputed"
    → category = DISPUTED

ELSE
    → category = HEALTHY (no further processing)
```

## 3. LLM Reasoning Contract

### 3.1 Input the LLM receives (structured, never raw free text from external systems)

```json
{
  "event_id": "string",
  "category": "AT_RISK_RETRIABLE | AT_RISK_EXHAUSTED | OVERDUE_EARLY | OVERDUE_MID | OVERDUE_LATE | DISPUTED",
  "amount": "number",
  "currency": "string",
  "customer_history": {
    "past_successful_payments": "number",
    "past_failures": "number",
    "average_days_to_pay": "number | null"
  },
  "event_detail": {
    "failure_reason": "string | null",
    "attempts_so_far": "number",
    "days_overdue": "number | null"
  }
}
```

### 3.2 Output the LLM must return (strict schema, validated before use)

```json
{
  "diagnosis": "string — plain-language explanation of likely cause",
  "recommended_action": "RETRY_PAYMENT | SEND_REMINDER | ESCALATE_REMINDER | FLAG_FOR_HUMAN_REVIEW | NO_ACTION",
  "confidence": "number 0.0–1.0",
  "reasoning": "string — why this action, in one or two sentences"
}
```

If the response fails schema validation (malformed JSON, invalid enum value, missing field), the event is automatically routed to `FLAG_FOR_HUMAN_REVIEW` — never silently retried against the LLM in a loop, and never allowed to fall through to execution unvalidated.

### 3.3 Prompt Template (conceptual — not the literal production prompt)

```
You are a diagnostic assistant for a merchant revenue recovery system.
You do not have the authority to execute any action — you only recommend.
A separate system will check your recommendation against fixed safety rules
before anything happens.

Given this event: {structured_input}

Return ONLY valid JSON matching this schema: {schema}

Consider:
- Customer payment history (a customer with many past successes and one
  failure is very different from a customer with a poor track record)
- How many attempts have already been made
- Whether the situation calls for a soft touch (reminder) or firmer action
  (escalation) or is beyond what an automated system should decide
  (flag for human)
```

## 4. Policy Engine Rules (deterministic gate)

```
RULE: Amount ceiling
  IF recommended_action == RETRY_PAYMENT AND amount > MAX_AUTO_RETRY_AMOUNT
      → HOLD (reason: "exceeds auto-retry ceiling, needs human sign-off")

RULE: Retry limit
  IF recommended_action == RETRY_PAYMENT AND event.attempts_so_far >= 3
      → HOLD (reason: "retry limit already reached")

RULE: Idempotency
  IF an action of this same type has already been executed for this event_id
      → HOLD (reason: "duplicate action prevented")

RULE: Escalation ceiling
  IF recommended_action == ESCALATE_REMINDER AND customer has already
     received 2 reminders in the last 7 days
      → HOLD (reason: "escalation frequency cap reached, avoid customer fatigue")

RULE: Confidence floor
  IF confidence < 0.5
      → HOLD (reason: "LLM confidence too low for autonomous action")

DEFAULT: if none of the above trigger → APPROVED
```

`MAX_AUTO_RETRY_AMOUNT` and other thresholds are configuration values, not hardcoded magic numbers, so they can be tuned per merchant in a future version without code changes.

## 5. Verification Rules

```
IF action_type == RETRY_PAYMENT:
    poll payment status after a short delay
    → IF status == "captured" → outcome = RECOVERED
    → IF status == "failed" → outcome = RETRY_FAILED (event re-enters
      classification on next cycle, subject to the retry limit above)

IF action_type == SEND_REMINDER or ESCALATE_REMINDER:
    → outcome = SENT (logged; actual payment outcome tracked on the
      next relevant event, since reminders don't resolve instantly)

IF action_type == FLAG_FOR_HUMAN_REVIEW:
    → outcome = AWAITING_HUMAN (terminal state for this pipeline;
      a human action outside the system would resolve it)
```

## 6. What Makes This "Bounded Autonomy" Rather Than "An LLM With API Access"

The distinction worth stating explicitly, since it's the whole credibility argument of the project: nowhere does the LLM's output directly cause an API call. Every single recommended action passes through code that a human wrote and can read line by line, with named, fixed thresholds. If the LLM hallucinates a bad recommendation, the worst case is it gets held for human review — it cannot cause an unbounded or unsafe action, by construction rather than by hoping the prompt is good enough.
