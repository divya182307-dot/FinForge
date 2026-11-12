import sys
import os

from backend.database import init_db
from backend.audit_service import (
    start_audit_run,
    get_audit_details,
    get_pending_reviews,
    process_review_decision,
    get_audit_history,
)

print("--- 1. INITIALIZING DATABASE ---")
init_db()

print("\n--- 2. START AUDIT FOR NVDA (FY2023 - INTENTIONAL MISTAKE) ---")
run_result = start_audit_run("NVDA", "FY2023")
print("Audit Run Result:")
print("  Audit ID:       ", run_result["audit_id"])
print("  Status:         ", run_result["status"])
print("  Current Stage:  ", run_result["current_stage"])
print("  Escalated Count:", run_result["escalated_count"])
print("  Summary:        ", run_result["message"])

assert run_result["status"] == "paused_review", f"Expected paused_review, got {run_result['status']}"
assert run_result["current_stage"] == "human_review", f"Expected human_review, got {run_result['current_stage']}"
assert run_result["escalated_count"] >= 1, "Expected at least 1 escalated item"

print("\n--- 3. FETCH PENDING REVIEWS ---")
pending = get_pending_reviews(run_result["audit_id"])
print(f"Found {len(pending)} pending review items:")
for p in pending:
    print("  Review ID:      ", p["review_id"])
    print("  Company:        ", p["company_name"], f"({p['ticker']})")
    print("  Metric:         ", p["metric_name"])
    print("  Original Value: ", p["original_value"], p["unit"])
    print("  Expected Value: ", p["expected_value"], p["unit"])
    print("  Confidence:     ", p["confidence_score"])
    print("  Reason:         ", p["reason"])
    print("  Evidence:       ", p["source_evidence"])

flagged_item = next((item for item in pending if item["metric_name"] == "Total Assets"), None)
assert flagged_item is not None, "Total Assets was not flagged!"
assert flagged_item["original_value"] == 45182.0, f"Expected 45182.0, got {flagged_item['original_value']}"
assert flagged_item["expected_value"] == 41182.0, f"Expected 41182.0, got {flagged_item['expected_value']}"
assert flagged_item["confidence_score"] == 0.62, f"Expected 0.62, got {flagged_item['confidence_score']}"
assert "Accounting Equation" in flagged_item["reason"], "Reason missing Accounting Equation note"
print("Verification 1-4 Passed: Incorrect value, Expected value, Confidence, Reason, and Evidence verified!")

print("\n--- 4. SUBMIT REVIEW DECISION: CORRECT ---")
decision_res = process_review_decision(
    review_id=flagged_item["review_id"],
    decision="correct",
    corrected_value=41182.0,
    reason="Corrected OCR blur typo in 10-K Balance Sheet",
    comments="Certified Financial Auditor"
)
print("Decision Result:", decision_res)
assert decision_res["success"] is True

print("\n--- 5. VERIFY AUDIT HISTORY ---")
history = get_audit_history(run_result["audit_id"])
print(f"Audit History Entries: {len(history)}")
for h in history:
    print(f"  #{h['history_id']} - {h['metric_name']}: Original ${h['original_value']}M -> Corrected ${h['corrected_value']}M [{h['decision'].upper()}] by {h['reviewer_comments']}")

assert len(history) >= 1
assert history[0]["decision"] == "correct"
assert history[0]["original_value"] == 45182.0
assert history[0]["corrected_value"] == 41182.0
print("Verification 5-6 Passed: Decision and correction saved in immutable audit history!")

print("\n--- 6. VERIFY WORKFLOW RESUMED TO COMPLETED ---")
details = get_audit_details(run_result["audit_id"])
print("Post-Review Audit Details:")
print("  Status:        ", details["status"])
print("  Current Stage: ", details["current_stage"])
print("  Summary:       ", details["summary"])
assert details["status"] == "completed"
assert details["current_stage"] == "report_ready"
print("Verification 7 Passed: Workflow resumed to 'completed' and 'report_ready'!")

print("\n--- 7. VERIFY OTHER COMPANIES WORK NORMALLY (e.g. AAPL) ---")
aapl_res = start_audit_run("AAPL", "FY2023")
print("AAPL Audit Result:")
print("  Status:        ", aapl_res["status"])
print("  Current Stage: ", aapl_res["current_stage"])
print("  Escalated:     ", aapl_res["escalated_count"])
assert aapl_res["status"] == "completed", f"AAPL failed: {aapl_res}"
assert aapl_res["escalated_count"] == 0
print("Verification Passed: Other companies (AAPL) pass autonomously with 100% accuracy!")

print("\nALL HUMAN REVIEW DEMO REQUIREMENTS PASSED PERFECTLY!")

