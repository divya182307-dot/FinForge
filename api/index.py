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
)
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
    global _initialized
    if not _initialized:
        try:
            init_db()
            seed_companies_if_empty()
            _initialized = True
        except Exception as e:
            logger.error("Database cold-start initialization error: %s", e)
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
    return get_all_companies()


# ==========================================
# Pydantic Request Models
# ==========================================
class AuditRunRequest(BaseModel):
    ticker: str
    period: str = "FY2023"

class ReviewDecisionRequest(BaseModel):
    decision: str
    corrected_value: Optional[float] = None
    reason: Optional[str] = ""
    comments: Optional[str] = ""

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

@app.get("/api/companies")
def api_get_companies():
    """1. GET /api/companies"""
    return get_all_companies()

@app.post("/api/audit/run", status_code=201)
def api_run_audit(req: AuditRunRequest):
    """2. POST /api/audit/run"""
    try:
        return start_audit_run(req.ticker, req.period)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/audit/{audit_id}")
def api_get_audit(audit_id: str):
    """3. GET /api/audit/{id}"""
    details = get_audit_details(audit_id)
    if not details:
        raise HTTPException(status_code=404, detail="Audit run not found")
    return details

@app.get("/api/reviews")
def api_get_reviews(audit_id: Optional[str] = None):
    """4. GET /api/reviews"""
    return get_pending_reviews(audit_id)

@app.post("/api/reviews/{review_id}/decision")
def api_submit_review_decision(review_id: str, req: ReviewDecisionRequest):
    """5. POST /api/reviews/{id}/decision"""
    try:
        return process_review_decision(
            review_id,
            req.decision,
            req.corrected_value,
            req.reason,
            req.comments,
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/audit/{audit_id}/report")
def api_get_audit_report(audit_id: str):
    """6. GET /api/audit/{id}/report"""
    report = get_accuracy_report(audit_id)
    if not report:
        raise HTTPException(status_code=404, detail="Accuracy report not ready")
    return report

@app.get("/api/audit/{audit_id}/history")
def api_get_audit_history(audit_id: str):
    """7. GET /api/audit/{id}/history"""
    return get_audit_history(audit_id)


# ==========================================
# Supplementary Hackathon Endpoints
# ==========================================

@app.get("/api/dashboard/summary")
def api_dashboard_summary():
    return get_dashboard_summary()

@app.get("/api/workflow/{audit_id}")
def api_workflow_state(audit_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT thread_id FROM audit_runs WHERE audit_id = ?", (audit_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Audit workflow not found")
    graph = AuditWorkflowGraph()
    return graph.get_execution_state(row["thread_id"])

@app.get("/api/audits")
def api_list_audits():
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

@app.get("/api/audit/{audit_id}/anomalies")
def api_anomalies(audit_id: str):
    """Feature 1: Anomaly Explanation Engine"""
    return get_audit_anomalies_and_explanations(audit_id)

@app.get("/api/audit/{audit_id}/evidence")
def api_evidence(audit_id: str):
    """Feature 2: Smart Evidence Viewer"""
    return get_smart_evidence_viewer(audit_id)

@app.post("/api/copilot/chat")
def api_copilot(req: CopilotChatRequest):
    """Feature 3: AI Copilot Chat Assistant"""
    try:
        return process_copilot_chat(req.query, req.audit_id, req.session_history)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/audit/{audit_id}/risk-score")
def api_risk_score(audit_id: str):
    """Feature 4: Financial Risk Score"""
    return calculate_audit_risk_score(audit_id)

@app.get("/api/analytics/benchmarks")
def api_benchmarks():
    """Feature 5: Multi-Company Peer Benchmarking"""
    return get_multi_company_benchmarking()

@app.get("/api/company/{ticker}/history")
def api_company_history(ticker: str):
    """Feature 6: Historical Financial Intelligence"""
    return get_company_historical_intelligence(ticker)

@app.get("/api/audit/{audit_id}/reconciliation")
def api_reconciliation(audit_id: str):
    """Feature 7: Accounting Reconciliation Workspace"""
    return get_accounting_reconciliation_workspace(audit_id)

@app.get("/api/audit/{audit_id}/report/download")
def api_report_download(audit_id: str, format: str = Query("html")):
    """Feature 8: Exportable Audit Report (HTML/Certificate)"""
    if format == "html":
        html_content = generate_audit_report_html(audit_id)
        return HTMLResponse(content=html_content)
    return generate_audit_report_payload(audit_id)

@app.get("/api/audit/{audit_id}/timeline")
def api_timeline(audit_id: str):
    """Feature 9: Chronological Audit Timeline"""
    return get_audit_timeline(audit_id)

@app.get("/api/analytics/feedback")
def api_feedback():
    """Feature 10: Reviewer Feedback Analytics"""
    return get_reviewer_feedback_analytics()

@app.get("/api/audit/{audit_id}/integrity")
def api_integrity(audit_id: str):
    """Feature 11: Tamper-Evident SHA-256 Hash Chain Verification"""
    return verify_audit_trail_integrity(audit_id)

@app.get("/api/audit/{audit_id}/live-status")
def api_live_monitoring(audit_id: str):
    """Feature 12: Live 9-Stage Telemetry Monitoring"""
    return get_live_audit_monitoring(audit_id)


# ==========================================
# SPA Catch-All Client Routing
# ==========================================

@app.get("/{full_path:path}", response_class=HTMLResponse)
def spa_client_fallback(full_path: str):
    """Fallback handler for React SPA client-side routes, avoiding 404s."""
    if full_path.startswith("api/") or full_path == "api":
        raise HTTPException(status_code=404, detail=f"API endpoint '/{full_path}' not found")
    return HTMLResponse(content=get_frontend_html(), status_code=200)


