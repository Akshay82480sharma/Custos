"""Bounded, provenance-aware operational memory for CUSTOS."""
import datetime
import json
import uuid


def record_verified_recovery(db, *, case_id, customer_id, action_type, amount, policy_version):
    """Persist only verified outcomes; recommendations never become facts."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    db.execute(
        """INSERT INTO recovery_memory
           (memory_id, case_id, customer_id, action_type, outcome, amount, time_to_recovery, policy_version, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), case_id, customer_id, action_type, "VERIFIED_RECOVERED", amount, None, policy_version, now),
    )
    db.execute(
        """INSERT INTO customer_memory
           (memory_id, customer_id, type, key, value, confidence, source, created_at, updated_at, expires_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), customer_id or "unknown", "OUTCOME", "verified_recovery",
         json.dumps({"amount": amount, "case_id": case_id}), 1.0, "verified_action", now, now, None),
    )


def recent_verified_outcomes(db, customer_id, limit=5):
    """Retrieve only timestamped outcomes for bounded reasoning context."""
    return db.execute(
        """SELECT action_type, outcome, amount, created_at FROM recovery_memory
           WHERE customer_id = ? ORDER BY created_at DESC LIMIT ?""",
        (customer_id, limit),
    ).fetchall()
