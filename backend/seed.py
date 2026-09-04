import sqlite3
import json
import uuid
import datetime
from database import get_db, init_db

events = [
    {"source_id": "pay_7f2a3b1c", "amount": 499,    "status": "failed",    "method": "card",    "customer": "raj@example.com"},
    {"source_id": "pay_3b1c9d4e", "amount": 1299,   "status": "captured",  "method": "upi",     "customer": "priya@example.com"},
    {"source_id": "pay_9d4e1a8f", "amount": 79900,  "status": "failed",    "method": "card",    "customer": "amit@corp.com"},
    {"source_id": "pay_1a8f5c2d", "amount": 2499,   "status": "disputed",  "method": "netbanking","customer": "neha@example.com"},
    {"source_id": "pay_5c2d7e3f", "amount": 899,    "status": "failed",    "method": "card",    "customer": "vikram@example.com"},
    {"source_id": "pay_8e3f2a1b", "amount": 45000,  "status": "captured",  "method": "upi",     "customer": "sunita@example.com"},
    {"source_id": "pay_2a1b4c5d", "amount": 1599,   "status": "failed",    "method": "card",    "customer": "arjun@example.com"},
    {"source_id": "pay_4c5d6e7f", "amount": 32900,  "status": "unpaid",    "method": None,       "customer": "meera@example.com"},
    {"source_id": "pay_6e7f8a9b", "amount": 699,    "status": "captured",  "method": "upi",     "customer": "raj@example.com"},
    {"source_id": "pay_0a9b1c2d", "amount": 45000,  "status": "failed",    "method": "card",    "customer": "kiran@startup.io"},
    {"source_id": "pay_1c2d3e4f", "amount": 299,    "status": "captured",  "method": "wallet",  "customer": "divya@example.com"},
    {"source_id": "pay_3e4f5a6b", "amount": 24999,  "status": "disputed",  "method": "netbanking","customer": "rohan@example.com"},
    {"source_id": "pay_5a6b7c8d", "amount": 1799,   "status": "failed",    "method": "card",    "customer": "ananya@example.com"},
    {"source_id": "pay_7c8d9e0f", "amount": 79900,  "status": "failed",    "method": "card",    "customer": "tech@corp.com"},
    {"source_id": "pay_9e0f1a2b", "amount": 599,    "status": "captured",  "method": "upi",     "customer": "priya@example.com"},
    {"source_id": "pay_0f1a2b3c", "amount": 45000,  "status": "failed",    "method": "card",    "customer": "suresh@example.com"},
]

def reset_and_seed():
    init_db()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with get_db() as db:
        # Clear tables
        db.execute("DELETE FROM events")
        db.execute("DELETE FROM classifications")
        db.execute("DELETE FROM llm_decisions")
        db.execute("DELETE FROM policy_checks")
        db.execute("DELETE FROM actions")
        db.execute("DELETE FROM audit_log")
        db.execute("DELETE FROM risk_assessments")
        db.execute("DELETE FROM growth_opportunities")
        db.execute("DELETE FROM finance_reconciliations")
        
        for e in events:
            # Need amounts in paise/cents because the UI divides by 100
            amt_cents = e["amount"] * 100
            event_type = "payment"
            if e["status"] == "unpaid": event_type = "invoice"
            if e["status"] == "disputed": event_type = "order"
            
            payload = {
                "method": e["method"],
                "email": e["customer"],
                "attempts": 1,
                "international": True if "79900" in str(amt_cents) else False,
                "failure_is_retryable": e["status"] == "failed",
                "simulated_retry_outcome": "CAPTURED" if e["source_id"] in {"pay_7f2a3b1c", "pay_5c2d7e3f"} else "FAILED",
            }
            if e["status"] == "unpaid":
                payload["due_date"] = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=15)).isoformat()
                
            db.execute(
                "INSERT INTO events (id, source_id, type, amount, status, customer_ref, raw_payload, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), e["source_id"], event_type, amt_cents, e["status"], e["customer"], json.dumps(payload), now)
            )

        # Explicit settlement records: one exact match and one amount mismatch.
        db.execute("INSERT OR REPLACE INTO settlements (id, reference, gross_amount, net_amount, status, settled_at) VALUES (?, ?, ?, ?, ?, ?)",
                   (str(uuid.uuid4()), "pay_3b1c9d4e", 129900, 126652, "SETTLED", now))
        db.execute("INSERT OR REPLACE INTO settlements (id, reference, gross_amount, net_amount, status, settled_at) VALUES (?, ?, ?, ?, ?, ?)",
                   (str(uuid.uuid4()), "pay_8e3f2a1b", 4400000, 4312000, "SETTLED", now))
            
reset_and_seed()
print("Database seeded with realistic test data.")
