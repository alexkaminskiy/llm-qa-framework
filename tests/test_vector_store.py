"""
Vector store validation — sanity checks on the FAISS index built by RAGPipeline.

These tests validate the embedding layer itself, separate from LLM evaluation:
  - Index integrity (file exists, correct dimensions, expected vector count)
  - Retrieval correctness (known queries return expected documents)
  - Retrieval boundaries (out-of-domain queries return low-similarity results)

Why this matters: a corrupted or stale FAISS index causes silent retrieval
failures — the LLM generates answers from wrong context with no obvious error.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

pytestmark = [
    pytest.mark.requirement("SYS-REQ-009"),
    pytest.mark.requirement("SYS-REQ-010"),
]

FAISS_PATH = Path(__file__).parent.parent / "faiss_store"
EMBED_MODEL = "all-MiniLM-L6-v2"
EXPECTED_DIMENSIONS = 384       # all-MiniLM-L6-v2 output size
MIN_VECTOR_COUNT = 4            # at least one chunk per source document
MAX_VECTOR_COUNT = 50           # sanity upper bound for our small corpus
SIMILARITY_THRESHOLD = 0.5     # minimum score for a relevant result


@pytest.fixture(scope="module")
def vector_store() -> FAISS:
    assert FAISS_PATH.exists(), (
        f"FAISS index not found at {FAISS_PATH}. "
        f"Run: pytest evaluations/ to build it first."
    )
    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    return FAISS.load_local(
        str(FAISS_PATH),
        embeddings,
        allow_dangerous_deserialization=True,
    )


# ---------------------------------------------------------------------------
# Index integrity
# ---------------------------------------------------------------------------

def test_index_files_exist() -> None:
    """Both FAISS index files must exist — missing either means a partial write."""
    assert (FAISS_PATH / "index.faiss").exists(), "index.faiss missing"
    assert (FAISS_PATH / "index.pkl").exists(), "index.pkl (docstore) missing"


def test_index_vector_count(vector_store: FAISS) -> None:
    """Index must contain a reasonable number of vectors for our corpus size."""
    count = vector_store.index.ntotal
    assert MIN_VECTOR_COUNT <= count <= MAX_VECTOR_COUNT, (
        f"Vector count {count} outside expected range "
        f"[{MIN_VECTOR_COUNT}, {MAX_VECTOR_COUNT}]. "
        f"Index may be empty or corrupted."
    )


def test_index_embedding_dimensions(vector_store: FAISS) -> None:
    """
    Index dimensionality must match the embedding model.
    A mismatch (e.g., index built with model A, queries use model B)
    produces nonsense retrieval with no error message — a silent failure.
    """
    dimensions = vector_store.index.d
    assert dimensions == EXPECTED_DIMENSIONS, (
        f"Index has {dimensions}-dimensional vectors, "
        f"expected {EXPECTED_DIMENSIONS} for {EMBED_MODEL}. "
        f"Delete faiss_store/ and rebuild: pytest evaluations/"
    )


# ---------------------------------------------------------------------------
# Retrieval correctness
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("query,expected_source", [
    ("What is the payload of the F-35?", "f35_specs"),
    ("What is a CONOPS document?", "systems_engineering"),
    ("How does RAG reduce hallucination?", "ai_architecture"),
    ("What is the latency SLA for supply chain dashboards?", "supply_chain"),
])
def test_relevant_query_retrieves_correct_source(
    query: str,
    expected_source: str,
    vector_store: FAISS,
) -> None:
    """
    Known queries must retrieve chunks from the expected source document.
    Catches embedding model drift, index corruption, or corpus mismatches.
    """
    docs = vector_store.similarity_search(query, k=1)
    assert docs, f"No documents retrieved for query: '{query}'"

    retrieved_source = docs[0].metadata.get("source", "")
    assert retrieved_source == expected_source, (
        f"Query: '{query}'\n"
        f"Expected source: '{expected_source}'\n"
        f"Retrieved source: '{retrieved_source}'\n"
        f"Content: '{docs[0].page_content[:100]}...'"
    )


def test_out_of_domain_query_low_similarity(vector_store: FAISS) -> None:
    """
    A query completely unrelated to the corpus should return low similarity
    scores — the retriever must not confidently return irrelevant chunks.
    """
    docs_and_scores = vector_store.similarity_search_with_score(
        "best pizza recipe with mozzarella",
        k=1,
    )
    assert docs_and_scores, "No results returned"

    # FAISS returns L2 distance — higher = less similar
    # For cosine-normalized vectors: score > 1.0 indicates low similarity
    _, score = docs_and_scores[0]
    assert score > SIMILARITY_THRESHOLD, (
        f"Out-of-domain query returned unexpectedly high similarity score: {score:.4f}. "
        f"The index may contain unintended content."
    )