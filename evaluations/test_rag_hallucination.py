"""
Out-of-context hallucination guard: when the corpus contains no relevant
information, the pipeline must acknowledge uncertainty rather than fabricate.

Note: in-context hallucination (model claims beyond retrieved chunks) is
covered by FaithfulnessMetric in test_rag_faithfulness.py. Duplicating that
coverage here with HallucinationMetric produces structural false positives
when the model elaborates on topics that are technically correct but more
detailed than the stored chunk — a known limitation of per-claim evaluation
against short context windows.
"""
import json
from pathlib import Path

import pytest

_GOLD = json.loads(
    (Path(__file__).parent.parent / "datasets" / "gold_standard.json").read_text()
)

OUT_OF_CONTEXT_SAMPLES = [s for s in _GOLD if "out-of-context" in s["tags"]]


@pytest.mark.parametrize(
    "sample", [pytest.param(s, id=s["id"]) for s in OUT_OF_CONTEXT_SAMPLES]
)
def test_out_of_context_refuses_to_answer(sample: dict, rag_pipeline) -> None:
    """
    The RAG pipeline must not fabricate answers for questions outside the corpus.
    Uses direct string assertion — no LLM judge, no non-determinism, zero flakiness.
    """
    result = rag_pipeline.query(sample["input"])
    answer = result["answer"].lower()

    refusal_phrases = [
        "i don't know",
        "i do not know",
        "not in the context",
        "cannot find",
        "no information",
        "not mentioned",
    ]

    assert any(phrase in answer for phrase in refusal_phrases), (
        f"Expected refusal for out-of-context question.\n"
        f"Question: {sample['input']}\n"
        f"Got: {result['answer']}"
    )