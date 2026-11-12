"""
fin_sec_api.py - Public Integration API & FastAPI Router for FinAudit AI Member 1.

FinAudit AI - Member 1: SEC EDGAR Integration & Financial Extraction
Exposes all mandated integration functions and FastAPI endpoints:
- get_supported_companies()
- fetch_latest_10k(cik)
- extract_financial_metrics(cik)
- get_company_facts(cik)
- compare_with_ground_truth(extracted_data, facts_data)
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query

from sec_client import SECClient
from filing_retriever import FilingRetriever
from xbrl_client import XBRLClient
from financial_extractor import FinancialExtractor
from metric_mapping import (
    SUPPORTED_COMPANIES,
    normalize_cik,
    get_company_by_identifier,
)
from extraction_models import (
    CompanyInfo,
    FilingMetadata,
    MetricExtraction,
    GroundTruthFact,
    VerificationSummary,
)
from verification import compare_with_ground_truth

logger = logging.getLogger("FinSecAPI")

# Shared singletons
_sec_client = SECClient()
_retriever = FilingRetriever(_sec_client)
_xbrl_client = XBRLClient(_sec_client)
_extractor = FinancialExtractor(_sec_client)

# ==========================================
# 1. Mandatory Core Python Functions
# ==========================================

def get_supported_companies() -> List[Dict[str, Any]]:
    """
    Return the list of 5 supported companies (name, ticker, CIK).
    """
    return [comp.model_dump() for comp in SUPPORTED_COMPANIES.values()]


def fetch_latest_10k(cik: str, target_year: Optional[int] = None) -> FilingMetadata:
    """
    Retrieve filing metadata and URLs for the latest Form 10-K filing for the given CIK or ticker.
    """
    comp = get_company_by_identifier(cik)
    return _retriever.fetch_latest_10k(comp.cik, target_year=target_year)


def extract_financial_metrics(cik: str, target_year: Optional[int] = None) -> List[MetricExtraction]:
    """
    Extract the 8 financial metrics from the latest Form 10-K filing for the given CIK or ticker.
    Returns list of MetricExtraction objects matching the shared JSON output contract.
    """
    comp = get_company_by_identifier(cik)
    filing_meta = _retriever.fetch_latest_10k(comp.cik, target_year=target_year)
    return _extractor.extract_metrics_from_filing(filing_meta)


def get_company_facts(cik: str) -> Dict[str, Any]:
    """
    Retrieve raw SEC XBRL Company Facts JSON from SEC EDGAR.
    """
    comp = get_company_by_identifier(cik)
    return _xbrl_client.get_company_facts(comp.cik)


def get_ground_truth_for_filing(cik: str, accession_number: str) -> Dict[str, GroundTruthFact]:
    """
    Retrieve the 8 ground-truth facts for a specific filing accession number from SEC XBRL.
    """
    comp = get_company_by_identifier(cik)
    return _xbrl_client.extract_ground_truth_for_filing(comp.cik, accession_number)


def verify_company_extraction(cik: str, target_year: Optional[int] = None) -> VerificationSummary:
    """
    Convenience function that extracts metrics and immediately verifies them against SEC XBRL facts.
    """
    comp = get_company_by_identifier(cik)
    filing_meta = fetch_latest_10k(comp.cik, target_year=target_year)
    extracted = _extractor.extract_metrics_from_filing(filing_meta)
    ground_truth = _xbrl_client.extract_ground_truth_for_filing(comp.cik, filing_meta.accession_number)
    return compare_with_ground_truth(extracted, ground_truth)


# ==========================================
# 2. FastAPI APIRouter for Backend Integration
# ==========================================

router = APIRouter(prefix="/api/v1/sec", tags=["SEC EDGAR Integration"])


@router.get("/companies", response_model=List[CompanyInfo], summary="Get Supported Companies")
def api_get_supported_companies():
    """Returns the list of 5 supported companies."""
    return list(SUPPORTED_COMPANIES.values())


@router.get("/filings/{identifier}/latest-10k", response_model=FilingMetadata, summary="Fetch Latest 10-K Metadata")
def api_fetch_latest_10k(identifier: str, year: Optional[int] = Query(None, description="Optional target fiscal year")):
    """Fetch latest Form 10-K filing metadata and SEC document URLs by CIK or ticker."""
    try:
        return fetch_latest_10k(identifier, target_year=year)
    except Exception as e:
        logger.error("Error fetching 10-K for %s: %s", identifier, e)
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/extract/{identifier}", response_model=List[MetricExtraction], summary="Extract Financial Metrics")
def api_extract_financial_metrics(identifier: str, year: Optional[int] = Query(None, description="Optional target fiscal year")):
    """Extract the 8 financial metrics from the 10-K filing matching the shared JSON contract."""
    try:
        return extract_financial_metrics(identifier, target_year=year)
    except Exception as e:
        logger.error("Error extracting metrics for %s: %s", identifier, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/facts/{identifier}", summary="Get Raw SEC XBRL Company Facts")
def api_get_company_facts(identifier: str):
    """Retrieve raw SEC XBRL Company Facts from data.sec.gov."""
    try:
        return get_company_facts(identifier)
    except Exception as e:
        logger.error("Error fetching company facts for %s: %s", identifier, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/verify/{identifier}", response_model=VerificationSummary, summary="Verify Extracted Metrics with Ground Truth")
def api_verify_extraction(identifier: str, year: Optional[int] = Query(None, description="Optional target fiscal year")):
    """Extract metrics and verify them against SEC XBRL ground-truth facts."""
    try:
        return verify_company_extraction(identifier, target_year=year)
    except Exception as e:
        logger.error("Error verifying extraction for %s: %s", identifier, e)
        raise HTTPException(status_code=500, detail=str(e))

