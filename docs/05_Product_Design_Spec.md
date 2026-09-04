# Product Design Specification
## Custos — Autonomous Revenue Recovery Agent

**Version:** 1.0

This covers the dashboard/UI — the one part of the system a judge will actually look at and click through, so it earns real design attention despite being architecturally "just a viewer."

---

## 1. Design Principles

1. **Show the money first.** The very first thing on screen is what's at risk and what's been recovered — numbers, not navigation.
2. **Never hide the reasoning.** Every action the system took should be one click away from its full explanation. The dashboard's entire value proposition is trust through transparency, not just pretty charts.
3. **Read as calm, not alarmist.** This is a guardian, not a fire alarm. Avoid aggressive red/siren styling even for disputed transactions — status should be clear without being panicky.
4. **No dead ends.** Every number on the summary view should be clickable through to the events that make it up.

## 2. Screens

### 2.1 Overview (landing screen)

```
┌─────────────────────────────────────────────────────┐
│  CUSTOS                                    [● Live]  │
├─────────────────────────────────────────────────────┤
│                                                       │
│   Revenue at risk         Revenue recovered          │
│   ₹6,42,000               ₹3,21,500                  │
│                                                       │
│   Held for review         Records processed          │
│   3                       24                         │
│                                                       │
├─────────────────────────────────────────────────────┤
│  Recent activity                                     │
│                                                       │
│  ● Payment retried — ₹35,000 — RECOVERED     [view]  │
│  ● Reminder sent — ₹12,400 — pending         [view]  │
│  ● Held for review — ₹1,20,000 — over ceiling[view]  │
│  ...                                                  │
└─────────────────────────────────────────────────────┘
```

- Four key numbers, always visible, no scrolling required
- "Held for review" is shown as a first-class number, not buried — it demonstrates the system knows its own limits, which is a trust signal for judges
- Activity feed is reverse-chronological, each row clickable

### 2.2 Event Detail / "Why" View

This is the single most important screen for judging credibility — it's where "trust us" becomes "here's exactly what happened."

```
┌─────────────────────────────────────────────────────┐
│  ← Back                                              │
│                                                       │
│  Event #1938 — Overdue Invoice — ₹35,000            │
│                                                       │
│  1. DETECTED                                         │
│     Invoice overdue by 9 days                        │
│     Classified as: OVERDUE_MID                       │
│                                                       │
│  2. DIAGNOSED (by AI)                                │
│     "Customer has a strong payment history — 14      │
│      successful past invoices, average 3 days to     │
│      pay. This looks like an oversight, not          │
│      unwillingness to pay."                           │
│     Recommended: SEND_REMINDER   Confidence: 0.88     │
│                                                       │
│  3. POLICY CHECK                                     │
│     ✓ APPROVED — under escalation frequency cap,     │
│       confidence above threshold                      │
│                                                       │
│  4. ACTION TAKEN                                     │
│     Reminder sent (simulated) — 2:14 PM               │
│                                                       │
│  5. OUTCOME                                          │
│     Invoice paid — 3:40 PM — RECOVERED               │
└─────────────────────────────────────────────────────┘
```

- Numbered stages map exactly to the architecture pipeline — a judge who read the architecture doc will recognize this immediately, which reinforces that the system does what the docs claim
- The AI's own words are shown verbatim (its `reasoning` field) — this is the most human-readable part of the whole product and should not be paraphrased away

### 2.3 "Held for Review" Queue

```
┌─────────────────────────────────────────────────────┐
│  Held for human review (3)                          │
│                                                       │
│  ₹1,20,000 — exceeds auto-retry ceiling      [view]  │
│  ₹8,200    — LLM confidence too low (0.41)   [view]  │
│  ₹45,000   — retry limit already reached     [view]  │
└─────────────────────────────────────────────────────┘
```

- Exists specifically to make the "bounded autonomy" architectural claim visible and concrete rather than something only described in a document

### 2.4 "Run Custos" Control (for demo purposes)

A single button that triggers a batch run over the loaded synthetic/test dataset, with a lightweight progress indicator (event count processed) so the video has something visually active to show rather than a static page.

```
┌─────────────────────────────────────────────────────┐
│              [ ▶ Run Custos ]                        │
│                                                       │
│   Processing event 14 / 24...                        │
└─────────────────────────────────────────────────────┘
```

## 3. Visual Style

- **Palette:** calm, financial-app-neutral — deep blue/slate for structure, a single accent (green) for recovered, muted amber (not alarm-red) for held-for-review, restrained red only for disputed/failed states that truly need attention
- **Typography:** one clean sans-serif, numeric figures given visual weight (larger, tabular figures) since the dollar/rupee amounts are the emotional core of the pitch
- **Density:** favor whitespace over cramming — a judge skimming for 2 minutes should never feel like they're parsing a spreadsheet
- **Motion:** minimal — a progress indicator during "Run Custos" is the only animation that earns its place; avoid decorative transitions that add build time without adding clarity

## 4. What NOT to Build (time-boxing the design effort)

- No user accounts / login flow — single simulated merchant, no auth needed for a hackathon demo
- No settings/configuration UI — policy thresholds live in a config file, not a settings screen
- No mobile-responsive polish — demo video will be recorded on desktop
- No custom charting library — simple numbers and a list are more credible than a half-finished chart

## 5. Accessibility Baseline (minimum, not exhaustive)

- Sufficient color contrast on all status indicators (don't rely on color alone — pair with text labels like "RECOVERED" / "HELD", not just colored dots)
- Logical heading structure so the page isn't a flat visual soup if read by assistive tech
