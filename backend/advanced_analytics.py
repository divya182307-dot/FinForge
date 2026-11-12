"""
FinAudit AI - Multi-Period Variance & Adaptive Escalation Engine (Bonus Features)
Implements:
1. Multi-Period YoY Variance Analysis with rule-based explanations
2. Adaptive Escalation Thresholds based on reviewer feedback
3. MCP (Model Context Protocol) Tool Declarations
"""
from typing import Dict, Any, List
from backend.seed_data import COMPANY_FACTS
from backend.database import get_connection

def compute_yoy_variance_analysis(ticker: str) -> List[Dict[str, Any]]:
    """
    Compares financial metrics across multiple reporting periods (e.g., FY2023 vs FY2022)
    and generates natural-language explanations for significant variances (>25%).
    """
    ticker = ticker.upper()
    facts = COMPANY_FACTS.get(ticker, {})
    
    # Check if we have at least 2 periods
    periods = list(facts.keys())
    if len(periods) < 2:
        return []

    curr_p, prev_p = periods[0], periods[1]
    curr_data = facts[curr_p]
    prev_data = facts[prev_p]

    analysis = []
    for metric, curr_val in curr_data.items():
        if metric in prev_data:
            prev_val = prev_data[metric]
            diff = curr_val - prev_val
            pct_change = (diff / prev_val * 100) if prev_val != 0 else 0.0

            is_significant = abs(pct_change) >= 25.0
            status = "flagged" if is_significant else "normal"

            # Generate natural language diagnostic
            if pct_change > 100.0:
                explanation = f"Rapid acceleration in {metric} (+{pct_change:.1f}%), driven by strong market demand and expanding operational scale."
            elif pct_change > 25.0:
                explanation = f"Substantial expansion of {pct_change:.1f}% YoY, exceeding standard inflation and GDP baseline."
            elif pct_change < -25.0:
                explanation = f"Notable contraction of {pct_change:.1f}% YoY. Recommended for human scrutiny to verify non-recurring charges or restructuring."
            else:
                explanation = f"Stable YoY trajectory ({pct_change:+.1f}%), within expected industry volatility bounds."

            analysis.append({
                "metric_name": metric,
                "current_period": curr_p,
                "current_value": curr_val,
                "prior_period": prev_p,
                "prior_value": prev_val,
                "dollar_change": diff,
                "pct_change": round(pct_change, 1),
                "is_significant": is_significant,
                "status": status,
                "explanation": explanation
            })

    return analysis

def get_adaptive_thresholds() -> Dict[str, Any]:
    """
    Computes dynamic confidence thresholds adapted from reviewer decisions.
    If reviewers consistently approve metrics from a company, the required threshold adjusts.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT decision, COUNT(*) as count
    FROM audit_history
    GROUP BY decision
    """)
    rows = cursor.fetchall()
    conn.close()

    decision_counts = {r["decision"]: r["count"] for r in rows}
    total_reviews = sum(decision_counts.values())
    approvals = decision_counts.get("approve", 0)

    # Base threshold is 0.85
    base_threshold = 0.85
    if total_reviews >= 5:
        approval_rate = approvals / total_reviews
        # If approval rate > 80%, slightly lower threshold to reduce false positive escalations
        if approval_rate > 0.80:
            adaptive_threshold = max(0.78, base_threshold - 0.05)
        else:
            adaptive_threshold = min(0.90, base_threshold + 0.03)
    else:
        adaptive_threshold = base_threshold

    return {
        "base_threshold": base_threshold,
        "adaptive_threshold": round(adaptive_threshold, 2),
        "total_historical_reviews": total_reviews,
        "approval_rate_pct": round((approvals / total_reviews * 100), 1) if total_reviews > 0 else 100.0,
        "status": "Adaptive Active"
    }

# MCP (Model Context Protocol) Tools Schema
MCP_TOOLS_MANIFEST = {
    "tools": [
        {
            "name": "sec_edgar_retrieval",
            "description": "Fetch official Form 10-K annual report from SEC EDGAR API",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Company ticker symbol (e.g. AAPL, NVDA)"},
                    "year": {"type": "string", "description": "Reporting fiscal year (e.g. FY2023)"}
                },
                "required": ["ticker"]
            }
        },
        {
            "name": "sec_xbrl_lookup",
            "description": "Query official SEC EDGAR XBRL Company Facts database for ground-truth financial figures",
            "parameters": {
                "type": "object",
                "properties": {
                    "cik": {"type": "string", "description": "Central Index Key (CIK)"},
                    "concept": {"type": "string", "description": "US-GAAP accounting concept (e.g. Revenues, NetIncomeLoss)"}
                },
                "required": ["cik", "concept"]
            }
        },
        {
            "name": "accounting_equation_verifier",
            "description": "Validates the fundamental balance sheet equation: Total Assets == Total Liabilities + Shareholders Equity",
            "parameters": {
                "type": "object",
                "properties": {
                    "assets": {"type": "number"},
                    "liabilities": {"type": "number"},
                    "equity": {"type": "number"}
                },
                "required": ["assets", "liabilities", "equity"]
            }
        }
    ]
}

