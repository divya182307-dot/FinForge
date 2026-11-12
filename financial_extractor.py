"""
financial_extractor.py - Financial metrics extractor from Form 10-K filings.

FinAudit AI - Member 1: SEC EDGAR Integration & Financial Extraction
Extracts at least 8 mandatory financial metrics from SEC 10-K filings using
high-precision inline XBRL (iXBRL) and financial statement parsing.
"""

import re
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Union

from sec_client import SECClient
from filing_retriever import FilingRetriever
from metric_mapping import (
    normalize_cik,
    get_company_by_identifier,
    SUPPORTED_COMPANIES,
    METRIC_DEFINITIONS,
    ORDERED_METRICS,
)
from extraction_models import (
    MetricExtraction,
    FilingMetadata,
    CompanyInfo,
)

logger = logging.getLogger("FinancialExtractor")


def normalize_currency_unit(raw_unit: Optional[str]) -> str:
    """Normalize XBRL unitRef (e.g. 'u_usd', 'iso4217_USD', 'USD', '$') to standard ISO currency code."""
    if not raw_unit:
        return "USD"
    u = raw_unit.strip().upper()
    if "USD" in u or u in ("$", "US_DOLLAR", "DOLLARS"):
        return "USD"
    if "EUR" in u or u == "€":
        return "EUR"
    if "GBP" in u or u == "£":
        return "GBP"
    if "JPY" in u or u == "¥":
        return "JPY"
    if "CAD" in u:
        return "CAD"
    return u


class FinancialExtractor:
    """
    Extracts financial metrics from SEC Form 10-K filings.
    
    Supports:
    - Primary Inline XBRL (iXBRL) extraction with context resolution (consolidated annual 12-month periods)
    - Source evidence snippet extraction
    - Accurate scaling (thousands, millions, billions)
    - Handling missing metrics gracefully (never default to zero)
    - Generating standardized shared JSON output contract
    """

    def __init__(self, sec_client: Optional[SECClient] = None):
        self.client = sec_client or SECClient()
        self.retriever = FilingRetriever(self.client)

    def extract_metrics_from_filing(
        self,
        filing_meta: FilingMetadata,
        html_content: Optional[str] = None
    ) -> List[MetricExtraction]:
        """
        Extract the 8 financial metrics from a Form 10-K filing.
        """
        if not html_content:
            html_content = self.retriever.fetch_10k_document(filing_meta)

        logger.info(
            "Extracting metrics for %s (CIK %s) from 10-K %s",
            filing_meta.ticker,
            filing_meta.cik,
            filing_meta.accession_number
        )

        # 1. Parse XBRL contexts to isolate consolidated annual contexts from segments / quarters
        contexts = self._parse_contexts(html_content)

        # 2. Parse inline XBRL nonFraction tags
        facts_by_tag = self._parse_ixbrl_facts(html_content, contexts)

        # 3. Match metrics
        extracted_list: List[MetricExtraction] = []
        period_str = f"FY{filing_meta.fiscal_year}" if filing_meta.fiscal_year else "FY"

        for metric_name in ORDERED_METRICS:
            metric_def = METRIC_DEFINITIONS[metric_name]
            ctype = metric_def["concept_type"]
            cand_tags = metric_def["xbrl_tags"]

            best_entry: Optional[Dict[str, Any]] = None
            best_tag: Optional[str] = None

            for ctag in cand_tags:
                if ctag in facts_by_tag:
                    entries = facts_by_tag[ctag]
                    # Filter candidates:
                    # - Must NOT have segment (must be consolidated company total)
                    # - Duration concepts: duration >= 350 days (full fiscal year)
                    # - Date must align with filing report_date or latest year
                    filtered = []
                    for e in entries:
                        ctx = e.get("ctx", {})
                        if ctx.get("has_segment"):
                            continue
                        
                        if ctype == "duration":
                            days = ctx.get("days", 0)
                            if days >= 350:
                                filtered.append(e)
                        else: # instant
                            filtered.append(e)

                    if filtered:
                        # Sort by end date or instant date descending to select primary period
                        chosen = sorted(
                            filtered,
                            key=lambda x: (x["ctx"].get("end") or x["ctx"].get("instant") or "")
                        )[-1]
                        best_entry = chosen
                        best_tag = ctag
                        break

            if best_entry is not None:
                # Format snippet for source evidence
                raw_snippet = best_entry.get("snippet", "")
                evidence = (
                    f"Filing {filing_meta.accession_number} [{best_entry.get('raw_tag', best_tag)}]: "
                    f"Reported value '{best_entry['raw_text']}' with scale=10^{best_entry['scale']} "
                    f"(Context: {best_entry.get('cid')}, End: {best_entry['ctx'].get('end') or best_entry['ctx'].get('instant')})"
                )
                
                # Determine period from fact if possible
                fact_end = best_entry["ctx"].get("end") or best_entry["ctx"].get("instant")
                metric_period = period_str
                if fact_end and len(fact_end) >= 4:
                    metric_period = f"FY{fact_end[:4]}"

                extraction = MetricExtraction(
                    company=filing_meta.company,
                    ticker=filing_meta.ticker,
                    cik=filing_meta.cik,
                    metric=metric_name,
                    value=best_entry["val"],
                    unit=normalize_currency_unit(best_entry.get("unit")),
                    period=metric_period,
                    filing_url=filing_meta.filing_url,
                    accession_number=filing_meta.accession_number,
                    source_evidence=evidence,
                    xbrl_tag=best_tag,
                    confidence=1.0,
                    extraction_method="ixbrl",
                    scale=best_entry.get("scale"),
                )
            else:
                # Metric was not found in filing tags.
                # Per requirements: "Never treat missing information as zero."
                evidence_msg = (
                    f"Metric '{metric_name}' is not reported or tagged as an individual concept "
                    f"in Form 10-K accession {filing_meta.accession_number}."
                )
                extraction = MetricExtraction(
                    company=filing_meta.company,
                    ticker=filing_meta.ticker,
                    cik=filing_meta.cik,
                    metric=metric_name,
                    value=None,  # Explicitly None, NEVER 0!
                    unit="USD",
                    period=period_str,
                    filing_url=filing_meta.filing_url,
                    accession_number=filing_meta.accession_number,
                    source_evidence=evidence_msg,
                    xbrl_tag=None,
                    confidence=None,
                    extraction_method="absent_in_filing",
                )

            extracted_list.append(extraction)

        return extracted_list

    def extract_financial_metrics(
        self, cik_or_ticker: str, target_year: Optional[int] = None
    ) -> List[MetricExtraction]:
        """
        Convenience function to fetch latest 10-K for a company and extract the 8 metrics.
        """
        comp = get_company_by_identifier(cik_or_ticker)
        filing_meta = self.retriever.fetch_latest_10k(comp.cik, target_year=target_year)
        html_doc = self.retriever.fetch_10k_document(filing_meta)
        return self.extract_metrics_from_filing(filing_meta, html_doc)

    def _parse_contexts(self, html_content: str) -> Dict[str, Dict[str, Any]]:
        """
        Parse XBRL contexts to extract timeframe and segmental dimensions.
        """
        contexts: Dict[str, Dict[str, Any]] = {}
        context_pattern = re.compile(
            r'<(?:\w+:)?context\s+id=["\']([^"\']+)["\']>(.*?)</(?:\w+:)?context>',
            re.DOTALL | re.IGNORECASE
        )

        for match in context_pattern.finditer(html_content):
            cid = match.group(1)
            cbody = match.group(2)

            # Check for segment or scenario (indicates dimensional breakdown)
            has_segment = bool(re.search(r'<(?:\w+:)?(?:segment|scenario)>', cbody, re.IGNORECASE))

            start_m = re.search(r'<(?:\w+:)?startDate>([^<]+)</(?:\w+:)?startDate>', cbody, re.IGNORECASE)
            end_m = re.search(r'<(?:\w+:)?endDate>([^<]+)</(?:\w+:)?endDate>', cbody, re.IGNORECASE)
            instant_m = re.search(r'<(?:\w+:)?instant>([^<]+)</(?:\w+:)?instant>', cbody, re.IGNORECASE)

            start = start_m.group(1).strip() if start_m else None
            end = end_m.group(1).strip() if end_m else None
            instant = instant_m.group(1).strip() if instant_m else None

            days = 0
            if start and end:
                try:
                    d1 = datetime.strptime(start, "%Y-%m-%d")
                    d2 = datetime.strptime(end, "%Y-%m-%d")
                    days = (d2 - d1).days
                except Exception:
                    pass

            contexts[cid] = {
                "has_segment": has_segment,
                "start": start,
                "end": end,
                "instant": instant,
                "days": days,
            }

        return contexts

    def _parse_ixbrl_facts(
        self, html_content: str, contexts: Dict[str, Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Parse inline XBRL nonFraction numeric elements from the 10-K document.
        """
        facts_by_tag: Dict[str, List[Dict[str, Any]]] = {}
        tag_pattern = re.compile(
            r'<ix:nonFraction\s+([^>]+)>(.*?)</ix:nonFraction>',
            re.DOTALL | re.IGNORECASE
        )

        for match in tag_pattern.finditer(html_content):
            attrs = match.group(1)
            inner_text = match.group(2)

            name_m = re.search(r'name=["\']([^"\']+)["\']', attrs)
            if not name_m:
                continue

            tag_full = name_m.group(1)
            tag_clean = tag_full.split(":")[-1]

            ctx_m = re.search(r'contextRef=["\']([^"\']+)["\']', attrs)
            cid = ctx_m.group(1) if ctx_m else ""
            ctx = contexts.get(cid, {})

            scale_m = re.search(r'scale=["\']([^"\']+)["\']', attrs)
            unit_m = re.search(r'unitRef=["\']([^"\']+)["\']', attrs)
            sign_m = re.search(r'sign=["\']([^"\']+)["\']', attrs)

            scale = int(scale_m.group(1)) if scale_m else 0
            sign = -1 if (sign_m and sign_m.group(1) == "-") else 1
            clean_text = re.sub(r'<[^>]+>', '', inner_text).strip()
            num_str = clean_text.replace(",", "").replace("$", "").replace("(", "").replace(")", "").strip()

            try:
                numeric_val = float(num_str) * (10 ** scale) * sign
                # If cleanly integer, cast to int
                if numeric_val.is_integer():
                    numeric_val = int(numeric_val)
            except ValueError:
                continue

            snippet = f"<ix:nonFraction {attrs.strip()}>{clean_text}</ix:nonFraction>"

            entry = {
                "val": numeric_val,
                "raw_text": clean_text,
                "scale": scale,
                "unit": unit_m.group(1) if unit_m else "USD",
                "cid": cid,
                "ctx": ctx,
                "raw_tag": tag_full,
                "snippet": snippet[:250],
            }

            if tag_clean not in facts_by_tag:
                facts_by_tag[tag_clean] = []
            facts_by_tag[tag_clean].append(entry)

        return facts_by_tag
