"""Stage 1: Risk Assessment — 5-signal rule-based engine. No LLM needed."""
import os, sys, json, uuid, datetime, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database import get_db, init_db
from engine.audit import log_audit_event


def _get_customer_age(customer_ref, db):
    """How many days since this customer's first event?"""
    if not customer_ref or customer_ref == "unknown":
        return None
    row = db.execute(
        "SELECT MIN(created_at) as first_seen FROM events WHERE customer_ref = ?",
        (customer_ref,)
    ).fetchone()
    if row and row["first_seen"]:
        try:
            first = datetime.datetime.fromisoformat(row["first_seen"].replace("Z", "+00:00"))
            now = datetime.datetime.now(datetime.timezone.utc)
            return max(0, (now - first).days)
        except Exception:
            return None
    return None


def _count_recent_failures(customer_ref, db, hours=24):
    """Count failed events from this customer in the last N hours."""
    if not customer_ref:
        return 0
    cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours)).isoformat()
    row = db.execute(
        "SELECT COUNT(*) as cnt FROM events WHERE customer_ref = ? AND status = 'failed' AND created_at >= ?",
        (customer_ref, cutoff),
    ).fetchone()
    return row["cnt"] if row else 0


def _count_disputes(customer_ref, db):
    """Count disputed events from this customer."""
    if not customer_ref:
        return 0
    row = db.execute(
        "SELECT COUNT(*) as cnt FROM events WHERE customer_ref = ? AND status = 'disputed'",
        (customer_ref,)
    ).fetchone()
    return row["cnt"] if row else 0


def assess_risk(event, raw, db):
    """Run 5-signal risk assessment on a single event. Returns dict."""
    t0 = time.time()
    signals = []
    risk_score = 0.0
    amount = event["amount"] / 100.0  # paise to INR
    customer_ref = event["customer_ref"] or raw.get("email", "")

    # Signal 1: Amount threshold
    if amount >= 50000:
        signals.append({"signal": "High value transaction", "risk": 0.3, "detail": f"₹{amount:,.0f} exceeds ₹50,000 threshold"})
        risk_score += 0.3
    elif amount >= 10000:
        signals.append({"signal": "Medium-high value", "risk": 0.15, "detail": f"₹{amount:,.0f}"})
        risk_score += 0.15
    else:
        signals.append({"signal": "Normal value", "risk": 0.0, "detail": f"₹{amount:,.0f}"})

    # Signal 2: Customer age
    age_days = _get_customer_age(customer_ref, db)
    if age_days is not None:
        if age_days < 7:
            signals.append({"signal": "New customer", "risk": 0.25, "detail": f"Account is {age_days} days old"})
            risk_score += 0.25
        elif age_days < 30:
            signals.append({"signal": "Recent customer", "risk": 0.1, "detail": f"Account is {age_days} days old"})
            risk_score += 0.1
        else:
            signals.append({"signal": "Established customer", "risk": 0.0, "detail": f"Account is {age_days} days old"})
    else:
        signals.append({"signal": "Unknown customer age", "risk": 0.1, "detail": "Cannot determine account age"})
        risk_score += 0.1

    # Signal 3: Repeat failures
    recent_failures = _count_recent_failures(customer_ref, db)
    if recent_failures >= 5:
        signals.append({"signal": "High failure frequency", "risk": 0.35, "detail": f"{recent_failures} failures on record"})
        risk_score += 0.35
    elif recent_failures >= 3:
        signals.append({"signal": "Elevated failure frequency", "risk": 0.2, "detail": f"{recent_failures} failures on record"})
        risk_score += 0.2
    else:
        signals.append({"signal": "Normal failure rate", "risk": 0.0, "detail": f"{recent_failures} failure(s) on record"})

    # Signal 4: Dispute history
    dispute_count = _count_disputes(customer_ref, db)
    if dispute_count >= 2:
        signals.append({"signal": "Repeat disputer", "risk": 0.3, "detail": f"{dispute_count} prior disputes"})
        risk_score += 0.3
    elif dispute_count == 1:
        signals.append({"signal": "Prior dispute", "risk": 0.15, "detail": "1 prior dispute"})
        risk_score += 0.15
    else:
        signals.append({"signal": "No dispute history", "risk": 0.0, "detail": "Clean record"})

    # Signal 5: International transaction
    is_international = raw.get("international", False)
    if is_international:
        signals.append({"signal": "International transaction", "risk": 0.2, "detail": "Cross-border payment detected"})
        risk_score += 0.2
    else:
        signals.append({"signal": "Domestic transaction", "risk": 0.0, "detail": "Local payment"})

    # Cap at 1.0
    risk_score = min(risk_score, 1.0)
    score_100 = round(risk_score * 100)
    risk_level = "LOW" if score_100 < 40 else "MEDIUM" if score_100 < 70 else "HIGH" if score_100 < 90 else "CRITICAL"
    is_safe = risk_score < 0.5
    verdict = "SAFE_TO_PROCEED" if is_safe else "FLAG_FOR_REVIEW"
    duration_ms = int((time.time() - t0) * 1000)

    return {
        "risk_score": round(risk_score, 2),
        "risk_level": risk_level,
        "is_safe": is_safe,
        "verdict": verdict,
        "signals": signals,
        "reasoning": f"Risk score {risk_score:.2f}/1.00 — {'within threshold, safe to proceed' if is_safe else 'exceeds 0.5 threshold, manual review recommended'}",
        "duration_ms": duration_ms,
    }


def process_risk():
    init_db()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with get_db() as db:
        rows = db.execute("SELECT * FROM events").fetchall()
        for e in rows:
            raw = json.loads(e["raw_payload"])
            result = assess_risk(e, raw, db)
            db.execute(
                "INSERT OR REPLACE INTO risk_assessments (id, event_id, risk_score, is_safe, verdict, signals, reasoning, assessed_at, risk_level) VALUES (?,?,?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), e["id"], result["risk_score"], result["is_safe"], result["verdict"],
                 json.dumps(result["signals"]), result["reasoning"], now, result["risk_level"])
            )
            db.execute(
                "INSERT INTO audit_log (event_id, stage, detail, timestamp) VALUES (?,?,?,?)",
                (e["id"], "risk", f"{result['verdict']} (score={result['risk_score']})", now)
            )
    print(f"Risk assessed {len(rows)} events.")


if __name__ == "__main__":
    process_risk()
