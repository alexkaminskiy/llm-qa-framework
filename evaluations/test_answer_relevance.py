"""
Answer relevance: does the answer actually address the question asked?
Catches cases where the model retrieves correct chunks but answers tangentially.
"""
import pytest
from deepeval import assert_test
from deepeval.metrics import AnswerRelevancyMetric
from deepeval.test_case import LLMTestCase

pytestmark = pytest.mark.requirement("SYS-REQ-002")

RELEVANCE_THRESHOLD = 0.90


@pytest.mark.parametrize("sample", [
    pytest.param(s, id=s["id"])
    for s in __import__("json").loads(
        (__import__("pathlib").Path(__file__).parent.parent / "datasets" / "gold_standard.json").read_text()
    )
    if "out-of-context" not in s["tags"]
])
def test_answer_relevance(sample: dict, rag_pipeline, judge) -> None:
    result = rag_pipeline.query(sample["input"])

    test_case = LLMTestCase(
        input=sample["input"],
        actual_output=result["answer"],
        retrieval_context=result["retrieved_chunks"],
    )

    metric = AnswerRelevancyMetric(
        threshold=RELEVANCE_THRESHOLD,
        model=judge,
        include_reason=True,
    )

    assert_test(test_case, [metric])