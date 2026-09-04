# Memory Architecture & Specification
## Custos — Autonomous Revenue Recovery Agent

**Version:** 1.0

"Memory" here means: what does the system remember about past events, decisions, and outcomes, and how does that memory influence future reasoning? This is distinct from the audit log (which is a record for humans) — memory is what the *system itself* reads back in order to make better decisions over time.

---

## 1. Why Memory Matters for This System

A stateless version of Custos would re-diagnose every event from scratch with no awareness of what happened last time. That's weaker on two fronts:

1. **Worse decisions** — a customer's payment history is exactly the kind of context that should change how the LLM reasons (a customer with 14 successful past payments and one failure is a very different situation than a customer with a poor track record), per the Rules & Reasoning Spec
2. **Repeated mistakes** — without memory of past policy holds and outcomes, the system could recommend the same action that already failed twice

For the hackathon scope, memory is **structured and queryable**, not a vector-store "the AI remembers everything" black box. Every piece of memory should be traceable to a specific row in a specific table — this keeps it consistent with the project's whole "explainable, not magic" philosophy.

## 2. Layers of Memory

### 2.1 Working Memory (per-decision context)

Scope: exists only for the duration of a single LLM call.

What's included in the prompt context for any one event (see Rules & Reasoning Spec §3.1):
- The event itself
- A summarized customer history (aggregates, not a full raw transaction dump — keeps prompts small and avoids the LLM re-deriving facts it should be handed pre-computed)
- Prior attempts on *this specific event*, if any (e.g., "this is retry attempt 2 of 3")

This is not persisted as its own store — it's assembled fresh from the tables in 2.2 every time.

### 2.2 Episodic Memory (structured event history)

This is just the database tables already defined in the Architecture doc, considered here as *memory* rather than as a data model:

```
events            — what happened
classifications   — how it was categorized
llm_decisions     — what the AI diagnosed and recommended, and why
policy_checks     — what was allowed or held, and why
actions           — what was actually executed
audit_log         — the full timeline, append-only
```

Querying these tables **is** the system's episodic memory. For example, "customer_history.past_failures" (used in the LLM prompt) is computed by querying past `events` and `actions` rows for that customer — not stored redundantly, not hand-waved as "the AI remembers."

### 2.3 Semantic/Aggregate Memory (derived summaries)

Lightweight, recomputed rather than separately maintained wherever possible, to avoid a second source of truth drifting from the raw event log:

```
customer_profile (derived view, not a separately-written table)
  customer_ref, total_transactions, success_rate,
  average_days_to_pay, last_dispute_date, risk_notes
```

This is what gets summarized into the LLM's `customer_history` input field. It should be computed on read (a query/view) for the hackathon build — pre-aggregating into a separate maintained table is a legitimate future optimization but adds sync-correctness risk that isn't worth it for a 2-week build.

### 2.4 Policy Memory (what the system has learned it's NOT allowed to do)

This is the one layer that's deliberately **not** dynamic for this build:

- Policy thresholds (retry limits, amount ceilings, confidence floors) live in a static config file, not in a learned/adjusted-over-time store
- **Why:** a policy engine that changes its own rules based on outcomes is a much bigger trust and safety surface than a hackathon should take on. "The rules are fixed and readable" is a feature, not a limitation, for this pitch.
- Future version (see Development Phases, Future Phases section): thresholds could become per-merchant configuration, still human-set, never self-modifying

## 3. What Memory Is Explicitly NOT, in This System

- **Not a vector database of embeddings** — nothing here requires semantic similarity search; the data is structured and small enough that plain SQL queries outperform embedding retrieval both in accuracy and in explainability
- **Not persistent LLM conversation history** — each reasoning call is stateless and self-contained (receives a fresh structured payload); the system does not maintain a chat-style running conversation with the model, which would make behavior harder to audit and reproduce
- **Not self-modifying** — nothing the system "learns" changes its own decision-making code or policy thresholds autonomously

## 4. Memory Retrieval Flow (for a single incoming event)

```
New event arrives
      │
      ▼
Query: past events for this customer_ref
      │
      ▼
Compute: aggregate stats (success rate, avg days to pay, dispute history)
      │
      ▼
Query: prior attempts on THIS event_id specifically (for retry counting)
      │
      ▼
Assemble: structured context object
      │
      ▼
Pass to LLM reasoning layer (Working Memory, §2.1)
```

## 5. Data Retention

For the hackathon build, retention is indefinite (small synthetic dataset, no real customer PII beyond test-mode dummy data). A production version would need an explicit retention policy per relevant data-protection regulation — flagged here as a known gap, not solved in this build.

## 6. Future Extension Hook

The generic schema (Architecture doc §4) means memory naturally extends when other tracks are added later:

- Risk scoring (Phase 9) would read from the same `events` history to compute a risk-memory aggregate, following the same "derived view, not a second source of truth" pattern used in §2.3
- This is what makes the "future-proof" claim about the architecture concrete rather than just asserted — the memory model doesn't need to change shape to support it, only grow more views over the same tables
