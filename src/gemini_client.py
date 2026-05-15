from __future__ import annotations

from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import GEMINI_API_KEY, GEMINI_MODEL

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def call_gemini(prompt: str, max_output_tokens: int = 4096) -> str:
    response = _get_client().models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=max_output_tokens,
        ),
    )
    return response.text or ""
