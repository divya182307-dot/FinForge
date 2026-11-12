"""
extraction_models.py - Data models for SEC EDGAR financial extraction and verification.

FinAudit AI - Member 1: SEC EDGAR Integration & Financial Extraction
"""

from typing import Optional, Union, List, Dict, Any
from pydantic import BaseModel, Field


class CompanyInfo(BaseModel):
    """Supported company information."""
    name: str
    ticker: str
    cik: str  # 10-digit zero-padded CIK string


class FilingMetadata(BaseModel):
    """Metadata for a retrieved SEC 10-K filing."""
    company: str
    ticker: str
    cik: str
    form: str = "10-K"
    accession_number: str
    filing_date: str
    report_date: str
    fiscal_year: Optional[int] = None
    fiscal_period: str = "FY"
    primary_document: str
    filing_url: str
    directory_url: str


class MetricExtraction(BaseModel):
    """
    Standard output contract for an extracted financial metric.
    
    Shared JSON Output Contract:
    {
      "company": "Apple",
      "ticker": "AAPL",
      "cik": "0000320193",
      "metric": "Revenue",
      "value": 0,
      "unit": "USD",
      "period": "FY2025",
      "filing_url": "actual SEC filing URL",
      "accession_number": "actual accession number",
      "source_evidence": "original filing evidence",
      "xbrl_tag": "actual tag",
      "confidence": null
    }
    """
    company: str
    ticker: str
    cik: str
    metric: str
    value: Optional[Union[float, int]] = None
    unit: Optional[str] = "USD"
    period: Optional[str] = None
    filing_url: Optional[str] = None
    accession_number: Optional[str] = None
    source_evidence: Optional[str] = None
    xbrl_tag: Optional[str] = None
    confidence: Optional[float] = None
    extraction_method: Optional[str] = "ixbrl"
    decimals: Optional[int] = None
    scale: Optional[int] = None

    def to_contract_dict(self) -> Dict[str, Any]:
        """Return exactly the fields defined in the shared JSON contract."""
        return {
            "company": self.company,
            "ticker": self.ticker,
            "cik": self.cik,
            "metric": self.metric,
            "value": self.value,
            "unit": self.unit,
            "period": self.period,
            "filing_url": self.filing_url,
            "accession_number": self.accession_number,
            "source_evidence": self.source_evidence,
            "xbrl_tag": self.xbrl_tag,
            "confidence": self.confidence,
        }


class GroundTruthFact(BaseModel):
    """A ground truth financial fact retrieved directly from SEC XBRL Company Facts API."""
    metric: str
    xbrl_tag: str
    taxonomy: str = "us-gaap"
    value: Optional[Union[float, int]] = None
    unit: str = "USD"
    period: str
    fiscal_year: Optional[int] = None
    fiscal_period: str = "FY"
    form: str = "10-K"
    accession_number: str
    filed_date: Optional[str] = None
    end_date: Optional[str] = None
    frame: Optional[str] = None


class MetricVerification(BaseModel):
    """Comparison between an extracted metric and its SEC XBRL ground truth fact."""
    metric: str
    extracted_value: Optional[Union[float, int]] = None
    ground_truth_value: Optional[Union[float, int]] = None
    unit_match: bool = False
    period_match: bool = False
    concept_match: bool = False
    absolute_difference: Optional[float] = None
    percentage_difference: Optional[float] = None
    status: str  # EXACT_MATCH, CLOSE_MATCH, DISCREPANCY, MISSING_EXTRACTED, MISSING_GROUND_TRUTH
    details: str
    xbrl_tag: Optional[str] = None
    ground_truth_tag: Optional[str] = None


class VerificationSummary(BaseModel):
    """Aggregate ground-truth verification summary for a company filing."""
    company: str
    ticker: str
    cik: str
    period: str
    filing_url: Optional[str] = None
    accession_number: Optional[str] = None
    total_metrics: int = 8
    verified_metrics: int = 0
    match_count: int = 0
    discrepancy_count: int = 0
    missing_count: int = 0
    accuracy_rate: float = 0.0
    metrics: List[MetricVerification] = Field(default_factory=list)

