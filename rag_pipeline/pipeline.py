from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()

DOCUMENTS = [
    Document(
        page_content=(
            "The F-35 Lightning II is a family of single-seat, single-engine, "
            "all-weather stealth multirole combat aircraft. The F-35A variant has "
            "a maximum internal payload of 5,700 lbs and can carry up to 18,000 lbs "
            "including external hardpoints. Its combat radius is approximately 669 nm."
        ),
        metadata={"source": "f35_specs", "doc_id": "DOC-001"},
    ),
    Document(
        page_content=(
            "CONOPS (Concept of Operations) is a document describing the "
            "characteristics of a proposed system from the viewpoint of the "
            "individual who will use that system. In defense procurement, a CONOPS "
            "must be approved before formal system requirements are baselined."
        ),
        metadata={"source": "systems_engineering", "doc_id": "DOC-002"},
    ),
    Document(
        page_content=(
            "Retrieval-Augmented Generation (RAG) combines a retrieval mechanism "
            "with a generative model. The retrieval step fetches relevant document "
            "chunks from a vector database. The generation step produces an answer "
            "grounded in those chunks. RAG reduces hallucination by anchoring "
            "outputs to a trusted document corpus."
        ),
        metadata={"source": "ai_architecture", "doc_id": "DOC-003"},
    ),
    Document(
        page_content=(
            "Supply chain risk scoring models evaluate supplier reliability using "
            "financial health indicators, delivery performance history, and "
            "geopolitical exposure scores. Latency SLA for real-time dashboard "
            "updates is typically under 500ms at p95."
        ),
        metadata={"source": "supply_chain", "doc_id": "DOC-004"},
    ),
]

_FAISS_PATH = Path(__file__).parent.parent / "faiss_store"
_EMBED_MODEL = "all-MiniLM-L6-v2"


def _get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name=_EMBED_MODEL)


def _build_vectorstore() -> FAISS:
    embeddings = _get_embeddings()
    splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=50)
    chunks = splitter.split_documents(DOCUMENTS)
    store = FAISS.from_documents(chunks, embeddings)
    store.save_local(str(_FAISS_PATH))
    return store


def _load_vectorstore() -> FAISS:
    return FAISS.load_local(
        str(_FAISS_PATH),
        _get_embeddings(),
        allow_dangerous_deserialization=True,  # safe: we wrote this index ourselves
    )


class RAGPipeline:
    """Minimal RAG pipeline. This is the system under test."""
    
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    
    def __init__(self, rebuild: bool = False) -> None:
        needs_build = rebuild or not _FAISS_PATH.exists()
        self._store = _build_vectorstore() if needs_build else _load_vectorstore()

        self._llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=self.GROQ_API_KEY,
            temperature=0.0,
        )

    def query(self, question: str, k: int = 3) -> dict:
        """
        Returns:
            {
                "answer": str,
                "retrieved_chunks": list[str],
                "source_ids": list[str],
            }
        """
        docs = self._store.similarity_search(question, k=k)
        context = "\n\n".join(d.page_content for d in docs)

        prompt = (
            f"Answer the question using ONLY the context below. "
            f"If the answer is not in the context, say 'I don't know'.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}"
        )

        response = self._llm.invoke(prompt)

        return {
            "answer": response.content,
            "retrieved_chunks": [d.page_content for d in docs],
            "source_ids": [d.metadata.get("doc_id", "") for d in docs],
        }