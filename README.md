# FinAudit AI — Human-in-the-Loop Financial Filing Auditor Agent (PS-01)

**MINEARENA 1.0 Hackathon (BIET Davangere)**  
**Module:** Task 3 – Financial Audit Dashboard, Human Review & System Integration  
**Role:** Member 3 – Senior Full-Stack Engineer, Fintech UI/UX Designer & System Integration Architect

---

## 1. Executive Summary

**FinAudit AI** is an enterprise-grade agentic financial filing auditor designed for autonomous SEC EDGAR 10-K analysis with a strictly governed **Human-in-the-Loop (HITL)** architecture. 

It solves the critical problem of automated financial extraction hallucination and OCR discrepancies by combining:
1. **Member 1 – SEC Extraction Engine:** Automated retrieval of 10-K filings, metric extraction, and confidence scoring.
2. **Member 2 – Accounting Validation Engine:** Automated checking of accounting rules ($Assets = Liabilities + Equity$), segment integrity, and LangGraph state graph with interrupt checkpoints.
3. **Member 3 (This Module) – Integration & Review Dashboard:** FastAPI REST API, SQLite database with append-only immutable audit history, LangGraph resumption controller, and a dark-navy fintech dashboard (Bloomberg / Linear inspired) featuring 8 full views and Approve / Correct / Reject workflows.

---

## 2. Complete Workflow

```
[Company Selection: AAPL, MSFT, AMZN, GOOGL, NVDA]
                       │
                       ▼
          [SEC 10-K Filing Retrieval]
                       │
                       ▼
          [Financial Metrics Extraction]
     (Revenue, Net Income, Assets, Liabilities,
      Shareholders' Equity, Operating Cash Flow, etc.)
                       │
                       ▼
         [Confidence Scoring & Evidence]
                       │
                       ▼
        [Accounting Equation Validation]
   (Total Assets == Total Liabilities + Equity)
                       │
        ┌──────────────┴──────────────┐
        ▼                             ▼
 [Passed Checks]               [Flagged Discrepancy]
  (Confidence >= 0.85)          (Low Confidence / Variance)
        │                             │
        │                             ▼
        │                 [LangGraph Interrupt Node]
        │                (Workflow Paused: paused_review)
        │                             │
        │                             ▼
        │                 [Human Review Center]
        │              ┌──────────────┼──────────────┐
        │              ▼              ▼              ▼
        │          [APPROVE]      [CORRECT]       [REJECT]
        │              │              │              │
        │              └──────────────┼──────────────┘
        │                             ▼
        │                 [Append-Only Audit History]
        │              (Original Value NEVER Overwritten)
        │                             │
        │                             ▼
        │                 [LangGraph Resumes Execution]
        │                             │
        └──────────────┬──────────────┘
                       │
                       ▼
    [SEC EDGAR XBRL Ground-Truth Verification]
                       │
                       ▼
       [Final Accuracy Certificate & Report]
```

---

## 3. Technology Stack

- **Backend:** Python 3.12, FastAPI / REST Standard Architecture, SQLite3, LangGraph-compatible state graph.
- **Frontend:** React 18, Tailwind CSS, Lucide Icons, JetBrains Mono & Inter typography, Bloomberg Terminal & Linear Dark Navy styling.
- **Zero-Dependency Instant Run:** The server contains an automated database seeder and unified REST engine that serves both the API and the full interactive UI out-of-the-box.

---

## 4. Quick Start (Instant Live Demonstration)

To run the complete full-stack application (FastAPI backend + 8-page interactive dashboard):

```powershell
python run_server.py
```

Open your browser and navigate to:
```
http://localhost:8000
```

### Pre-Seeded Demonstration Targets for Hackathon Judges:
1. **Apple Inc. (AAPL - FY2023):** Demonstrates a completed, fully autonomous audit with 100% SEC XBRL accuracy verification.
2. **NVIDIA Corporation (NVDA - FY2024):** Demonstrates a live **paused audit** awaiting human review! Net Income has been flagged due to OCR blur variance ($39,760M extracted vs $29,760M true fact, confidence 64%).
   - Navigate to **Human Review Center**.
   - Click **Correct Value**, enter `29760`, submit, and watch LangGraph **instantly resume**, update the audit status, log the immutable history, and re-compute the XBRL accuracy report to 100%!

---

## 5. API Reference (Agreed Endpoints)

| Method | Endpoint | Description |
| :---: | :--- | :--- |
| `GET` | `/api/companies` | List all 5 supported companies (AAPL, MSFT, AMZN, GOOGL, NVDA) |
| `POST` | `/api/audit/run` | Initiate an SEC filing audit (`{ "ticker": "AAPL", "period": "FY2023" }`) |
| `GET` | `/api/audit/{id}` | Retrieve audit metrics, validation results, and execution state |
| `GET` | `/api/reviews` | Fetch pending review queue items requiring human intervention |
| `POST` | `/api/reviews/{id}/decision` | Submit reviewer action (`approve`, `correct`, `reject`) & resume LangGraph |
| `GET` | `/api/audit/{id}/history` | Retrieve immutable, append-only human review audit history |
| `GET` | `/api/audit/{id}/report` | Retrieve final SEC XBRL ground-truth accuracy report |
| `GET` | `/api/dashboard/summary` | Real-time KPI statistics for executive overview |
| `GET` | `/api/workflow/{id}` | LangGraph execution thread state and node progress |

---

## 6. The 8 Dedicated Dashboard Views

1. **Overview Dashboard:** Total audited companies, total extracted metrics, auto-approved count, pending review alerts, extraction accuracy, and live audit runs table.
2. **Company Selection:** Company cards with SEC CIK, filing status, available 10-K reporting periods, and one-click "Initiate Full Financial Audit" action.
3. **Financial Extraction:** Multi-metric data grid (Revenue, Net Income, Total Assets, Total Liabilities, Shareholders' Equity, Operating Cash Flow, etc.), real-time search, status filtering, and expandable SEC 10-K source evidence snippet drawers.
4. **Validation Results:** Live Accounting Equation calculator visualizer ($Assets = Liabilities + Equity$), tolerance checks, and margin consistency checks.
5. **Human Review Center (Core HITL Workspace):** Review cards showing company, metric, original value, confidence score, escalation trigger diagnostic, original SEC evidence, and 3 functional actions:
   - **Approve:** Confirms value and resumes workflow.
   - **Correct:** Opens form with read-only original value, corrected value input, reason, comments, preserving original value separately in the database.
   - **Reject:** Requires rejection justification and marks metric as rejected.
6. **Workflow Monitoring:** Visual 6-stage pipeline tracker showing LangGraph node execution (`retrieval` → `extraction` → `validation` → `human_review` → `reconciliation` → `report_ready`).
7. **Audit History:** Append-only immutable ledger. Cannot be edited or deleted. Tracks original value, corrected value, reviewer decision, reason, and timestamp.
8. **Accuracy Reports:** Automated reconciliation against SEC EDGAR XBRL facts with metric-wise variance and printable Audit Certificate export.
