import datetime

def log_audit_event(db, event_id, stage, detail):
    """Centralized audit logging for the OS."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    db.execute(
        "INSERT INTO audit_log (event_id, stage, detail, timestamp) VALUES (?, ?, ?, ?)",
        (event_id, stage, detail, now)
    )
