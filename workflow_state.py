"""
FinAudit AI - Workflow State & Data Contracts (Member 2)
Defines Pydantic models, TypedDicts, and contract schemas for:
- Input financial metrics from Member 1
- Confidence scores and explanations
- Financial validation results (Accounting Equation, Segments, YoY)
- LangGraph Workflow State
- Shared JSON output contract
"""

from typing import Dict, Any, List, Optional, Union
from typing_extensions import TypedDict
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 1. Input Metric Model (from Member 1)
# ---------------------------------------------------------------------------
class MetricInput(BaseModel):
    company: str = Field(..., description="Company name, e.g. Apple Inc.")
    ticker: str = Field(..., description="Ticker symbol, e.g. AAPL")
    metric: str = Field(..., description="Metric name, e.g. Total Assets, Revenue")
    value: float = Field(..., description="Numerical value of the metric")
    unit: str = Field(default="USD", description="Currency/unit, e.g. USD, USD Millions")
    period: str = Field(..., description="Reporting period, e.g. FY2026, Q3 2026")
    filing_url: Optional[str] = Field(default=None, description="URL of SEC EDGAR filing")
    source_evidence: Optional[str] = Field(default=None, description="Excerpt or citation from filing")
    xbrl_tag: Optional[str] = Field(default=None, description="Standard US-GAAP or IFRS XBRL tag")
    extraction_method: Optional[str] = Field(
        default="xbrl_facts",
        description="Method used for extraction: xbrl_facts, table_extraction, llm_text"
    )
    confidence: Optional[float] = Field(default=None, description="Initial extraction confidence")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MetricInput":
        """Normalize varied input key names from Member 1 (e.g. metric vs metric_name)."""
        normalized = dict(data)
        if "metric_name" in normalized and "metric" not in normalized:
            normalized["metric"] = normalized["metric_name"]
        if "extracted_value" in normalized and "value" not in normalized:
            normalized["value"] = normalized["extracted_value"]
        if "reporting_period" in normalized and "period" not in normalized:
            normalized["period"] = normalized["reporting_period"]
        if "sec_filing_ref" in normalized and "filing_url" not in normalized:
            normalized["filing_url"] = normalized["sec_filing_ref"]
        if "sec_evidence" in normalized and "source_evidence" not in normalized:
            normalized["source_evidence"] = normalized["sec_evidence"]
        return cls(**normalized)


# ---------------------------------------------------------------------------
# 2. Confidence Scoring Models
# ---------------------------------------------------------------------------
class ConfidenceBreakdown(BaseModel):
    source_evidence: float = Field(..., description="Points for source evidence presence and specificity (0-25)")
    extraction_reliability: float = Field(..., description="Points for extraction method reliability (0-25)")
    metric_identification: float = Field(..., description="Points for canonical GAAP/IFRS tag recognition (0-20)")
    unit_period_consistency: float = Field(..., description="Points for unit and period consistency (0-15)")
    xbrl_agreement: float = Field(..., description="Points for SEC XBRL fact verification (0-15)")


class ConfidenceScore(BaseModel):
    metric: str
    score: float = Field(..., ge=0.0, le=100.0, description="Overall confidence score (0-100)")
    level: str = Field(..., description="HIGH (90-100), MEDIUM (70-89), LOW (<70)")
    breakdown: ConfidenceBreakdown
    reasons: List[str] = Field(default_factory=list, description="Explainable scoring breakdown factors")
    is_flagged: bool = Field(default=False, description="Flagged if score < high_threshold")


# ---------------------------------------------------------------------------
# 3. Financial Validation Models
# ---------------------------------------------------------------------------
class ValidationResult(BaseModel):
    validation_type: str = Field(..., description="accounting_equation, segment_validation, year_on_year")
    status: str = Field(..., description="PASSED, FAILED, NOT_APPLICABLE, WARNING")
    message: str = Field(..., description="Human-readable explanation of the validation outcome")
    details: Dict[str, Any] = Field(default_factory=dict)
    discrepancy: Optional[float] = None
    flagged_metrics: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 4. Human Review & Resolution Models
# ---------------------------------------------------------------------------
class HumanDecision(BaseModel):
    action: str = Field(..., description="APPROVE, CORRECT, or REJECT")
    corrected_value: Optional[float] = None
    correction_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    reviewer_id: Optional[str] = "auditor_human"
    timestamp: Optional[str] = None


class ReviewRequestPayload(BaseModel):
    audit_id: str
    metric: str
    original_value: float
    confidence_score: float
    confidence_level: str
    validation_status: str
    reasons: List[str]
    source_evidence: Optional[str] = None
    xbrl_tag: Optional[str] = None
    allowed_actions: List[str] = Field(default=["APPROVE", "CORRECT", "REJECT"])


# ---------------------------------------------------------------------------
# 5. Shared JSON Output Contract (Section 10)
# ---------------------------------------------------------------------------
class SharedMetricContract(BaseModel):
    metric: str
    value: float
    confidence: float
    confidence_level: str
    validation_status: str
    decision: str  # AUTO_APPROVED or NEEDS_HUMAN_REVIEW
    review_required: bool
    reason: str
    source_evidence: Optional[str] = None
    original_value: Optional[float] = None
    corrected_value: Optional[float] = None
    rejection_reason: Optional[str] = None
    human_resolution: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "metric": self.metric,
            "value": self.value,
            "confidence": round(self.confidence, 1),
            "confidence_level": self.confidence_level,
            "validation_status": self.validation_status,
            "decision": self.decision,
            "review_required": self.review_required,
            "reason": self.reason
        }
        if self.source_evidence:
            result["source_evidence"] = self.source_evidence
        if self.original_value is not None and self.original_value != self.value:
            result["original_value"] = self.original_value
            result["corrected_value"] = self.value
        if self.rejection_reason:
            result["rejection_reason"] = self.rejection_reason
        if self.human_resolution:
            result["human_resolution"] = self.human_resolution
        return result


# ---------------------------------------------------------------------------
# 6. LangGraph State Definition
# ---------------------------------------------------------------------------
class AuditState(TypedDict, total=False):
    audit_id: str
    thread_id: str
    company: str
    ticker: str
    period: str
    raw_input: Union[List[Dict[str, Any]], Dict[str, Any]]
    metrics: List[Dict[str, Any]]
    prior_period_metrics: Optional[List[Dict[str, Any]]]
    segments_data: Optional[Dict[str, Any]]
    confidence_scores: Dict[str, Dict[str, Any]]
    validation_results: Dict[str, Dict[str, Any]]
    audit_decision: str  # AUTO_APPROVED or NEEDS_HUMAN_REVIEW
    escalation_reasons: List[str]
    flagged_metrics: List[str]
    review_payload: Optional[Dict[str, Any]]
    human_decision: Optional[Dict[str, Any]]
    shared_contracts: List[Dict[str, Any]]
    execution_log: List[Dict[str, Any]]
    status: str  # INITIALIZED, PROCESSING, AWAITING_HUMAN_REVIEW, RESUMED_REVIEWED, COMPLETED, REJECTED
    completed_nodes: List[str]  # Idempotency tracking to avoid duplicate side effects
