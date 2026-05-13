from __future__ import annotations

import google.auth
import google.auth.transport.requests
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import EXA_API_KEY, VERTEX_ENDPOINT

_CREDS = None


def _get_creds():
    global _CREDS
    if _CREDS is None:
        _CREDS, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
    return _CREDS


def get_access_token() -> str:
    creds = _get_creds()
    request = google.auth.transport.requests.Request()
    creds.refresh(request)
    return creds.token


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def call_gemini_with_exa(prompt: str, num_results: int = 10) -> dict:
    token = get_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "tools": [
            {
                "exaAiSearch": {
                    "api_key": EXA_API_KEY,
                    "customConfigs": {
                        "numResults": num_results,
                        "contents": {
                            "highlights": {"maxCharacters": 1200}
                        },
                    },
                }
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 4096,
        },
    }
    resp = requests.post(VERTEX_ENDPOINT, headers=headers, json=body, timeout=120)
    resp.raise_for_status()
    return resp.json()


def extract_text(response: dict) -> str:
    try:
        parts = response["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts)
    except (KeyError, IndexError):
        return ""


def extract_sources(response: dict) -> list[dict]:
    try:
        chunks = (
            response["candidates"][0]
            .get("groundingMetadata", {})
            .get("groundingChunks", [])
        )
        sources = []
        for chunk in chunks:
            web = chunk.get("web", {})
            url = web.get("uri", "")
            if url:
                sources.append({
                    "url": url,
                    "title": web.get("title", url),
                    "domain": web.get("domain", ""),
                })
        return sources
    except (KeyError, IndexError):
        return []
