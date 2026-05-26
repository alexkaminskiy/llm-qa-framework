"""
Faithfulness: does the answer stay within the retrieved context?
A faithful answer makes no claims beyond what the retrieved chunks support.
"""
import pytest
from deepeval import assert_test
from deepeval.metrics import FaithfulnessMetric
from deepeval.test_case import LLMTestCase

pytestmark = pytest.mark.requirement("SYS-REQ-001")


FAITHFULNESS_THRESHOLD = 0.80


@pytest.mark.parametrize("sample", [
    pytest.param(s, id=s["id"])
    for s in __import__("json").loads(
        (__import__("pathlib").Path(__file__).parent.parent / "datasets" / "gold_standard.json").read_text()
    )
    if "out-of-context" not in s["tags"]  # exclude hallucination traps from faithfulness
])
def test_faithfulness(sample: dict, rag_pipeline, judge) -> None:
    result = rag_pipeline.query(sample["input"])

    test_case = LLMTestCase(
        input=sample["input"],
        actual_output=result["answer"],
        retrieval_context=result["retrieved_chunks"],
    )

    metric = FaithfulnessMetric(
        threshold=FAITHFULNESS_THRESHOLD,
        model=judge,
        include_reason=True,
    )

    assert_test(test_case, [metric])
