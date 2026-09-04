# Project Requirements Document (PRD)
## Custos — Autonomous Revenue Recovery Agent

**Track:** 03 — AI Revenue Recovery
**Version:** 1.0
**Status:** Draft for hackathon build

---

## 1. Problem Statement

Merchants lose revenue silently through three channels:

1. **Failed payments** — a charge fails (card declined, insufficient funds, network timeout) and nobody follows up
2. **Overdue invoices** — B2B or subscription invoices go unpaid past their due date with no systematic escalation
3. **Disputed/chargeback transactions** — a transaction is disputed and the merchant either doesn't respond or responds without proper evidence

Today, most small-to-mid merchants handle this manually or not at all. There's no system that watches every transaction, decides what (if anything) should be done about it, and takes safe, bounded action without a human initiating every step.

## 2. Goal

Build **Custos**: an agent that continuously watches a merchant's transaction stream, diagnoses revenue leakage as it happens, decides on a bounded recovery action, executes it, verifies the outcome, and logs every decision it made and why.

The system should feel like a guardian standing between "money is at risk" and "money is lost" — not a dashboard that reports leakage after the fact.

## 3. Non-Goals (explicitly out of scope for this build)

- We are **not** building a general-purpose finance platform (no growth/upsell engine, no full reconciliation suite) — those are future extensions, not this deliverable
- We are **not** handling real money or production merchants — Razorpay **test mode** only
- We are **not** training a custom ML model from scratch — we use rules + an LLM reasoning layer, not a bespoke classifier
- We are **not** building multi-tenant merchant onboarding — a single simulated merchant account is sufficient

## 4. Users

- **Primary user (hackathon framing):** a merchant operations person who currently manually chases failed payments and overdue invoices
- **Actual user for this build:** the judges, evaluating whether the system runs, reasons sensibly, and takes safe action

## 5. Core User Stories

1. As a merchant, when a payment fails, I want the system to figure out *why* it failed and *whether* retrying is likely to work, without me having to investigate manually.
2. As a merchant, when an invoice goes overdue, I want the system to escalate appropriately (reminder → firmer reminder → flag for human review) rather than staying silent or over-escalating instantly.
3. As a merchant, I want to trust that the system **cannot** take an action outside safe bounds (e.g., it can't retry a charge unlimited times or attempt to move an arbitrarily large amount) — I want a visible policy layer, not a black box.
4. As a merchant (or judge), I want to see **why** the system did what it did — a readable audit trail, not just a final state.

## 6. Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR1 | System ingests transaction/payment/invoice events from Razorpay test mode | Must |
| FR2 | System classifies each event (healthy / at-risk / failed / disputed) using a rules layer | Must |
| FR3 | System uses an LLM to diagnose the likely cause and recommend one action, with a confidence score and a plain-language reason | Must |
| FR4 | System checks every LLM-recommended action against a deterministic policy engine before allowing execution | Must |
| FR5 | System executes approved actions against Razorpay test-mode APIs (retry payment, send reminder — simulated where no real API exists, e.g. messaging) | Must |
| FR6 | System verifies the outcome of an action (did the retry succeed? did the invoice get paid?) | Must |
| FR7 | Every decision (diagnosis, policy check, action, outcome) is written to an append-only audit log | Must |
| FR8 | A simple dashboard shows current at-risk revenue, recovered revenue, and the audit trail in human-readable form | Should |
| FR9 | System can be run against a batch of historical/synthetic events for demo purposes | Should |
| FR10 | System exposes a "why" view for any single decision — the full chain from detection to outcome | Should |

## 7. Non-Functional Requirements

- **Explainability over cleverness** — every automated decision must be traceable to a rule or an LLM output that's visible in the log, not implicit
- **Bounded autonomy** — the LLM never executes an action directly; it only ever recommends, and the policy engine is the sole executor gate
- **Idempotency** — the same event must not trigger the same action twice (this was a real failure mode encountered during build — see architecture doc)
- **Demoable in under 5 minutes** — the entire loop, from ingesting events to showing recovered revenue, must run end-to-end without manual intervention during the video recording

## 8. Success Criteria (for the hackathon submission specifically)

- [ ] Repo runs end-to-end from a clean clone with a documented setup step
- [ ] At least 10 synthetic/test-mode events processed with a mix of outcomes (some recovered, some correctly left alone, at least one correctly escalated to human review)
- [ ] Audit log is human-readable and demonstrates the reasoning chain
- [ ] 5-minute video shows the live loop running, not just slides
- [ ] One genuine engineering failure and fix is documented (not fabricated)

## 9. Constraints

- Time: hackathon window only
- Data: Razorpay test mode (no real transactions, no real money)
- Team: solo build
- Must apply under a single track (Track 03) per hackathon rules; other capabilities (risk scoring, growth signals) may appear only as inputs that inform the recovery decision, not as separate submitted features

## 10. Open Questions

- Do we simulate customer messaging (email/SMS reminder) or is a logged "would have sent" sufficient for the demo? → Default: simulate with a logged message, since real email/SMS sending adds infrastructure risk with little judging upside
- How many synthetic events is "enough" for a convincing demo? → Target 15–25, covering failed payment, overdue invoice, and disputed transaction categories
