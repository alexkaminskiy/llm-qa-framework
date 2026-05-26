#!/usr/bin/env python
"""
Generates the traceability matrix CSV and TRR markdown from test run results.

Usage:
    python scripts/generate_traceability.py

Reads:
    reports/traceability.json       (written by root conftest.py)
    requirements/system_requirements.json

Writes:
    reports/traceability_matrix.csv
    docs/TRR.md
"""
from __future__ import annotations

import csv
import json
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
TRACEABILITY_JSON = ROOT / "reports" / "traceability.json"
REQUIREMENTS_JSON = ROOT / "requirements" / "system_requirements.json"
MATRIX_CSV = ROOT / "reports" / "traceability_matrix.csv"
TRR_MD = ROOT / "docs" / "TRR.md"
TRR_PDF = ROOT / "docs" / "TRR.pdf"


def load_data() -> tuple[list[dict], dict]:
    with open(TRACEABILITY_JSON, encoding="utf-8") as f:
        results = json.load(f)
    with open(REQUIREMENTS_JSON, encoding="utf-8") as f:
        requirements = json.load(f)
    return results, requirements


def build_matrix(results: list[dict], requirements: dict) -> dict:
    """
    Returns a dict keyed by requirement ID, each containing:
        - requirement metadata
        - list of (test_id, outcome) pairs
        - overall status: PASS | FAIL | NOT TESTED
    """
    req_map: dict[str, dict] = {}

    for req_id, req in requirements.items():
        req_map[req_id] = {
            **req,
            "tests": [],
            "status": "NOT TESTED",
        }

    for result in results:
        for req_id in result["requirements"]:
            if req_id not in req_map:
                continue
            req_map[req_id]["tests"].append({
                "test_id": result["test_id"],
                "outcome": result["outcome"],
            })

    for req_id, entry in req_map.items():
        if not entry["tests"]:
            entry["status"] = "NOT TESTED"
        elif all(t["outcome"] == "passed" for t in entry["tests"]):
            entry["status"] = "PASS"
        else:
            entry["status"] = "FAIL"

    return req_map


def write_csv(matrix: dict) -> None:
    MATRIX_CSV.parent.mkdir(exist_ok=True)
    with open(MATRIX_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Requirement ID", "Title", "Category", "Priority",
            "Test Count", "Passed", "Failed", "Status"
        ])
        for req_id, entry in sorted(matrix.items()):
            passed = sum(1 for t in entry["tests"] if t["outcome"] == "passed")
            failed = len(entry["tests"]) - passed
            writer.writerow([
                req_id,
                entry["title"],
                entry["category"],
                entry["priority"],
                len(entry["tests"]),
                passed,
                failed,
                entry["status"],
            ])
    print(f"Traceability matrix written to {MATRIX_CSV}")


def _get_commit_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "unknown"


def _coverage_summary(matrix: dict) -> tuple[int, int, int, int]:
    total = len(matrix)
    passed = sum(1 for e in matrix.values() if e["status"] == "PASS")
    failed = sum(1 for e in matrix.values() if e["status"] == "FAIL")
    untested = sum(1 for e in matrix.values() if e["status"] == "NOT TESTED")
    return total, passed, failed, untested


def write_trr(matrix: dict) -> None:
    TRR_MD.parent.mkdir(exist_ok=True)
    total, passed, failed, untested = _coverage_summary(matrix)
    coverage_pct = round((passed / total) * 100, 1) if total else 0
    overall = "APPROVED FOR STAGE GATE" if failed == 0 and untested == 0 else "NOT APPROVED — REMEDIATION REQUIRED"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    commit = _get_commit_sha()

    lines = [
        "# Test Readiness Review (TRR)",
        "",
        "---",
        "",
        "## Document Control",
        "",
        f"| Field | Value |",
        f"|---|---|",
        f"| Document ID | TRR-LLM-QA-001 |",
        f"| System | LLM-QA Evaluation Framework — RAG Pipeline |",
        f"| Stage Gate | MVP → Production |",
        f"| Generated | {timestamp} |",
        f"| Commit | `{commit}` |",
        f"| Classification | UNCLASSIFIED |",
        "",
        "---",
        "",
        "## 1. Executive Summary",
        "",
        f"This Test Readiness Review documents the verification and validation "
        f"status of the LLM-QA Evaluation Framework prior to Stage Gate review. "
        f"The system under test is a Retrieval-Augmented Generation (RAG) pipeline "
        f"with automated quality evaluation, data validation, and regression detection.",
        "",
        f"**Overall status: {overall}**",
        "",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Total requirements | {total} |",
        f"| Requirements verified (PASS) | {passed} |",
        f"| Requirements failed | {failed} |",
        f"| Requirements not tested | {untested} |",
        f"| Requirements coverage | {coverage_pct}% |",
        "",
        "---",
        "",
        "## 2. System Under Test",
        "",
        "### 2.1 System Description",
        "",
        "The LLM-QA Framework provides automated validation of a RAG pipeline "
        "designed for defense supply chain intelligence. The system ingests "
        "technical documentation, retrieves relevant context via FAISS vector "
        "search, and generates grounded answers via a large language model.",
        "",
        "### 2.2 Components",
        "",
        "| Component | Technology | Version |",
        "|---|---|---|",
        "| RAG Pipeline | LangChain + FAISS | 0.2.16 + 1.8.0 |",
        "| Embedding Model | all-MiniLM-L6-v2 | sentence-transformers 3.0.1 |",
        "| LLM / Judge | Groq llama-3.3-70b-versatile | API |",
        "| Evaluation Framework | DeepEval | 0.21.73 |",
        "| RAG Metrics | RAGAS | 0.1.21 |",
        "| Data Validation | Great Expectations | 0.18.15 |",
        "| Data Store | SQLite | stdlib |",
        "| Test Runner | pytest | 8.3.2 |",
        "",
        "### 2.3 Test Environment",
        "",
        "| Parameter | Value |",
        "|---|---|",
        "| CI Platform | GitHub Actions — ubuntu-latest |",
        "| Python | 3.11 |",
        "| Execution | Automated on every push to main, PR, and nightly at 06:00 UTC |",
        "",
        "---",
        "",
        "## 3. Requirements Traceability Matrix",
        "",
        "Each row maps a system requirement to its verification tests and current status.",
        "",
        "| Req ID | Title | Priority | Tests | Status |",
        "|---|---|---|---|---|",
    ]

    for req_id, entry in sorted(matrix.items()):
        test_count = len(entry["tests"])
        status_icon = "✅ PASS" if entry["status"] == "PASS" else \
                      "❌ FAIL" if entry["status"] == "FAIL" else \
                      "⚠️ NOT TESTED"
        lines.append(
            f"| {req_id} | {entry['title']} | {entry['priority']} "
            f"| {test_count} | {status_icon} |"
        )

    lines += [
        "",
        "---",
        "",
        "## 4. Detailed Test Results",
        "",
    ]

    for req_id, entry in sorted(matrix.items()):
        lines.append(f"### {req_id} — {entry['title']}")
        lines.append("")
        lines.append(f"**Description:** {entry['description']}")
        lines.append("")
        lines.append(f"**Category:** {entry['category']} | **Priority:** {entry['priority']} | **Status:** {entry['status']}")
        lines.append("")

        if entry["tests"]:
            lines.append("| Test ID | Outcome |")
            lines.append("|---|---|")
            for t in entry["tests"]:
                icon = "✅" if t["outcome"] == "passed" else "❌"
                short_id = t["test_id"].split("::")[-1]
                lines.append(f"| `{short_id}` | {icon} {t['outcome'].upper()} |")
        else:
            lines.append("*No tests mapped to this requirement.*")

        lines.append("")

    lines += [
        "---",
        "",
        "## 5. Confidence Levels",
        "",
        "| Score Range | Label | Action |",
        "|---|---|---|",
        "| ≥ 0.90 | High | Deploy to production |",
        "| 0.75–0.90 | Medium | Deploy with monitoring |",
        "| 0.60–0.75 | Low | Do not deploy, investigate |",
        "| < 0.60 | Failing | Block deployment, escalate |",
        "",
        "Faithfulness and answer relevance thresholds are set at 0.80 and 0.75 "
        "respectively, providing a buffer above the minimum acceptable quality level.",
        "",
        "---",
        "",
        "## 6. Open Issues",
        "",
        "| ID | Description | Severity | Status |",
        "|---|---|---|---|",
        "| OI-001 | RAGAS tests not included in baseline regression harness | Low | Open |",
        "| OI-002 | Gold Standard dataset size (5 samples) below recommended 50+ for pre-production | Medium | Open |",
        "",
        "---",
        "",
        "## 7. Stage Gate Recommendation",
        "",
        f"**Recommendation: {overall}**",
        "",
    ]

    if failed == 0 and untested == 0:
        lines += [
            "All system requirements have been verified through automated testing. "
            "The system demonstrates:",
            "",
            "- AI output quality meeting defined faithfulness and relevance thresholds",
            "- Hallucination prevention verified through out-of-context refusal tests",
            "- Data integrity validated across BOM, supplier, and compliance dimensions",
            "- Vector retrieval accuracy confirmed for all known query types",
            "- Regression baseline established with automated nightly monitoring",
            "",
            "The system is approved to proceed to the next Stage Gate.",
        ]
    else:
        lines += [
            f"**{failed} requirement(s) failed verification.** "
            "The system is not approved to proceed until all FAIL items are resolved.",
            "",
            "Remediation required before re-submission for Stage Gate review.",
        ]

    lines += ["", "---", "", "*Generated automatically by `scripts/generate_traceability.py`*"]

    with open(TRR_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"TRR written to {TRR_MD}")


def generate_pdf() -> None:
    """
    Generates PDF via xhtml2pdf — pure Python, no native system libraries.
    Works on Windows, Linux, and macOS without GTK or LaTeX.
    """
    try:
        import markdown as md_lib
        from xhtml2pdf import pisa
    except ImportError:
        print("PDF skipped. Install: pip install xhtml2pdf markdown")
        return

    with open(TRR_MD, encoding="utf-8") as f:
        md_content = f.read()

    # Convert markdown → HTML with table support
    html_body = md_lib.markdown(
        md_content,
        extensions=["tables", "toc", "fenced_code"],
    )

    # Minimal CSS for readable PDF output
    html_full = f"""<!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
    body {{ font-family: Arial, sans-serif; font-size: 11px;
            margin: 2cm; line-height: 1.5; }}
    h1   {{ font-size: 20px; border-bottom: 2px solid #333; padding-bottom: 6px; }}
    h2   {{ font-size: 15px; border-bottom: 1px solid #aaa; margin-top: 24px; }}
    h3   {{ font-size: 13px; margin-top: 16px; }}
    table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
    th, td {{ border: 1px solid #ccc; padding: 5px 8px; text-align: left; }}
    th   {{ background-color: #f0f0f0; font-weight: bold; }}
    code {{ background: #f5f5f5; padding: 1px 4px; font-size: 10px; }}
    pre  {{ background: #f5f5f5; padding: 8px; font-size: 10px; }}
    hr   {{ border: none; border-top: 1px solid #ccc; margin: 16px 0; }}
    </style>
    </head>
    <body>{html_body}</body>
    </html>"""

    with open(TRR_PDF, "wb") as f:
        status = pisa.CreatePDF(html_full, dest=f)

    if status.err:
        print(f"PDF generation failed with {status.err} error(s)")
    else:
        print(f"TRR PDF written to {TRR_PDF}")


def main() -> None:
    if not TRACEABILITY_JSON.exists():
        print(f"ERROR: {TRACEABILITY_JSON} not found. Run pytest first.")
        raise SystemExit(1)

    results, requirements = load_data()
    matrix = build_matrix(results, requirements)
    write_csv(matrix)
    write_trr(matrix)
    generate_pdf()

    total, passed, failed, untested = _coverage_summary(matrix)
    print(f"\nCoverage: {passed}/{total} requirements verified ({round(passed/total*100)}%)")
    if failed:
        print(f"FAILED: {failed} requirement(s) — see {TRR_MD}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()