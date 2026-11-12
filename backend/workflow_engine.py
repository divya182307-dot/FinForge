"""
FinAudit AI - LangGraph Workflow Engine
Implements an agentic state graph with Human-in-the-Loop checkpoint interrupts:
Nodes:
1. filing_retrieval (SEC EDGAR 10-K retrieval)
2. financial_extraction (Member 1 extraction engine)
3. accounting_validation (Member 2 validation engine)
4. human_review_interrupt (LangGraph Interrupt checkpoint)
5. reconciliation_and_resume (Resume token handler)
6. ground_truth_report (SEC XBRL comparison)
"""
from typing import Dict, Any, Optional
from datetime import datetime
import json
from backend.database import get_connection

class AuditWorkflowGraph:
    """
    Manages the lifecycle of the LangGraph audit state.
    Emulates LangGraph Checkpointer & Interrupt semantics:
    - State: { audit_id, ticker, period, stage, interrupted, metrics, anomalies }
    - Interrupt: Pauses execution before 'human_review' when confidence < 0.85 or accounting equation fails
    - Resume: Receives human decision payload, updates state, and continues graph execution
    """
    STAGES = [
        "retrieval",
        "extraction",
        "validation",
        "human_review",
        "reconciliation",
        "report_ready"
    ]

    @staticmethod
    def get_workflow_state(audit_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audit_runs WHERE audit_id = ?", (audit_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None

        cursor.execute("SELECT COUNT(*) as pending FROM review_items WHERE audit_id = ? AND status = 'pending'", (audit_id,))
        pending = cursor.fetchone()["pending"]

        cursor.execute("SELECT * FROM review_items WHERE audit_id = ?", (audit_id,))
        reviews = [dict(r) for r in cursor.fetchall()]

        conn.close()

        current_stage = row["current_stage"]
        status = row["status"]

        stage_progress = {
            "retrieval": 15,
            "extraction": 35,
            "validation": 55,
            "human_review": 75,
            "reconciliation": 90,
            "report_ready": 100
        }

        return {
            "audit_id": row["audit_id"],
            "ticker": row["ticker"],
            "period": row["period"],
            "thread_id": row["thread_id"],
            "status": status,
            "current_stage": current_stage,
            "progress_pct": stage_progress.get(current_stage, 100),
            "is_interrupted": (status == "paused_review"),
            "pending_reviews_count": pending,
            "reviews": reviews,
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
            "summary": row["summary"]
        }

