"""
FinAudit AI - Database Seeder
Pre-seeds:
- 5 Companies (AAPL, MSFT, AMZN, GOOGL, NVDA)
- Completed audit for Apple Inc. (AAPL FY2023) with 100% accuracy report
- Active paused audit for NVIDIA Corp. (NVDA FY2024) with Human Review Interrupt ready to test
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import init_db
from backend.audit_service import seed_companies_if_empty, start_audit_run, get_dashboard_summary

def seed_demo_environment():
    print("[1/3] Initializing SQLite database schema...")
    init_db()

    print("[2/3] Seeding 5 supported companies...")
    seed_companies_if_empty()

    print("[3/3] Generating initial audits for live demonstration...")
    # 1. Completed audit for AAPL
    aapl_audit = start_audit_run("AAPL", "FY2023")
    print(f" -> Apple audit created: {aapl_audit['audit_id']} (Status: {aapl_audit['status']})")

    # 2. Paused audit for NVDA to demo Human Review Queue
    nvda_audit = start_audit_run("NVDA", "FY2024")
    print(f" -> NVIDIA audit created: {nvda_audit['audit_id']} (Status: {nvda_audit['status']}, Flagged: {nvda_audit['escalated_count']})")

    summary = get_dashboard_summary()
    print("Pre-seed complete. Dashboard KPIs:", summary["kpis"])

if __name__ == "__main__":
    seed_demo_environment()

