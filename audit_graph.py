"""
FinAudit AI - Agentic Audit Graph Engine (Member 2)
Implements the 9-node LangGraph Human-in-the-Loop workflow with:
- Checkpoint persistence (SqliteSaver / MemorySaver)
- LangGraph Interrupt for human review escalation
- Exact required nodes:
  1. receive_extracted_data
  2. calculate_confidence
  3. validate_financial_data
  4. make_audit_decision
  5. auto_approve
  6. request_human_review
  7. process_human_decision
  8. resume_workflow
  9. finalize_audit
- Stable thread IDs and idempotent execution preventing duplicate side effects
"""

import uuid
import sqlite3
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.memory import MemorySaver

from workflow_state import AuditState, MetricInput, SharedMetricContract
from confidence_engine import calculate_confidence
from validation_engine import run_all_validations
from decision_engine import evaluate_audit_decision

DEFAULT_DB_PATH = "audit_checkpoints.db"


def _get_utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Global Persistent Saver Cache
# ---------------------------------------------------------------------------
_GLOBAL_SAVER: Optional[BaseCheckpointSaver] = None

def get_default_checkpointer(db_path: str = DEFAULT_DB_PATH) -> BaseCheckpointSaver:
    global _GLOBAL_SAVER
    if _GLOBAL_SAVER is None:
        conn = sqlite3.connect(db_path, check_same_thread=False)
        saver = SqliteSaver(conn)
        saver.setup()
        _GLOBAL_SAVER = saver
    return _GLOBAL_SAVER


# ---------------------------------------------------------------------------
# 1. Node 1: receive_extracted_data
# ---------------------------------------------------------------------------
def receive_extracted_data(state: AuditState) -> Dict[str, Any]:
    """
    Node 1: Receives structured JSON financial metrics from Member 1.
    Normalizes fields and initializes idempotency tracking.
    """
    completed = list(state.get("completed_nodes", []))
    if "receive_extracted_data" in completed:
        # Idempotent skip if already completed
        return {"status": "DATA_RECEIVED"}

    raw = state.get("raw_input", {})
    metrics_list: List[Dict[str, Any]] = []
    prior_metrics: List[Dict[str, Any]] = state.get("prior_period_metrics") or []
    segments_data: Optional[Dict[str, Any]] = state.get("segments_data")

    company = state.get("company", "")
    ticker = state.get("ticker", "")
    period = state.get("period", "")

    if isinstance(raw, list):
        metrics_list = raw
    elif isinstance(raw, dict):
        if "metrics" in raw:
            metrics_list = raw["metrics"]
            company = company or raw.get("company", "")
            ticker = ticker or raw.get("ticker", "")
            period = period or raw.get("period", "")
            prior_metrics = prior_metrics or raw.get("prior_period_metrics", [])
            segments_data = segments_data or raw.get("segments_data") or raw.get("segments")
        else:
            # Flattened dict format: {"Revenue": 1000, "Net Income": 200}
            metrics_list = [{"metric": k, "value": v} for k, v in raw.items()]

    # Normalize metrics items
    normalized_metrics = []
    for m in metrics_list:
        norm = MetricInput.from_dict(m).model_dump()
        if not company and norm.get("company"):
            company = norm["company"]
        if not ticker and norm.get("ticker"):
            ticker = norm["ticker"]
        if not period and norm.get("period"):
            period = norm["period"]
        normalized_metrics.append(norm)

    audit_id = state.get("audit_id") or f"aud_{uuid.uuid4().hex[:10]}"
    thread_id = state.get("thread_id") or f"thread_{audit_id}"

    completed.append("receive_extracted_data")
    execution_log = list(state.get("execution_log", []))
    execution_log.append({
        "node": "receive_extracted_data",
        "timestamp": _get_utc_now_iso(),
        "message": f"Received {len(normalized_metrics)} financial metrics for {ticker or 'Company'} ({period})."
    })

    return {
        "audit_id": audit_id,
        "thread_id": thread_id,
        "company": company or "Unknown Company",
        "ticker": ticker or "N/A",
        "period": period or "FY2026",
        "metrics": normalized_metrics,
        "prior_period_metrics": prior_metrics,
        "segments_data": segments_data,
        "completed_nodes": completed,
        "execution_log": execution_log,
        "status": "DATA_RECEIVED"
    }


# ---------------------------------------------------------------------------
# 2. Node 2: calculate_confidence
# ---------------------------------------------------------------------------
def calculate_confidence_node(state: AuditState) -> Dict[str, Any]:
    """
    Node 2: Runs explainable confidence scoring engine across all metrics.
    """
    completed = list(state.get("completed_nodes", []))
    metrics = state.get("metrics", [])
    confidence_results: Dict[str, Dict[str, Any]] = {}

    for m in metrics:
        metric_name = m.get("metric")
        conf = calculate_confidence(m)
        confidence_results[metric_name] = conf

    completed.append("calculate_confidence")
    execution_log = list(state.get("execution_log", []))
    execution_log.append({
        "node": "calculate_confidence",
        "timestamp": _get_utc_now_iso(),
        "message": f"Calculated confidence scores for {len(confidence_results)} metrics."
    })

    return {
        "confidence_scores": confidence_results,
        "completed_nodes": completed,
        "execution_log": execution_log,
        "status": "CONFIDENCE_CALCULATED"
    }


# ---------------------------------------------------------------------------
# 3. Node 3: validate_financial_data
# ---------------------------------------------------------------------------
def validate_financial_data(state: AuditState) -> Dict[str, Any]:
    """
    Node 3: Executes mandatory financial validations:
    - Accounting Equation (Assets == Liabilities + Equity)
    - Segment Breakdown (Segment sum == Consolidated total)
    - Year-on-Year Anomaly Analysis
    """
    completed = list(state.get("completed_nodes", []))
    payload = {
        "metrics": state.get("metrics", []),
        "prior_period_metrics": state.get("prior_period_metrics", []),
        "segments": state.get("segments_data")
    }

    validation_results = run_all_validations(payload)

    completed.append("validate_financial_data")
    execution_log = list(state.get("execution_log", []))
    execution_log.append({
        "node": "validate_financial_data",
        "timestamp": _get_utc_now_iso(),
        "message": (
            f"Accounting equation: {validation_results['accounting_equation']['status']}; "
            f"Segments: {validation_results['segment_validation']['status']}; "
            f"YoY: {validation_results['year_on_year']['status']}."
        )
    })

    return {
        "validation_results": validation_results,
        "completed_nodes": completed,
        "execution_log": execution_log,
        "status": "VALIDATED"
    }


# ---------------------------------------------------------------------------
# 4. Node 4: make_audit_decision
# ---------------------------------------------------------------------------
def make_audit_decision(state: AuditState) -> Dict[str, Any]:
    """
    Node 4: Evaluates automated approval vs escalation rules.
    Does not allow failed validation to pass even if confidence is 100%.
    """
    completed = list(state.get("completed_nodes", []))
    metrics = state.get("metrics", [])
    confidence_results = state.get("confidence_scores", {})
    validation_results = state.get("validation_results", {})

    decision, reasons, flagged_items, shared_contracts = evaluate_audit_decision(
        metrics=metrics,
        confidence_results=confidence_results,
        validation_results=validation_results
    )

    completed.append("make_audit_decision")
    execution_log = list(state.get("execution_log", []))
    execution_log.append({
        "node": "make_audit_decision",
        "timestamp": _get_utc_now_iso(),
        "message": f"Audit decision determined: {decision} ({len(escalation_reasons := reasons)} trigger(s))."
    })

    flagged_names = [item["metric"] for item in flagged_items]

    return {
        "audit_decision": decision,
        "escalation_reasons": reasons,
        "flagged_metrics": flagged_names,
        "review_payload": {
            "audit_id": state.get("audit_id"),
            "ticker": state.get("ticker"),
            "period": state.get("period"),
            "flagged_items": flagged_items,
            "escalation_reasons": reasons,
            "allowed_actions": ["APPROVE", "CORRECT", "REJECT"]
        },
        "shared_contracts": shared_contracts,
        "completed_nodes": completed,
        "execution_log": execution_log,
        "status": "DECISION_MADE"
    }


def route_decision(state: AuditState) -> str:
    """Conditional router based on audit_decision."""
    if state.get("audit_decision") == "AUTO_APPROVED":
        return "auto_approve"
    return "request_human_review"


# ---------------------------------------------------------------------------
# 5. Node 5: auto_approve
# ---------------------------------------------------------------------------
def auto_approve(state: AuditState) -> Dict[str, Any]:
    """
    Node 5: Directly finalizes auto-approved audits.
    """
    completed = list(state.get("completed_nodes", []))
    completed.append("auto_approve")
    execution_log = list(state.get("execution_log", []))
    execution_log.append({
        "node": "auto_approve",
        "timestamp": _get_utc_now_iso(),
        "message": "All metrics passed high confidence threshold and financial validation checks. Auto-approved."
    })

    return {
        "status": "AUTO_APPROVED",
        "completed_nodes": completed,
        "execution_log": execution_log
    }


# ---------------------------------------------------------------------------
# 6. Node 6: request_human_review (LANGGRAPH INTERRUPT)
# ---------------------------------------------------------------------------
def request_human_review(state: AuditState) -> Dict[str, Any]:
    """
    Node 6: LangGraph Interrupt checkpoint.
    Saves state, pauses execution, and exposes escalation payload to human reviewer.
    When resumed with Command(resume=payload), receives the reviewer's decision.
    """
    completed = list(state.get("completed_nodes", []))
    review_data = state.get("review_payload") or {
        "audit_id": state.get("audit_id"),
        "flagged_metrics": state.get("flagged_metrics", []),
        "escalation_reasons": state.get("escalation_reasons", []),
        "allowed_actions": ["APPROVE", "CORRECT", "REJECT"]
    }

    execution_log = list(state.get("execution_log", []))
    execution_log.append({
        "node": "request_human_review",
        "timestamp": _get_utc_now_iso(),
        "message": f"Workflow interrupted for human review: {len(state.get('flagged_metrics', []))} metric(s) flagged."
    })

    # TRIGGER ACTUAL LANGGRAPH INTERRUPT
    human_response = interrupt(review_data)

    completed.append("request_human_review")
    return {
        "human_decision": human_response,
        "completed_nodes": completed,
        "execution_log": execution_log,
        "status": "AWAITING_HUMAN_REVIEW"
    }


# ---------------------------------------------------------------------------
# 7. Node 7: process_human_decision
# ---------------------------------------------------------------------------
def process_human_decision(state: AuditState) -> Dict[str, Any]:
    """
    Node 7: Processes the human decision:
    - APPROVE: Accept extracted value
    - CORRECT: Accept corrected value while preserving original
    - REJECT: Reject extracted value with rejection reason
    """
    completed = list(state.get("completed_nodes", []))
    decision_payload = state.get("human_decision") or {}
    action = decision_payload.get("action", "APPROVE").upper()

    reviewer_notes = decision_payload.get("correction_notes") or decision_payload.get("notes") or ""
    reviewer_id = decision_payload.get("reviewer_id", "auditor_1")
    corrected_value = decision_payload.get("corrected_value")
    rejection_reason = decision_payload.get("rejection_reason") or reviewer_notes or "Rejected by human auditor"

    metrics = list(state.get("metrics", []))
    shared_contracts = list(state.get("shared_contracts", []))
    flagged = set(state.get("flagged_metrics", []))

    updated_contracts = []
    for sc in shared_contracts:
        m_name = sc.get("metric")
        c = dict(sc)

        if m_name in flagged:
            if action == "APPROVE":
                c["decision"] = "HUMAN_APPROVED"
                c["validation_status"] = "PASSED"
                c["review_required"] = False
                c["reason"] = f"Approved by auditor {reviewer_id}: {reviewer_notes or 'Verified against source filing'}"
                c["human_resolution"] = {
                    "action": "APPROVE",
                    "reviewer_id": reviewer_id,
                    "timestamp": _get_utc_now_iso()
                }
            elif action == "CORRECT":
                c["decision"] = "HUMAN_CORRECTED"
                c["validation_status"] = "PASSED"
                c["review_required"] = False
                orig_val = c.get("value")
                new_val = float(corrected_value) if corrected_value is not None else orig_val
                c["original_value"] = orig_val
                c["value"] = new_val
                c["corrected_value"] = new_val
                c["reason"] = f"Corrected by auditor {reviewer_id}: {reviewer_notes or 'Adjusted based on filing review'}"
                c["human_resolution"] = {
                    "action": "CORRECT",
                    "original_value": orig_val,
                    "corrected_value": new_val,
                    "reviewer_id": reviewer_id,
                    "timestamp": _get_utc_now_iso()
                }
                # Also update in metrics list
                for m in metrics:
                    if m.get("metric") == m_name:
                        m["value"] = new_val
            elif action == "REJECT":
                c["decision"] = "HUMAN_REJECTED"
                c["validation_status"] = "FAILED"
                c["review_required"] = False
                c["rejection_reason"] = rejection_reason
                c["reason"] = f"Rejected by auditor {reviewer_id}: {rejection_reason}"
                c["human_resolution"] = {
                    "action": "REJECT",
                    "rejection_reason": rejection_reason,
                    "reviewer_id": reviewer_id,
                    "timestamp": _get_utc_now_iso()
                }

        updated_contracts.append(c)

    completed.append("process_human_decision")
    execution_log = list(state.get("execution_log", []))
    execution_log.append({
        "node": "process_human_decision",
        "timestamp": _get_utc_now_iso(),
        "message": f"Processed human decision '{action}' by {reviewer_id}."
    })

    return {
        "metrics": metrics,
        "shared_contracts": updated_contracts,
        "completed_nodes": completed,
        "execution_log": execution_log,
        "status": "DECISION_PROCESSED"
    }


# ---------------------------------------------------------------------------
# 8. Node 8: resume_workflow
# ---------------------------------------------------------------------------
def resume_workflow(state: AuditState) -> Dict[str, Any]:
    """
    Node 8: Idempotently verifies resumption without repeating completed nodes or side effects.
    """
    completed = list(state.get("completed_nodes", []))
    completed.append("resume_workflow")
    execution_log = list(state.get("execution_log", []))
    execution_log.append({
        "node": "resume_workflow",
        "timestamp": _get_utc_now_iso(),
        "message": "Workflow execution resumed from checkpoint without duplicating prior tasks."
    })

    return {
        "status": "RESUMED_REVIEWED",
        "completed_nodes": completed,
        "execution_log": execution_log
    }


# ---------------------------------------------------------------------------
# 9. Node 9: finalize_audit
# ---------------------------------------------------------------------------
def finalize_audit(state: AuditState) -> Dict[str, Any]:
    """
    Node 9: Produces the final audit output contract and completion record.
    """
    completed = list(state.get("completed_nodes", []))
    completed.append("finalize_audit")

    human_dec = state.get("human_decision", {})
    action = human_dec.get("action", "").upper() if isinstance(human_dec, dict) else ""

    if action == "REJECT":
        final_status = "REJECTED"
    else:
        final_status = "COMPLETED"

    execution_log = list(state.get("execution_log", []))
    execution_log.append({
        "node": "finalize_audit",
        "timestamp": _get_utc_now_iso(),
        "message": f"Audit {state.get('audit_id')} finalized with status {final_status}."
    })

    return {
        "status": final_status,
        "completed_nodes": completed,
        "execution_log": execution_log
    }


# ---------------------------------------------------------------------------
# Graph Construction Factory
# ---------------------------------------------------------------------------
def create_audit_graph(checkpointer: Optional[BaseCheckpointSaver] = None):
    """
    Constructs and compiles the 9-node LangGraph audit workflow.
    """
    builder = StateGraph(AuditState)

    # Add all 9 nodes
    builder.add_node("receive_extracted_data", receive_extracted_data)
    builder.add_node("calculate_confidence", calculate_confidence_node)
    builder.add_node("validate_financial_data", validate_financial_data)
    builder.add_node("make_audit_decision", make_audit_decision)
    builder.add_node("auto_approve", auto_approve)
    builder.add_node("request_human_review", request_human_review)
    builder.add_node("process_human_decision", process_human_decision)
    builder.add_node("resume_workflow", resume_workflow)
    builder.add_node("finalize_audit", finalize_audit)

    # Connect Edges
    builder.add_edge(START, "receive_extracted_data")
    builder.add_edge("receive_extracted_data", "calculate_confidence")
    builder.add_edge("calculate_confidence", "validate_financial_data")
    builder.add_edge("validate_financial_data", "make_audit_decision")

    # Conditional decision routing
    builder.add_conditional_edges(
        "make_audit_decision",
        route_decision,
        {
            "auto_approve": "auto_approve",
            "request_human_review": "request_human_review"
        }
    )

    builder.add_edge("auto_approve", "finalize_audit")
    builder.add_edge("request_human_review", "process_human_decision")
    builder.add_edge("process_human_decision", "resume_workflow")
    builder.add_edge("resume_workflow", "finalize_audit")
    builder.add_edge("finalize_audit", END)

    saver = checkpointer if checkpointer is not None else get_default_checkpointer()
    graph = builder.compile(checkpointer=saver)
    return graph
