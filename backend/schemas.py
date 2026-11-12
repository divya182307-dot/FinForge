"""
Pydantic-compatible schemas and data structures for FinAudit AI
Supports both Pydantic (if installed) and pure Python dataclasses / dict validation.
"""
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field, asdict

# Request Schemas
@dataclass
class AuditRunRequest:
    ticker: str
    period: str = "FY2023"

@dataclass
class DecisionRequest:
    decision: str  # 'approve', 'correct', 'reject'
    corrected_value: Optional[float] = None
    reason: str = ""
    comments: Optional[str] = ""

# Response Schemas
@dataclass
class CompanyInfo:
    ticker: str
    name: str
    cik: str
    sector: str
    available_periods: List[str]
    filing_status: str
    current_audit_status: str

@dataclass
class MetricItem:
    metric_id: str
    audit_id: str
    ticker: str
    period: str
    metric_name: str
    extracted_value: float
    unit: str
    confidence_score: float
    validation_status: str  # 'passed', 'failed', 'pending_review'
    source_evidence: str
    sec_filing_ref: str
    created_at: str

@dataclass
class ValidationItem:
    validation_id: str
    audit_id: str
    rule_name: str
    status: str
    description: str
    expected_value: Optional[float]
    actual_value: Optional[float]
    discrepancy: Optional[float]
    details: Dict[str, Any]

@dataclass
class ReviewItem:
    review_id: str
    audit_id: str
    metric_id: str
    ticker: str
    company_name: str
    metric_name: str
    period: str
    original_value: float
    unit: str
    confidence_score: float
    validation_result: str
    reason: str
    source_evidence: str
    status: str
    created_at: str

@dataclass
class AuditHistoryItem:
    history_id: int
    audit_id: str
    metric_name: str
    original_value: float
    corrected_value: Optional[float]
    decision: str
    reason: str
    reviewer_comments: Optional[str]
    timestamp: str

@dataclass
class AccuracyReport:
    report_id: str
    audit_id: str
    ticker: str
    period: str
    total_metrics: int
    correct_metrics: int
    incorrect_metrics: int
    accuracy_pct: float
    auto_approved_count: int
    escalated_count: int
    status: str
    ground_truth_comparison: List[Dict[str, Any]]

