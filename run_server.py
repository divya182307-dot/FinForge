"""
FinAudit AI - Startup Entrypoint
Launches the full-stack server (FastAPI REST Endpoints + Financial Dashboard).
"""
import sys
import os

if __name__ == "__main__":
    from backend.init_db import seed_demo_environment
    from backend.main import run_server

    print("[*] FinAudit AI - Starting up...")
    seed_demo_environment()
    port = int(os.environ.get("PORT", 8000))
    run_server(port=port)

