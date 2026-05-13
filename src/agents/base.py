from __future__ import annotations

import json
import re

from src.config import PROMPTS_DIR
from src.models import Finding


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.txt").read_text(encoding="utf-8")


def parse_findings(text: str | None, sources: list[dict]) -> list[Finding]:
    """Extract a findings array from LLM text, mapping source_index → URL."""
    if not text:
        return []
    match = re.search(r"\[[\s\S]*\]", text)
    if not match:
        return []
    try:
        raw = json.loads(match.group())
    except json.JSONDecodeError:
        return []

    findings: list[Finding] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        claim = item.get("claim", "").strip()
        if not claim:
            continue
        idx = item.get("source_index", -1)
        confidence = item.get("confidence", "low")
        if confidence not in ("low", "medium", "high"):
            confidence = "low"
        if not (isinstance(idx, int) and 0 <= idx < len(sources)):
            continue
        src = sources[idx]
        url = src.get("url", "")
        if not url:
            continue
        try:
            findings.append(Finding(
                claim=claim, source_url=url,
                source_title=src.get("title") or url,
                confidence=confidence,
            ))
        except Exception:
            continue
    return findings


def parse_rich_json(text: str | None) -> dict:
    """Extract the outermost JSON object from LLM text, stripping markdown fences."""
    if not text:
        return {}
    text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`")
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return {}
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return {}
