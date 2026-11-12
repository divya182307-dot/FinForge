"""
FinAudit AI - Automated System Integration & Verification Suite
Tests the complete end-to-end flow:
Company Selection -> Run Audit -> Extract -> Validate -> Escalate -> Review (Correct/Approve) -> Resume -> Report & History
"""
import sys
import os
import unittest
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import init_db, get_connection
from backend.audit_service import (
    get_all_companies,
    start_audit_run,
    get_audit_details,
    get_pending_reviews,
    process_review_decision,
    get_audit_history,
    get_accuracy_report,
    get_dashboard_summary
)
from backend.workflow_engine import AuditWorkflowGraph

class TestFinAuditIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def test_01_companies_list(self):
        companies = get_all_companies()
        self.assertEqual(len(companies), 5)
        tickers = [c["ticker"] for c in companies]
        for expected in ["AAPL", "MSFT", "AMZN", "GOOGL", "NVDA"]:
            self.assertIn(expected, tickers)
        print("[PASS] 1. Companies listing returns all 5 enterprise targets.")

    def test_02_run_audit_autonomous(self):
        # Apple FY2023 has clean 10-K figures and should pass autonomously
        result = start_audit_run("AAPL", "FY2023")
        self.assertIn("audit_id", result)
        self.assertEqual(result["ticker"], "AAPL")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["current_stage"], "report_ready")
        print(f"[PASS] 2. Autonomous audit completed successfully for AAPL: {result['audit_id']}.")

    def test_03_run_audit_with_human_escalation(self):
        # NVIDIA FY2024 has simulated OCR ambiguity on Net Income to trigger Human Review
        result = start_audit_run("NVDA", "FY2024")
        self.assertIn("audit_id", result)
        self.assertEqual(result["ticker"], "NVDA")
        self.assertEqual(result["status"], "paused_review")
        self.assertEqual(result["current_stage"], "human_review")
        self.assertGreaterEqual(result["escalated_count"], 1)
        print(f"[PASS] 3. Workflow paused at Human Review checkpoint for NVDA: {result['audit_id']}.")

        audit_id = result["audit_id"]

        # Verify pending review exists
        reviews = get_pending_reviews(audit_id)
        self.assertGreaterEqual(len(reviews), 1)
        net_income_review = next(r for r in reviews if r["metric_name"] == "Net Income")
        self.assertEqual(net_income_review["original_value"], 39760.0)
        self.assertEqual(net_income_review["confidence_score"], 0.64)
        print(f"[PASS] 4. Review queue item inspected: {net_income_review['review_id']} (Original: ${net_income_review['original_value']}M).")

        # Test Action 2: Human Reviewer applies 'correct' decision ($29,760M)
        decision_res = process_review_decision(
            review_id=net_income_review["review_id"],
            decision="correct",
            corrected_value=29760.0,
            reason="Verified against SEC EDGAR XBRL Item 8 Operations statement ($29,760M)",
            comments="OCR had blur misreading '2' as '3'"
        )
        self.assertTrue(decision_res["success"])
        self.assertEqual(decision_res["workflow_status"], "completed")
        self.assertEqual(decision_res["current_stage"], "report_ready")
        print("[PASS] 5. LangGraph workflow successfully resumed upon human decision submission.")

        # Test Immutable Audit History (Original value must NOT be overwritten!)
        history = get_audit_history(audit_id)
        self.assertGreaterEqual(len(history), 1)
        h_record = history[-1]
        self.assertEqual(h_record["original_value"], 39760.0)
        self.assertEqual(h_record["corrected_value"], 29760.0)
        self.assertEqual(h_record["decision"], "correct")
        print(f"[PASS] 6. Append-only history verified: Original (${h_record['original_value']}M) preserved alongside Corrected (${h_record['corrected_value']}M).")

        # Test Accuracy Report
        report = get_accuracy_report(audit_id)
        self.assertIsNotNone(report)
        self.assertEqual(report["accuracy_pct"], 100.0)
        self.assertEqual(report["status"], "final")
        print(f"[PASS] 7. SEC EDGAR XBRL Ground-Truth Report verified: Accuracy is {report['accuracy_pct']}%.")

    def test_04_dashboard_summary(self):
        summary = get_dashboard_summary()
        self.assertIn("kpis", summary)
        self.assertIn("recent_audits", summary)
        k = summary["kpis"]
        self.assertGreaterEqual(k["companies_audited"], 2)
        self.assertGreaterEqual(k["total_metrics_extracted"], 10)
        print(f"[PASS] 8. Dashboard KPIs telemetry verified: {k}")

if __name__ == "__main__":
    unittest.main()

