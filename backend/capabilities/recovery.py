"""
Capability 3: Recovery. 
Orchestrates Classification -> Reasoning -> Policy -> Action using shared engines.
"""
import os, sys, json, uuid, datetime, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database import get_db, init_db
from engine.audit import log_audit_event
from engine.reasoning import call_llm
from engine.policy import evaluate_policy
from engine.actions import execute_action

def classify_event(event, raw):
    category = "HEALTHY"
    
    if event["type"] == "payment" and event["status"] == "failed":
        attempts = raw.get("attempts", 1)
        if attempts < 3:
            category = "AT_RISK_RETRIABLE"
        else:
            category = "AT_RISK_EXHAUSTED"
            
    elif event["type"] == "invoice" and event["status"] == "unpaid":
        due = raw.get("due_date")
        if due:
            try:
                due_dt = datetime.datetime.fromisoformat(due.replace("Z", "+00:00"))
                days = (datetime.datetime.now(datetime.timezone.utc) - due_dt).days
                if days <= 7: category = "OVERDUE_EARLY"
                elif days <= 30: category = "OVERDUE_MID"
                else: category = "OVERDUE_LATE"
            except:
                category = "OVERDUE_UNKNOWN"
                
    elif event["status"] == "disputed":
        category = "DISPUTED"
        
    return category

def process_recovery():
    init_db()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with get_db() as db:
        # Step 1: Classify unclassified events
        unclassified = db.execute("SELECT * FROM events WHERE id NOT IN (SELECT event_id FROM classifications)").fetchall()
        for e in unclassified:
            raw = json.loads(e["raw_payload"])
            category = classify_event(e, raw)
            db.execute("INSERT INTO classifications (event_id, category, classified_at) VALUES (?, ?, ?)", (e["id"], category, now))
            log_audit_event(db, e["id"], "classification", f"Classified as {category}")
            
        # Step 2: Reasoning for at-risk events
        query = """
        SELECT c.event_id, c.category, e.amount, e.type, e.status, e.raw_payload
        FROM classifications c
        JOIN events e ON c.event_id = e.id
        WHERE c.category != 'HEALTHY' 
        AND c.event_id NOT IN (SELECT event_id FROM llm_decisions)
        """
        needs_reasoning = db.execute(query).fetchall()
        for e in needs_reasoning:
            raw = json.loads(e["raw_payload"])
            structured_input = {
                "event_id": e["event_id"],
                "category": e["category"],
                "amount": e["amount"],
                "currency": raw.get("currency", "INR"),
                "event_detail": {
                    "status": e["status"],
                    "failure_reason": raw.get("error_reason") or raw.get("error_description") or raw.get("error"),
                    "attempts_so_far": raw.get("attempts", 1)
                }
            }
            decision = call_llm(structured_input)
            db.execute(
                "INSERT INTO llm_decisions (event_id, diagnosis, recommended_action, confidence, reasoning, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (e["event_id"], decision["diagnosis"], decision.get("recommended_action", "FLAG_FOR_HUMAN_REVIEW"), decision.get("confidence", 0.0), decision.get("reasoning", ""), now)
            )
            log_audit_event(db, e["event_id"], "llm_reasoning", f"Recommended: {decision.get('recommended_action')}")
            
        # Step 3: Policy gating
        query = """
        SELECT l.event_id, l.recommended_action, l.confidence, e.amount, e.status
        FROM llm_decisions l
        JOIN events e ON l.event_id = e.id
        WHERE l.event_id NOT IN (SELECT event_id FROM policy_checks)
        """
        needs_policy = db.execute(query).fetchall()
        for p in needs_policy:
            decision, reason = evaluate_policy(p["recommended_action"], p["amount"], p["status"], p["confidence"])
            db.execute("INSERT INTO policy_checks (event_id, decision, reason, checked_at) VALUES (?, ?, ?, ?)", (p["event_id"], decision, reason, now))
            log_audit_event(db, p["event_id"], "policy", f"{decision}: {reason}")
            
        # Step 4: Action execution
        query = """
        SELECT p.event_id, l.recommended_action
        FROM policy_checks p
        JOIN llm_decisions l ON p.event_id = l.event_id
        WHERE p.decision = 'APPROVED'
        AND p.event_id NOT IN (SELECT event_id FROM actions)
        """
        needs_action = db.execute(query).fetchall()
        for a in needs_action:
            action_type = a["recommended_action"]
            result = execute_action(action_type)
            db.execute("INSERT INTO actions (event_id, action_type, executed_at, result) VALUES (?, ?, ?, ?)", (a["event_id"], action_type, now, result))
            log_audit_event(db, a["event_id"], "action", f"Executed: {action_type} -> {result}")

    print(f"Recovery capability processed.")

if __name__ == "__main__":
    process_recovery()
