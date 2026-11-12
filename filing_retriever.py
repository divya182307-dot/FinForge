"""
filing_retriever.py - Retrieves actual SEC Form 10-K filings and submissions metadata.

FinAudit AI - Member 1: SEC EDGAR Integration & Financial Extraction
Official SEC API Reference: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
"""

import logging
from typing import Optional, List, Dict, Any
from sec_client import SECClient, SECClientError, SECNotFoundError
from metric_mapping import normalize_cik, get_company_by_identifier, SUPPORTED_COMPANIES
from extraction_models import FilingMetadata

logger = logging.getLogger("FilingRetriever")

SUBMISSIONS_URL_TEMPLATE = "https://data.sec.gov/submissions/CIK{cik}.json"
ARCHIVES_BASE_URL = "https://www.sec.gov/Archives/edgar/data"


class FilingRetriever:
    """
    Retrieves Form 10-K filings from SEC EDGAR.
    """

    def __init__(self, sec_client: Optional[SECClient] = None):
        self.client = sec_client or SECClient()

    def get_submissions(self, cik: str) -> Dict[str, Any]:
        """Fetch full company submissions metadata by CIK."""
        norm_cik = normalize_cik(cik)
        url = SUBMISSIONS_URL_TEMPLATE.format(cik=norm_cik)
        return self.client.get_json(url)

    def fetch_latest_10k(self, cik: str, target_year: Optional[int] = None) -> FilingMetadata:
        """
        Locate and return metadata for the latest Form 10-K filing for the given CIK.
        If target_year is supplied, locates the 10-K for that specific report year.
        """
        norm_cik = normalize_cik(cik)
        submissions = self.get_submissions(norm_cik)
        
        entity_name = submissions.get("name", "Unknown")
        tickers = submissions.get("tickers", [])
        ticker = tickers[0] if tickers else ""
        
        # If ticker is missing in submissions, check our registry
        if not ticker:
            try:
                comp = get_company_by_identifier(norm_cik)
                ticker = comp.ticker
                entity_name = comp.name
            except Exception:
                pass

        recent = submissions.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accn_list = recent.get("accessionNumber", [])
        filing_dates = recent.get("filingDate", [])
        report_dates = recent.get("reportDate", [])
        primary_docs = recent.get("primaryDocument", [])

        if not forms:
            raise SECNotFoundError(f"No filings found for CIK {norm_cik}")

        # Iterate through filings to find 10-K
        for i, form in enumerate(forms):
            if form in ("10-K", "10-K/A"):
                report_date = report_dates[i] if i < len(report_dates) else ""
                filing_date = filing_dates[i] if i < len(filing_dates) else ""
                accn = accn_list[i] if i < len(accn_list) else ""
                pdoc = primary_docs[i] if i < len(primary_docs) else ""
                
                # Derive report year from reportDate (YYYY-MM-DD)
                year = None
                if report_date and len(report_date) >= 4:
                    try:
                        year = int(report_date[:4])
                    except ValueError:
                        pass
                
                if target_year is not None and year != target_year:
                    continue

                cik_int = str(int(norm_cik))
                accn_no_hyphen = accn.replace("-", "")
                filing_url = f"{ARCHIVES_BASE_URL}/{cik_int}/{accn_no_hyphen}/{pdoc}"
                directory_url = f"{ARCHIVES_BASE_URL}/{cik_int}/{accn_no_hyphen}/"

                meta = FilingMetadata(
                    company=entity_name,
                    ticker=ticker,
                    cik=norm_cik,
                    form=form,
                    accession_number=accn,
                    filing_date=filing_date,
                    report_date=report_date,
                    fiscal_year=year,
                    fiscal_period="FY",
                    primary_document=pdoc,
                    filing_url=filing_url,
                    directory_url=directory_url,
                )
                logger.info("Found 10-K for %s (%s): Accn=%s, FY=%s, Filed=%s", ticker, entity_name, accn, year, filing_date)
                return meta

        target_desc = f" for year {target_year}" if target_year else ""
        raise SECNotFoundError(f"No Form 10-K filing found{target_desc} for CIK {norm_cik}")

    def fetch_10k_document(self, filing_meta: FilingMetadata) -> str:
        """Download the primary 10-K document (HTML/iXBRL text)."""
        logger.info("Downloading 10-K document for %s: %s", filing_meta.ticker, filing_meta.filing_url)
        return self.client.get_text(filing_meta.filing_url)

    def list_available_10ks(self, cik: str, limit: int = 5) -> List[FilingMetadata]:
        """Return a list of recent 10-K filings for a company."""
        norm_cik = normalize_cik(cik)
        submissions = self.get_submissions(norm_cik)
        
        entity_name = submissions.get("name", "Unknown")
        tickers = submissions.get("tickers", [])
        ticker = tickers[0] if tickers else ""
        
        recent = submissions.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accn_list = recent.get("accessionNumber", [])
        filing_dates = recent.get("filingDate", [])
        report_dates = recent.get("reportDate", [])
        primary_docs = recent.get("primaryDocument", [])

        results: List[FilingMetadata] = []
        for i, form in enumerate(forms):
            if form in ("10-K", "10-K/A"):
                report_date = report_dates[i] if i < len(report_dates) else ""
                filing_date = filing_dates[i] if i < len(filing_dates) else ""
                accn = accn_list[i] if i < len(accn_list) else ""
                pdoc = primary_docs[i] if i < len(primary_docs) else ""
                
                year = None
                if report_date and len(report_date) >= 4:
                    try:
                        year = int(report_date[:4])
                    except ValueError:
                        pass
                
                cik_int = str(int(norm_cik))
                accn_no_hyphen = accn.replace("-", "")
                filing_url = f"{ARCHIVES_BASE_URL}/{cik_int}/{accn_no_hyphen}/{pdoc}"
                directory_url = f"{ARCHIVES_BASE_URL}/{cik_int}/{accn_no_hyphen}/"

                results.append(FilingMetadata(
                    company=entity_name,
                    ticker=ticker,
                    cik=norm_cik,
                    form=form,
                    accession_number=accn,
                    filing_date=filing_date,
                    report_date=report_date,
                    fiscal_year=year,
                    fiscal_period="FY",
                    primary_document=pdoc,
                    filing_url=filing_url,
                    directory_url=directory_url,
                ))
                if len(results) >= limit:
                    break

        return results

