"""Database read models for the dashboard."""
import json
from typing import Any
from backend.database import get_db

def _money(paise: int | None) -> float:
    return round((paise or 0) / 100, 2)

def _record(row: Any) -> dict[str, Any]:
    value = dict(row)
    value["amount_inr"] = _money(value.get("amount"))
    return value

def overview() -> dict[str, Any]:
    with get_db() as db:
        at_risk = db.execute("SELECT COALESCE(SUM(amount), 0) AS value FROM events WHERE status IN ('failed', 'unpaid')").fetchone()["value"]
        recovered = db.execute("SELECT COALESCE(SUM(amount), 0) AS value FROM events WHERE status = 'recovered'").fetchone()["value"]
        risk = db.execute("SELECT COALESCE(SUM(e.amount), 0) AS value FROM risk_assessments r JOIN events e ON e.id = r.event_id WHERE r.verdict = 'FLAG_FOR_REVIEW'").fetchone()["value"]
        finance = db.execute("SELECT COUNT(*) AS value FROM finance_reconciliations WHERE reconciliation_status IN ('NO_SETTLEMENT', 'AMOUNT_HELD', 'ACCOUNTS_RECEIVABLE', 'EXCEPTION')").fetchone()["value"]
        growth = db.execute("SELECT COALESCE(SUM(e.amount), 0) AS value FROM growth_opportunities g JOIN events e ON g.event_id = e.id WHERE g.has_opportunity = 1").fetchone()["value"]
        events = db.execute("""SELECT e.*, c.category, l.recommended_action, p.decision AS policy_decision
            FROM events e LEFT JOIN classifications c ON c.event_id = e.id
            LEFT JOIN llm_decisions l ON l.event_id = e.id LEFT JOIN policy_checks p ON p.event_id = e.id
            ORDER BY e.created_at DESC LIMIT 20""").fetchall()
    return {"metrics": {"revenue_at_risk": _money(at_risk), "verified_recovered": _money(recovered), "risk_exposure": _money(risk), "growth_potential": _money(growth), "finance_exceptions": finance}, "events": [_record(event) for event in events]}

def recovery_cases() -> list[dict[str, Any]]:
    with get_db() as db:
        rows = db.execute("""SELECT e.*, c.category, l.recommended_action, p.decision AS policy_decision, a.result AS action_result,
            'PENDING' AS recovery_state, e.amount AS amount_at_risk, e.amount AS expected_recovery_amount, 
            CASE WHEN e.status = 'recovered' THEN e.amount ELSE 0 END AS verified_recovered_amount
            FROM events e LEFT JOIN classifications c ON c.event_id = e.id LEFT JOIN llm_decisions l ON l.event_id = e.id
            LEFT JOIN policy_checks p ON p.event_id = e.id LEFT JOIN actions a ON a.event_id = e.id
            WHERE e.status IN ('failed', 'unpaid', 'recovered') ORDER BY e.created_at DESC""").fetchall()
    return [_record(row) for row in rows]

def risk_cases() -> list[dict[str, Any]]:
    with get_db() as db:
        rows = db.execute("SELECT e.*, r.risk_score, 'HIGH' as risk_level, r.verdict, r.signals, r.reasoning FROM risk_assessments r JOIN events e ON e.id = r.event_id ORDER BY r.risk_score DESC").fetchall()
    result = []
    for row in rows:
        item = _record(row); item["signals"] = json.loads(item["signals"] or "[]"); item["risk_score_display"] = round(float(item["risk_score"]) * 100); result.append(item)
    return result

def growth_cases() -> list[dict[str, Any]]:
    with get_db() as db:
        rows = db.execute("SELECT e.*, g.opportunities, g.best_offer, g.reasoning, g.probability as probability, g.potential_value as potential_value FROM growth_opportunities g JOIN events e ON e.id = g.event_id WHERE g.has_opportunity = 1 ORDER BY g.identified_at DESC").fetchall()
    result = []
    for row in rows:
        item = _record(row); item["opportunities"] = json.loads(item["opportunities"] or "[]"); item["best_offer"] = json.loads(item["best_offer"] or "null"); item["potential_value_inr"] = _money(item.get("potential_value")); result.append(item)
    return result

def finance_cases() -> list[dict[str, Any]]:
    with get_db() as db:
        rows = db.execute("SELECT e.*, f.reconciliation_status, f.expected_settlement, f.fee_deducted, f.fee_rate, f.settlement_date, f.reasoning FROM finance_reconciliations f JOIN events e ON e.id = f.event_id ORDER BY f.reconciled_at DESC").fetchall()
    result = []
    for row in rows:
        item = _record(row); item["expected_settlement_inr"] = float(item.get("expected_settlement") or 0); item["fee_inr"] = float(item.get("fee_deducted") or 0); result.append(item)
    return result

def event_detail(event_id: str) -> dict[str, Any] | None:
    with get_db() as db:
        event = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        if not event: return None
        item = _record(event); item["payload"] = json.loads(item.get("raw_payload") or "{}")
        item["audit"] = [dict(row) for row in db.execute("SELECT * FROM audit_log WHERE event_id = ? ORDER BY timestamp ASC", (event_id,)).fetchall()]
    return item
