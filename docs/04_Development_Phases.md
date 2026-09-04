# Product Development Phases
## Custos — Autonomous Revenue Recovery Agent

**Version:** 1.0

This is the actual build order. Each phase produces something runnable — never move to the next phase until the current one genuinely works, since every later phase depends on the one before being real (not mocked).

---

## Phase 0 — Data Access (Day 1)

**Goal:** Prove you can pull real Razorpay test-mode data programmatically.

- [ ] Razorpay test API keys generated and stored (never committed to the repo — use environment variables)
- [ ] Script authenticates and creates a test order
- [ ] A handful of test payments completed via mock checkout (mix of success/failure) so real records exist
- [ ] Script fetches and prints those records as JSON

**Exit condition:** you have seen real JSON from Razorpay's test API on your screen, not a mock.

## Phase 1 — Ingestion & Storage (Day 2)

**Goal:** Real events land in a local database, normalized into one schema.

- [ ] `events` table created (SQLite)
- [ ] Ingestion script pulls from Razorpay and/or replays a synthetic batch, writes normalized rows
- [ ] Can re-run ingestion without creating duplicate rows (idempotent by source_id)

**Exit condition:** querying the `events` table shows a believable mix of transaction states.

## Phase 2 — Rule-Based Classification (Day 3, morning)

**Goal:** Every event gets a deterministic category with zero AI involved yet.

- [ ] Classification rules from the Rules & Reasoning Spec implemented
- [ ] `classifications` table populated for every event
- [ ] Manually verify a sample of classifications make sense

**Exit condition:** you can point at any event and say exactly why it got the category it did, with no ambiguity.

## Phase 3 — LLM Reasoning Layer (Day 3 afternoon – Day 4)

**Goal:** Non-healthy events get a diagnosis and recommended action.

- [ ] Prompt template built per the Rules & Reasoning Spec
- [ ] Structured JSON output enforced and validated
- [ ] Malformed/invalid responses correctly fall back to `FLAG_FOR_HUMAN_REVIEW`
- [ ] `llm_decisions` table populated

**Exit condition:** for 10+ real events, the diagnoses read as sensible to a human skimming them.

## Phase 4 — Policy Engine (Day 5)

**Goal:** No action reaches execution without passing a deterministic, readable gate.

- [ ] All policy rules from the spec implemented as plain code (not prompts)
- [ ] `policy_checks` table populated with decision + reason for every event
- [ ] Deliberately test a case designed to be HELD (e.g. an amount above the ceiling) and confirm it's actually held

**Exit condition:** you can demonstrate one approved case and one deliberately-blocked case side by side.

## Phase 5 — Action Layer & Verification (Day 6)

**Goal:** Approved actions actually happen and their outcomes are checked.

- [ ] Retry-payment action wired to Razorpay test API
- [ ] Reminder/escalation actions simulated and logged (per PRD scope decision)
- [ ] Verification step polls and records outcome
- [ ] `actions` table and outcome tracking complete

**Exit condition:** at least one full case goes from "failed payment" to "verified recovered" with no manual steps in between.

## Phase 6 — Audit Log & Dashboard (Day 7)

**Goal:** The whole reasoning chain is visible and presentable.

- [ ] `audit_log` populated at every stage
- [ ] Simple dashboard (even a clean HTML page) shows: total at-risk, total recovered, and a scrollable/expandable decision trail
- [ ] Pick one event and confirm you can trace its full story (detected → why → gate decision → action → outcome) just by reading the dashboard

**Exit condition:** you could hand this to someone else and they could understand a single decision without you explaining it verbally.

## Phase 7 — Demo Hardening (Day 8–9)

**Goal:** The system survives being demoed live or on camera.

- [ ] A pre-built synthetic batch exists as a fallback in case live API calls are flaky during recording
- [ ] Run the entire pipeline start to finish at least 3 times to catch intermittent bugs
- [ ] Deliberately break something small (kill the LLM call, feed a malformed event) and confirm it fails gracefully rather than crashing the whole run — this is also good material for the "what broke" story if it produces a genuine bug

**Exit condition:** you can run the whole loop twice in a row with identical, predictable results.

## Phase 8 — Video, Docs, Submission (Day 10–12)

**Goal:** Package everything per the hackathon's actual evaluation criteria.

- [ ] Record the 5-minute video per the script structure discussed earlier
- [ ] Write the 1-page architecture doc (a trimmed-down version of this doc's Section 2 diagram + tech table is enough)
- [ ] README with clear setup steps, tested from a clean clone
- [ ] Submit under Track 03, with an honest note that other capabilities are inputs to the recovery decision, not separately claimed features

**Exit condition:** someone with zero context could clone the repo, follow the README, and get it running.

---

## Future Phases (explicitly NOT part of this hackathon build — road-mapped only)

These exist to show the architecture is genuinely extensible, per the generic schema design in the Architecture doc. Do not attempt these during the hackathon — listing them is what makes the "future-proof" claim honest rather than aspirational hand-waving.

- **Phase 9:** Risk scoring as an additional classifier feeding into the same `events` → `llm_decisions` pipeline (Track 02 capability, added as an input signal, not a new UI)
- **Phase 10:** Growth/upsell signals as a second recommended-action category using the same policy-engine pattern (Track 01 capability)
- **Phase 11:** Full reconciliation layer reading from the same `events` table to reconcile settlements (Track 04 capability)
- **Phase 12:** Natural-language merchant query interface over the accumulated audit log ("why did revenue drop this week") — Track 05 / open-track capability, only sensible once Phases 9–11 exist to query across
