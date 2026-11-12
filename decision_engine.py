"""
FinAudit AI - Automated Decision Engine (Member 2)
Implements business rules for routing financial audits:
1. AUTO_APPROVED:
   - Confidence meets the configured threshold (>= 90)
   - Mandatory validation checks pass
2. NEEDS_HUMAN_REVIEW:
   - Confidence is below the configured threshold (< 90)
   OR
   - Any mandatory validation check fails

CRITICAL REQUIREMENT:
A failed validation CANNOT be automatically approved merely because confidence is high.
Produces the shared JSON output contract for Member 1 and Member 3.
"""

from typing import Dict, Any, List, Tuple
from workflow_state import SharedMetricContract, MetricInput


def evaluate_audit_decision(
    metrics: List[Dict[str, Any]],
    confidence_results: Dict[str, Dict[str, Any]],
    validation_results: Dict[str, Dict[str, Any]],
    high_threshold: float = 90.0
) -> Tuple[str, List[str], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Evaluates automated audit decision across all metrics and validation results.

    Returns:
    - overall_decision: 'AUTO_APPROVED' | 'NEEDS_HUMAN_REVIEW'
    - escalation_reasons: List of human-readable reasons why human review was triggered
    - flagged_items: List of specific metric payloads requiring review
    - shared_contracts: List of SharedMetricContract dictionaries (Section 10 specification)
    """
    escalation_reasons: List[str] = []
    flagged_metrics_set = set()

    # 1. Inspect Validation Results first
    # Even if confidence is 100%, any failed validation MUST escalate
    acct_res = validation_results.get("accounting_equation", {})
    seg_res = validation_results.get("segment_validation", {})
    yoy_res = validation_results.get("year_on_year", {})

    if acct_res.get("status") == "FAILED":
        reason = f"Accounting equation failed: {acct_res.get('message', 'Mismatch between Assets, Liabilities and Equity')}"
        escalation_reasons.append(reason)
        for m in acct_res.get("flagged_metrics", []):
            flagged_metrics_set.add(m)

    if seg_res.get("status") == "FAILED":
        reason = f"Segment validation failed: {seg_res.get('message', 'Segment totals do not match reported consolidated total')}"
        escalation_reasons.append(reason)
        for m in seg_res.get("flagged_metrics", []):
            flagged_metrics_set.add(m)

    if yoy_res.get("status") == "WARNING":
        reason = f"Unusual YoY variance detected: {yoy_res.get('message')}"
        escalation_reasons.append(reason)
        for m in yoy_res.get("flagged_metrics", []):
            flagged_metrics_set.add(m)

    # 2. Inspect Confidence Scores
    for metric_name, conf_data in confidence_results.items():
        score = conf_data.get("score", 0.0)
        if score < high_threshold:
            escalation_reasons.append(
                f"Metric '{metric_name}' confidence score ({score:.1f}) is below approval threshold ({high_threshold})"
            )
            flagged_metrics_set.add(metric_name)

    # 3. Build Shared JSON Output Contracts
    shared_contracts: List[Dict[str, Any]] = []
    flagged_items: List[Dict[str, Any]] = []

    for item in metrics:
        m_input = MetricInput.from_dict(item)
        m_name = m_input.metric
        conf_data = confidence_results.get(m_name, {})
        score = conf_data.get("score", 50.0)
        level = conf_data.get("level", "LOW")

        # Determine metric-specific validation status
        if m_name in flagged_metrics_set:
            if acct_res.get("status") == "FAILED" and m_name in acct_res.get("flagged_metrics", []):
                val_status = "FAILED"
                metric_reason = "Accounting equation mismatch"
            elif seg_res.get("status") == "FAILED" and m_name in seg_res.get("flagged_metrics", []):
                val_status = "FAILED"
                metric_reason = "Segment validation mismatch"
            elif yoy_res.get("status") == "WARNING" and m_name in yoy_res.get("flagged_metrics", []):
                val_status = "WARNING"
                metric_reason = "Unusual year-on-year variation exceeding threshold"
            elif score < high_threshold:
                val_status = "PASSED" if acct_res.get("status") == "PASSED" else "NEEDS_REVIEW"
                metric_reason = f"Confidence score ({score:.1f}) below threshold ({high_threshold})"
            else:
                val_status = "FAILED"
                metric_reason = "Flagged during comprehensive audit validation"

            metric_decision = "NEEDS_HUMAN_REVIEW"
            review_required = True

            contract = SharedMetricContract(
                metric=m_name,
                value=m_input.value,
                confidence=score,
                confidence_level=level,
                validation_status=val_status,
                decision=metric_decision,
                review_required=review_required,
                reason=metric_reason,
                source_evidence=m_input.source_evidence,
                original_value=m_input.value
            )

            flagged_items.append({
                "metric": m_name,
                "value": m_input.value,
                "unit": m_input.unit,
                "period": m_input.period,
                "confidence": score,
                "confidence_level": level,
                "validation_status": val_status,
                "reason": metric_reason,
                "source_evidence": m_input.source_evidence,
                "xbrl_tag": m_input.xbrl_tag
            })
        else:
            val_status = "PASSED"
            metric_decision = "AUTO_APPROVED"
            review_required = False
            metric_reason = "Confidence threshold met and validation passed"

            contract = SharedMetricContract(
                metric=m_name,
                value=m_input.value,
                confidence=score,
                confidence_level=level,
                validation_status=val_status,
                decision=metric_decision,
                review_required=review_required,
                reason=metric_reason,
                source_evidence=m_input.source_evidence,
                original_value=m_input.value
            )

        shared_contracts.append(contract.to_dict())

    # Overall Audit Decision
    if len(flagged_metrics_set) > 0 or len(escalation_reasons) > 0:
        overall_decision = "NEEDS_HUMAN_REVIEW"
    else:
        overall_decision = "AUTO_APPROVED"

    return overall_decision, escalation_reasons, flagged_items, shared_contracts
