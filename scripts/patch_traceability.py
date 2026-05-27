"""
Rebuilds reports/traceability.json from two existing sources:
  - pytest --collect-only  (markers, no test execution, ~3 seconds)
  - reports/results.xml    (outcomes from the last real test run)

Use this after fixing the conftest marker capture to avoid re-running
expensive LLM evaluation tests just to regenerate traceability data.
"""
from __future__ import annotations

import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
import pytest

ROOT = Path(__file__).parent.parent
RESULTS_XML = ROOT / "reports" / "results.xml"
TRACEABILITY_JSON = ROOT / "reports" / "traceability.json"


def collect_markers() -> dict[str, list[str]]:
    """
    Runs pytest --collect-only to get nodeid → requirements mapping.
    No tests are executed — pure collection, takes ~3 seconds.
    """
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "--no-header"],
        capture_output=True, text=True, cwd=ROOT
    )

    # Use Python's pytest API for reliable marker extraction
    

    class MarkerCollector:
        def __init__(self):
            self.mapping: dict[str, list[str]] = {}

        def pytest_collection_finish(self, session):
            for item in session.items:
                self.mapping[item.nodeid] = [
                    str(marker.args[0])
                    for marker in item.iter_markers("requirement")
                    if marker.args
                ]

    collector = MarkerCollector()
    pytest.main(
        ["--collect-only", "-q", "--no-header",
         "--ignore=scripts", "--ignore=data_validation"],
        plugins=[collector],
    )
    return collector.mapping


def load_outcomes() -> dict[str, str]:
    """Reads test outcomes from the last JUnit XML run."""
    if not RESULTS_XML.exists():
        print(f"WARNING: {RESULTS_XML} not found — all outcomes will be 'unknown'.")
        return {}

    tree = ET.parse(RESULTS_XML)
    outcomes: dict[str, str] = {}

    for testcase in tree.iter("testcase"):
        classname = testcase.get("classname", "")
        name = testcase.get("name", "")

        # Reconstruct nodeid from JUnit classname + name
        # JUnit format: classname=evaluations.test_rag_faithfulness, name=test_faithfulness[GS-001]
        nodeid = classname.replace(".", "/") + ".py::" + name
        # Normalise Windows path separators
        nodeid = nodeid.replace("\\", "/")

        if testcase.find("failure") is not None:
            outcomes[nodeid] = "failed"
        elif testcase.find("error") is not None:
            outcomes[nodeid] = "error"
        elif testcase.find("skipped") is not None:
            outcomes[nodeid] = "skipped"
        else:
            outcomes[nodeid] = "passed"

    return outcomes


def main() -> None:
    print("Collecting markers (no tests executed)...")
    markers = collect_markers()
    print(f"  {len(markers)} test nodes found")

    print("Loading outcomes from last test run...")
    outcomes = load_outcomes()
    print(f"  {len(outcomes)} outcomes loaded from {RESULTS_XML.name}")

    results = []
    matched = 0
    for nodeid, requirements in markers.items():
        # Normalise for matching
        normalised = nodeid.replace("\\", "/")
        outcome = outcomes.get(normalised, "unknown")
        if outcome != "unknown":
            matched += 1
        results.append({
            "test_id": nodeid,
            "requirements": requirements,
            "outcome": outcome,
        })

    TRACEABILITY_JSON.parent.mkdir(exist_ok=True)
    with open(TRACEABILITY_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"  {matched}/{len(results)} tests matched to outcomes")
    print(f"Traceability JSON written to {TRACEABILITY_JSON}")


if __name__ == "__main__":
    main()