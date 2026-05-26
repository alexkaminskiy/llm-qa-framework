"""
Root conftest — captures requirement markers during the test run and writes
them to reports/traceability.json for downstream TRR generation.
"""
from __future__ import annotations

import json
from pathlib import Path

_TRACEABILITY_PATH = Path("reports/traceability.json")

# Built during collection — maps nodeid → requirement IDs
# item.iter_markers() correctly resolves inherited pytestmark decorators
_node_requirements: dict[str, list[str]] = {}
_results: list[dict] = []


def pytest_collection_finish(session) -> None:
    """Runs after all tests are collected. Builds nodeid → requirements map."""
    for item in session.items:
        _node_requirements[item.nodeid] = [
            str(marker.args[0])
            for marker in item.iter_markers("requirement")
            if marker.args
        ]


def pytest_runtest_logreport(report) -> None:
    if report.when != "call":
        return

    _results.append({
        "test_id": report.nodeid,
        "requirements": _node_requirements.get(report.nodeid, []),
        "outcome": report.outcome,
    })


def pytest_sessionfinish(session, exitstatus) -> None:
    _TRACEABILITY_PATH.parent.mkdir(exist_ok=True)
    with open(_TRACEABILITY_PATH, "w", encoding="utf-8") as f:
        json.dump(_results, f, indent=2)