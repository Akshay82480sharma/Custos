"""Stage 8: Finance Reconciliation — Razorpay fee-aware engine. No LLM needed."""
import os, sys, json, uuid, datetime, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database import get_db, init_db

# Razorpay fee structure (simplified)
RAZORPAY_FEES = {
    "upi":          {"rate": 0.02, "settle_days": 2, "label": "2%"},
    "card":         {"rate": 0.025, "settle_days": 3, "label": "2.5%"},
    "netbanking":   {"rate": 0.025, "settle_days": 3, "label": "2.5%"},
    "wallet":       {"rate": 0.02, "settle_days": 2, "label": "2%"},
    "bank_transfer":{"rate": 0.02, "settle_days": 3, "label": "2%"},
    "emi":          {"rate": 0.02, "settle_days": 3, "label": "2%"},
}
DEFAULT_FEE = {"rate": 0.023, "settle_days": 3, "label": "2.3%"}


def reconcile_event(event, raw, db):
    """Run finance reconciliation on a single event. Returns dict."""
    t0 = time.time()
    status = event["status"].lower()
    amount = event["amount"] / 100.0
    method = raw.get("method", "upi").lower()

    fee_info = RAZORPAY_FEES.get(method, DEFAULT_FEE)
    fee_rate = fee_info["rate"]
    settle_days = fee_info["settle_days"]
    fee_label = fee_info["label"]

    if status in ("captured", "paid", "recovered"):
        fee = round(amount * fee_rate, 2)
        net = round(amount - fee, 2)
        result = {
            "reconciliation_status": "PENDING_SETTLEMENT",
            "expected_settlement": net,
            "fee_deducted": fee,
            "fee_rate": fee_label,
            "settlement_date": f"T+{settle_days}",
            "reasoning": f"₹{net:,.2f} expected in settlement after {fee_label} Razorpay fee ({method}, T+{settle_days})",
        }

    elif status == "failed":
        # Check if there's a recovery action
        action = db.execute("SELECT result FROM actions WHERE event_id = ?", (event["id"],)).fetchone()
        if action and "SUCCESS" in (action["result"] or "").upper():
            fee = round(amount * fee_rate, 2)
            net = round(amount - fee, 2)
            result = {
                "reconciliation_status": "RECOVERY_PENDING_SETTLEMENT",
                "expected_settlement": net,
                "fee_deducted": fee,
                "fee_rate": fee_label,
                "settlement_date": f"T+{settle_days} (from recovery)",
                "reasoning": f"Original failed. Recovery simulated — if successful, ₹{net:,.2f} will settle after {fee_label} fee",
            }
        else:
            result = {
                "reconciliation_status": "NO_SETTLEMENT",
                "expected_settlement": 0.0,
                "fee_deducted": 0.0,
                "fee_rate": "0%",
                "settlement_date": "N/A",
                "reasoning": "Payment failed — no settlement expected. If recovery succeeds, a new transaction will generate its own settlement.",
            }

    elif status == "disputed":
        result = {
            "reconciliation_status": "AMOUNT_HELD",
            "expected_settlement": 0.0,
            "fee_deducted": 0.0,
            "fee_rate": "TBD",
            "settlement_date": "Held until resolved",
            "reasoning": f"₹{amount:,.2f} held by Razorpay pending dispute resolution. If merchant wins: settles at T+{settle_days} minus fee. If lost: reversed to customer.",
        }

    elif status in ("unpaid", "overdue"):
        result = {
            "reconciliation_status": "ACCOUNTS_RECEIVABLE",
            "expected_settlement": 0.0,
            "fee_deducted": 0.0,
            "fee_rate": "N/A",
            "settlement_date": "Pending payment",
            "reasoning": f"₹{amount:,.2f} outstanding — no settlement until customer pays. If recovered via reminder, settlement follows normal T+{settle_days} timeline.",
        }

    else:
        result = {
            "reconciliation_status": "UNKNOWN",
            "expected_settlement": 0.0,
            "fee_deducted": 0.0,
            "fee_rate": "N/A",
            "settlement_date": "N/A",
            "reasoning": f"Cannot determine settlement for status '{status}'",
        }

    result["duration_ms"] = int((time.time() - t0) * 1000)
    return result


def reconcile_against_settlement(event, raw, db):
    """Reconcile payment state against an explicit settlement record.

    A fee estimate is not a settlement. Captured/recovered payments remain
    settlement-pending until a matching provider settlement is present.
    """
    status = event["status"].lower()
    settlement = db.execute("SELECT * FROM settlements WHERE reference = ?", (event["source_id"],)).fetchone()
    if status not in {"captured", "paid", "recovered"}:
        return {"reconciliation_status": "NO_SETTLEMENT", "expected_settlement": 0.0,
                "fee_deducted": 0.0, "fee_rate": "N/A", "settlement_date": "N/A",
                "reasoning": "No captured payment exists; settlement is not expected."}
    if not settlement:
        return {"reconciliation_status": "SETTLEMENT_PENDING", "expected_settlement": 0.0,
                "fee_deducted": 0.0, "fee_rate": "N/A", "settlement_date": "Awaiting provider settlement record",
                "reasoning": "Payment is captured/recovered but no settlement record has been verified."}
    gross, net = settlement["gross_amount"], settlement["net_amount"]
    if gross != event["amount"]:
        return {"reconciliation_status": "EXCEPTION", "expected_settlement": net / 100.0,
                "fee_deducted": (gross - net) / 100.0, "fee_rate": "Provider record",
                "settlement_date": settlement["settled_at"] or "Provider settlement pending",
                "reasoning": f"Payment and settlement differ by ₹{abs(event['amount'] - gross) / 100:,.2f}; investigation required."}
    if settlement["status"] != "SETTLED":
        return {"reconciliation_status": "SETTLEMENT_PENDING", "expected_settlement": net / 100.0,
                "fee_deducted": (gross - net) / 100.0, "fee_rate": "Provider record",
                "settlement_date": "Provider settlement pending",
                "reasoning": "Settlement record exists but is not yet confirmed settled."}
    return {"reconciliation_status": "MATCHED", "expected_settlement": net / 100.0,
            "fee_deducted": (gross - net) / 100.0, "fee_rate": "Provider record",
            "settlement_date": settlement["settled_at"],
            "reasoning": "Payment reference and gross amount match the verified settlement record."}


def process_finance():
    init_db()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with get_db() as db:
        rows = db.execute("SELECT * FROM events").fetchall()
        for e in rows:
            raw = json.loads(e["raw_payload"])
            result = reconcile_against_settlement(e, raw, db)
            db.execute(
                "INSERT OR REPLACE INTO finance_reconciliations (id, event_id, expected_settlement, fee_deducted, fee_rate, settlement_date, reconciliation_status, reasoning, reconciled_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), e["id"], result["expected_settlement"], result["fee_deducted"],
                 result["fee_rate"], result["settlement_date"], result["reconciliation_status"],
                 result["reasoning"], now)
            )
            if result["reconciliation_status"] == "MATCHED":
                db.execute(
                    "UPDATE recovery_cases SET state = 'SETTLED', updated_at = ? WHERE event_id = ? AND state = 'SETTLEMENT_PENDING'",
                    (now, e["id"]),
                )
    print(f"Finance reconciled {len(rows)} events.")


if __name__ == "__main__":
    process_finance()
