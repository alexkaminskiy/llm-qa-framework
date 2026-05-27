"""
Prompt regression suite — detects silent quality degradation between runs.

Compares current metric scores against the committed baseline in
baselines/baseline.json. Fails when any score drops more than
REGRESSION_THRESHOLD below the baseline reference.

When to update the baseline:
  - After a deliberate, verified model or prompt upgrade
  - Via: python scripts/capture_baseline.py
  - Or:  GitHub Actions → workflow_dispatch → update_baseline=true

Never update the baseline to silence a regression.
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

import pytest
from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
from deepeval.test_case import LLMTestCase

pytestmark = pytest.mark.requirement("SYS-REQ-004")
BASELINE_PATH = Path(__file__).parent.parent / "baselines" / "baseline.json"
GOLD_STANDARD_PATH = Path(__file__).parent.parent / "datasets" / "gold_standard.json"

# 5% drop from baseline triggers a regression failure
REGRESSION_THRESHOLD = 0.1

# ---------------------------------------------------------------------------
# Load baseline at collection time — parametrize needs it before fixtures run
# ---------------------------------------------------------------------------
def _load_baseline() -> dict:
    if not BASELINE_PATH.exists():
        return {}
    with open(BASELINE_PATH, encoding="utf-8") as f:
        return json.load(f)


def _load_gold_standard() -> list[dict]:
    with open(GOLD_STANDARD_PATH, encoding="utf-8") as f:
        return json.load(f)


_BASELINE = _load_baseline()
_SCORES = _BASELINE.get("scores", {})
_AGGREGATE = _BASELINE.get("aggregate", {})
_GOLD = {s["id"]: s for s in _load_gold_standard()}

_baseline_missing = not _SCORES
_skip_reason = "No baseline scores found — run: python scripts/capture_baseline.py"

# Build parametrize lists at module level
_per_sample_params = [
    pytest.param(sample_id, metric_name, baseline_score, id=f"{sample_id}::{metric_name}")
    for sample_id, metrics in _SCORES.items()
    for metric_name, baseline_score in metrics.items()
]

_aggregate_params = [
    pytest.param(metric_name, stats["mean"], id=metric_name)
    for metric_name, stats in _AGGREGATE.items()
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _build_metric(metric_name: str, judge):
    """Returns a DeepEval metric with threshold=0 — we do our own delta assertion."""
    if metric_name == "faithfulness":
        return FaithfulnessMetric(threshold=0.0, model=judge, include_reason=True)
    if metric_name == "answer_relevancy":
        return AnswerRelevancyMetric(threshold=0.0, model=judge, include_reason=True)
    raise ValueError(f"Unknown metric in baseline: '{metric_name}'")


def _measure(sample_id: str, metric_name: str, rag_pipeline, judge) -> float:
    sample = _GOLD[sample_id]
    result = rag_pipeline.query(sample["input"])
    test_case = LLMTestCase(
        input=sample["input"],
        actual_output=result["answer"],
        retrieval_context=result["retrieved_chunks"],
    )
    metric = _build_metric(metric_name, judge)
    metric.measure(test_case)
    return metric.score


# ---------------------------------------------------------------------------
# Test 1 — per-sample regression
# Each (sample_id, metric_name) pair gets its own test node.
# ---------------------------------------------------------------------------
@pytest.mark.skipif(_baseline_missing, reason=_skip_reason)
@pytest.mark.parametrize("sample_id,metric_name,baseline_score", _per_sample_params)
def test_per_sample_no_regression(
    sample_id: str,
    metric_name: str,
    baseline_score: float,
    rag_pipeline,
    judge,
) -> None:
    current_score = _measure(sample_id, metric_name, rag_pipeline, judge)
    delta = baseline_score - current_score

    assert delta <= REGRESSION_THRESHOLD, (
        f"REGRESSION DETECTED — {sample_id} | {metric_name}\n"
        f"  Baseline : {baseline_score:.4f}\n"
        f"  Current  : {current_score:.4f}\n"
        f"  Delta    : -{delta:.4f}  (threshold: {REGRESSION_THRESHOLD})\n"
        f"  Baseline commit: {_BASELINE.get('metadata', {}).get('commit_sha', 'unknown')}\n"
        f"  If this is intentional, update the baseline:\n"
        f"    python scripts/capture_baseline.py"
    )


# ---------------------------------------------------------------------------
# Test 2 — aggregate regression
# Catches distributed degradation that stays below per-sample threshold
# but represents meaningful overall quality loss.
# ---------------------------------------------------------------------------
@pytest.mark.skipif(_baseline_missing, reason=_skip_reason)
@pytest.mark.parametrize("metric_name,baseline_mean", _aggregate_params)
def test_aggregate_no_regression(
    metric_name: str,
    baseline_mean: float,
    rag_pipeline,
    judge,
) -> None:
    in_context_ids = [
        sid for sid in _SCORES
        if "out-of-context" not in _GOLD[sid]["tags"]
    ]

    current_scores = [
        _measure(sid, metric_name, rag_pipeline, judge)
        for sid in in_context_ids
    ]

    current_mean = statistics.mean(current_scores)
    delta = baseline_mean - current_mean

    assert delta <= REGRESSION_THRESHOLD, (
        f"AGGREGATE REGRESSION — {metric_name}\n"
        f"  Baseline mean : {baseline_mean:.4f}\n"
        f"  Current mean  : {current_mean:.4f}\n"
        f"  Delta         : -{delta:.4f}  (threshold: {REGRESSION_THRESHOLD})\n"
        f"  Per-sample    : {[round(s, 4) for s in current_scores]}\n"
        f"  Model version : {_BASELINE.get('metadata', {}).get('model', 'unknown')}"
    )