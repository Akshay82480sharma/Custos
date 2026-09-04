"""Recovery orchestration with explicit states, policy, idempotency, and verification."""
import datetime
import json
import os
import sys
import uuid

# Supports both ``python -m`` and the existing pipeline's script execution.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.database import get_db, init_db
from backend.engine.actions import execute_action
from backend.engine.audit import log_audit_event
from backend.engine.policy import DEFAULT_RETRY_LIMIT, POLICY_VERSION, evaluate_recovery_policy
from backend.engine.reasoning import call_llm
from backend.engine.verification import verify_pending_recoveries
from backend.capabilities.recovery import classify_event


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _ensure_classification(db, event, raw, now):
    row = db.execute("SELECT category FROM classifications WHERE event_id = ?", (event["id"],)).fetchone()
    if row:
        return row["category"]
    category = classify_event(event, raw)
    db.execute("INSERT INTO classifications (event_id, category, classified_at) VALUES (?, ?, ?)", (event["id"], category, now))
    log_audit_event(db, event["id"], "classification", f"Classified as {category}")
    return category


def _decision(db, event, category, raw, now):
    row = db.execute("SELECT * FROM llm_decisions WHERE event_id = ?", (event["id"],)).fetchone()
    if row:
        return row
    result = call_llm({
        "event_id": event["id"], "category": category, "amount": event["amount"],
        "event_detail": {"status": event["status"], "attempts_so_far": raw.get("attempts", 1)},
    })
    db.execute(
        """INSERT INTO llm_decisions (event_id, diagnosis, recommended_action, confidence, reasoning, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (event["id"], result["diagnosis"], result["recommended_action"], result["confidence"], result["reasoning"], now),
    )
    log_audit_event(db, event["id"], "reasoning", f"Evidence-bounded recommendation: {result['recommended_action']}")
    return db.execute("SELECT * FROM llm_decisions WHERE event_id = ?", (event["id"],)).fetchone()


def _create_case(db, event, raw, now):
    existing = db.execute("SELECT * FROM recovery_cases WHERE event_id = ?", (event["id"],)).fetchone()
    if existing:
        return existing
    retry_count = int(raw.get("attempts", 1)) - 1
    probability = 0.78 if raw.get("failure_is_retryable", True) else 0.20
    db.execute(
        """INSERT INTO recovery_cases
           (id, event_id, state, amount_at_risk, retry_count, retry_limit, recovery_probability,
            expected_recovery_amount, policy_version, created_at, updated_at)
           VALUES (?, ?, 'AT_RISK', ?, ?, ?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), event["id"], event["amount"], retry_count, DEFAULT_RETRY_LIMIT, probability,
         round(event["amount"] * probability), POLICY_VERSION, now, now),
    )
    log_audit_event(db, event["id"], "recovery_state", "AT_RISK — failed or unpaid revenue detected")
    return db.execute("SELECT * FROM recovery_cases WHERE event_id = ?", (event["id"],)).fetchone()


def _execute_auto_action(db, *, event, case, decision, policy, now):
    idempotency_key = f"{event['id']}:{case['retry_count'] + 1}:{decision['recommended_action']}"
    action_id = str(uuid.uuid4())
    result = execute_action(decision["recommended_action"])
    execution_status = "SIMULATED_SUCCESS" if "SIMULATED_SUCCESS" in result else "SIMULATED_FAILED"
    db.execute(
        """INSERT INTO action_runs
           (id, event_id, recovery_case_id, idempotency_key, action_type, authorization,
            execution_status, execution_detail, simulated, executed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)""",
        (action_id, event["id"], case["id"], idempotency_key, decision["recommended_action"],
         policy.decision, execution_status, result, now),
    )
    # Legacy table remains populated for current dashboard compatibility.
    db.execute("INSERT OR REPLACE INTO actions (event_id, action_type, executed_at, result) VALUES (?, ?, ?, ?)",
               (event["id"], decision["recommended_action"], now, f"CUSTOS SIMULATOR — {result}"))
    db.execute("UPDATE recovery_cases SET state = 'VERIFYING', updated_at = ? WHERE id = ?", (now, case["id"]))
    log_audit_event(db, event["id"], "action", f"CUSTOS SIMULATOR — {decision['recommended_action']} executed; verification pending")


def process_recovery_workflow():
    """Run detect → evidence/reasoning → policy → action → independent verification."""
    init_db()
    processed = 0
    with get_db() as db:
        now = _now()
        events = db.execute("SELECT * FROM events WHERE status IN ('failed', 'unpaid')").fetchall()
        for event in events:
            raw = json.loads(event["raw_payload"] or "{}")
            category = _ensure_classification(db, event, raw, now)
            decision = _decision(db, event, category, raw, now)
            case = _create_case(db, event, raw, now)
            if case["state"] not in {"AT_RISK", "RECOVERY_PENDING"}:
                continue
            risk = db.execute("SELECT risk_score FROM risk_assessments WHERE event_id = ?", (event["id"],)).fetchone()
            duplicate = db.execute("SELECT 1 FROM action_runs WHERE recovery_case_id = ?", (case["id"],)).fetchone() is not None
            policy = evaluate_recovery_policy(
                action=decision["recommended_action"], amount=event["amount"], payment_status=event["status"],
                failure_is_retryable=raw.get("failure_is_retryable", event["status"] == "failed"),
                retry_count=case["retry_count"], retry_limit=case["retry_limit"],
                risk_score=risk["risk_score"] if risk else None, duplicate_action_exists=duplicate,
            )
            db.execute(
                """INSERT OR REPLACE INTO policy_checks
                   (event_id, decision, reason, checked_at, policy_version, authorization)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (event["id"], policy.decision, policy.reason, now, policy.version, policy.decision),
            )
            log_audit_event(db, event["id"], "policy", f"{policy.decision}: {policy.reason}")
            if policy.decision == "AUTO_EXECUTE":
                _execute_auto_action(db, event=event, case=case, decision=decision, policy=policy, now=now)
            elif policy.decision == "APPROVAL_REQUIRED":
                db.execute("UPDATE recovery_cases SET state = 'RECOVERY_PENDING', updated_at = ? WHERE id = ?", (now, case["id"]))
            processed += 1
        verified = verify_pending_recoveries(db)
    return {"processed": processed, "verified": verified}


if __name__ == "__main__":
    print(process_recovery_workflow())
