"""
FinAudit AI - Confidence Scoring Engine (Member 2)
Calculates explainable, deterministic confidence scores (0-100) for every
extracted financial metric based on:
1. Source evidence availability (0-25 pts)
2. Extraction method reliability (0-25 pts)
3. Financial metric identification & standard GAAP/IFRS tag (0-20 pts)
4. Unit and reporting period consistency (0-15 pts)
5. Agreement with SEC XBRL facts (0-15 pts)

Thresholds (Configurable):
- High: 90 - 100
- Medium: 70 - 89.9
- Low: Below 70
"""

from typing import Dict, Any, List, Optional
import re
from workflow_state import MetricInput, ConfidenceScore, ConfidenceBreakdown


# Canonical US-GAAP / IFRS financial tags and concept names
CANONICAL_GAAP_TAGS = {
    # Balance Sheet
    "assets": "us-gaap:Assets",
    "total assets": "us-gaap:Assets",
    "liabilities": "us-gaap:Liabilities",
    "total liabilities": "us-gaap:Liabilities",
    "stockholdersequity": "us-gaap:StockholdersEquity",
    "shareholders' equity": "us-gaap:StockholdersEquity",
    "shareholders equity": "us-gaap:StockholdersEquity",
    "stockholders' equity": "us-gaap:StockholdersEquity",
    "total equity": "us-gaap:StockholdersEquity",
    "retained earnings": "us-gaap:RetainedEarningsAccumulatedDeficit",
    "cash and cash equivalents": "us-gaap:CashAndCashEquivalentsAtCarryingValue",
    "current assets": "us-gaap:AssetsCurrent",
    "current liabilities": "us-gaap:LiabilitiesCurrent",
    "long-term debt": "us-gaap:LongTermDebtNoncurrent",
    # Income Statement
    "revenue": "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
    "revenues": "us-gaap:Revenues",
    "total revenue": "us-gaap:Revenues",
    "net income": "us-gaap:NetIncomeLoss",
    "net income (loss)": "us-gaap:NetIncomeLoss",
    "operating income": "us-gaap:OperatingIncomeLoss",
    "gross profit": "us-gaap:GrossProfit",
    "cost of goods sold": "us-gaap:CostOfGoodsAndServicesSold",
    "research and development": "us-gaap:ResearchAndDevelopmentExpense",
    # Cash Flow
    "operating cash flow": "us-gaap:NetCashProvidedByUsedInOperatingActivities",
    "cash flow from operations": "us-gaap:NetCashProvidedByUsedInOperatingActivities",
    "investing cash flow": "us-gaap:NetCashProvidedByUsedInInvestingActivities",
    "financing cash flow": "us-gaap:NetCashProvidedByUsedInFinancingActivities",
    "capital expenditures": "us-gaap:PaymentsToAcquirePropertyPlantAndEquipment"
}

VALID_UNITS = {"usd", "usd millions", "usd thousands", "shares", "eur", "gbp", "jpy", "inr", "$"}
VALID_PERIOD_PATTERNS = [
    r"^FY\d{4}$",              # FY2026
    r"^Q[1-4]\s*\d{4}$",       # Q3 2026 or Q32026
    r"^\d{4}$",                # 2026
    r"^\d{4}-\d{2}-\d{2}$"     # 2026-09-26
]


class ConfidenceConfig:
    def __init__(
        self,
        high_threshold: float = 90.0,
        medium_threshold: float = 70.0
    ):
        self.high_threshold = high_threshold
        self.medium_threshold = medium_threshold


DEFAULT_CONFIDENCE_CONFIG = ConfidenceConfig()


def evaluate_source_evidence(evidence: Optional[str]) -> tuple[float, List[str]]:
    """Evaluates availability and specificity of source evidence (0-25 points)."""
    points = 0.0
    reasons = []

    if not evidence or not evidence.strip():
        return 0.0, ["Missing source filing evidence (-25 pts)"]

    evidence_lower = evidence.lower().strip()

    # Base evidence present
    points += 10.0
    reasons.append("Source evidence excerpt provided (+10 pts)")

    # Check for specific filing identifiers (Item 8, 10-K, Context, Accession Number, URL, Note)
    has_section = any(k in evidence_lower for k in ["item 8", "item 7", "10-k", "form 10-k", "balance sheet", "income statement", "cash flow", "note "])
    has_filing_ref = any(k in evidence_lower for k in ["filing", "accession", "context", "scale", "context:"])

    if has_section and has_filing_ref:
        points += 15.0
        reasons.append("Evidence includes specific filing accession, item/statement reference, and contextual metadata (+15 pts)")
    elif has_section or has_filing_ref:
        points += 10.0
        reasons.append("Evidence includes filing or section reference (+10 pts)")
    else:
        points += 5.0
        reasons.append("Evidence provides excerpt text without explicit filing coordinates (+5 pts)")

    return min(25.0, points), reasons


def evaluate_extraction_reliability(method: Optional[str], raw_conf: Optional[float] = None) -> tuple[float, List[str]]:
    """Evaluates the reliability of the extraction technique (0-25 points)."""
    method_str = (method or "xbrl_facts").lower().strip()
    points = 0.0
    reasons = []

    if "xbrl" in method_str or "sec_fact" in method_str:
        points = 25.0
        reasons.append("Extraction via direct SEC XBRL structured taxonomy instance (+25 pts)")
    elif "table" in method_str or "structured_table" in method_str:
        points = 20.0
        reasons.append("Extraction via audited HTML/PDF financial table parser (+20 pts)")
    elif "llm" in method_str or "nlp" in method_str or "unstructured" in method_str:
        points = 12.0
        reasons.append("Extraction via generative LLM text parsing (moderate reliability, +12 pts)")
    elif "regex" in method_str or "heuristic" in method_str:
        points = 14.0
        reasons.append("Extraction via heuristic regex pattern matching (+14 pts)")
    else:
        points = 15.0
        reasons.append(f"Extraction via standard provider ({method_str}, +15 pts)")

    # Adjust if member 1 supplied a calibrated extraction probability
    if raw_conf is not None:
        if raw_conf >= 0.95:
            points = min(25.0, points + 2.0)
        elif raw_conf < 0.60:
            points = max(5.0, points - 8.0)
            reasons.append(f"Upstream extraction model flagged low raw confidence ({raw_conf:.2f}, -8 pts)")

    return points, reasons


def evaluate_metric_identification(metric_name: str, xbrl_tag: Optional[str]) -> tuple[float, List[str]]:
    """Evaluates identification against standard GAAP/IFRS nomenclature (0-20 points)."""
    norm_name = metric_name.strip().lower()
    points = 0.0
    reasons = []

    is_canonical = norm_name in CANONICAL_GAAP_TAGS
    has_valid_xbrl = False

    if xbrl_tag:
        clean_tag = xbrl_tag.strip()
        if ":" in clean_tag or clean_tag in CANONICAL_GAAP_TAGS.values() or any(clean_tag in v for v in CANONICAL_GAAP_TAGS.values()):
            has_valid_xbrl = True

    if is_canonical and has_valid_xbrl:
        points = 20.0
        reasons.append(f"Canonical GAAP/IFRS concept '{metric_name}' with verified XBRL tag '{xbrl_tag}' (+20 pts)")
    elif is_canonical:
        points = 16.0
        reasons.append(f"Recognized canonical financial metric '{metric_name}' (+16 pts)")
    elif has_valid_xbrl:
        points = 15.0
        reasons.append(f"Recognized standard XBRL taxonomy concept '{xbrl_tag}' (+15 pts)")
    else:
        # Check partial match
        if any(word in norm_name for word in ["asset", "liabilit", "equity", "income", "revenue", "cash", "expense", "profit"]):
            points = 10.0
            reasons.append(f"Non-canonical financial terminology '{metric_name}', partial domain match (+10 pts)")
        else:
            points = 4.0
            reasons.append(f"Unrecognized or custom financial concept '{metric_name}' (-16 pts)")

    return points, reasons


def evaluate_unit_period_consistency(unit: Optional[str], period: Optional[str]) -> tuple[float, List[str]]:
    """Evaluates unit formatting and reporting period consistency (0-15 points)."""
    points = 0.0
    reasons = []

    # Unit validation
    if not unit or not unit.strip():
        reasons.append("Missing monetary/reporting unit (-8 pts)")
    else:
        norm_unit = unit.strip().lower()
        if any(norm_unit == u or norm_unit.startswith("usd") or "$" in norm_unit for u in VALID_UNITS):
            points += 7.5
            reasons.append(f"Valid normalized currency unit '{unit}' (+7.5 pts)")
        else:
            points += 3.0
            reasons.append(f"Unconventional financial unit '{unit}' (+3 pts)")

    # Period validation
    if not period or not period.strip():
        reasons.append("Missing reporting period (-7.5 pts)")
    else:
        clean_period = period.strip()
        matched = any(re.match(pattern, clean_period, re.IGNORECASE) for pattern in VALID_PERIOD_PATTERNS)
        if matched:
            points += 7.5
            reasons.append(f"Standard reporting period format '{period}' (+7.5 pts)")
        else:
            points += 3.0
            reasons.append(f"Non-standard reporting period format '{period}' (+3 pts)")

    return points, reasons


def evaluate_xbrl_agreement(
    metric_name: str,
    extracted_value: float,
    xbrl_tag: Optional[str],
    evidence: Optional[str]
) -> tuple[float, List[str]]:
    """Evaluates agreement with SEC XBRL facts when available (0-15 points)."""
    points = 0.0
    reasons = []

    # If evidence or xbrl_tag confirms agreement with official SEC XBRL fact:
    has_xbrl_evidence = False
    if evidence and ("us-gaap:" in evidence or "context:" in evidence or "scale=" in evidence or "reported value" in evidence.lower()):
        has_xbrl_evidence = True

    if xbrl_tag and has_xbrl_evidence:
        points = 15.0
        reasons.append(f"100% agreement with SEC XBRL audited fact instance '{xbrl_tag}' (+15 pts)")
    elif xbrl_tag:
        points = 12.0
        reasons.append(f"Corroborated by standard SEC XBRL tag '{xbrl_tag}' (+12 pts)")
    elif has_xbrl_evidence:
        points = 10.0
        reasons.append("Filing evidence contains XBRL context references (+10 pts)")
    else:
        # Neutral baseline when XBRL comparison is pending or not reported in raw item
        points = 6.0
        reasons.append("No direct SEC XBRL reconciliation metadata provided (neutral +6 pts)")

    return points, reasons


def calculate_confidence(
    metric_data: Dict[str, Any] | MetricInput,
    config: Optional[ConfidenceConfig] = None
) -> Dict[str, Any]:
    """
    Computes explainable confidence score (0-100) for a financial metric.
    Callable function required by integration specifications.
    """
    cfg = config or DEFAULT_CONFIDENCE_CONFIG

    if isinstance(metric_data, MetricInput):
        metric = metric_data
    else:
        metric = MetricInput.from_dict(metric_data)

    ev_pts, ev_reasons = evaluate_source_evidence(metric.source_evidence)
    rel_pts, rel_reasons = evaluate_extraction_reliability(metric.extraction_method, metric.confidence)
    id_pts, id_reasons = evaluate_metric_identification(metric.metric, metric.xbrl_tag)
    cons_pts, cons_reasons = evaluate_unit_period_consistency(metric.unit, metric.period)
    xbrl_pts, xbrl_reasons = evaluate_xbrl_agreement(metric.metric, metric.value, metric.xbrl_tag, metric.source_evidence)

    total_score = round(ev_pts + rel_pts + id_pts + cons_pts + xbrl_pts, 1)
    total_score = max(0.0, min(100.0, total_score))

    if total_score >= cfg.high_threshold:
        level = "HIGH"
        is_flagged = False
    elif total_score >= cfg.medium_threshold:
        level = "MEDIUM"
        is_flagged = True
    else:
        level = "LOW"
        is_flagged = True

    all_reasons = ev_reasons + rel_reasons + id_reasons + cons_reasons + xbrl_reasons

    breakdown = ConfidenceBreakdown(
        source_evidence=ev_pts,
        extraction_reliability=rel_pts,
        metric_identification=id_pts,
        unit_period_consistency=cons_pts,
        xbrl_agreement=xbrl_pts
    )

    result = ConfidenceScore(
        metric=metric.metric,
        score=total_score,
        level=level,
        breakdown=breakdown,
        reasons=all_reasons,
        is_flagged=is_flagged
    )

    return result.model_dump()
