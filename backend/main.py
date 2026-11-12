"""
FinAudit AI - FastAPI Application & Standard-Library Unified HTTP Server
Provides the 7 required hackathon REST endpoints:
1. GET  /api/companies
2. POST /api/audit/run
3. GET  /api/audit/{id}
4. GET  /api/reviews
5. POST /api/reviews/{id}/decision
6. GET  /api/audit/{id}/report
7. GET  /api/audit/{id}/history

Also provides:
- GET /api/dashboard/summary
- GET /api/workflow/{id}
- GET /api/audits
- Serves the frontend single-page fintech dashboard at /
"""
import sys
import os
import json
import re
from urllib.parse import urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler
import socketserver

# Add repo root to sys.path
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
from backend.advanced_analytics import compute_yoy_variance_analysis, get_adaptive_thresholds, MCP_TOOLS_MANIFEST

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))
if not os.path.exists(FRONTEND_DIR):
    FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

class FinAuditRequestHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        # Enable CORS for local development
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, message, status=400):
        self.send_json({"error": message, "status": status}, status=status)

    def get_parsed_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            raw_body = self.rfile.read(content_length).decode("utf-8")
            try:
                return json.loads(raw_body)
            except Exception:
                return {}
        return {}

    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query = parse_qs(parsed_url.query)

        # 1. GET /api/companies
        if path == "/api/companies":
            companies = get_all_companies()
            return self.send_json(companies)

        # 2. GET /api/dashboard/summary
        if path == "/api/dashboard/summary":
            summary = get_dashboard_summary()
            return self.send_json(summary)

        # Bonus 1: GET /api/analytics/adaptive-thresholds
        if path == "/api/analytics/adaptive-thresholds":
            thresholds = get_adaptive_thresholds()
            return self.send_json(thresholds)

        # Bonus 2: GET /api/mcp/tools
        if path == "/api/mcp/tools":
            return self.send_json(MCP_TOOLS_MANIFEST)

        # Bonus 3: GET /api/analytics/yoy/{ticker}
        yoy_match = re.match(r"^/api/analytics/yoy/([^/]+)$", path)
        if yoy_match:
            ticker = yoy_match.group(1)
            yoy_data = compute_yoy_variance_analysis(ticker)
            return self.send_json(yoy_data)

        # 3. GET /api/reviews
        if path == "/api/reviews":
            audit_id = query.get("audit_id", [None])[0]
            reviews = get_pending_reviews(audit_id)
            return self.send_json(reviews)

        # 4. GET /api/audits (all audits)
        if path == "/api/audits":
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
            SELECT a.*, c.name as company_name
            FROM audit_runs a
            JOIN companies c ON a.ticker = c.ticker
            ORDER BY a.started_at DESC
            """)
            audits = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return self.send_json(audits)

        # 5. GET /api/audit/{id}/report
        report_match = re.match(r"^/api/audit/([^/]+)/report$", path)
        if report_match:
            audit_id = report_match.group(1)
            report = get_accuracy_report(audit_id)
            if report:
                return self.send_json(report)
            return self.send_error_json("Audit or report not found", status=404)

        # 6. GET /api/audit/{id}/history
        history_match = re.match(r"^/api/audit/([^/]+)/history$", path)
        if history_match:
            audit_id = history_match.group(1)
            history = get_audit_history(audit_id)
            return self.send_json(history)

        # 7. GET /api/workflow/{id}
        wf_match = re.match(r"^/api/workflow/([^/]+)$", path)
        if wf_match:
            audit_id = wf_match.group(1)
            wf_state = AuditWorkflowGraph.get_workflow_state(audit_id)
            if wf_state:
                return self.send_json(wf_state)
            return self.send_error_json("Workflow not found", status=404)

        # 8. GET /api/audit/{id}
        audit_match = re.match(r"^/api/audit/([^/]+)$", path)
        if audit_match:
            audit_id = audit_match.group(1)
            audit = get_audit_details(audit_id)
            if audit:
                return self.send_json(audit)
            return self.send_error_json("Audit run not found", status=404)

        # Serve static UI files
        self.serve_frontend(path)

    def do_POST(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        body = self.get_parsed_body()

        # 1. POST /api/audit/run
        if path == "/api/audit/run":
            ticker = body.get("ticker")
            period = body.get("period", "FY2023")
            if not ticker:
                return self.send_error_json("Ticker is required", status=400)
            try:
                result = start_audit_run(ticker, period)
                return self.send_json(result, status=201)
            except Exception as e:
                return self.send_error_json(str(e), status=500)

        # 2. POST /api/reviews/{id}/decision
        decision_match = re.match(r"^/api/reviews/([^/]+)/decision$", path)
        if decision_match:
            review_id = decision_match.group(1)
            decision = body.get("decision")
            corrected_value = body.get("corrected_value")
            reason = body.get("reason", "")
            comments = body.get("comments", "")
            if not decision:
                return self.send_error_json("Decision ('approve', 'correct', 'reject') is required", status=400)
            try:
                result = process_review_decision(review_id, decision, corrected_value, reason, comments)
                return self.send_json(result)
            except ValueError as ve:
                return self.send_error_json(str(ve), status=400)
            except Exception as e:
                return self.send_error_json(str(e), status=500)

        self.send_error_json("Endpoint not found", status=404)

    def serve_frontend(self, path):
        # Default to index.html for SPA routes
        if path == "/" or not os.path.exists(os.path.join(FRONTEND_DIR, path.lstrip("/"))):
            filepath = os.path.join(FRONTEND_DIR, "index.html")
        else:
            filepath = os.path.join(FRONTEND_DIR, path.lstrip("/"))

        if os.path.exists(filepath) and os.path.isfile(filepath):
            content_type = "text/html"
            if filepath.endswith(".js") or filepath.endswith(".jsx"):
                content_type = "application/javascript"
            elif filepath.endswith(".css"):
                content_type = "text/css"
            elif filepath.endswith(".json"):
                content_type = "application/json"
            elif filepath.endswith(".png"):
                content_type = "image/png"
            elif filepath.endswith(".svg"):
                content_type = "image/svg+xml"

            try:
                with open(filepath, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_error_json(f"Error reading file: {str(e)}", status=500)
        else:
            self.send_error_json("Frontend file not found", status=404)

def run_server(port=8000):
    init_db()
    server_address = ("0.0.0.0", port)
    httpd = socketserver.TCPServer(server_address, FinAuditRequestHandler)
    print("=" * 70)
    print(f"[*] FinAudit AI Backend & Dashboard Server Active")
    print(f"[*] Local URL: http://localhost:{port}")
    print(f"[*] API Base:  http://localhost:{port}/api")
    print("=" * 70)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        httpd.server_close()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    run_server(port=port)

