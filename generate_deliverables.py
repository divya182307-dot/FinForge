"""
generate_deliverables.py - Generates actual real SEC extraction and verification output files.

FinAudit AI - Member 1: SEC EDGAR Integration & Financial Extraction
"""

import json
import logging
from metric_mapping import SUPPORTED_COMPANIES
from fin_sec_api import (
    fetch_latest_10k,
    extract_financial_metrics,
    get_ground_truth_for_filing,
    compare_with_ground_truth,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("Deliverables")

def main():
    logger.info("Generating sample real extraction and comparison deliverables for all 5 companies...")
    
    all_extractions = {}
    all_comparisons = {}

    for ticker, comp in SUPPORTED_COMPANIES.items():
        logger.info("Processing %s (%s)...", ticker, comp.name)
        meta = fetch_latest_10k(comp.cik)
        metrics = extract_financial_metrics(comp.cik)
        ground_truth = get_ground_truth_for_filing(comp.cik, meta.accession_number)
        summary = compare_with_ground_truth(metrics, ground_truth)
        
        # Serialize to contract dict list
        all_extractions[ticker] = [m.to_contract_dict() for m in metrics]
        all_comparisons[ticker] = summary.model_dump()
        
        logger.info(
            "%s Done: %d metrics extracted, %d/%d verified matches (%.1f%% accuracy)",
            ticker,
            len(metrics),
            summary.match_count,
            summary.verified_metrics,
            summary.accuracy_rate,
        )

    # Write sample_sec_extraction.json
    with open("sample_sec_extraction.json", "w", encoding="utf-8") as f:
        json.dump(all_extractions, f, indent=2)
    logger.info("Saved sample_sec_extraction.json")

    # Write sample_xbrl_comparison.json
    with open("sample_xbrl_comparison.json", "w", encoding="utf-8") as f:
        json.dump(all_comparisons, f, indent=2)
    logger.info("Saved sample_xbrl_comparison.json")

if __name__ == "__main__":
    main()

