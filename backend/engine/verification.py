"""Independent simulated-provider verification for recovery actions."""
import datetime
import json
import uuid

from backend.engine.audit import log_audit_event
from backend.engine.memory import record_verified_recovery


def verify_pending_recoveries(db):
    """Refresh simulated provider state after execution, never infer it from action success."""
    rows = db.execute(
        """SELECT ar.*, rc.id AS case_id, rc.policy_version, e.status, e.amount, e.customer_ref, e.raw_payload
           FROM action_runs ar JOIN recovery_cases rc ON rc.id = ar.recovery_case_id
           JOIN events e ON e.id = ar.event_id
           WHERE ar.execution_status = 'SIMULATED_SUCCESS' AND rc.state = 'VERIFYING'"""
    ).fetchall()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    verified_count = 0
    for row in rows:
        raw = json.loads(row["raw_payload"] or "{}")
        # This is deliberately separate from execute_action. A seed or test provider response
        # must state whether the retry resulted in a captured payment.
        succeeded = raw.get("simulated_retry_outcome") == "CAPTURED"
        provider_status = "CAPTURED" if succeeded else "FAILED"
        verified_amount = row["amount"] if succeeded else 0
        db.execute(
            """INSERT INTO verification_results
               (id, recovery_case_id, action_run_id, provider_status, verified, verified_amount, verification_mode, checked_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(uuid.uuid4()), row["case_id"], row["id"], provider_status, int(succeeded),
             verified_amount, "CUSTOS_SIMULATOR", now),
        )
        if succeeded:
            db.execute("UPDATE events SET status = 'recovered' WHERE id = ?", (row["event_id"],))
            db.execute(
                """UPDATE recovery_cases SET state = 'SETTLEMENT_PENDING',
                   verified_recovered_amount = ?, updated_at = ? WHERE id = ?""",
                (verified_amount, now, row["case_id"]),
            )
            record_verified_recovery(
                db, case_id=row["case_id"], customer_id=row["customer_ref"],
                action_type=row["action_type"], amount=verified_amount,
                policy_version=row["policy_version"],
            )
            log_audit_event(db, row["event_id"], "verification", "CUSTOS SIMULATOR — independently verified recovery success")
            verified_count += 1
        else:
            db.execute("UPDATE recovery_cases SET state = 'RECOVERY_FAILED', updated_at = ? WHERE id = ?", (now, row["case_id"]))
            log_audit_event(db, row["event_id"], "verification", "CUSTOS SIMULATOR — recovery verification failed; revenue remains at risk")
    return verified_count
