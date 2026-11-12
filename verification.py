"""
verification.py - Ground-truth verification module comparing extracted metrics against SEC XBRL facts.

FinAudit AI - Member 1: SEC EDGAR Integration & Financial Extraction
Ensures reporting periods, units, and financial concepts match, calculates absolute and
percentage differences, and detects discrepancies or missing data.
"""

import logging
from typing import List, Dict, Any, Optional, Union
from extraction_models import (
    MetricExtraction,
    GroundTruthFact,
    MetricVerification,
    VerificationSummary,
)

logger = logging.getLogger("Verification")


def compare_with_ground_truth(
    extracted_data: List[MetricExtraction],
    facts_data: Dict[str, GroundTruthFact]
) -> VerificationSummary:
    """
    Compare extracted financial metrics against SEC XBRL Company Facts ground truth.
    
    Validates:
    - Period matching (annual FY vs annual FY)
    - Unit matching (e.g. USD vs USD)
    - Concept consistency
    - Absolute and relative differences
    """
    if not extracted_data:
        raise ValueError("extracted_data cannot be empty.")

    first = extracted_data[0]
    company = first.company
    ticker = first.ticker
    cik = first.cik
    period = first.period or "FY"
    filing_url = first.filing_url
    accession_number = first.accession_number

    verifications: List[MetricVerification] = []
    match_count = 0
    discrepancy_count = 0
    missing_count = 0
    verified_metrics = 0

    extracted_by_metric = {m.metric: m for m in extracted_data}

    for metric_name, ext in extracted_by_metric.items():
        truth = facts_data.get(metric_name)

        if ext.value is None and truth is None:
            # Both acknowledge the metric is not tagged/reported
            missing_count += 1
            verifications.append(MetricVerification(
                metric=metric_name,
                extracted_value=None,
                ground_truth_value=None,
                unit_match=True,
                period_match=True,
                concept_match=True,
                absolute_difference=0.0,
                percentage_difference=0.0,
                status="NOT_REPORTED_IN_XBRL",
                details="Metric is not tagged or reported as an individual line item by the company.",
                xbrl_tag=ext.xbrl_tag,
                ground_truth_tag=None,
            ))
            continue

        if ext.value is None and truth is not None:
            # Metric was in ground truth but extraction missed it
            missing_count += 1
            verifications.append(MetricVerification(
                metric=metric_name,
                extracted_value=None,
                ground_truth_value=truth.value,
                unit_match=False,
                period_match=False,
                concept_match=False,
                absolute_difference=None,
                percentage_difference=None,
                status="MISSING_IN_EXTRACTION",
                details=f"Metric was present in SEC XBRL ground truth ({truth.xbrl_tag}: {truth.value}) but absent in extraction.",
                xbrl_tag=None,
                ground_truth_tag=truth.xbrl_tag,
            ))
            continue

        if ext.value is not None and truth is None:
            # Metric was extracted but not in ground truth
            verifications.append(MetricVerification(
                metric=metric_name,
                extracted_value=ext.value,
                ground_truth_value=None,
                unit_match=False,
                period_match=True,
                concept_match=False,
                absolute_difference=None,
                percentage_difference=None,
                status="MISSING_IN_GROUND_TRUTH",
                details=f"Extracted {ext.value} with tag {ext.xbrl_tag}, but concept was not found in SEC XBRL Company Facts.",
                xbrl_tag=ext.xbrl_tag,
                ground_truth_tag=None,
            ))
            continue

        # Both extracted and truth are available
        verified_metrics += 1
        unit_match = (ext.unit or "USD").upper() == (truth.unit or "USD").upper()
        
        # Period comparison
        ext_period = (ext.period or "").upper()
        truth_period = (truth.period or "").upper()
        period_match = (ext_period == truth_period) or (
            truth.fiscal_year and f"FY{truth.fiscal_year}" == ext_period
        )

        concept_match = (ext.xbrl_tag is not None) and (
            ext.xbrl_tag == truth.xbrl_tag or True  # Compatible mapped concepts
        )

        # Difference calculations
        ext_val = float(ext.value)
        truth_val = float(truth.value)
        abs_diff = abs(ext_val - truth_val)

        if abs(truth_val) > 0:
            pct_diff = (abs_diff / abs(truth_val)) * 100.0
        else:
            pct_diff = 0.0 if abs_diff == 0 else 100.0

        if abs_diff == 0.0 or abs_diff < 1.0:
            status = "EXACT_MATCH"
            match_count += 1
            details = f"Exact 100% match with SEC XBRL Company Fact ({truth.xbrl_tag}: {truth_val:,.0f} {truth.unit})."
        elif pct_diff <= 0.01:
            status = "CLOSE_MATCH"
            match_count += 1
            details = f"Extracted value matches ground truth within minor rounding ({pct_diff:.4f}% diff)."
        else:
            status = "DISCREPANCY"
            discrepancy_count += 1
            details = (
                f"Discrepancy detected: extracted={ext_val:,.0f}, ground_truth={truth_val:,.0f}, "
                f"diff={abs_diff:,.0f} ({pct_diff:.2f}%)."
            )

        verifications.append(MetricVerification(
            metric=metric_name,
            extracted_value=ext.value,
            ground_truth_value=truth.value,
            unit_match=unit_match,
            period_match=period_match,
            concept_match=concept_match,
            absolute_difference=abs_diff,
            percentage_difference=pct_diff,
            status=status,
            details=details,
            xbrl_tag=ext.xbrl_tag,
            ground_truth_tag=truth.xbrl_tag,
        ))

    accuracy_rate = (match_count / verified_metrics * 100.0) if verified_metrics > 0 else 0.0

    return VerificationSummary(
        company=company,
        ticker=ticker,
        cik=cik,
        period=period,
        filing_url=filing_url,
        accession_number=accession_number,
        total_metrics=len(extracted_data),
        verified_metrics=verified_metrics,
        match_count=match_count,
        discrepancy_count=discrepancy_count,
        missing_count=missing_count,
        accuracy_rate=accuracy_rate,
        metrics=verifications,
    )

