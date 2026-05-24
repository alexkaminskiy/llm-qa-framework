from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Generator

import pytest
from deepeval.models.base_model import DeepEvalBaseLLM
from dotenv import load_dotenv

# Add project root to sys.path so rag_pipeline can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag_pipeline.pipeline import RAGPipeline
from langchain_groq import ChatGroq
from evaluations.judge import GroqJudge, build_groq_llm

load_dotenv()

# Prefer Groq judge when API key is available; otherwise use a deterministic
# offline DummyJudge to allow tests to run in air-gapped or CI-less environments.
_GROQ_API_KEY = os.getenv("GROQ_API_KEY")
_HAS_GROQ = False

if _GROQ_API_KEY:
    _HAS_GROQ = True
else:
    _HAS_GROQ = False

GOLD_STANDARD_PATH = Path(__file__).parent.parent / "datasets" / "gold_standard.json"


# ---------------------------------------------------------------------------
# Custom Groq judge — teaches DeepEval to use Groq instead of OpenAI
# ---------------------------------------------------------------------------
# if _HAS_GROQ:
    # class GroqJudge(DeepEvalBaseLLM):
    #     """Wraps Groq's LLM as the evaluation judge for DeepEval metrics."""

    #     def __init__(self) -> None:
    #         self._client = ChatGroq(
    #             model="llama-3.3-70b-versatile",
    #             api_key=_GROQ_API_KEY,
    #             temperature=0.0,
    #         )

    #     def load_model(self):
    #         return self._client

    #     def generate(self, prompt: str) -> str:
    #         response = self._client.invoke(prompt)
    #         return response.content

    #     async def a_generate(self, prompt: str) -> str:
    #         response = await self._client.ainvoke(prompt)
    #         return response.content

    #     def get_model_name(self) -> str:
    #         return "groq/llama-3.3-70b-versatile"
# else:
#     class DummyJudge(DeepEvalBaseLLM):
#         """Deterministic offline judge used when Groq is not available."""

#         def __init__(self) -> None:
#             pass

#         def load_model(self):
#             return None

#         def generate(self, prompt: str) -> str:
#             # Keep replies short and deterministic; DeepEval will still run.
#             return "DUMMY_JUDGE_RESPONSE"

#         async def a_generate(self, prompt: str) -> str:
#             return "DUMMY_JUDGE_RESPONSE"

#         def get_model_name(self) -> str:
#             return "dummy/offline"


# ---------------------------------------------------------------------------
# Session-scoped fixtures — build RAG pipeline once per test run
# ---------------------------------------------------------------------------

# @pytest.fixture(scope="session")
# def groq_llm() -> ChatGroq:
#     llm = build_groq_llm()
#     return llm

@pytest.fixture(scope="session")
def rag_pipeline() -> RAGPipeline:
    return RAGPipeline(rebuild=False)


@pytest.fixture(scope="session")
def judge() -> DeepEvalBaseLLM:
    return GroqJudge(build_groq_llm())



@pytest.fixture(scope="session")
def gold_standard() -> list[dict]:
    with open(GOLD_STANDARD_PATH, encoding="utf-8") as f:
        return json.load(f)