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

    def test_05_advanced_12_features(self):
        from backend.advanced_features import (
            get_audit_anomalies_and_explanations,
            get_smart_evidence_viewer,
            process_copilot_chat,
            calculate_audit_risk_score,
            get_multi_company_benchmarking,
            get_company_historical_intelligence,
            get_accounting_reconciliation_workspace,
            generate_audit_report_payload,
            generate_audit_report_html,
            get_audit_timeline,
            get_reviewer_feedback_analytics,
            verify_audit_trail_integrity,
            get_live_audit_monitoring
        )

        # 1. Start a fresh audit to test
        run = start_audit_run("AAPL", "FY2023")
        audit_id = run["audit_id"]

        # Feature 1: Anomaly explanations
        anoms = get_audit_anomalies_and_explanations(audit_id)
        self.assertIn("anomalies", anoms)
        print("[PASS] Feature 1: AI Anomaly Explanation Engine working.")

        # Feature 2: Smart Evidence viewer
        evid = get_smart_evidence_viewer(audit_id)
        self.assertGreaterEqual(evid["evidence_count"], 5)
        print("[PASS] Feature 2: Smart Evidence Highlighting viewer working.")

        # Feature 3: AI Financial Audit Copilot
        copilot_res = process_copilot_chat("Why was NVIDIA flagged?", audit_id=audit_id)
        self.assertIn("answer", copilot_res)
        self.assertIn("NVIDIA", copilot_res["answer"])
        print("[PASS] Feature 3: AI Financial Audit Copilot working.")

        # Feature 4: Explainable Financial Risk Score
        risk_res = calculate_audit_risk_score(audit_id)
        self.assertIn("risk_score", risk_res)
        self.assertIn(risk_res["classification"], ["LOW RISK", "MEDIUM RISK", "HIGH RISK"])
        print(f"[PASS] Feature 4: Financial Risk Score working ({risk_res['classification']}).")

        # Feature 5: Multi-Company Benchmarking
        bench_res = get_multi_company_benchmarking("FY2023")
        self.assertEqual(len(bench_res["companies"]), 5)
        print("[PASS] Feature 5: Multi-Company Benchmarking working (5 companies ranked).")

        # Feature 6: Historical Financial Intelligence
        hist_res = get_company_historical_intelligence("AAPL")
        self.assertIn("multi_year_series", hist_res)
        print("[PASS] Feature 6: Historical Financial Intelligence working.")

        # Feature 7: Smart Accounting Reconciliation
        recon_res = get_accounting_reconciliation_workspace(audit_id)
        self.assertIn("balance_sheet_reconciliation", recon_res)
        self.assertEqual(recon_res["balance_sheet_reconciliation"]["status"], "PASSED")
        print("[PASS] Feature 7: Smart Accounting Reconciliation working.")

        # Feature 8: Professional Audit Report Generator
        rep_html = generate_audit_report_html(audit_id)
        self.assertIn("FINFORGE", rep_html)
        self.assertIn("Audit Certificate", rep_html)
        print("[PASS] Feature 8: Professional Audit Report & Certificate generated.")

        # Feature 9: Chronological Audit Decision Timeline
        timeline_res = get_audit_timeline(audit_id)
        self.assertGreaterEqual(len(timeline_res["timeline"]), 4)
        print("[PASS] Feature 9: Chronological Audit Timeline working.")

        # Feature 10: Reviewer Feedback Intelligence
        feedback_res = get_reviewer_feedback_analytics()
        self.assertIn("decisions_breakdown", feedback_res)
        print("[PASS] Feature 10: Reviewer Feedback Intelligence working.")

        # Feature 11: Tamper-Evident SHA-256 Hash-Linked Audit Trail
        integrity_res = verify_audit_trail_integrity(audit_id)
        self.assertTrue(integrity_res["is_valid"])
        print(f"[PASS] Feature 11: Tamper-Evident Hash Chain verified ({integrity_res['status']}).")

        # Feature 12: Live 9-Stage Audit Monitoring
        mon_res = get_live_audit_monitoring()
        self.assertGreaterEqual(len(mon_res["monitored_audits"]), 1)
        self.assertEqual(len(mon_res["workflow_stages"]), 9)
        print("[PASS] Feature 12: Live 9-Stage Audit Monitoring working.")

if __name__ == "__main__":
    unittest.main()

