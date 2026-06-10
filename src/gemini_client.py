from __future__ import annotations

import openai
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import OPENAI_API_KEY, OPENAI_MODEL

_client: openai.OpenAI | None = None


def _get_client() -> openai.OpenAI:
    global _client
    if _client is None:
        _client = openai.OpenAI(api_key=OPENAI_API_KEY)
    return _client


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def call_gemini(prompt: str, reasoning_effort: str = "medium") -> str:
    response = _get_client().responses.create(
        model=OPENAI_MODEL,
        input=prompt,
        reasoning={"effort": reasoning_effort},
    )
    return response.output_text or ""
