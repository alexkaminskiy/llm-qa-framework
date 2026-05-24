#!/usr/bin/env python
"""
Captures current evaluation scores and writes baselines/baseline.json.

Usage:
    python scripts/capture_baseline.py

Run this when you want to establish a new reference point — after a
deliberate model upgrade, prompt change, or corpus update that you've
manually verified improves quality.

Never run this to silence a regression. Fix the regression first.
"""
from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
from deepeval.test_case import LLMTestCase

from evaluations.judge import GroqJudge, build_groq_llm
from rag_pipeline import RAGPipeline

load_dotenv()

BASELINE_PATH = Path(__file__).parent.parent / "baselines" / "baseline.json"
GOLD_STANDARD_PATH = Path(__file__).parent.parent / "datasets" / "gold_standard.json"
MODEL_NAME = "llama-3.3-70b-versatile"
PROMPT_VERSION = "v1.0"
DATASET_VERSION = "1.0"


def _get_commit_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "unknown"


def _make_metrics(judge: GroqJudge) -> dict:
    # threshold=0.0 — we want raw scores, not pass/fail assertions
    return {
        "faithfulness": FaithfulnessMetric(threshold=0.0, model=judge, include_reason=False),
        "answer_relevancy": AnswerRelevancyMetric(threshold=0.0, model=judge, include_reason=False),
    }


def main() -> None:
    print("Building RAG pipeline...")
    pipeline = RAGPipeline(rebuild=False)
    judge = GroqJudge(build_groq_llm())
    metrics = _make_metrics(judge)

    with open(GOLD_STANDARD_PATH, encoding="utf-8") as f:
        gold_standard = json.load(f)

    in_context_samples = [s for s in gold_standard if "out-of-context" not in s["tags"]]

    per_sample_scores: dict[str, dict[str, float]] = {}
    scores_by_metric: dict[str, list[float]] = {m: [] for m in metrics}

    print(f"Capturing scores for {len(in_context_samples)} samples × {len(metrics)} metrics...\n")

    for sample in in_context_samples:
        result = pipeline.query(sample["input"])
        test_case = LLMTestCase(
            input=sample["input"],
            actual_output=result["answer"],
            retrieval_context=result["retrieved_chunks"],
        )

        sample_scores: dict[str, float] = {}
        for metric_name, metric in metrics.items():
            metric.measure(test_case)
            score = round(metric.score, 6)
            sample_scores[metric_name] = score
            scores_by_metric[metric_name].append(score)
            print(f"  {sample['id']} | {metric_name:20s} | {score:.4f}")

        per_sample_scores[sample["id"]] = sample_scores

    aggregate = {
        metric_name: {
            "mean": round(statistics.mean(scores), 6),
            "stddev": round(statistics.stdev(scores), 6) if len(scores) > 1 else 0.0,
        }
        for metric_name, scores in scores_by_metric.items()
    }

    baseline = {
        "metadata": {
            "model": MODEL_NAME,
            "prompt_version": PROMPT_VERSION,
            "dataset_version": DATASET_VERSION,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "commit_sha": _get_commit_sha(),
        },
        "scores": per_sample_scores,
        "aggregate": aggregate,
    }

    BASELINE_PATH.parent.mkdir(exist_ok=True)
    with open(BASELINE_PATH, "w", encoding="utf-8") as f:
        json.dump(baseline, f, indent=2)

    print(f"\nBaseline written to {BASELINE_PATH}")
    print("\nAggregate scores:")
    for metric_name, stats in aggregate.items():
        print(f"  {metric_name:20s} mean={stats['mean']:.4f}  stddev={stats['stddev']:.4f}")


if __name__ == "__main__":
    main()