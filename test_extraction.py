"""
test_extraction.py - Comprehensive test suite for FinAudit AI Member 1 module.

FinAudit AI - Member 1: SEC EDGAR Integration & Financial Extraction
Tests:
1. Supported company registry and CIK resolution.
2. Shared JSON contract compliance.
3. Missing metric handling (never defaults to 0).
4. Comparison and verification logic (exact match, discrepancy, missing handling).
5. Error handling on invalid CIK / 404 responses.
6. Live SEC EDGAR filing retrieval and extraction for supported companies.
7. End-to-end ground truth verification against SEC XBRL Company Facts.
"""

import unittest
import json
import logging
from typing import Dict, Any

from extraction_models import (
    MetricExtraction,
    GroundTruthFact,
    MetricVerification,
    VerificationSummary,
    CompanyInfo,
)
from metric_mapping import (
    SUPPORTED_COMPANIES,
    ORDERED_METRICS,
    normalize_cik,
    get_company_by_identifier,
)
from sec_client import SECClient, SECNotFoundError
from filing_retriever import FilingRetriever
from xbrl_client import XBRLClient
from financial_extractor import FinancialExtractor
from verification import compare_with_ground_truth
from fin_sec_api import (
    get_supported_companies,
    fetch_latest_10k,
    extract_financial_metrics,
    get_company_facts,
    verify_company_extraction,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestExtraction")


class TestSupportedCompanies(unittest.TestCase):
    """Test supported company configuration and CIK normalization."""

    def test_mandated_companies_present(self):
        mandated_tickers = ["AAPL", "MSFT", "AMZN", "GOOGL", "NVDA"]
        for ticker in mandated_tickers:
            self.assertIn(ticker, SUPPORTED_COMPANIES)
            comp = SUPPORTED_COMPANIES[ticker]
            self.assertEqual(len(comp.cik), 10)
            self.assertTrue(comp.cik.isdigit())

    def test_cik_normalization(self):
        self.assertEqual(normalize_cik("320193"), "0000320193")
        self.assertEqual(normalize_cik("0000320193"), "0000320193")
        self.assertEqual(normalize_cik("CIK0000789019"), "0000789019")

    def test_get_company_lookup(self):
        comp = get_company_by_identifier("AAPL")
        self.assertEqual(comp.name, "Apple Inc.")
        comp_cik = get_company_by_identifier("0000320193")
        self.assertEqual(comp_cik.ticker, "AAPL")


class TestExtractionModelsAndContract(unittest.TestCase):
    """Test data models and the shared JSON output contract."""

    def test_shared_json_contract_keys(self):
        ext = MetricExtraction(
            company="Apple",
            ticker="AAPL",
            cik="0000320193",
            metric="Revenue",
            value=391035000000,
            unit="USD",
            period="FY2024",
            filing_url="https://www.sec.gov/Archives/edgar/data/320193/000032019324000106/aapl-20240928.htm",
            accession_number="0000320193-24-000106",
            source_evidence="<ix:nonFraction name=\"us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax\">391,035</ix:nonFraction>",
            xbrl_tag="RevenueFromContractWithCustomerExcludingAssessedTax",
            confidence=1.0,
        )

        contract_dict = ext.to_contract_dict()
        expected_keys = {
            "company",
            "ticker",
            "cik",
            "metric",
            "value",
            "unit",
            "period",
            "filing_url",
            "accession_number",
            "source_evidence",
            "xbrl_tag",
            "confidence",
        }
        self.assertEqual(set(contract_dict.keys()), expected_keys)
        self.assertEqual(contract_dict["value"], 391035000000)
        self.assertEqual(contract_dict["metric"], "Revenue")

    def test_missing_metric_never_zero(self):
        """Verify missing metrics have value=None and confidence=None, NEVER 0."""
        missing_ext = MetricExtraction(
            company="Amazon",
            ticker="AMZN",
            cik="0001018724",
            metric="Total Liabilities",
            value=None,  # MUST BE None, NOT 0
            unit="USD",
            period="FY2025",
            source_evidence="Metric not reported as single tag",
            confidence=None,
        )
        self.assertIsNone(missing_ext.value)
        self.assertNotEqual(missing_ext.value, 0)
        self.assertIsNone(missing_ext.confidence)


class TestVerificationLogic(unittest.TestCase):
    """Test ground-truth verification comparisons."""

    def setUp(self):
        self.extracted = [
            MetricExtraction(
                company="Apple",
                ticker="AAPL",
                cik="0000320193",
                metric="Revenue",
                value=400000000000,
                unit="USD",
                period="FY2026",
                xbrl_tag="RevenueFromContractWithCustomerExcludingAssessedTax",
            ),
            MetricExtraction(
                company="Apple",
                ticker="AAPL",
                cik="0000320193",
                metric="Net Income",
                value=100000000000,
                unit="USD",
                period="FY2026",
                xbrl_tag="NetIncomeLoss",
            ),
            MetricExtraction(
                company="Apple",
                ticker="AAPL",
                cik="0000320193",
                metric="Total Liabilities",
                value=None,  # Missing
                unit="USD",
                period="FY2026",
            ),
        ]

    def test_exact_match(self):
        facts = {
            "Revenue": GroundTruthFact(
                metric="Revenue",
                xbrl_tag="RevenueFromContractWithCustomerExcludingAssessedTax",
                value=400000000000,
                unit="USD",
                period="FY2026",
                fiscal_year=2026,
                accession_number="0000320193-26-000026",
            )
        }
        summary = compare_with_ground_truth(self.extracted[:1], facts)
        self.assertEqual(summary.match_count, 1)
        self.assertEqual(summary.discrepancy_count, 0)
        self.assertEqual(summary.metrics[0].status, "EXACT_MATCH")
        self.assertEqual(summary.accuracy_rate, 100.0)

    def test_discrepancy_detection(self):
        facts = {
            "Net Income": GroundTruthFact(
                metric="Net Income",
                xbrl_tag="NetIncomeLoss",
                value=120000000000,  # Differs from extracted 100000000000
                unit="USD",
                period="FY2026",
                fiscal_year=2026,
                accession_number="0000320193-26-000026",
            )
        }
        summary = compare_with_ground_truth(self.extracted[1:2], facts)
        self.assertEqual(summary.discrepancy_count, 1)
        self.assertEqual(summary.match_count, 0)
        self.assertEqual(summary.metrics[0].status, "DISCREPANCY")
        self.assertAlmostEqual(summary.metrics[0].percentage_difference, 16.6666, places=2)

    def test_missing_handling(self):
        facts = {}
        summary = compare_with_ground_truth(self.extracted[2:], facts)
        self.assertEqual(summary.metrics[0].status, "NOT_REPORTED_IN_XBRL")
        self.assertIsNone(summary.metrics[0].extracted_value)


class TestInvalidAPIResponses(unittest.TestCase):
    """Test error handling on invalid CIK and 404 responses."""

    def test_invalid_cik_not_found(self):
        client = SECClient()
        retriever = FilingRetriever(client)
        with self.assertRaises((SECNotFoundError, ValueError)):
            retriever.get_submissions("9999999999")


class TestLiveSECIntegration(unittest.TestCase):
    """
    Live integration test against SEC EDGAR API for 3+ companies.
    Retrieves Form 10-K, extracts all 8 metrics, and verifies against SEC XBRL facts.
    """

    @classmethod
    def setUpClass(cls):
        cls.test_companies = ["AAPL", "MSFT", "NVDA"]

    def test_live_retrieval_and_extraction_for_three_companies(self):
        for ticker in self.test_companies:
            logger.info("Running Live SEC Integration test for %s...", ticker)
            comp = SUPPORTED_COMPANIES[ticker]
            
            # 1. Fetch 10-K metadata
            meta = fetch_latest_10k(comp.cik)
            self.assertEqual(meta.form, "10-K")
            self.assertTrue(meta.filing_url.startswith("https://www.sec.gov/Archives/edgar/data/"))
            self.assertTrue(len(meta.accession_number) > 10)

            # 2. Extract metrics
            metrics = extract_financial_metrics(comp.cik)
            self.assertEqual(len(metrics), 8)

            extracted_names = [m.metric for m in metrics]
            self.assertEqual(extracted_names, ORDERED_METRICS)

            # Check that mandatory revenue and net income are positive real numbers
            rev = next(m for m in metrics if m.metric == "Revenue")
            net_inc = next(m for m in metrics if m.metric == "Net Income")
            self.assertIsNotNone(rev.value)
            self.assertGreater(rev.value, 1_000_000_000)
            self.assertEqual(rev.unit, "USD")
            self.assertTrue(rev.period.startswith("FY"))
            self.assertIsNotNone(rev.source_evidence)

            self.assertIsNotNone(net_inc.value)
            self.assertGreater(net_inc.value, 1_000_000_000)

            # 3. Verify against official SEC XBRL ground truth facts
            summary = verify_company_extraction(comp.cik)
            self.assertGreaterEqual(summary.accuracy_rate, 85.0)
            logger.info(
                "%s Verification: %d/%d matches (Accuracy: %.1f%%)",
                ticker,
                summary.match_count,
                summary.verified_metrics,
                summary.accuracy_rate
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)

