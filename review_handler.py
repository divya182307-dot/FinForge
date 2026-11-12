"""
FinAudit AI - Human Review Handler & Workflow Controller (Member 2)
Provides official integration endpoints specified in Section 11:
- calculate_confidence(metric)
- validate_accounting_equation(financial_data)
- validate_segments(financial_data)
- analyze_year_on_year(financial_data)
- run_audit_workflow(audit_data)
- submit_human_decision(audit_id, decision)
- resume_audit_workflow(audit_id)
"""

from typing import Dict, Any, Optional, Union, List
from langgraph.types import Command
from langgraph.checkpoint.base import BaseCheckpointSaver

from confidence_engine import calculate_confidence
from validation_engine import (
    validate_accounting_equation,
    validate_segments,
    analyze_year_on_year
)
from audit_graph import (
    create_audit_graph,
    get_default_checkpointer,
    DEFAULT_DB_PATH
)
from workflow_state import AuditState

# Map of active audit_id -> thread_id
_AUDIT_THREAD_REGISTRY: Dict[str, str] = {}


def register_audit_thread(audit_id: str, thread_id: str):
    _AUDIT_THREAD_REGISTRY[audit_id] = thread_id


def get_thread_for_audit(audit_id: str) -> str:
    return _AUDIT_THREAD_REGISTRY.get(audit_id, f"thread_{audit_id}")


def run_audit_workflow(
    audit_data: Union[Dict[str, Any], List[Dict[str, Any]]],
    checkpointer: Optional[BaseCheckpointSaver] = None,
    audit_id: Optional[str] = None,
    thread_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes the 9-node LangGraph audit workflow.
    If human review is required, pauses at request_human_review interrupt and persists state.
    Returns the current execution state (including interrupt details if paused).
    """
    saver = checkpointer if checkpointer is not None else get_default_checkpointer()
    graph = create_audit_graph(checkpointer=saver)

    # Resolve audit_id and thread_id
    if isinstance(audit_data, dict):
        aid = audit_id or audit_data.get("audit_id")
        tid = thread_id or audit_data.get("thread_id")
    else:
        aid = audit_id
        tid = thread_id

    if not aid:
        import uuid
        aid = f"aud_{uuid.uuid4().hex[:10]}"
    if not tid:
        tid = f"thread_{aid}"

    register_audit_thread(aid, tid)
    thread_config = {"configurable": {"thread_id": tid}}

    initial_state: AuditState = {
        "audit_id": aid,
        "thread_id": tid,
        "raw_input": audit_data,
        "completed_nodes": [],
        "execution_log": []
    }

    # Run workflow until complete or interrupted
    result_state = graph.invoke(initial_state, config=thread_config)
    return result_state


def submit_human_decision(
    audit_id: str,
    decision: Dict[str, Any],
    checkpointer: Optional[BaseCheckpointSaver] = None
) -> Dict[str, Any]:
    """
    Submits a human review decision (APPROVE, CORRECT, REJECT) for a paused audit.
    Resumes workflow execution from saved checkpoint.
    """
    return resume_audit_workflow(
        audit_id=audit_id,
        decision=decision,
        checkpointer=checkpointer
    )


def resume_audit_workflow(
    audit_id: str,
    decision: Optional[Dict[str, Any]] = None,
    checkpointer: Optional[BaseCheckpointSaver] = None
) -> Dict[str, Any]:
    """
    Resumes a paused audit workflow from its checkpoint using LangGraph Command(resume=decision).
    Avoids duplicate extraction or re-executing previously finished nodes.
    """
    saver = checkpointer if checkpointer is not None else get_default_checkpointer()
    graph = create_audit_graph(checkpointer=saver)

    tid = get_thread_for_audit(audit_id)
    thread_config = {"configurable": {"thread_id": tid}}

    human_payload = decision or {"action": "APPROVE", "reviewer_id": "auditor_auto"}

    # Resume graph execution using LangGraph Command(resume=...)
    resumed_state = graph.invoke(
        Command(resume=human_payload),
        config=thread_config
    )
    return resumed_state


def get_audit_state(
    audit_id: str,
    checkpointer: Optional[BaseCheckpointSaver] = None
) -> Optional[Dict[str, Any]]:
    """
    Retrieves current checkpoint state of an audit workflow from persistent checkpointer.
    """
    saver = checkpointer if checkpointer is not None else get_default_checkpointer()
    graph = create_audit_graph(checkpointer=saver)

    tid = get_thread_for_audit(audit_id)
    thread_config = {"configurable": {"thread_id": tid}}

    snapshot = graph.get_state(thread_config)
    if not snapshot or not snapshot.values:
        return None

    state_values = dict(snapshot.values)
    state_values["next_nodes"] = list(snapshot.next)
    state_values["is_interrupted"] = bool(snapshot.next and "request_human_review" in snapshot.next)
    return state_values
