import os
import uuid
import datetime
import json
import sqlite3
import razorpay
from database import get_db, init_db

def ingest_live_events():
    # Load env
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    try:
        with open(env_path) as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    os.environ.setdefault(k, v)
    except FileNotFoundError:
        pass
        
    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    
    if not key_id or not key_secret:
        print("No Razorpay keys found in .env")
        return
        
    client = razorpay.Client(auth=(key_id, key_secret))
    try:
        payments = client.payment.all()
    except Exception as e:
        print(f"Failed to fetch from Razorpay: {e}")
        return
        
    items = payments.get("items", [])
    print(f"Found {len(items)} live payments from Razorpay.")
    
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    with get_db() as db:
        for p in items:
            source_id = p["id"]
            amount = p["amount"]
            status = p["status"]
            method = p.get("method", "unknown")
            customer_ref = p.get("email", "unknown@example.com")
            
            # Map razorpay status to our internal states if needed
            event_type = "payment"
            
            payload = {
                "method": method,
                "email": customer_ref,
                "category": "Live Transaction",
                "attempts": 1,
                "international": p.get("international", False)
            }
            
            if status == "failed":
                payload["error_code"] = p.get("error_code") or "GATEWAY_ERROR"
                payload["error_reason"] = p.get("error_reason") or "payment_failed"
                payload["error_step"] = p.get("error_step") or "authentication"
                payload["error_description"] = p.get("error_description") or "Live transaction failed"
                
            if method == "card" and "card" in p:
                c = p["card"]
                payload["card"] = {
                    "name": c.get("name") or customer_ref.split("@")[0].title(),
                    "network": c.get("network", "Unknown"),
                    "type": c.get("type", "Unknown"),
                    "sub_type": c.get("sub_type", "Unknown"),
                    "last4": c.get("last4", "****"),
                    "international": c.get("international", False)
                }
                
            event_id = str(uuid.uuid4())
            try:
                db.execute(
                    "INSERT INTO events (id, source_id, type, amount, status, customer_ref, raw_payload, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (event_id, source_id, event_type, amount, status, customer_ref, json.dumps(payload), now)
                )
                db.execute(
                    "INSERT INTO audit_log (event_id, stage, detail, timestamp) VALUES (?, ?, ?, ?)",
                    (event_id, "ingestion", f"Live Razorpay Sync {source_id}", now)
                )
                print(f"Ingested live event: {source_id}")
            except sqlite3.IntegrityError:
                # Already exists
                pass

if __name__ == "__main__":
    init_db()
    ingest_live_events()
