"""Stage 2: Growth Opportunity — 4-lever rule-based engine. No LLM needed."""
import os, sys, json, uuid, datetime, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database import get_db, init_db


def _get_order_count(customer_ref, db):
    """Count total events for this customer."""
    if not customer_ref:
        return 0
    row = db.execute("SELECT COUNT(*) as cnt FROM events WHERE customer_ref = ?", (customer_ref,)).fetchone()
    return row["cnt"] if row else 0


def identify_growth(event, raw, db):
    """Run 4-lever growth opportunity analysis. Returns dict."""
    t0 = time.time()
    opportunities = []
    amount = event["amount"] / 100.0
    method = raw.get("method", "")
    status = event["status"].lower()
    customer_ref = event["customer_ref"] or raw.get("email", "")

    # Growth is for credible successful/returning customer behaviour, not failed payments.
    if status not in ("captured", "paid", "recovered"):
        duration_ms = int((time.time() - t0) * 1000)
        return {
            "has_opportunity": False,
            "opportunities": [],
            "best_offer": None,
            "reasoning": "No completed purchase evidence is available for a credible growth recommendation",
            "probability": 0.0,
            "potential_value": 0,
            "duration_ms": duration_ms,
        }

    # Lever 1: Upsell/cross-sell for completed purchases.
    order_count = _get_order_count(customer_ref, db)
    if order_count >= 3:
        discount_pct = min(15, 5 * (order_count // 3))
        opportunities.append({
            "type": "loyalty_discount",
            "offer": "Premium bundle cross-sell",
            "reason": f"Repeat customer — {order_count} completed purchase signals support a credible cross-sell.",
            "impact": "high",
        })
    elif order_count >= 1:
        opportunities.append({
            "type": "repeat_purchase",
            "offer": "Repeat-purchase offer",
            "reason": f"Returning customer — {order_count} prior purchase signal(s).",
            "impact": "low",
        })

    # Lever 2: Premium option for high-value purchases.
    if amount >= 3000:
        opportunities.append({
            "type": "upsell",
            "offer": "Premium bundle recommendation",
            "reason": f"High-value completed purchase (₹{amount:,.0f}) supports an upsell recommendation",
            "impact": "medium",
        })

    # Sort by impact
    impact_order = {"high": 0, "medium": 1, "low": 2}
    opportunities.sort(key=lambda x: impact_order.get(x.get("impact", "low"), 2))


    has_opp = len(opportunities) > 0
    best = opportunities[0] if has_opp else None
    probability = 0.88 if order_count >= 3 else 0.68 if order_count >= 1 else 0.52 if amount >= 3000 else 0.0
    potential_value = round(event["amount"] * (0.12 if has_opp else 0))
    duration_ms = int((time.time() - t0) * 1000)

    return {
        "has_opportunity": has_opp,
        "opportunities": opportunities,
        "best_offer": best,
        "reasoning": best["reason"] if has_opp else "No specific growth lever for this event type",
        "probability": probability,
        "potential_value": potential_value,
        "duration_ms": duration_ms,
    }


def process_growth():
    init_db()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with get_db() as db:
        rows = db.execute("SELECT * FROM events").fetchall()
        for e in rows:
            raw = json.loads(e["raw_payload"])
            result = identify_growth(e, raw, db)
            db.execute(
                "INSERT OR REPLACE INTO growth_opportunities (id, event_id, has_opportunity, opportunities, best_offer, reasoning, identified_at, probability, potential_value) VALUES (?,?,?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), e["id"], result["has_opportunity"],
                 json.dumps(result["opportunities"]), json.dumps(result["best_offer"]),
                 result["reasoning"], now, result["probability"], result["potential_value"])
            )
    print(f"Growth analyzed {len(rows)} events.")


if __name__ == "__main__":
    process_growth()
