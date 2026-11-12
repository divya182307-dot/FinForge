"""
SEC EDGAR 10-K Ground Truth and Initial Database Fixtures
Contains real SEC 10-K reported figures (in millions USD) for:
- Apple Inc. (AAPL) CIK: 0000320193
- Microsoft Corp. (MSFT) CIK: 0000789019
- Amazon.com Inc. (AMZN) CIK: 0001018724
- Alphabet Inc. (GOOGL) CIK: 0001652044
- NVIDIA Corp. (NVDA) CIK: 0001045810
"""

COMPANIES_DATA = [
    {
        "ticker": "AAPL",
        "name": "Apple Inc.",
        "cik": "0000320193",
        "sector": "Technology Hardware & Equipment",
        "available_periods": ["FY2023", "FY2022", "FY2021"],
        "filing_status": "10-K Filed",
        "current_audit_status": "Ready for Audit"
    },
    {
        "ticker": "MSFT",
        "name": "Microsoft Corporation",
        "cik": "0000789019",
        "sector": "Software & Cloud Services",
        "available_periods": ["FY2023", "FY2022", "FY2021"],
        "filing_status": "10-K Filed",
        "current_audit_status": "Ready for Audit"
    },
    {
        "ticker": "AMZN",
        "name": "Amazon.com, Inc.",
        "cik": "0001018724",
        "sector": "E-Commerce & Cloud Infrastructure",
        "available_periods": ["FY2023", "FY2022", "FY2021"],
        "filing_status": "10-K Filed",
        "current_audit_status": "Ready for Audit"
    },
    {
        "ticker": "GOOGL",
        "name": "Alphabet Inc.",
        "cik": "0001652044",
        "sector": "Interactive Media & Services",
        "available_periods": ["FY2023", "FY2022", "FY2021"],
        "filing_status": "10-K Filed",
        "current_audit_status": "Ready for Audit"
    },
    {
        "ticker": "NVDA",
        "name": "NVIDIA Corporation",
        "cik": "0001045810",
        "sector": "Semiconductors & AI Compute",
        "available_periods": ["FY2024", "FY2023", "FY2022"],
        "filing_status": "10-K Filed",
        "current_audit_status": "Ready for Audit"
    }
]

# Ground Truth 10-K Facts (Values in Millions USD)
COMPANY_FACTS = {
    "AAPL": {
        "FY2023": {
            "Revenue": 383285.0,
            "Cost of Goods Sold": 214137.0,
            "Gross Profit": 169148.0,
            "Operating Income": 114301.0,
            "Net Income": 96995.0,
            "Total Assets": 352583.0,
            "Total Liabilities": 290437.0,
            "Shareholders' Equity": 62146.0,
            "Operating Cash Flow": 110543.0,
            "Cash and Cash Equivalents": 29965.0,
            "Capital Expenditures": 10959.0
        },
        "FY2022": {
            "Revenue": 394328.0,
            "Net Income": 99803.0,
            "Total Assets": 352755.0,
            "Total Liabilities": 302083.0,
            "Shareholders' Equity": 50672.0
        }
    },
    "MSFT": {
        "FY2023": {
            "Revenue": 211915.0,
            "Cost of Goods Sold": 65863.0,
            "Gross Profit": 146052.0,
            "Operating Income": 88523.0,
            "Net Income": 72361.0,
            "Total Assets": 411976.0,
            "Total Liabilities": 205753.0,
            "Shareholders' Equity": 206223.0,
            "Operating Cash Flow": 87582.0,
            "Cash and Cash Equivalents": 34704.0,
            "Capital Expenditures": 28107.0
        },
        "FY2022": {
            "Revenue": 198270.0,
            "Net Income": 72738.0,
            "Total Assets": 364840.0,
            "Total Liabilities": 198298.0,
            "Shareholders' Equity": 166542.0
        }
    },
    "AMZN": {
        "FY2023": {
            "Revenue": 574785.0,
            "Cost of Goods Sold": 304531.0,
            "Gross Profit": 270254.0,
            "Operating Income": 36852.0,
            "Net Income": 30425.0,
            "Total Assets": 527854.0,
            "Total Liabilities": 326101.0,
            "Shareholders' Equity": 201753.0,
            "Operating Cash Flow": 84946.0,
            "Cash and Cash Equivalents": 73890.0,
            "Capital Expenditures": 48100.0
        },
        "FY2022": {
            "Revenue": 513983.0,
            "Net Income": -2722.0,
            "Total Assets": 462675.0,
            "Total Liabilities": 316632.0,
            "Shareholders' Equity": 146043.0
        }
    },
    "GOOGL": {
        "FY2023": {
            "Revenue": 307394.0,
            "Cost of Goods Sold": 133332.0,
            "Gross Profit": 174062.0,
            "Operating Income": 84293.0,
            "Net Income": 73795.0,
            "Total Assets": 402392.0,
            "Total Liabilities": 119041.0,
            "Shareholders' Equity": 283351.0,
            "Operating Cash Flow": 101746.0,
            "Cash and Cash Equivalents": 24048.0,
            "Capital Expenditures": 32251.0
        },
        "FY2022": {
            "Revenue": 282836.0,
            "Net Income": 59972.0,
            "Total Assets": 365264.0,
            "Total Liabilities": 109122.0,
            "Shareholders' Equity": 256142.0
        }
    },
    "NVDA": {
        "FY2024": {
            "Revenue": 60922.0,
            "Cost of Goods Sold": 16621.0,
            "Gross Profit": 44301.0,
            "Operating Income": 32972.0,
            "Net Income": 29760.0,
            "Total Assets": 65728.0,
            "Total Liabilities": 22750.0,
            "Shareholders' Equity": 42978.0,
            "Operating Cash Flow": 28090.0,
            "Cash and Cash Equivalents": 7280.0,
            "Capital Expenditures": 1056.0
        },
        "FY2023": {
            "Revenue": 26974.0,
            "Cost of Goods Sold": 11618.0,
            "Gross Profit": 15356.0,
            "Operating Income": 4224.0,
            "Net Income": 4368.0,
            "Total Assets": 41182.0,
            "Total Liabilities": 19081.0,
            "Shareholders' Equity": 22101.0,
            "Operating Cash Flow": 5641.0,
            "Cash and Cash Equivalents": 3389.0
        }
    }
}

# Raw Extracted values from SEC Filings (Includes realistic edge cases / OCR discrepancies to trigger Human Review)
SIMULATED_EXTRACTIONS = {
    "AAPL": {
        "FY2023": [
            {
                "metric_name": "Revenue",
                "extracted_value": 383285.0,
                "unit": "USD Millions",
                "confidence_score": 0.99,
                "source_evidence": "Item 8, Consolidated Statements of Operations: Total net sales was $383,285 million for the fiscal year ended September 30, 2023.",
                "sec_filing_ref": "Form 10-K, Part II, Item 8, Page 48"
            },
            {
                "metric_name": "Net Income",
                "extracted_value": 96995.0,
                "unit": "USD Millions",
                "confidence_score": 0.98,
                "source_evidence": "Consolidated Statements of Operations: Net income was $96,995 million compared to $99,803 million in 2022.",
                "sec_filing_ref": "Form 10-K, Part II, Item 8, Page 48"
            },
            {
                "metric_name": "Total Assets",
                "extracted_value": 352583.0,
                "unit": "USD Millions",
                "confidence_score": 0.97,
                "source_evidence": "Consolidated Balance Sheets: Total assets as of September 30, 2023 stood at $352,583 million.",
                "sec_filing_ref": "Form 10-K, Part II, Item 8, Page 50"
            },
            {
                "metric_name": "Total Liabilities",
                "extracted_value": 290437.0,
                "unit": "USD Millions",
                "confidence_score": 0.96,
                "source_evidence": "Consolidated Balance Sheets: Total liabilities recorded at $290,437 million.",
                "sec_filing_ref": "Form 10-K, Part II, Item 8, Page 50"
            },
            {
                "metric_name": "Shareholders' Equity",
                "extracted_value": 62146.0,
                "unit": "USD Millions",
                "confidence_score": 0.96,
                "source_evidence": "Consolidated Balance Sheets: Total shareholders' equity was $62,146 million.",
                "sec_filing_ref": "Form 10-K, Part II, Item 8, Page 50"
            },
            {
                "metric_name": "Operating Cash Flow",
                "extracted_value": 110543.0,
                "unit": "USD Millions",
                "confidence_score": 0.97,
                "source_evidence": "Consolidated Statements of Cash Flows: Cash generated by operating activities was $110,543 million.",
                "sec_filing_ref": "Form 10-K, Part II, Item 8, Page 52"
            },
            {
                "metric_name": "Gross Profit",
                "extracted_value": 169148.0,
                "unit": "USD Millions",
                "confidence_score": 0.98,
                "source_evidence": "Gross margin recorded at $169,148 million for fiscal 2023.",
                "sec_filing_ref": "Form 10-K, Part II, Item 8, Page 48"
            },
            {
                "metric_name": "Operating Income",
                "extracted_value": 114301.0,
                "unit": "USD Millions",
                "confidence_score": 0.98,
                "source_evidence": "Operating income was $114,301 million for fiscal year 2023.",
                "sec_filing_ref": "Form 10-K, Part II, Item 8, Page 48"
            },
            {
                "metric_name": "Cash and Cash Equivalents",
                "extracted_value": 29965.0,
                "unit": "USD Millions",
                "confidence_score": 0.98,
                "source_evidence": "Consolidated Balance Sheets: Cash and cash equivalents were $29,965 million as of September 30, 2023.",
                "sec_filing_ref": "Form 10-K, Part II, Item 8, Page 50"
            },
            {
                "metric_name": "Capital Expenditures",
                "extracted_value": 10959.0,
                "unit": "USD Millions",
                "confidence_score": 0.95,
                "source_evidence": "Payments for acquisition of property, plant and equipment were $10,959 million.",
                "sec_filing_ref": "Form 10-K, Part II, Item 8, Page 52"
            }
        ]
    },
    "MSFT": {
        "FY2023": [
            {
                "metric_name": "Revenue",
                "extracted_value": 211915.0,
                "unit": "USD Millions",
                "confidence_score": 0.99,
                "source_evidence": "Income Statement: Total revenue was $211,915 million for year ended June 30, 2023.",
                "sec_filing_ref": "Form 10-K, Part II, Item 8, Page 64"
            },
            {
                "metric_name": "Net Income",
                "extracted_value": 72361.0,
                "unit": "USD Millions",
                "confidence_score": 0.98,
                "source_evidence": "Net Income: $72,361 million.",
                "sec_filing_ref": "Form 10-K, Part II, Item 8, Page 64"
            },
            {
                "metric_name": "Total Assets",
                "extracted_value": 411976.0,
                "unit": "USD Millions",
                "confidence_score": 0.98,
                "source_evidence": "Balance Sheet: Total Assets was $411,976 million.",
                "sec_filing_ref": "Form 10-K, Part II, Item 8, Page 66"
            },
            {
                "metric_name": "Total Liabilities",
                "extracted_value": 205753.0,
                "unit": "USD Millions",
                "confidence_score": 0.97,
                "source_evidence": "Balance Sheet: Total Liabilities $205,753 million.",
                "sec_filing_ref": "Form 10-K, Part II, Item 8, Page 66"
            },
            {
                "metric_name": "Shareholders' Equity",
                "extracted_value": 206223.0,
                "unit": "USD Millions",
                "confidence_score": 0.97,
                "source_evidence": "Balance Sheet: Total Stockholders' Equity was $206,223 million.",
                "sec_filing_ref": "Form 10-K, Part II, Item 8, Page 66"
            },
            {
                "metric_name": "Operating Cash Flow",
                "extracted_value": 87582.0,
                "unit": "USD Millions",
                "confidence_score": 0.96,
                "source_evidence": "Cash Flows: Net cash from operations $87,582 million.",
                "sec_filing_ref": "Form 10-K, Part II, Item 8, Page 68"
            },
            {
                "metric_name": "Gross Profit",
                "extracted_value": 146052.0,
                "unit": "USD Millions",
                "confidence_score": 0.97,
                "source_evidence": "Gross margin $146,052 million.",
                "sec_filing_ref": "Form 10-K, Part II, Item 8, Page 64"
            },
            {
                "metric_name": "Operating Income",
                "extracted_value": 88523.0,
                "unit": "USD Millions",
                "confidence_score": 0.98,
                "source_evidence": "Operating income was $88,523 million.",
                "sec_filing_ref": "Form 10-K, Part II, Item 8, Page 64"
            },
            {
                "metric_name": "Cash and Cash Equivalents",
                "extracted_value": 34704.0,
                "unit": "USD Millions",
                "confidence_score": 0.98,
                "source_evidence": "Balance Sheet: Cash and cash equivalents $34,704 million as of June 30, 2023.",
                "sec_filing_ref": "Form 10-K, Part II, Item 8, Page 66"
            }
        ]
    },
    "AMZN": {
        "FY2023": [
            {
                "metric_name": "Revenue",
                "extracted_value": 574785.0,
                "unit": "USD Millions",
                "confidence_score": 0.99,
                "source_evidence": "Consolidated Statements of Operations: Net sales $574,785 million.",
                "sec_filing_ref": "Form 10-K, Part II, Item 8, Page 43"
            },
            {
                "metric_name": "Net Income",
                "extracted_value": 30425.0,
                "unit": "USD Millions",
                "confidence_score": 0.98,
                "source_evidence": "Consolidated Statements of Operations: Net income $30,425 million.",
                "sec_filing_ref": "Form 10-K, Part II, Item 8, Page 43"
            },
            {
                "metric_name": "Total Assets",
                "extracted_value": 527854.0,
                "unit": "USD Millions",
                "confidence_score": 0.96,
                "source_evidence": "Balance Sheet: Total assets $527,854 million.",
                "sec_filing_ref": "Form 10-K, Part II, Item 8, Page 45"
            },
            {
                "metric_name": "Total Liabilities",
                "extracted_value": 326101.0,
                "unit": "USD Millions",
                "confidence_score": 0.96,
                "source_evidence": "Balance Sheet: Total liabilities $326,101 million.",
                "sec_filing_ref": "Form 10-K, Part II, Item 8, Page 45"
            },
            {
                "metric_name": "Shareholders' Equity",
                "extracted_value": 201753.0,
                "unit": "USD Millions",
                "confidence_score": 0.96,
                "source_evidence": "Balance Sheet: Total stockholders' equity $201,753 million.",
                "sec_filing_ref": "Form 10-K, Part II, Item 8, Page 45"
            },
            {
                "metric_name": "Operating Cash Flow",
                "extracted_value": 84946.0,
                "unit": "USD Millions",
                "confidence_score": 0.97,
                "source_evidence": "Cash Flows: Net cash from operating activities $84,946 million.",
                "sec_filing_ref": "Form 10-K, Part II, Item 8, Page 47"
            },
            {
                "metric_name": "Gross Profit",
                "extracted_value": 270254.0,
                "unit": "USD Millions",
                "confidence_score": 0.95,
                "source_evidence": "Total revenue less cost of sales was $270,254 million.",
                "sec_filing_ref": "Form 10-K, Part II, Item 8, Page 43"
            },
            {
                "metric_name": "Operating Income",
                "extracted_value": 36852.0,
                "unit": "USD Millions",
                "confidence_score": 0.97,
                "source_evidence": "Operating income $36,852 million.",
                "sec_filing_ref": "Form 10-K, Part II, Item 8, Page 43"
            },
            {
                "metric_name": "Cash and Cash Equivalents",
                "extracted_value": 73890.0,
                "unit": "USD Millions",
                "confidence_score": 0.98,
                "source_evidence": "Consolidated Balance Sheets: Cash, cash equivalents, and restricted cash $73,890 million as of December 31, 2023.",
                "sec_filing_ref": "Form 10-K, Part II, Item 8, Page 45"
            }
        ]
    },
    "GOOGL": {
        "FY2023": [
            {
                "metric_name": "Revenue",
                "extracted_value": 307394.0,
                "unit": "USD Millions",
                "confidence_score": 0.99,
                "source_evidence": "Revenues totaled $307,394 million for 2023.",
                "sec_filing_ref": "Form 10-K, Item 8, Page 51"
            },
            {
                "metric_name": "Net Income",
                "extracted_value": 73795.0,
                "unit": "USD Millions",
                "confidence_score": 0.98,
                "source_evidence": "Net income was $73,795 million.",
                "sec_filing_ref": "Form 10-K, Item 8, Page 51"
            },
            {
                "metric_name": "Total Assets",
                "extracted_value": 402392.0,
                "unit": "USD Millions",
                "confidence_score": 0.97,
                "source_evidence": "Total assets stood at $402,392 million.",
                "sec_filing_ref": "Form 10-K, Item 8, Page 53"
            },
            {
                "metric_name": "Total Liabilities",
                "extracted_value": 119041.0,
                "unit": "USD Millions",
                "confidence_score": 0.97,
                "source_evidence": "Total liabilities were $119,041 million.",
                "sec_filing_ref": "Form 10-K, Item 8, Page 53"
            },
            {
                "metric_name": "Shareholders' Equity",
                "extracted_value": 283351.0,
                "unit": "USD Millions",
                "confidence_score": 0.98,
                "source_evidence": "Total stockholders' equity was $283,351 million.",
                "sec_filing_ref": "Form 10-K, Item 8, Page 53"
            },
            {
                "metric_name": "Operating Cash Flow",
                "extracted_value": 101746.0,
                "unit": "USD Millions",
                "confidence_score": 0.96,
                "source_evidence": "Net cash provided by operating activities was $101,746 million.",
                "sec_filing_ref": "Form 10-K, Item 8, Page 55"
            },
            {
                "metric_name": "Gross Profit",
                "extracted_value": 174062.0,
                "unit": "USD Millions",
                "confidence_score": 0.98,
                "source_evidence": "Revenues less cost of revenues was $174,062 million.",
                "sec_filing_ref": "Form 10-K, Item 8, Page 51"
            },
            {
                "metric_name": "Operating Income",
                "extracted_value": 84293.0,
                "unit": "USD Millions",
                "confidence_score": 0.98,
                "source_evidence": "Income from operations was $84,293 million.",
                "sec_filing_ref": "Form 10-K, Item 8, Page 51"
            },
            {
                "metric_name": "Cash and Cash Equivalents",
                "extracted_value": 24048.0,
                "unit": "USD Millions",
                "confidence_score": 0.98,
                "source_evidence": "Consolidated Balance Sheets: Cash and cash equivalents $24,048 million as of December 31, 2023.",
                "sec_filing_ref": "Form 10-K, Item 8, Page 53"
            }
        ]
    },
    "NVDA": {
        "FY2023": [
            {
                "metric_name": "Revenue",
                "extracted_value": 26974.0,
                "unit": "USD Millions",
                "confidence_score": 0.99,
                "source_evidence": "Consolidated Statements of Income: Revenue was $26,974 million for fiscal year 2023.",
                "sec_filing_ref": "Form 10-K, Item 8, Page 47"
            },
            {
                "metric_name": "Net Income",
                "extracted_value": 4368.0,
                "unit": "USD Millions",
                "confidence_score": 0.98,
                "source_evidence": "Consolidated Statements of Income: Net income was $4,368 million.",
                "sec_filing_ref": "Form 10-K, Item 8, Page 47"
            },
            {
                "metric_name": "Total Assets",
                # INTENTIONAL MISTAKE / OCR DISCREPANCY FOR HUMAN ESCALATION DEMO:
                # Extracted as 45,182 instead of 41,182 (discrepancy of $4,000M against Liabilities + Equity)
                "extracted_value": 45182.0,
                "unit": "USD Millions",
                "confidence_score": 0.62,
                "source_evidence": "Consolidated Balance Sheets: Total assets recorded as [OCR Discrepancy] $45,182 million (violates Liabilities + Equity = $41,182 million).",
                "sec_filing_ref": "Form 10-K, Item 8, Page 49"
            },
            {
                "metric_name": "Total Liabilities",
                "extracted_value": 19081.0,
                "unit": "USD Millions",
                "confidence_score": 0.98,
                "source_evidence": "Consolidated Balance Sheets: Total liabilities recorded at $19,081 million.",
                "sec_filing_ref": "Form 10-K, Item 8, Page 49"
            },
            {
                "metric_name": "Shareholders' Equity",
                "extracted_value": 22101.0,
                "unit": "USD Millions",
                "confidence_score": 0.98,
                "source_evidence": "Consolidated Balance Sheets: Total shareholders' equity recorded at $22,101 million.",
                "sec_filing_ref": "Form 10-K, Item 8, Page 49"
            },
            {
                "metric_name": "Operating Cash Flow",
                "extracted_value": 5641.0,
                "unit": "USD Millions",
                "confidence_score": 0.98,
                "source_evidence": "Consolidated Statements of Cash Flows: Net cash from operating activities was $5,641 million.",
                "sec_filing_ref": "Form 10-K, Item 8, Page 51"
            },
            {
                "metric_name": "Gross Profit",
                "extracted_value": 15356.0,
                "unit": "USD Millions",
                "confidence_score": 0.97,
                "source_evidence": "Gross profit was $15,356 million for fiscal year 2023.",
                "sec_filing_ref": "Form 10-K, Item 8, Page 47"
            },
            {
                "metric_name": "Operating Income",
                "extracted_value": 4224.0,
                "unit": "USD Millions",
                "confidence_score": 0.98,
                "source_evidence": "Operating income was $4,224 million for fiscal year 2023.",
                "sec_filing_ref": "Form 10-K, Item 8, Page 47"
            },
            {
                "metric_name": "Cash and Cash Equivalents",
                "extracted_value": 3389.0,
                "unit": "USD Millions",
                "confidence_score": 0.98,
                "source_evidence": "Consolidated Balance Sheets: Cash and cash equivalents $3,389 million as of January 29, 2023.",
                "sec_filing_ref": "Form 10-K, Item 8, Page 49"
            }
        ],
        "FY2024": [
            {
                "metric_name": "Revenue",
                "extracted_value": 60922.0,
                "unit": "USD Millions",
                "confidence_score": 0.99,
                "source_evidence": "Revenue surged to $60,922 million, up 126% YoY.",
                "sec_filing_ref": "Form 10-K, Item 8, Page 47"
            },
            {
                "metric_name": "Net Income",
                # SIMULATED ANOMALY / OCR DISCREPANCY FOR HUMAN ESCALATION DEMO:
                # Extracted as 39,760 instead of 29,760, with low confidence score (0.64)
                "extracted_value": 39760.0,
                "unit": "USD Millions",
                "confidence_score": 0.64,
                "source_evidence": "Consolidated Statements of Income: Net income reported as [OCR Blur] $39,760 million (potential typo with 29,760).",
                "sec_filing_ref": "Form 10-K, Item 8, Page 47"
            },
            {
                "metric_name": "Total Assets",
                "extracted_value": 65728.0,
                "unit": "USD Millions",
                "confidence_score": 0.97,
                "source_evidence": "Total assets stood at $65,728 million.",
                "sec_filing_ref": "Form 10-K, Item 8, Page 49"
            },
            {
                "metric_name": "Total Liabilities",
                "extracted_value": 22750.0,
                "unit": "USD Millions",
                "confidence_score": 0.96,
                "source_evidence": "Total liabilities were $22,750 million.",
                "sec_filing_ref": "Form 10-K, Item 8, Page 49"
            },
            {
                "metric_name": "Shareholders' Equity",
                "extracted_value": 42978.0,
                "unit": "USD Millions",
                "confidence_score": 0.96,
                "source_evidence": "Total shareholders' equity $42,978 million.",
                "sec_filing_ref": "Form 10-K, Item 8, Page 49"
            },
            {
                "metric_name": "Operating Cash Flow",
                "extracted_value": 28090.0,
                "unit": "USD Millions",
                "confidence_score": 0.98,
                "source_evidence": "Cash flows from operating activities $28,090 million.",
                "sec_filing_ref": "Form 10-K, Item 8, Page 51"
            },
            {
                "metric_name": "Gross Profit",
                "extracted_value": 44301.0,
                "unit": "USD Millions",
                "confidence_score": 0.97,
                "source_evidence": "Gross profit $44,301 million (72.7% margin).",
                "sec_filing_ref": "Form 10-K, Item 8, Page 47"
            },
            {
                "metric_name": "Operating Income",
                "extracted_value": 32972.0,
                "unit": "USD Millions",
                "confidence_score": 0.98,
                "source_evidence": "Operating income was $32,972 million.",
                "sec_filing_ref": "Form 10-K, Item 8, Page 47"
            },
            {
                "metric_name": "Cash and Cash Equivalents",
                "extracted_value": 7280.0,
                "unit": "USD Millions",
                "confidence_score": 0.98,
                "source_evidence": "Consolidated Balance Sheets: Cash, cash equivalents and marketable securities $7,280 million as of January 28, 2024.",
                "sec_filing_ref": "Form 10-K, Item 8, Page 49"
            }
        ]
    }
}

