"""
xbrl_client.py - SEC XBRL Company Facts client for ground-truth financial data retrieval.

FinAudit AI - Member 1: SEC EDGAR Integration & Financial Extraction
Official SEC API Reference: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
"""

import logging
from typing import Optional, Dict, Any, List
from sec_client import SECClient, SECClientError, SECNotFoundError
from metric_mapping import (
    normalize_cik,
    METRIC_DEFINITIONS,
    ORDERED_METRICS,
    get_company_by_identifier,
)
from financial_extractor import normalize_currency_unit
from extraction_models import GroundTruthFact

logger = logging.getLogger("XBRLClient")

COMPANY_FACTS_URL_TEMPLATE = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
COMPANY_CONCEPT_URL_TEMPLATE = "https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/{taxonomy}/{tag}.json"


class XBRLClient:
    """
    Client for SEC EDGAR XBRL Company Facts and Concept APIs.
    Retrieves normalized, official ground-truth XBRL data.
    """

    def __init__(self, sec_client: Optional[SECClient] = None):
        self.client = sec_client or SECClient()

    def get_company_facts(self, cik: str) -> Dict[str, Any]:
        """Fetch all XBRL company facts for a given CIK."""
        norm_cik = normalize_cik(cik)
        url = COMPANY_FACTS_URL_TEMPLATE.format(cik=norm_cik)
        return self.client.get_json(url)

    def get_company_concept(self, cik: str, taxonomy: str, tag: str) -> Dict[str, Any]:
        """Fetch all values for a specific concept/tag for a given CIK."""
        norm_cik = normalize_cik(cik)
        url = COMPANY_CONCEPT_URL_TEMPLATE.format(cik=norm_cik, taxonomy=taxonomy, tag=tag)
        return self.client.get_json(url)

    def extract_ground_truth_for_filing(
        self, cik: str, accession_number: str, target_year: Optional[int] = None
    ) -> Dict[str, GroundTruthFact]:
        """
        Extract ground-truth values for all 8 metrics corresponding to a specific 10-K accession number.
        Returns a dict mapping metric_name -> GroundTruthFact.
        """
        norm_cik = normalize_cik(cik)
        facts_data = self.get_company_facts(norm_cik)
        us_gaap = facts_data.get("facts", {}).get("us-gaap", {})

        results: Dict[str, GroundTruthFact] = {}

        for metric_name in ORDERED_METRICS:
            metric_def = METRIC_DEFINITIONS[metric_name]
            tags = metric_def["xbrl_tags"]
            concept_type = metric_def["concept_type"]

            found_fact: Optional[GroundTruthFact] = None

            for tag in tags:
                if tag not in us_gaap:
                    continue

                units_dict = us_gaap[tag].get("units", {})
                # Look in USD first, then any other currency unit
                unit_keys = ["USD", "usd"] + [k for k in units_dict.keys() if k not in ("USD", "usd")]

                for unit_key in unit_keys:
                    if unit_key not in units_dict:
                        continue
                    
                    entries = units_dict[unit_key]
                    # Filter for entries matching this accession number and Form 10-K
                    matching_entries = [
                        e for e in entries
                        if e.get("accn") == accession_number
                        and e.get("form") in ("10-K", "10-K/A")
                    ]

                    # Further filter by concept type
                    valid_candidates = []
                    for e in matching_entries:
                        # For duration concepts (income statement / cash flow), require fp == "FY"
                        if concept_type == "duration":
                            if e.get("fp") == "FY":
                                valid_candidates.append(e)
                        else:
                            # For instant balance sheet concepts, any balance date matching filing
                            valid_candidates.append(e)

                    if valid_candidates:
                        # Sort by end date or fiscal year descending to take the primary period fact
                        chosen = sorted(valid_candidates, key=lambda x: (x.get("fy", 0), x.get("end", "")))[-1]
                        fy = chosen.get("fy")
                        period_str = f"FY{fy}" if fy else f"FY{target_year or ''}"
                        
                        found_fact = GroundTruthFact(
                            metric=metric_name,
                            xbrl_tag=tag,
                            taxonomy="us-gaap",
                            value=chosen.get("val"),
                            unit=normalize_currency_unit(unit_key),
                            period=period_str,
                            fiscal_year=fy,
                            fiscal_period=chosen.get("fp", "FY"),
                            form=chosen.get("form", "10-K"),
                            accession_number=accession_number,
                            filed_date=chosen.get("filed"),
                            end_date=chosen.get("end"),
                            frame=chosen.get("frame"),
                        )
                        break

                if found_fact:
                    break

            if found_fact:
                results[metric_name] = found_fact
                logger.debug("Ground truth found for %s: %s (%s)", metric_name, found_fact.value, found_fact.xbrl_tag)
            else:
                logger.info("Ground truth metric '%s' not tagged in 10-K %s", metric_name, accession_number)

        return results

    def get_latest_annual_facts(
        self, cik: str, fiscal_year: Optional[int] = None
    ) -> Dict[str, GroundTruthFact]:
        """
        Extract the latest Form 10-K ground-truth facts for all 8 metrics.
        If fiscal_year is specified, retrieves facts specifically for that fiscal year.
        """
        norm_cik = normalize_cik(cik)
        facts_data = self.get_company_facts(norm_cik)
        us_gaap = facts_data.get("facts", {}).get("us-gaap", {})

        results: Dict[str, GroundTruthFact] = {}

        for metric_name in ORDERED_METRICS:
            metric_def = METRIC_DEFINITIONS[metric_name]
            tags = metric_def["xbrl_tags"]
            concept_type = metric_def["concept_type"]

            found_fact: Optional[GroundTruthFact] = None

            for tag in tags:
                if tag not in us_gaap:
                    continue

                units_dict = us_gaap[tag].get("units", {})
                unit_keys = ["USD", "usd"] + [k for k in units_dict.keys() if k not in ("USD", "usd")]

                for unit_key in unit_keys:
                    if unit_key not in units_dict:
                        continue
                    
                    entries = units_dict[unit_key]
                    
                    # Annual 10-K filter: form must be 10-K or 10-K/A
                    filtered = [
                        e for e in entries
                        if e.get("form") in ("10-K", "10-K/A")
                    ]

                    if fiscal_year is not None:
                        filtered = [e for e in filtered if e.get("fy") == fiscal_year]

                    if concept_type == "duration":
                        # Strictly annual (fp == "FY")
                        filtered = [e for e in filtered if e.get("fp") == "FY"]

                    if filtered:
                        # Pick latest by fiscal year and end date
                        latest = sorted(filtered, key=lambda x: (x.get("fy", 0), x.get("end", "")))[-1]
                        fy = latest.get("fy")
                        period_str = f"FY{fy}" if fy else "FY"
                        
                        found_fact = GroundTruthFact(
                            metric=metric_name,
                            xbrl_tag=tag,
                            taxonomy="us-gaap",
                            value=latest.get("val"),
                            unit=normalize_currency_unit(unit_key),
                            period=period_str,
                            fiscal_year=fy,
                            fiscal_period=latest.get("fp", "FY"),
                            form=latest.get("form", "10-K"),
                            accession_number=latest.get("accn", ""),
                            filed_date=latest.get("filed"),
                            end_date=latest.get("end"),
                            frame=latest.get("frame"),
                        )
                        break

                if found_fact:
                    break

            if found_fact:
                results[metric_name] = found_fact

        return results
