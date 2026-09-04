# System Architecture Document
## Custos — Autonomous Revenue Recovery Agent

**Version:** 1.0

---

## 1. Architecture Philosophy

Three separate kinds of authority, kept strictly separate:

- **Intelligence** (the LLM) — reasons about ambiguous situations, proposes actions, explains itself. Never touches money or external systems directly.
- **Authority** (the policy engine) — deterministic, hard-coded rules. The only component allowed to say "yes, execute this." Cannot be talked into anything by clever prompting because it isn't a prompt — it's plain code.
- **Execution** (the action layer) — dumb, mechanical. Does exactly what the policy engine approved, nothing more.

This separation is the core design decision. It's what makes the system defensible to a technical judge: the LLM's job is judgment, not control.

## 2. High-Level Flow

```
                    EVENT SOURCE
              (Razorpay test-mode webhook
               or polled API / batch replay)
                          │
                          ▼
                ┌───────────────────┐
                │   INGESTION       │
                │  Normalize event  │
                │  → events table   │
                └─────────┬─────────┘
                          │
                          ▼
                ┌───────────────────┐
                │  RULE-BASED       │
                │  CLASSIFIER       │
                │  healthy /        │
                │  at-risk /        │
                │  failed / disputed│
                └─────────┬─────────┘
                          │ (if not "healthy")
                          ▼
                ┌───────────────────┐
                │   LLM REASONING   │
                │  Diagnose cause   │
                │  Recommend action │
                │  Confidence score │
                │  Plain-English why│
                └─────────┬─────────┘
                          │
                          ▼
                ┌───────────────────┐
                │  POLICY ENGINE    │
                │  Deterministic    │
                │  gate. Checks:    │
                │  - amount limits  │
                │  - retry count    │
                │  - action allowed?│
                │  - conflicts?     │
                └─────────┬─────────┘
                     approved │ rejected
                          │        └──────► Logged as "held for human review"
                          ▼
                ┌───────────────────┐
                │  ACTION LAYER     │
                │  Executes against │
                │  Razorpay test API│
                │  (retry, refund,  │
                │  simulated notify)│
                └─────────┬─────────┘
                          │
                          ▼
                ┌───────────────────┐
                │  VERIFICATION     │
                │  Poll/confirm     │
                │  outcome          │
                └─────────┬─────────┘
                          │
                          ▼
                ┌───────────────────┐
                │  AUDIT LOG        │
                │  Append-only      │
                │  record of every  │
                │  stage above      │
                └───────────────────┘
                          │
                          ▼
                    DASHBOARD (reads
                    from events + audit
                    log — never writes)
```

## 3. Components

### 3.1 Ingestion
- Pulls from Razorpay test-mode API (Orders, Payments) or replays a batch of synthetic events for demo determinism
- Normalizes into one internal schema regardless of source, so real API data and synthetic replay data are indistinguishable downstream — this is what makes the demo reliable even if live API calls are flaky on presentation day

### 3.2 Rule-Based Classifier
- Simple, deterministic, no ML training required for the hackathon
- Example rules: `status == 'failed'` → at-risk; `due_date < today AND status == 'unpaid'` → overdue; `status == 'disputed'` → disputed
- Cheap to run on every event; filters out the "healthy" majority before spending an LLM call on anything

### 3.3 LLM Reasoning Layer
- Receives a structured JSON payload (event + relevant history) — never raw uncontrolled data
- Returns structured JSON back: `{diagnosis, recommended_action, confidence, reasoning}`
- One model, one prompt template per event type — deliberately not "4 different LLMs," per the architecture reasoning explored earlier
- Never calls any external API itself — its output is a recommendation object, nothing more

### 3.4 Policy Engine
- Pure deterministic code (no LLM involved)
- Checks, at minimum:
  - Is the recommended action in the allowed set for this event type?
  - Is the amount under the configured ceiling?
  - Has this event already been actioned (idempotency check)?
  - Has the retry/attempt count been exceeded?
- Outputs either `APPROVED` (with the action to run) or `HELD` (with a reason, routed to a human-review queue instead of silently dropped)

### 3.5 Action Layer
- Executes exactly what the policy engine approved
- Talks to Razorpay test-mode APIs for anything payment-related (retry, refund)
- Simulates non-payment actions (e.g., "send reminder email") by logging the action and its content rather than integrating a real messaging provider — documented explicitly as a scope decision, not hidden

### 3.6 Verification
- After an action executes, checks the resulting state (e.g., did the retried payment succeed?)
- Writes the outcome back to the audit log — this closes the loop and is what lets the dashboard show "recovered" vs. "attempted"

### 3.7 Audit Log
- Append-only table: one row per stage per event (detected → diagnosed → gated → executed → verified)
- This is the single most important component for the demo's credibility — it's what turns "trust us, it works" into "here's exactly what it decided and why"

### 3.8 Dashboard
- Read-only view over `events` + `audit_log`
- Shows: revenue at risk, revenue recovered, a scrollable decision trail
- Deliberately never writes to the system — keeps it simple and keeps the interesting logic in the backend, not the UI

## 4. Data Model (minimal)

```
events
  id, source_id, type, amount, status, customer_ref,
  raw_payload, created_at

classifications
  event_id, category, classified_at

llm_decisions
  event_id, diagnosis, recommended_action,
  confidence, reasoning, created_at

policy_checks
  event_id, decision (APPROVED/HELD), reason, checked_at

actions
  event_id, action_type, executed_at, result

audit_log
  event_id, stage, detail, timestamp
```

Generic naming (`events`, `actions`, `policy_checks`) is intentional — it's what allows this to extend to other tracks (risk, growth, finance) later without a schema rewrite. See the Product Development Phases doc for how that extension would work.

## 5. Technology Choices

| Layer | Choice | Why |
|---|---|---|
| Backend | Python + FastAPI | Fast to build, good for both API + background processing |
| Database | SQLite (hackathon), Postgres-ready schema | Zero setup cost now, trivial migration later |
| LLM | Single model via API, structured JSON output | Avoids multi-model complexity for no added credibility |
| Payments | Razorpay test mode | Already set up; real test-mode data beats mocked data |
| Frontend | Simple React + Tailwind, or plain HTML if time is short | Dashboard is a viewer, not the hard part — don't over-invest here |
| Hosting | Local run for demo video is acceptable; Railway/Render if deployed | Judges watch a video — a polished local run is enough |

## 6. Known Failure Modes to Design Around

- **Duplicate webhook delivery** → handled by idempotency check in the policy engine (event_id + action_type uniqueness)
- **LLM returns malformed JSON** → wrap parsing in validation; on failure, route to HELD rather than crashing or guessing
- **Razorpay test API flakiness during live demo** → have a pre-recorded batch of events ready as a fallback replay source so the video isn't at the mercy of live network calls
