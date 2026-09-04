"""Deterministic authorization rules for CUSTOS.

Recommendations never authorize themselves. Policy produces only the three
product contract outcomes: AUTO_EXECUTE, APPROVAL_REQUIRED, or DENIED.
"""
from dataclasses import dataclass

POLICY_VERSION = "RECOVERY_RETRY_V2"
HIGH_RISK_THRESHOLD = 0.70
HIGH_VALUE_THRESHOLD = 5_000_000  # ₹50,000 in paise
DEFAULT_RETRY_LIMIT = 3


@dataclass(frozen=True)
class PolicyResult:
    decision: str
    reason: str
    version: str = POLICY_VERSION


def evaluate_recovery_policy(
    *, action, amount, payment_status, failure_is_retryable, retry_count,
    retry_limit=DEFAULT_RETRY_LIMIT, risk_score=None, duplicate_action_exists=False,
):
    """Authorize a recovery recommendation using current verified facts only."""
    if payment_status not in {"failed", "unpaid"}:
        return PolicyResult("DENIED", "Current payment state is not eligible for recovery")
    if duplicate_action_exists:
        return PolicyResult("DENIED", "Duplicate action prevented by idempotency policy")
    if action not in {"RETRY_PAYMENT", "SEND_REMINDER", "FLAG_FOR_HUMAN_REVIEW"}:
        return PolicyResult("DENIED", "Recommended action is not allow-listed")
    if action == "FLAG_FOR_HUMAN_REVIEW":
        return PolicyResult("APPROVAL_REQUIRED", "Case is explicitly routed for human review")
    if action == "RETRY_PAYMENT" and not failure_is_retryable:
        return PolicyResult("DENIED", "Failure is not classified as retryable")
    if action == "RETRY_PAYMENT" and retry_count >= retry_limit:
        return PolicyResult("DENIED", "Retry limit has been reached")
    if risk_score is None:
        return PolicyResult("DENIED", "Risk assessment is unavailable; policy fails closed")
    if risk_score >= HIGH_RISK_THRESHOLD:
        return PolicyResult("APPROVAL_REQUIRED", "High-risk transaction requires human approval")
    if amount > HIGH_VALUE_THRESHOLD:
        return PolicyResult("APPROVAL_REQUIRED", "High-value recovery requires human approval")
    return PolicyResult("AUTO_EXECUTE", "Eligible retry is within merchant safety limits")


def evaluate_policy(action, amount, status, confidence):
    """Compatibility wrapper for callers not migrated to the rich contract."""
    result = evaluate_recovery_policy(
        action=action, amount=amount, payment_status=status,
        failure_is_retryable=True, retry_count=0,
        risk_score=0.0 if confidence >= 0.5 else None,
    )
    return result.decision, result.reason
