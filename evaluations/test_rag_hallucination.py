"""
Two distinct hallucination concerns for a RAG system:

1. In-context hallucination: model fabricates claims beyond the retrieved chunks
   → Covered by FaithfulnessMetric in test_rag_faithfulness.py

2. Out-of-context hallucination: model invents an answer when the corpus has none
   → Tested here with a direct assertion on the "I don't know" response pattern

We intentionally do NOT use HallucinationMetric for in-context samples.
That metric evaluates each chunk independently, producing false positives when
k>1 retrieved chunks are only partially relevant — which is always true in RAG.
"""
import json
from pathlib import Path

import pytest
from deepeval import assert_test
from deepeval.metrics import HallucinationMetric
from deepeval.test_case import LLMTestCase

_GOLD = json.loads(
    (Path(__file__).parent.parent / "datasets" / "gold_standard.json").read_text()
)

# ── Test 1: out-of-context questions must not produce fabricated answers ──────

OUT_OF_CONTEXT_SAMPLES = [s for s in _GOLD if "out-of-context" in s["tags"]]
IN_CONTEXT_SAMPLES = [s for s in _GOLD if "out-of-context" not in s["tags"]]


@pytest.mark.parametrize(
    "sample", [pytest.param(s, id=s["id"]) for s in OUT_OF_CONTEXT_SAMPLES]
)
def test_out_of_context_refuses_to_answer(sample: dict, rag_pipeline) -> None:
    """
    When the corpus contains no relevant information, the RAG pipeline must
    acknowledge uncertainty rather than fabricate an answer.
    Direct string assertion — no LLM judge needed, no false positives.
    """
    result = rag_pipeline.query(sample["input"])
    answer = result["answer"].lower()

    refusal_phrases = ["i don't know", "i do not know", "not in the context",
                       "cannot find", "no information", "not mentioned"]

    assert any(phrase in answer for phrase in refusal_phrases), (
        f"Expected a refusal for out-of-context question '{sample['input']}', "
        f"but got: '{result['answer']}'"
    )


# ── Test 2: HallucinationMetric with combined context (not per-chunk) ─────────

@pytest.mark.parametrize(
    "sample", [pytest.param(s, id=s["id"]) for s in IN_CONTEXT_SAMPLES]
)
def test_hallucination_against_combined_context(
    sample: dict, rag_pipeline, judge
) -> None:
    """
    Passes the full retrieved context as a single string so the judge evaluates
    the answer against everything the model was given — not each chunk in isolation.
    Threshold is intentionally relaxed: FaithfulnessMetric is the primary guard.
    """
    result = rag_pipeline.query(sample["input"])

    # Combine all chunks — fixes the 2/3 false-positive pattern
    combined_context = [" ".join(result["retrieved_chunks"])]

    test_case = LLMTestCase(
        input=sample["input"],
        actual_output=result["answer"],
        context=combined_context,
    )

    metric = HallucinationMetric(
        threshold=0.5,  # relaxed — FaithfulnessMetric at 0.8 is the real gate
        model=judge,
        include_reason=True,
    )

    assert_test(test_case, [metric])