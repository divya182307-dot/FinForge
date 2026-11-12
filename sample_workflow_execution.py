"""
FinAudit AI - Sample Workflow Execution Demo (Member 2)
Demonstrates the full agentic auditing lifecycle:
1. Loading real SEC EDGAR extraction payload (Apple Inc. FY2026)
2. Calculating explainable confidence scores
3. Running Accounting Equation & Anomaly Validations
4. Making automated routing decision
5. Automatic Approval Scenario
6. Human-in-the-Loop Escalation, LangGraph Interrupt, and Resumption with Correction
"""

import json
from audit_graph import create_audit_graph
from review_handler import (
    run_audit_workflow,
    submit_human_decision,
    get_audit_state,
    calculate_confidence,
    validate_accounting_equation
)


def print_banner(text: str):
    print("\n" + "=" * 80)
    print(f" {text}")
    print("=" * 80)


def demo_auto_approval():
    print_banner("DEMO SCENARIO 1: HIGH-CONFIDENCE AUTOMATIC APPROVAL")
    sample_payload = {
        "company": "Apple Inc.",
        "ticker": "AAPL",
        "period": "FY2026",
        "metrics": [
            {
                "company": "Apple Inc.",
                "ticker": "AAPL",
                "metric": "Revenue",
                "value": 478834000000.0,
                "unit": "USD",
                "period": "FY2026",
                "filing_url": "https://www.sec.gov/Archives/edgar/data/320193/000032019326000026/aapl-20260926.htm",
                "source_evidence": "Filing 0000320193-26-000026 [us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax]: Item 8 reported value '478,834' with scale=10^6",
                "xbrl_tag": "RevenueFromContractWithCustomerExcludingAssessedTax",
                "extraction_method": "xbrl_facts"
            },
            {
                "company": "Apple Inc.",
                "ticker": "AAPL",
                "metric": "Total Assets",
                "value": 404548000000.0,
                "unit": "USD",
                "period": "FY2026",
                "source_evidence": "Filing 0000320193-26-000026 [us-gaap:Assets]: Balance Sheet Item 8 reported '404,548' with scale=10^6",
                "xbrl_tag": "Assets",
                "extraction_method": "xbrl_facts"
            },
            {
                "company": "Apple Inc.",
                "ticker": "AAPL",
                "metric": "Total Liabilities",
                "value": 292455000000.0,
                "unit": "USD",
                "period": "FY2026",
                "source_evidence": "Filing 0000320193-26-000026 [us-gaap:Liabilities]: Balance Sheet Item 8 reported '292,455' with scale=10^6",
                "xbrl_tag": "Liabilities",
                "extraction_method": "xbrl_facts"
            },
            {
                "company": "Apple Inc.",
                "ticker": "AAPL",
                "metric": "Shareholders' Equity",
                "value": 112093000000.0,
                "unit": "USD",
                "period": "FY2026",
                "source_evidence": "Filing 0000320193-26-000026 [us-gaap:StockholdersEquity]: Balance Sheet Item 8 reported '112,093' with scale=10^6",
                "xbrl_tag": "StockholdersEquity",
                "extraction_method": "xbrl_facts"
            }
        ]
    }

    print("Running audit workflow...")
    result = run_audit_workflow(sample_payload, audit_id="demo_auto_1")

    print(f"\nAudit Status: {result.get('status')}")
    print(f"Overall Decision: {result.get('audit_decision')}")
    print("\nShared JSON Output Contracts:")
    for sc in result.get("shared_contracts", []):
        print(json.dumps(sc, indent=2))


def demo_human_review_and_resumption():
    print_banner("DEMO SCENARIO 2: HUMAN-IN-THE-LOOP INTERRUPT & CORRECTION RESUMPTION")
    escalation_payload = {
        "company": "Apple Inc.",
        "ticker": "AAPL",
        "period": "FY2026",
        "metrics": [
            {
                "company": "Apple Inc.",
                "ticker": "AAPL",
                "metric": "Revenue",
                "value": 478834000000.0,
                "unit": "USD",
                "period": "FY2026",
                "source_evidence": "Item 8 Statement of Operations",
                "xbrl_tag": "RevenueFromContractWithCustomerExcludingAssessedTax"
            },
            {
                "company": "Apple Inc.",
                "ticker": "AAPL",
                "metric": "Total Assets",
                "value": 550000000000.0,  # Corrupted OCR / extraction anomaly
                "unit": "USD",
                "period": "FY2026",
                "source_evidence": "Balance sheet scan",
                "xbrl_tag": "Assets"
            },
            {
                "company": "Apple Inc.",
                "ticker": "AAPL",
                "metric": "Total Liabilities",
                "value": 292455000000.0,
                "unit": "USD",
                "period": "FY2026",
                "source_evidence": "Balance Sheet Item 8",
                "xbrl_tag": "Liabilities"
            },
            {
                "company": "Apple Inc.",
                "ticker": "AAPL",
                "metric": "Shareholders' Equity",
                "value": 112093000000.0,
                "unit": "USD",
                "period": "FY2026",
                "source_evidence": "Balance Sheet Item 8",
                "xbrl_tag": "StockholdersEquity"
            }
        ]
    }

    audit_id = "demo_human_escalation_2"
    print(f"1. Launching audit workflow for {audit_id}...")
    interrupted_result = run_audit_workflow(escalation_payload, audit_id=audit_id)

    print(f"Workflow Interrupted? {'__interrupt__' in interrupted_result}")
    print(f"Decision: {interrupted_result.get('audit_decision')}")
    print(f"Escalation reasons: {interrupted_result.get('escalation_reasons')}")
    print(f"Flagged Metrics: {interrupted_result.get('flagged_metrics')}")

    # Inspect checkpoint
    state = get_audit_state(audit_id)
    print(f"Checkpoint State: paused at node(s) {state.get('next_nodes')}")

    print("\n2. Auditor reviews escalation payload and submits CORRECTION...")
    corrected_payload = {
        "action": "CORRECT",
        "corrected_value": 404548000000.0,
        "reviewer_id": "cpa_sarah_connor",
        "correction_notes": "Corrected Total Assets from $550,000M to verified SEC Form 10-K value of $404,548M."
    }

    print("Resuming workflow from persistent checkpoint...")
    resumed_result = submit_human_decision(audit_id, corrected_payload)

    print(f"Final Status: {resumed_result.get('status')}")
    print("\nUpdated Contracts after Human Correction:")
    for sc in resumed_result.get("shared_contracts", []):
        if sc["metric"] == "Total Assets":
            print(json.dumps(sc, indent=2))


if __name__ == "__main__":
    demo_auto_approval()
    demo_human_review_and_resumption()
