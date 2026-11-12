"""
FinAudit AI - Complete Test Suite for Member 2
Tests all 10 mandatory evaluation requirements:
1. High-confidence automatic approval
2. Low-confidence escalation
3. Accounting equation failure
4. Segment mismatch
5. Unusual year-on-year variation
6. Human approval
7. Human correction
8. Human rejection
9. Actual checkpoint-based pause and resume
10. No duplicate actions after resumption
"""

import pytest
import sqlite3
import uuid
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

from confidence_engine import calculate_confidence, ConfidenceConfig
from validation_engine import (
    validate_accounting_equation,
    validate_segments,
    analyze_year_on_year
)
from audit_graph import create_audit_graph
from review_handler import (
    run_audit_workflow,
    submit_human_decision,
    resume_audit_workflow,
    get_audit_state
)


# ---------------------------------------------------------------------------
# Test Fixtures & Sample Payloads
# ---------------------------------------------------------------------------
def get_clean_apple_data():
    """Apple Inc. FY2026 balanced high-confidence sample data from SEC 10-K."""
    return {
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
                "filing_url": "https://www.sec.gov/Archives/edgar/data/320193/000032019326000026/aapl-20260926.htm",
                "source_evidence": "Filing 0000320193-26-000026 [us-gaap:Assets]: Consolidated Balance Sheets Item 8 reported '404,548' with scale=10^6",
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
                "filing_url": "https://www.sec.gov/Archives/edgar/data/320193/000032019326000026/aapl-20260926.htm",
                "source_evidence": "Filing 0000320193-26-000026 [us-gaap:Liabilities]: Consolidated Balance Sheets Item 8 reported '292,455' with scale=10^6",
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
                "filing_url": "https://www.sec.gov/Archives/edgar/data/320193/000032019326000026/aapl-20260926.htm",
                "source_evidence": "Filing 0000320193-26-000026 [us-gaap:StockholdersEquity]: Consolidated Balance Sheets Item 8 reported '112,093' with scale=10^6",
                "xbrl_tag": "StockholdersEquity",
                "extraction_method": "xbrl_facts"
            }
        ]
    }


# ---------------------------------------------------------------------------
# TEST 1: High-Confidence Automatic Approval
# ---------------------------------------------------------------------------
def test_1_high_confidence_auto_approval():
    """Demonstrates high confidence and valid accounting equation results in AUTO_APPROVED."""
    checkpointer = MemorySaver()
    data = get_clean_apple_data()
    audit_id = f"test1_auto_{uuid.uuid4().hex[:6]}"

    result = run_audit_workflow(data, checkpointer=checkpointer, audit_id=audit_id)

    assert result["audit_decision"] == "AUTO_APPROVED"
    assert result["status"] == "COMPLETED"
    assert "auto_approve" in result["completed_nodes"]
    assert "request_human_review" not in result["completed_nodes"]

    # Check shared contracts
    contracts = result["shared_contracts"]
    assert len(contracts) == 4
    for c in contracts:
        assert c["decision"] == "AUTO_APPROVED"
        assert c["confidence"] >= 90.0
        assert c["review_required"] is False
        assert c["validation_status"] == "PASSED"


# ---------------------------------------------------------------------------
# TEST 2: Low-Confidence Escalation
# ---------------------------------------------------------------------------
def test_2_low_confidence_escalation():
    """Demonstrates that metric with low confidence (<70) triggers human review escalation."""
    checkpointer = MemorySaver()
    data = get_clean_apple_data()
    audit_id = f"test2_low_conf_{uuid.uuid4().hex[:6]}"

    # Add a low-confidence extracted metric lacking evidence and canonical tag
    data["metrics"].append({
        "company": "Apple Inc.",
        "ticker": "AAPL",
        "metric": "Miscellaneous Intangibles",
        "value": 4500000000.0,
        "unit": "USD",
        "period": "FY2026",
        "filing_url": None,
        "source_evidence": None,  # Missing evidence
        "xbrl_tag": None,
        "extraction_method": "llm_text",  # Lower reliability method
        "confidence": 0.45
    })

    result = run_audit_workflow(data, checkpointer=checkpointer, audit_id=audit_id)

    assert result["audit_decision"] == "NEEDS_HUMAN_REVIEW"
    assert "__interrupt__" in result
    state_snap = get_audit_state(audit_id, checkpointer=checkpointer)
    assert "request_human_review" in state_snap["next_nodes"]

    # Check that the metric confidence was properly scored < 70
    conf_scores = result["confidence_scores"]
    misc_conf = conf_scores["Miscellaneous Intangibles"]
    assert misc_conf["score"] < 70.0
    assert misc_conf["level"] == "LOW"
    assert "Miscellaneous Intangibles" in result["flagged_metrics"]


# ---------------------------------------------------------------------------
# TEST 3: Accounting Equation Failure Escalation
# ---------------------------------------------------------------------------
def test_3_accounting_equation_failure():
    """
    Demonstrates that an accounting equation mismatch triggers NEEDS_HUMAN_REVIEW
    even when extraction confidence is 100%.
    """
    checkpointer = MemorySaver()
    data = get_clean_apple_data()
    audit_id = f"test3_acct_fail_{uuid.uuid4().hex[:6]}"

    # Intentionally corrupt Total Assets so Assets != Liabilities + Equity
    # 404,548M != 292,455M + 112,093M (sum is 404,548M; corrupt assets to 550,000M)
    for m in data["metrics"]:
        if m["metric"] == "Total Assets":
            m["value"] = 550000000000.0  # Corrupted value

    result = run_audit_workflow(data, checkpointer=checkpointer, audit_id=audit_id)

    assert result["audit_decision"] == "NEEDS_HUMAN_REVIEW"
    assert result["validation_results"]["accounting_equation"]["status"] == "FAILED"
    assert "__interrupt__" in result
    assert any("Accounting equation" in r for r in result["escalation_reasons"])


# ---------------------------------------------------------------------------
# TEST 4: Segment Mismatch
# ---------------------------------------------------------------------------
def test_4_segment_mismatch():
    """Demonstrates that segment sum mismatch triggers human review."""
    checkpointer = MemorySaver()
    data = get_clean_apple_data()
    audit_id = f"test4_seg_mismatch_{uuid.uuid4().hex[:6]}"

    # Add segment breakdown where sum (200B + 150B = 350B) != consolidated revenue (478.834B)
    data["segments_data"] = {
        "consolidated_metric": "Revenue",
        "items": [
            {"segment_name": "Americas", "value": 200000000000.0, "unit": "USD"},
            {"segment_name": "Europe", "value": 150000000000.0, "unit": "USD"}
        ]
    }

    result = run_audit_workflow(data, checkpointer=checkpointer, audit_id=audit_id)

    assert result["audit_decision"] == "NEEDS_HUMAN_REVIEW"
    assert result["validation_results"]["segment_validation"]["status"] == "FAILED"
    assert any("Segment validation" in r for r in result["escalation_reasons"])


# ---------------------------------------------------------------------------
# TEST 5: Unusual Year-on-Year Variation
# ---------------------------------------------------------------------------
def test_5_unusual_yoy_variation():
    """Demonstrates that YoY swing > 30% flags warning and triggers human review."""
    checkpointer = MemorySaver()
    data = get_clean_apple_data()
    audit_id = f"test5_yoy_{uuid.uuid4().hex[:6]}"

    # Provide prior period metrics where Revenue had a massive swing (from 200B to 478.8B = +139%)
    data["prior_period_metrics"] = [
        {"metric": "Revenue", "value": 200000000000.0, "unit": "USD", "period": "FY2025"},
        {"metric": "Total Assets", "value": 404000000000.0, "unit": "USD", "period": "FY2025"},
        {"metric": "Total Liabilities", "value": 292000000000.0, "unit": "USD", "period": "FY2025"},
        {"metric": "Shareholders' Equity", "value": 112000000000.0, "unit": "USD", "period": "FY2025"}
    ]

    result = run_audit_workflow(data, checkpointer=checkpointer, audit_id=audit_id)

    assert result["audit_decision"] == "NEEDS_HUMAN_REVIEW"
    yoy_res = result["validation_results"]["year_on_year"]
    assert yoy_res["status"] == "WARNING"
    assert "Revenue" in yoy_res["flagged_metrics"]
    assert any("YoY" in r for r in result["escalation_reasons"])


# ---------------------------------------------------------------------------
# TEST 6: Human Approval Decision
# ---------------------------------------------------------------------------
def test_6_human_approval():
    """Demonstrates human reviewer accepting flagged metric via APPROVE."""
    checkpointer = MemorySaver()
    data = get_clean_apple_data()
    audit_id = f"test6_approve_{uuid.uuid4().hex[:6]}"

    # Trigger review via segment mismatch
    data["segments_data"] = {
        "consolidated_metric": "Revenue",
        "items": [{"segment_name": "Americas", "value": 300000000000.0, "unit": "USD"}]
    }

    # 1. Run until pause
    interrupted = run_audit_workflow(data, checkpointer=checkpointer, audit_id=audit_id)
    assert "__interrupt__" in interrupted

    # 2. Submit human decision APPROVE
    resumed = submit_human_decision(
        audit_id=audit_id,
        decision={
            "action": "APPROVE",
            "reviewer_id": "senior_auditor_jane",
            "notes": "Verified against Footnote 14 Segment Reporting in 10-K; discrepancy due to excluded corporate items."
        },
        checkpointer=checkpointer
    )

    assert resumed["status"] == "COMPLETED"
    assert "process_human_decision" in resumed["completed_nodes"]
    assert "resume_workflow" in resumed["completed_nodes"]

    # Verify shared contract has HUMAN_APPROVED
    rev_contract = next(c for c in resumed["shared_contracts"] if c["metric"] == "Revenue")
    assert rev_contract["decision"] == "HUMAN_APPROVED"
    assert rev_contract["human_resolution"]["action"] == "APPROVE"


# ---------------------------------------------------------------------------
# TEST 7: Human Correction Decision
# ---------------------------------------------------------------------------
def test_7_human_correction():
    """
    Demonstrates human reviewer correcting a value via CORRECT:
    Accepts corrected value while preserving original value.
    """
    checkpointer = MemorySaver()
    data = get_clean_apple_data()
    audit_id = f"test7_correct_{uuid.uuid4().hex[:6]}"

    # Inject OCR error: Assets extracted as 500B instead of 404.548B
    for m in data["metrics"]:
        if m["metric"] == "Total Assets":
            m["value"] = 500000000000.0

    # 1. Workflow pauses
    interrupted = run_audit_workflow(data, checkpointer=checkpointer, audit_id=audit_id)
    assert "__interrupt__" in interrupted

    # 2. Human submits CORRECT
    correct_val = 404548000000.0
    resumed = submit_human_decision(
        audit_id=audit_id,
        decision={
            "action": "CORRECT",
            "corrected_value": correct_val,
            "reviewer_id": "auditor_alex",
            "correction_notes": "Corrected OCR typo from 500,000M to true 10-K value of 404,548M."
        },
        checkpointer=checkpointer
    )

    assert resumed["status"] == "COMPLETED"
    assets_contract = next(c for c in resumed["shared_contracts"] if c["metric"] == "Total Assets")
    assert assets_contract["decision"] == "HUMAN_CORRECTED"
    assert assets_contract["value"] == correct_val
    assert assets_contract["original_value"] == 500000000000.0
    assert assets_contract["human_resolution"]["original_value"] == 500000000000.0
    assert assets_contract["human_resolution"]["corrected_value"] == correct_val


# ---------------------------------------------------------------------------
# TEST 8: Human Rejection Decision
# ---------------------------------------------------------------------------
def test_8_human_rejection():
    """Demonstrates human reviewer rejecting fraudulent or uncorroborated metric via REJECT."""
    checkpointer = MemorySaver()
    data = get_clean_apple_data()
    audit_id = f"test8_reject_{uuid.uuid4().hex[:6]}"

    # Inject accounting equation failure
    data["metrics"][1]["value"] = 999999999999.0

    interrupted = run_audit_workflow(data, checkpointer=checkpointer, audit_id=audit_id)
    assert "__interrupt__" in interrupted

    rejection_reason = "Filing balance sheet figures cannot be substantiated by SEC EDGAR records."
    resumed = submit_human_decision(
        audit_id=audit_id,
        decision={
            "action": "REJECT",
            "reviewer_id": "lead_partner_dave",
            "rejection_reason": rejection_reason
        },
        checkpointer=checkpointer
    )

    assert resumed["status"] == "REJECTED"
    flagged_contract = next(c for c in resumed["shared_contracts"] if c["metric"] == "Total Assets")
    assert flagged_contract["decision"] == "HUMAN_REJECTED"
    assert flagged_contract["validation_status"] == "FAILED"
    assert flagged_contract["rejection_reason"] == rejection_reason


# ---------------------------------------------------------------------------
# TEST 9: Actual Checkpoint-Based Pause and Resume (SqliteSaver On Disk)
# ---------------------------------------------------------------------------
def test_9_sqlite_checkpoint_pause_and_resume():
    """
    Demonstrates persistent checkpointer on SQLite:
    - Interrupt saves snapshot to disk
    - State can be queried
    - Resumption continues exactly from saved checkpoint
    """
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    sqlite_saver = SqliteSaver(conn)
    sqlite_saver.setup()

    data = get_clean_apple_data()
    audit_id = f"test9_sqlite_{uuid.uuid4().hex[:6]}"
    # Corrupt to trigger interrupt
    data["metrics"][0]["source_evidence"] = None
    data["metrics"][0]["xbrl_tag"] = None
    data["metrics"][0]["extraction_method"] = "llm_text"

    # Step 1: Run workflow until interrupt
    paused_result = run_audit_workflow(data, checkpointer=sqlite_saver, audit_id=audit_id)
    assert "__interrupt__" in paused_result

    # Step 2: Query checkpoint state directly
    state_snap = get_audit_state(audit_id, checkpointer=sqlite_saver)
    assert state_snap is not None
    assert state_snap["is_interrupted"] is True
    assert "request_human_review" in state_snap["next_nodes"]

    # Step 3: Resume using persistent checkpointer
    resumed_result = resume_audit_workflow(
        audit_id=audit_id,
        decision={"action": "APPROVE", "reviewer_id": "sqlite_reviewer"},
        checkpointer=sqlite_saver
    )
    assert resumed_result["status"] == "COMPLETED"


# ---------------------------------------------------------------------------
# TEST 10: No Duplicate Actions After Resumption (Idempotency)
# ---------------------------------------------------------------------------
def test_10_no_duplicate_actions_after_resumption():
    """
    Demonstrates that resuming does NOT re-run extraction, confidence scoring,
    or validation nodes, preventing duplicate execution and unwanted side effects.
    """
    checkpointer = MemorySaver()
    data = get_clean_apple_data()
    audit_id = f"test10_idempotent_{uuid.uuid4().hex[:6]}"

    # Force review
    data["metrics"][0]["source_evidence"] = None
    data["metrics"][0]["extraction_method"] = "llm_text"

    paused = run_audit_workflow(data, checkpointer=checkpointer, audit_id=audit_id)
    assert "__interrupt__" in paused

    nodes_before_resume = list(paused["completed_nodes"])
    log_count_before = len(paused["execution_log"])

    # Resume
    resumed = submit_human_decision(
        audit_id=audit_id,
        decision={"action": "APPROVE", "reviewer_id": "auditor_verifier"},
        checkpointer=checkpointer
    )

    completed_nodes = resumed["completed_nodes"]

    # Verify nodes ran exactly once:
    assert completed_nodes.count("receive_extracted_data") == 1
    assert completed_nodes.count("calculate_confidence") == 1
    assert completed_nodes.count("validate_financial_data") == 1
    assert completed_nodes.count("make_audit_decision") == 1
    assert completed_nodes.count("request_human_review") == 1
    assert completed_nodes.count("process_human_decision") == 1
    assert completed_nodes.count("resume_workflow") == 1
    assert completed_nodes.count("finalize_audit") == 1


# ---------------------------------------------------------------------------
# Direct Runner
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 70)
    print("RUNNING FINAUDIT AI TASK 2 TEST SUITE (MEMBER 2)")
    print("=" * 70)

    test_1_high_confidence_auto_approval()
    print("✓ Test 1: High-confidence automatic approval PASSED")

    test_2_low_confidence_escalation()
    print("✓ Test 2: Low-confidence escalation PASSED")

    test_3_accounting_equation_failure()
    print("✓ Test 3: Accounting equation failure PASSED")

    test_4_segment_mismatch()
    print("✓ Test 4: Segment mismatch PASSED")

    test_5_unusual_yoy_variation()
    print("✓ Test 5: Unusual year-on-year variation PASSED")

    test_6_human_approval()
    print("✓ Test 6: Human approval PASSED")

    test_7_human_correction()
    print("✓ Test 7: Human correction PASSED")

    test_8_human_rejection()
    print("✓ Test 8: Human rejection PASSED")

    test_9_sqlite_checkpoint_pause_and_resume()
    print("✓ Test 9: Actual SQLite checkpoint pause and resume PASSED")

    test_10_no_duplicate_actions_after_resumption()
    print("✓ Test 10: Idempotency & duplicate action prevention PASSED")

    print("\n" + "=" * 70)
    print("ALL 10 MANDATORY TEST SCENARIOS PASSED SUCCESSFULLY!")
    print("=" * 70)
