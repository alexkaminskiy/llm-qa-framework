from __future__ import annotations

import os

from deepeval.models.base_model import DeepEvalBaseLLM
from langchain_groq import ChatGroq


class GroqJudge(DeepEvalBaseLLM):
    """DeepEval-compatible judge backed by Groq's free tier."""

    def __init__(self, llm: ChatGroq) -> None:
        self._client = llm

    def load_model(self):
        return self._client

    def generate(self, prompt: str) -> str:
        response = self._client.invoke(prompt)
        return response.content

    async def a_generate(self, prompt: str) -> str:
        response = await self._client.ainvoke(prompt)
        return response.content

    def get_model_name(self) -> str:
        return "groq/llama-3.3-70b-versatile"


def build_groq_llm() -> ChatGroq:
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.0,
    )