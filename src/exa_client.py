from __future__ import annotations

from exa_py import Exa
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import EXA_API_KEY

_exa: Exa | None = None


def _get_exa() -> Exa:
    global _exa
    if _exa is None:
        _exa = Exa(api_key=EXA_API_KEY)
    return _exa


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
def search(query: str, num_results: int = 8, category: str | None = None) -> list[dict]:
    kwargs: dict = {"num_results": num_results, "text": {"max_characters": 3000}}
    if category:
        kwargs["category"] = category
    try:
        results = _get_exa().search_and_contents(query, **kwargs)
        out = []
        for r in results.results:
            if r.url:
                out.append({"url": r.url, "title": r.title or r.url, "text": (r.text or "")[:3000]})
        return out
    except Exception as e:
        msg = str(e)
        if "402" in msg or "credits" in msg.lower():
            raise RuntimeError(f"Exa credits exhausted — top up at dashboard.exa.ai. ({msg})") from e
        return []


def multi_search(queries: list[tuple[str, str | None]], num_results: int = 6) -> list[dict]:
    seen: set[str] = set()
    all_results: list[dict] = []
    for query, category in queries:
        for r in search(query, num_results=num_results, category=category):
            if r["url"] not in seen:
                seen.add(r["url"])
                all_results.append(r)
    return all_results


def format_sources_for_prompt(sources: list[dict]) -> str:
    lines = []
    for i, s in enumerate(sources):
        lines.append(f"[{i}] {s['title']}\nURL: {s['url']}\n{s['text']}\n")
    return "\n".join(lines)
