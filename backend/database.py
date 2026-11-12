"""
FinAudit AI - SQLite Database Layer
Implements append-only audit history, financial metric extraction storage,
validation results, and LangGraph workflow checkpoints.
"""
import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "finaudit.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Companies Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS companies (
        ticker TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        cik TEXT NOT NULL,
        sector TEXT NOT NULL,
        available_periods TEXT NOT NULL,
        filing_status TEXT NOT NULL,
        current_audit_status TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    # 2. Audit Runs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_runs (
        audit_id TEXT PRIMARY KEY,
        ticker TEXT NOT NULL,
        period TEXT NOT NULL,
        status TEXT NOT NULL, -- 'processing', 'paused_review', 'completed', 'failed'
        current_stage TEXT NOT NULL, -- 'retrieval', 'extraction', 'validation', 'human_review', 'reconciliation', 'report_ready'
        thread_id TEXT NOT NULL, -- LangGraph thread ID
        started_at TEXT NOT NULL,
        completed_at TEXT,
        summary TEXT,
        FOREIGN KEY (ticker) REFERENCES companies(ticker)
    )
    """)

    # 3. Extracted Financial Metrics Table (Never overwritten)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS extracted_metrics (
        metric_id TEXT PRIMARY KEY,
        audit_id TEXT NOT NULL,
        ticker TEXT NOT NULL,
        period TEXT NOT NULL,
        metric_name TEXT NOT NULL,
        extracted_value REAL NOT NULL,
        unit TEXT NOT NULL,
        confidence_score REAL NOT NULL,
        validation_status TEXT NOT NULL, -- 'passed', 'failed', 'pending_review'
        source_evidence TEXT NOT NULL,
        sec_filing_ref TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (audit_id) REFERENCES audit_runs(audit_id)
    )
    """)

    # 4. Validation Results Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS validation_results (
        validation_id TEXT PRIMARY KEY,
        audit_id TEXT NOT NULL,
        rule_name TEXT NOT NULL, -- 'accounting_equation', 'segment_integrity', 'yoy_variance'
        status TEXT NOT NULL, -- 'passed', 'failed', 'flagged'
        description TEXT NOT NULL,
        expected_value REAL,
        actual_value REAL,
        discrepancy REAL,
        details_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (audit_id) REFERENCES audit_runs(audit_id)
    )
    """)

    # 5. Review Decisions (Queue Items)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS review_items (
        review_id TEXT PRIMARY KEY,
        audit_id TEXT NOT NULL,
        metric_id TEXT NOT NULL,
        ticker TEXT NOT NULL,
        metric_name TEXT NOT NULL,
        period TEXT NOT NULL,
        original_value REAL NOT NULL,
        unit TEXT NOT NULL,
        confidence_score REAL NOT NULL,
        validation_result TEXT NOT NULL,
        reason TEXT NOT NULL,
        source_evidence TEXT NOT NULL,
        status TEXT NOT NULL, -- 'pending', 'approved', 'corrected', 'rejected'
        created_at TEXT NOT NULL,
        resolved_at TEXT,
        FOREIGN KEY (audit_id) REFERENCES audit_runs(audit_id),
        FOREIGN KEY (metric_id) REFERENCES extracted_metrics(metric_id)
    )
    """)

    # 6. Immutable Append-Only Audit History Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_history (
        history_id INTEGER PRIMARY KEY AUTOINCREMENT,
        audit_id TEXT NOT NULL,
        metric_id TEXT NOT NULL,
        metric_name TEXT NOT NULL,
        original_value REAL NOT NULL,
        corrected_value REAL,
        decision TEXT NOT NULL, -- 'approve', 'correct', 'reject'
        reason TEXT NOT NULL,
        reviewer_comments TEXT,
        resumed_workflow INTEGER NOT NULL DEFAULT 1,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (audit_id) REFERENCES audit_runs(audit_id),
        FOREIGN KEY (metric_id) REFERENCES extracted_metrics(metric_id)
    )
    """)

    # 7. Final Accuracy Reports & Ground Truth Verification Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS accuracy_reports (
        report_id TEXT PRIMARY KEY,
        audit_id TEXT UNIQUE NOT NULL,
        ticker TEXT NOT NULL,
        period TEXT NOT NULL,
        total_metrics INTEGER NOT NULL,
        correct_metrics INTEGER NOT NULL,
        incorrect_metrics INTEGER NOT NULL,
        accuracy_pct REAL NOT NULL,
        auto_approved_count INTEGER NOT NULL,
        escalated_count INTEGER NOT NULL,
        ground_truth_json TEXT NOT NULL,
        status TEXT NOT NULL, -- 'draft', 'final'
        generated_at TEXT NOT NULL,
        FOREIGN KEY (audit_id) REFERENCES audit_runs(audit_id)
    )
    """)

    # 8. Feature 9: Chronological Audit Timeline Events
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_timeline_events (
        timeline_id TEXT PRIMARY KEY,
        audit_id TEXT NOT NULL,
        step_number INTEGER NOT NULL,
        stage_name TEXT NOT NULL,
        event_title TEXT NOT NULL,
        description TEXT NOT NULL,
        status TEXT NOT NULL, -- 'completed', 'in_progress', 'paused', 'failed'
        timestamp TEXT NOT NULL,
        reviewer_info TEXT,
        FOREIGN KEY (audit_id) REFERENCES audit_runs(audit_id)
    )
    """)

    # 9. Feature 11: Tamper-Evident SHA-256 Hash-Linked Audit Event Chain
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_event_chain (
        event_id TEXT PRIMARY KEY,
        audit_id TEXT NOT NULL,
        event_index INTEGER NOT NULL,
        prev_hash TEXT NOT NULL,
        curr_hash TEXT NOT NULL,
        event_type TEXT NOT NULL, -- 'INITIATED', 'FLAGGED_ANOMALY', 'HUMAN_DECISION', 'WORKFLOW_RESUMED', 'VERIFIED_REPORT'
        original_value REAL,
        corrected_value REAL,
        decision TEXT,
        reason TEXT,
        reviewer TEXT,
        timestamp TEXT NOT NULL,
        data_payload TEXT,
        FOREIGN KEY (audit_id) REFERENCES audit_runs(audit_id)
    )
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at:", DB_PATH)

