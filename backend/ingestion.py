import sqlite3
import json
import uuid
import datetime
from database import get_db, init_db

events_seed = [
    {"source_id": "pay_7f2a3b1c", "amount": 499,    "status": "failed",    "method": "card",    "customer": "raj@example.com"},
    {"source_id": "pay_3b1c9d4e", "amount": 1299,   "status": "captured",  "method": "upi",     "customer": "priya@example.com"},
    {"source_id": "pay_9d4e1a8f", "amount": 79900,  "status": "failed",    "method": "card",    "customer": "amit@corp.com"},
    {"source_id": "pay_1a8f5c2d", "amount": 2499,   "status": "disputed",  "method": "netbanking","customer": "neha@example.com"},
    {"source_id": "pay_5c2d7e3f", "amount": 899,    "status": "failed",    "method": "card",    "customer": "vikram@example.com"},
    {"source_id": "pay_8e3f2a1b", "amount": 45000,  "status": "captured",  "method": "upi",     "customer": "sunita@example.com"},
    {"source_id": "pay_2a1b4c5d", "amount": 1599,   "status": "failed",    "method": "card",    "customer": "arjun@example.com"},
    {"source_id": "pay_4c5d6e7f", "amount": 32900,  "status": "unpaid",    "method": "bank_transfer", "customer": "meera@example.com"},
    {"source_id": "pay_6e7f8a9b", "amount": 699,    "status": "captured",  "method": "upi",     "customer": "raj@example.com"},
    {"source_id": "pay_0a9b1c2d", "amount": 45000,  "status": "failed",    "method": "card",    "customer": "kiran@startup.io"},
    {"source_id": "pay_1c2d3e4f", "amount": 299,    "status": "captured",  "method": "wallet",  "customer": "divya@example.com"},
    {"source_id": "pay_3e4f5a6b", "amount": 24999,  "status": "disputed",  "method": "netbanking","customer": "rohan@example.com"},
    {"source_id": "pay_5a6b7c8d", "amount": 1799,   "status": "failed",    "method": "card",    "customer": "ananya@example.com"},
    {"source_id": "pay_7c8d9e0f", "amount": 79900,  "status": "failed",    "method": "card",    "customer": "tech@corp.com"},
    {"source_id": "pay_9e0f1a2b", "amount": 599,    "status": "captured",  "method": "upi",     "customer": "priya@example.com"},
    {"source_id": "pay_0f1a2b3c", "amount": 45000,  "status": "failed",    "method": "card",    "customer": "suresh@example.com"},
]

def ingest_event(source_id, event_type, amount, status, customer_ref, payload):
    event_id = str(uuid.uuid4())
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with get_db() as db:
        try:
            db.execute(
                "INSERT INTO events (id, source_id, type, amount, status, customer_ref, raw_payload, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (event_id, source_id, event_type, amount, status, customer_ref, json.dumps(payload), now)
            )
            db.execute(
                "INSERT INTO audit_log (event_id, stage, detail, timestamp) VALUES (?, ?, ?, ?)",
                (event_id, "ingestion", f"Ingested event {source_id}", now)
            )
        except sqlite3.IntegrityError:
            pass # idempotency handled by source_id UNIQUE constraint

def run_ingestion():
    init_db()
    for e in events_seed:
        amt_cents = e["amount"] * 100
        event_type = "payment"
        if e["status"] == "unpaid": event_type = "invoice"
        if e["status"] == "disputed": event_type = "order"
        
        payload = {
            "method": e["method"],
            "email": e["customer"],
            "category": "Electronics" if amt_cents > 500000 else "Subscription",
            "attempts": 1,
            "international": True if "79900" in str(amt_cents) else False,
            "failure_is_retryable": e["status"] == "failed",
            "simulated_retry_outcome": "CAPTURED" if e["source_id"] in {"pay_7f2a3b1c", "pay_5c2d7e3f"} else "FAILED",
        }
        
        if e["status"] == "failed":
            payload["error_code"] = "GATEWAY_ERROR" if e["method"] == "card" else "BAD_REQUEST_ERROR"
            payload["error_reason"] = "payment_failed"
            payload["error_step"] = "payment_authentication"
            payload["error_description"] = "The transaction could not be completed at the gateway"
            
        if e["method"] == "card":
            payload["card"] = {
                "name": e["customer"].split("@")[0].title(),
                "network": "Visa",
                "type": "credit",
                "sub_type": "consumer",
                "last4": "4242",
                "international": payload["international"]
            }
            
        if e["status"] == "unpaid":
            payload["due_date"] = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=15)).isoformat()
            
        ingest_event(
            source_id=e["source_id"],
            event_type=event_type,
            amount=amt_cents,
            status=e["status"],
            customer_ref=e["customer"],
            payload=payload
        )
    print("Ingested realistic seed data.")

if __name__ == "__main__":
    run_ingestion()
