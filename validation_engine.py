"""
FinAudit AI - Financial Validation Engine (Member 2)
Implements all three mandatory financial audit validations:
A. Accounting Equation:
   Total Assets = Total Liabilities + Shareholders' Equity
B. Segment Validation:
   Sum of business/operating segment metrics == Consolidated total reported metric
   (Returns NOT_APPLICABLE when segment breakdown is unavailable)
C. Year-on-Year (YoY) Analysis:
   Percentage variation across consecutive fiscal periods with anomaly detection
   for variations exceeding configurable thresholds (> 30.0% default)
"""

from typing import Dict, Any, List, Optional, Tuple, Union
from workflow_state import ValidationResult


def normalize_unit_multiplier(unit: Optional[str]) -> float:
    """Returns scaling multiplier to normalize monetary values to single base currency units."""
    if not unit:
        return 1.0
    u = unit.lower().strip()
    if "billion" in u:
        return 1e9
    if "million" in u:
        return 1e6
    if "thousand" in u:
        return 1e3
    return 1.0


def extract_metric_value(metrics: List[Dict[str, Any]], candidate_names: List[str]) -> Optional[Tuple[float, Dict[str, Any]]]:
    """Finds a metric from the metric list matching any of the candidate names."""
    target_names = [c.lower().replace(" ", "").replace("'", "").replace("_", "") for c in candidate_names]
    for m in metrics:
        name = (m.get("metric") or m.get("metric_name") or "").lower().replace(" ", "").replace("'", "").replace("_", "")
        if name in target_names:
            val = float(m.get("value", m.get("extracted_value", 0.0)))
            multiplier = normalize_unit_multiplier(m.get("unit"))
            return val * multiplier, m
    return None


# ---------------------------------------------------------------------------
# 1. Mandatory Validation A: Accounting Equation
# ---------------------------------------------------------------------------
def validate_accounting_equation(
    financial_data: Union[List[Dict[str, Any]], Dict[str, Any]],
    relative_tolerance: float = 0.005,  # 0.5% tolerance for rounding in SEC filings
    absolute_tolerance: float = 1_000_000.0  # $1M tolerance for multi-billion filings
) -> Dict[str, Any]:
    """
    Validates: Total Assets = Total Liabilities + Shareholders' Equity
    Returns ValidationResult dictionary.
    """
    if isinstance(financial_data, dict):
        metrics_list = financial_data.get("metrics", [])
        if not metrics_list and "Total Assets" in financial_data:
            # Flattened dict format: {"Total Assets": 100, "Total Liabilities": 60, "Shareholders' Equity": 40}
            metrics_list = [{"metric": k, "value": v} for k, v in financial_data.items()]
    else:
        metrics_list = financial_data

    assets_res = extract_metric_value(metrics_list, ["Total Assets", "Assets", "AssetsCurrentAndNoncurrent"])
    liabilities_res = extract_metric_value(metrics_list, ["Total Liabilities", "Liabilities", "LiabilitiesCurrentAndNoncurrent"])
    equity_res = extract_metric_value(metrics_list, [
        "Shareholders' Equity", "Shareholders Equity", "Stockholders' Equity",
        "StockholdersEquity", "Total Equity", "Common Stockholders' Equity"
    ])

    missing = []
    if not assets_res:
        missing.append("Total Assets")
    if not liabilities_res:
        missing.append("Total Liabilities")
    if not equity_res:
        missing.append("Shareholders' Equity")

    if missing:
        res = ValidationResult(
            validation_type="accounting_equation",
            status="FAILED",
            message=f"Accounting equation check cannot be verified: missing required components: {', '.join(missing)}",
            details={"missing_components": missing},
            flagged_metrics=missing
        )
        return res.model_dump()

    assets_val, assets_meta = assets_res
    liab_val, liab_meta = liabilities_res
    equity_val, equity_meta = equity_res

    balance_sum = liab_val + equity_val
    difference = assets_val - balance_sum
    abs_diff = abs(difference)

    # Relative difference against total assets
    rel_diff = abs_diff / max(abs(assets_val), 1.0)

    # Pass if difference is within either relative or absolute tolerance
    is_valid = (rel_diff <= relative_tolerance) or (abs_diff <= absolute_tolerance)

    flagged = []
    if not is_valid:
        flagged = ["Total Assets", "Total Liabilities", "Shareholders' Equity"]
        status = "FAILED"
        message = (
            f"Accounting equation mismatch: Total Assets (${assets_val:,.2f}) != "
            f"Total Liabilities (${liab_val:,.2f}) + Equity (${equity_val:,.2f}). "
            f"Difference of ${difference:,.2f} ({rel_diff * 100:.2f}%) exceeds acceptable tolerance."
        )
    else:
        status = "PASSED"
        message = (
            f"Accounting equation balanced: Total Assets (${assets_val:,.2f}) == "
            f"Liabilities (${liab_val:,.2f}) + Equity (${equity_val:,.2f}) "
            f"(Variance: ${abs_diff:,.2f}, {rel_diff * 100:.4f}%)."
        )

    res = ValidationResult(
        validation_type="accounting_equation",
        status=status,
        message=message,
        details={
            "total_assets": assets_val,
            "total_liabilities": liab_val,
            "shareholders_equity": equity_val,
            "liabilities_plus_equity": balance_sum,
            "difference": difference,
            "variance_pct": round(rel_diff * 100, 3)
        },
        discrepancy=difference,
        flagged_metrics=flagged
    )
    return res.model_dump()


# ---------------------------------------------------------------------------
# 2. Mandatory Validation B: Segment Validation
# ---------------------------------------------------------------------------
def validate_segments(
    financial_data: Union[List[Dict[str, Any]], Dict[str, Any]],
    tolerance_pct: float = 1.0
) -> Dict[str, Any]:
    """
    Validates operating / geographic segment sum vs consolidated total.
    If segment data is unavailable, marks the validation as NOT_APPLICABLE rather than PASSED.
    """
    segments_data = None
    metrics_list = []

    if isinstance(financial_data, dict):
        segments_data = financial_data.get("segments") or financial_data.get("segment_breakdown")
        metrics_list = financial_data.get("metrics", [])
    elif isinstance(financial_data, list):
        metrics_list = financial_data

    # Check if segment data is provided
    if not segments_data or not isinstance(segments_data, dict) or not segments_data.get("items"):
        return ValidationResult(
            validation_type="segment_validation",
            status="NOT_APPLICABLE",
            message="Segment-level financial data is not reported or unavailable for this filing period.",
            details={"segments_available": False}
        ).model_dump()

    consolidated_metric = segments_data.get("consolidated_metric", "Revenue")
    segment_items = segments_data.get("items", [])

    # Find reported consolidated value
    reported_res = extract_metric_value(metrics_list, [consolidated_metric])
    reported_total = None
    if reported_res:
        reported_total = reported_res[0]
    elif "reported_total" in segments_data:
        reported_total = float(segments_data["reported_total"])

    if reported_total is None or reported_total == 0:
        return ValidationResult(
            validation_type="segment_validation",
            status="FAILED",
            message=f"Consolidated total for metric '{consolidated_metric}' is missing to verify segment sum.",
            details={"segment_count": len(segment_items)},
            flagged_metrics=[consolidated_metric]
        ).model_dump()

    segment_sum = sum(float(item.get("value", 0.0)) * normalize_unit_multiplier(item.get("unit")) for item in segment_items)
    diff = abs(segment_sum - reported_total)
    diff_pct = (diff / abs(reported_total)) * 100.0

    if diff_pct <= tolerance_pct:
        status = "PASSED"
        message = (
            f"Segment validation passed: Sum of {len(segment_items)} segments (${segment_sum:,.2f}) "
            f"matches consolidated {consolidated_metric} (${reported_total:,.2f}) within {diff_pct:.2f}%."
        )
        flagged = []
    else:
        status = "FAILED"
        message = (
            f"Segment validation mismatch: Sum of segments (${segment_sum:,.2f}) differs from "
            f"reported consolidated {consolidated_metric} (${reported_total:,.2f}) by ${diff:,.2f} ({diff_pct:.2f}%)."
        )
        flagged = [consolidated_metric]

    return ValidationResult(
        validation_type="segment_validation",
        status=status,
        message=message,
        details={
            "consolidated_metric": consolidated_metric,
            "segment_sum": segment_sum,
            "reported_total": reported_total,
            "difference": diff,
            "difference_pct": round(diff_pct, 2),
            "segment_count": len(segment_items)
        },
        discrepancy=diff,
        flagged_metrics=flagged
    ) .model_dump()


# ---------------------------------------------------------------------------
# 3. Mandatory Validation C: Year-on-Year (YoY) Analysis
# ---------------------------------------------------------------------------
def analyze_year_on_year(
    financial_data: Union[List[Dict[str, Any]], Dict[str, Any]],
    threshold_pct: float = 30.0  # Alert on changes > 30%
) -> Dict[str, Any]:
    """
    Compares financial metrics across equivalent reporting periods.
    Calculates percentage change: ((current - prior) / abs(prior)) * 100.
    Identifies unusual variations exceeding threshold_pct and explains every flagged change.
    """
    current_metrics = []
    prior_metrics = []

    if isinstance(financial_data, dict):
        current_metrics = financial_data.get("metrics") or financial_data.get("current_period_metrics") or []
        prior_metrics = financial_data.get("prior_period_metrics") or financial_data.get("prior_metrics") or []
    elif isinstance(financial_data, list):
        current_metrics = financial_data

    if not prior_metrics:
        return ValidationResult(
            validation_type="year_on_year",
            status="NOT_APPLICABLE",
            message="Prior period financial metrics unavailable for year-on-year comparative analysis.",
            details={"prior_period_available": False}
        ).model_dump()

    # Build lookup for prior metrics
    prior_map = {}
    for m in prior_metrics:
        name = (m.get("metric") or m.get("metric_name") or "").strip().lower()
        val = float(m.get("value", m.get("extracted_value", 0.0))) * normalize_unit_multiplier(m.get("unit"))
        prior_map[name] = val

    comparisons = []
    flagged_metrics = []
    explanations = []

    for curr in current_metrics:
        metric_name = curr.get("metric") or curr.get("metric_name") or ""
        name_key = metric_name.strip().lower()
        if name_key in prior_map:
            prior_val = prior_map[name_key]
            curr_val = float(curr.get("value", curr.get("extracted_value", 0.0))) * normalize_unit_multiplier(curr.get("unit"))

            if abs(prior_val) < 1e-6:
                pct_change = 0.0 if abs(curr_val) < 1e-6 else 100.0
            else:
                pct_change = ((curr_val - prior_val) / abs(prior_val)) * 100.0

            is_unusual = abs(pct_change) > threshold_pct
            comp_entry = {
                "metric": metric_name,
                "current_value": curr_val,
                "prior_value": prior_val,
                "pct_change": round(pct_change, 2),
                "is_unusual": is_unusual
            }
            comparisons.append(comp_entry)

            if is_unusual:
                flagged_metrics.append(metric_name)
                direction = "increased" if pct_change > 0 else "decreased"
                explanation = (
                    f"Metric '{metric_name}' {direction} by {abs(pct_change):.1f}% YoY "
                    f"(from ${prior_val:,.0f} to ${curr_val:,.0f}), exceeding unusual variation threshold ({threshold_pct}%)."
                )
                explanations.append(explanation)

    if flagged_metrics:
        status = "WARNING"
        message = f"Identified {len(flagged_metrics)} unusual YoY variation(s): " + " | ".join(explanations)
    else:
        status = "PASSED"
        message = f"All {len(comparisons)} comparative metrics are within normal YoY variation thresholds (<={threshold_pct}%)."

    return ValidationResult(
        validation_type="year_on_year",
        status=status,
        message=message,
        details={
            "threshold_pct": threshold_pct,
            "comparisons": comparisons,
            "flagged_count": len(flagged_metrics),
            "explanations": explanations
        },
        flagged_metrics=flagged_metrics
    ).model_dump()


# ---------------------------------------------------------------------------
# Master Validator Helper
# ---------------------------------------------------------------------------
def run_all_validations(financial_data: Union[List[Dict[str, Any]], Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Runs all 3 mandatory validations and returns combined dictionary."""
    acct = validate_accounting_equation(financial_data)
    seg = validate_segments(financial_data)
    yoy = analyze_year_on_year(financial_data)

    return {
        "accounting_equation": acct,
        "segment_validation": seg,
        "year_on_year": yoy
    }
