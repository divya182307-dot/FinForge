"""
api/index.py - Vercel Serverless Function entrypoint for FinForge AI.

Wraps all hackathon endpoints, Task 1 SEC EDGAR APIs, Task 2 LangGraph workflow,
and all 12 advanced enterprise features into a high-performance FastAPI serverless application.
"""

import sys
import os
import logging
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

# Ensure repository root is on sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from backend.database import init_db, get_connection
from backend.audit_service import (
    get_all_companies,
    start_audit_run,
    get_audit_details,
    get_pending_reviews,
    process_review_decision,
    get_audit_history,
    get_accuracy_report,
    get_dashboard_summary,
    seed_companies_if_empty,
    reset_database_and_audits,
)
from backend.init_db import seed_demo_environment
from backend.workflow_engine import AuditWorkflowGraph
from backend.advanced_analytics import (
    compute_yoy_variance_analysis,
    get_adaptive_thresholds,
    MCP_TOOLS_MANIFEST,
)
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
    get_live_audit_monitoring,
)
from fin_sec_api import router as sec_router

logger = logging.getLogger("FinForgeServerless")

# 1. Initialize FastAPI Application
app = FastAPI(
    title="FinForge AI - Serverless API",
    description="Agentic Financial Filing Auditor API for Vercel Serverless Deployment",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# 2. Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Mount Task 1 SEC EDGAR Router
app.include_router(sec_router)

# 4. Frontend Single-Page App HTML Resolution
_FRONTEND_HTML_CACHE: Optional[str] = None

def get_frontend_html() -> str:
    global _FRONTEND_HTML_CACHE
    if _FRONTEND_HTML_CACHE is None:
        candidates = [
            os.path.join(os.path.dirname(__file__), "index.html"),
            os.path.join(REPO_ROOT, "index.html"),
            os.path.join(REPO_ROOT, "frontend", "index.html"),
            os.path.join(REPO_ROOT, "frontend", "dist", "index.html"),
        ]
        for c in candidates:
            if os.path.exists(c):
                try:
                    with open(c, "r", encoding="utf-8") as f:
                        _FRONTEND_HTML_CACHE = f.read()
                        break
                except Exception as e:
                    logger.warning("Failed to read %s: %s", c, e)
        if _FRONTEND_HTML_CACHE is None:
            _FRONTEND_HTML_CACHE = "<h1>FinForge AI Backend Running</h1>"
    return _FRONTEND_HTML_CACHE

# 5. Cold-Start Database Initialization & Path Normalization Middleware
_initialized = False

def ensure_database_ready():
    global _initialized
    if not _initialized:
        try:
            init_db()
            seed_companies_if_empty()
            # Ensure initial demonstration audits exist on cold-start
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM audit_runs")
            count = cursor.fetchone()["count"]
            conn.close()
            if count == 0:
                seed_demo_environment()
            _initialized = True
        except Exception as e:
            logger.error("Database cold-start initialization error: %s", e)

@app.middleware("http")
async def vercel_request_pipeline(request: Request, call_next):
    # A. Strip any Vercel internal script prefix if injected into ASGI path
    raw_path = request.scope.get("path", "")
    for prefix in ("/api/index.py", "/index.py"):
        if raw_path.startswith(prefix):
            remainder = raw_path[len(prefix):]
            if not remainder.startswith("/"):
                remainder = "/" + remainder
            request.scope["path"] = remainder
            break

    # B. Cold-start DB init
    ensure_database_ready()
    return await call_next(request)


# ==========================================
# Frontend SPA & Root Endpoints
# ==========================================

@app.get("/", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
@app.get("/app", response_class=HTMLResponse)
def serve_frontend():
    """Serves the FinForge AI React single-page application dashboard."""
    return HTMLResponse(content=get_frontend_html(), status_code=200)

@app.get("/health")
def root_health():
    return {"status": "healthy", "service": "FinForge AI", "deployment": "Vercel Serverless"}

@app.get("/companies")
def root_companies():
    ensure_database_ready()
    return get_all_companies()


# ==========================================
# Pydantic Request Models
# ==========================================
class AuditRunRequest(BaseModel):
    ticker: str
    period: str = "FY2023"

class FilingUploadRequest(BaseModel):
    ticker: str = "DEMO"
    company_name: Optional[str] = "Uploaded Filing Corp"
    period: str = "FY2023"
    sector: Optional[str] = "Corporate Financial Filing"
    cik: Optional[str] = "0009999999"
    metrics: Optional[List[Dict[str, Any]]] = None
    raw_content: Optional[str] = None

class ReviewDecisionRequest(BaseModel):
    decision: str
    corrected_value: Optional[float] = None
    reason: Optional[str] = ""
    comments: Optional[str] = ""
    audit_id: Optional[str] = None
    metric_name: Optional[str] = None

class CopilotChatRequest(BaseModel):
    query: str
    audit_id: Optional[str] = None
    session_history: Optional[List[Dict[str, Any]]] = []


# ==========================================
# Core Hackathon Endpoints (Task 1, 2, 3)
# ==========================================

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "FinForge AI", "deployment": "Vercel Serverless"}

@app.post("/api/audit/reset")
def api_reset_audits():
    """Wipe all audit runs and reviews for a clean demonstration run."""
    ensure_database_ready()
    return reset_database_and_audits()

@app.get("/api/companies")
def api_get_companies():
    """1. GET /api/companies"""
    ensure_database_ready()
    return get_all_companies()

@app.post("/api/audit/run", status_code=201)
def api_run_audit(req: AuditRunRequest):
    """2. POST /api/audit/run"""
    ensure_database_ready()
    try:
        return start_audit_run(req.ticker, req.period)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/audit/upload", status_code=201)
def api_upload_filing(req: FilingUploadRequest):
    """2b. POST /api/audit/upload - Ingest custom/uploaded Form 10-K filing data"""
    ensure_database_ready()
    try:
        metrics = req.metrics or []
        if req.raw_content and not metrics:
            import json as _json
            try:
                parsed = _json.loads(req.raw_content)
                if isinstance(parsed, list):
                    metrics = parsed
                elif isinstance(parsed, dict):
                    if "metrics" in parsed and isinstance(parsed["metrics"], list):
                        metrics = parsed["metrics"]
                    else:
                        metrics = [{"metric_name": k, "extracted_value": float(v)} for k, v in parsed.items() if isinstance(v, (int, float))]
            except Exception:
                pass
        return start_audit_run(
            ticker=req.ticker,
            period=req.period,
            custom_extractions=metrics,
            company_name=req.company_name,
            cik=req.cik,
            sector=req.sector
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/audit/{audit_id}")
def api_get_audit(audit_id: str):
    """3. GET /api/audit/{id}"""
    ensure_database_ready()
    details = get_audit_details(audit_id)
    if not details:
        raise HTTPException(status_code=404, detail="Audit run not found")
    return details

@app.get("/api/reviews")
def api_get_reviews(audit_id: Optional[str] = None):
    """4. GET /api/reviews"""
    ensure_database_ready()
    return get_pending_reviews(audit_id)

@app.post("/api/reviews/{review_id}/decision")
def api_submit_review_decision(review_id: str, req: ReviewDecisionRequest):
    """5. POST /api/reviews/{id}/decision"""
    ensure_database_ready()
    try:
        return process_review_decision(
            review_id,
            req.decision,
            req.corrected_value,
            req.reason,
            req.comments,
            audit_id=req.audit_id,
            metric_name=req.metric_name,
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/reviews/{review_id}/approve")
def api_quick_approve(review_id: str, req: Optional[ReviewDecisionRequest] = None):
    """Quick 1-click approval helper endpoint."""
    ensure_database_ready()
    reason = req.reason if req and req.reason else "Auditor approved extracted metric based on 10-K disclosures"
    comments = req.comments if req else ""
    audit_id = req.audit_id if req else None
    metric_name = req.metric_name if req else None
    return process_review_decision(review_id, "approve", None, reason, comments, audit_id=audit_id, metric_name=metric_name)

@app.post("/api/reviews/{review_id}/reject")
def api_quick_reject(review_id: str, req: Optional[ReviewDecisionRequest] = None):
    """Quick 1-click rejection helper endpoint."""
    ensure_database_ready()
    reason = req.reason if req and req.reason else "Auditor rejected metric due to balance sheet invariant failure"
    comments = req.comments if req else ""
    audit_id = req.audit_id if req else None
    metric_name = req.metric_name if req else None
    return process_review_decision(review_id, "reject", None, reason, comments, audit_id=audit_id, metric_name=metric_name)

@app.post("/api/reviews/{review_id}/correct")
def api_quick_correct(review_id: str, req: Optional[ReviewDecisionRequest] = None):
    """Quick 1-click correction helper endpoint."""
    ensure_database_ready()
    corrected_val = req.corrected_value if req else None
    reason = req.reason if req and req.reason else "Corrected to match SEC EDGAR XBRL Item 8 accounting invariants"
    comments = req.comments if req else ""
    audit_id = req.audit_id if req else None
    metric_name = req.metric_name if req else None
    return process_review_decision(review_id, "correct", corrected_val, reason, comments, audit_id=audit_id, metric_name=metric_name)

@app.get("/api/audit/{audit_id}/report")
def api_get_audit_report(audit_id: str):
    """6. GET /api/audit/{id}/report"""
    ensure_database_ready()
    report = get_accuracy_report(audit_id)
    if not report:
        raise HTTPException(status_code=404, detail="Accuracy report not ready")
    return report

@app.get("/api/audit/{audit_id}/history")
def api_get_audit_history(audit_id: str):
    """7. GET /api/audit/{id}/history"""
    ensure_database_ready()
    return get_audit_history(audit_id)


# ==========================================
# Supplementary Hackathon Endpoints
# ==========================================

@app.get("/api/dashboard/summary")
def api_dashboard_summary():
    ensure_database_ready()
    return get_dashboard_summary()

@app.get("/api/workflow/{audit_id}")
def api_workflow_state(audit_id: str):
    ensure_database_ready()
    wf_state = AuditWorkflowGraph.get_workflow_state(audit_id)
    if not wf_state:
        raise HTTPException(status_code=404, detail="Audit workflow not found")
    return wf_state

@app.get("/api/audits")
def api_list_audits():
    ensure_database_ready()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.*, c.name as company_name 
        FROM audit_runs a
        JOIN companies c ON a.ticker = c.ticker
        ORDER BY a.started_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ==========================================
# 12 Advanced Enterprise Feature Endpoints
# ==========================================

# Feature 1: Anomaly Explanation Engine
@app.get("/api/audit/{audit_id}/anomalies")
@app.get("/api/audit/{audit_id}/explanations")
def api_anomalies(audit_id: str):
    ensure_database_ready()
    return get_audit_anomalies_and_explanations(audit_id)

# Feature 2: Smart Evidence Viewer
@app.get("/api/audit/{audit_id}/evidence")
def api_evidence(audit_id: str, metric_id: Optional[str] = Query(None)):
    ensure_database_ready()
    return get_smart_evidence_viewer(audit_id, metric_id)

# Feature 3: AI Copilot Chat Assistant
@app.post("/api/copilot/chat")
def api_copilot(req: CopilotChatRequest):
    ensure_database_ready()
    try:
        return process_copilot_chat(req.query, req.audit_id, req.session_history)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Feature 4: Financial Risk Score
@app.get("/api/audit/{audit_id}/risk")
@app.get("/api/audit/{audit_id}/risk-score")
def api_risk_score(audit_id: str):
    ensure_database_ready()
    return calculate_audit_risk_score(audit_id)

# Feature 5: Multi-Company Peer Benchmarking
@app.get("/api/benchmark")
@app.get("/api/benchmarking")
@app.get("/api/analytics/benchmarks")
def api_benchmarks(period: str = Query("FY2023")):
    ensure_database_ready()
    return get_multi_company_benchmarking(period)

# Feature 6: Historical Financial Intelligence
@app.get("/api/company/{ticker}/historical")
@app.get("/api/company/{ticker}/history")
@app.get("/api/historical/{ticker}")
def api_company_history(ticker: str):
    ensure_database_ready()
    return get_company_historical_intelligence(ticker)

# Feature 7: Accounting Reconciliation Workspace
@app.get("/api/audit/{audit_id}/reconciliation")
def api_reconciliation(audit_id: str):
    ensure_database_ready()
    return get_accounting_reconciliation_workspace(audit_id)

# Feature 8: Exportable Audit Report (HTML/Certificate)
@app.get("/api/audit/{audit_id}/report/download")
@app.get("/api/audit/{audit_id}/report/pdf")
@app.get("/api/audit/{audit_id}/report/html")
def api_report_download(audit_id: str, format: str = Query("html")):
    ensure_database_ready()
    if format in ("html", "pdf"):
        html_content = generate_audit_report_html(audit_id)
        return HTMLResponse(content=html_content)
    return generate_audit_report_payload(audit_id)

# Feature 9: Chronological Audit Timeline
@app.get("/api/audit/{audit_id}/timeline")
def api_timeline(audit_id: str):
    ensure_database_ready()
    return get_audit_timeline(audit_id)

# Feature 10: Reviewer Feedback Analytics
@app.get("/api/reviewer/feedback")
@app.get("/api/analytics/feedback")
def api_feedback():
    ensure_database_ready()
    return get_reviewer_feedback_analytics()

# Feature 11: Tamper-Evident SHA-256 Hash Chain Verification
@app.get("/api/audit/{audit_id}/integrity")
def api_integrity(audit_id: str):
    ensure_database_ready()
    return verify_audit_trail_integrity(audit_id)

# Feature 12: Live 9-Stage Telemetry Monitoring
@app.get("/api/audits/monitor")
@app.get("/api/audit/{audit_id}/live-status")
def api_live_monitoring(audit_id: Optional[str] = None):
    ensure_database_ready()
    return get_live_audit_monitoring(audit_id)

# Supplementary Analytics & MCP Endpoints
@app.get("/api/analytics/adaptive-thresholds")
def api_adaptive_thresholds():
    ensure_database_ready()
    return get_adaptive_thresholds()

@app.get("/api/mcp/tools")
def api_mcp_tools():
    return MCP_TOOLS_MANIFEST

@app.get("/api/analytics/yoy/{ticker}")
def api_yoy_analysis(ticker: str):
    ensure_database_ready()
    return compute_yoy_variance_analysis(ticker)


# ==========================================
# SPA Catch-All Client Routing
# ==========================================

@app.get("/{full_path:path}", response_class=HTMLResponse)
def spa_client_fallback(full_path: str):
    """Fallback handler for React SPA client-side routes, avoiding 404s."""
    if full_path.startswith("api/") or full_path == "api":
        raise HTTPException(status_code=404, detail=f"API endpoint '/{full_path}' not found")
    return HTMLResponse(content=get_frontend_html(), status_code=200)
