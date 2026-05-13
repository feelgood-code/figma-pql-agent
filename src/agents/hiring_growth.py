from __future__ import annotations

import asyncio

from src.agents.base import load_prompt, parse_rich_json
from src.exa_client import format_sources_for_prompt, multi_search
from src.gemini_client import call_gemini
from src.models import Finding, SubAgentOutput

AGENT_NAME = "hiring_growth"


def _parse_findings(data: dict, sources: list[dict]) -> list[Finding]:
    findings: list[Finding] = []
    for item in data.get("findings", []):
        if not isinstance(item, dict):
            continue
        idx = item.get("source_index", -1)
        if not (isinstance(idx, int) and 0 <= idx < len(sources)):
            continue
        src = sources[idx]
        url = src.get("url", "")
        if not url:
            continue
        confidence = item.get("confidence", "medium")
        if confidence not in ("low", "medium", "high"):
            confidence = "medium"
        try:
            findings.append(Finding(
                claim=item.get("claim", ""),
                source_url=url,
                source_title=src.get("title") or url,
                confidence=confidence,
            ))
        except Exception:
            continue
    return findings


async def run(company: str, champion: str, status_queue: asyncio.Queue | None) -> SubAgentOutput:
    if status_queue:
        await status_queue.put((AGENT_NAME, "searching"))
    try:
        sources = await asyncio.to_thread(multi_search, [
            (f"{company} open jobs design product roles 2025 2026", None),
            (f"{company} hiring senior designer UX design systems", None),
            (f"{company} headcount employees growth 2024 2025", "company"),
            (f"{company} expansion new product market launch 2025 2026", "news"),
            (f"{company} layoffs hiring freeze reduction workforce", "news"),
            (f"{company} design operations design systems team building", None),
        ], 6)

        prompt = load_prompt("hiring_growth_v2").format(
            company=company,
            sources=format_sources_for_prompt(sources),
        )
        text = await asyncio.to_thread(call_gemini, prompt)
        data = parse_rich_json(text)
        findings = _parse_findings(data, sources)

        if status_queue:
            await status_queue.put((AGENT_NAME, "done"))
        return SubAgentOutput(
            agent_name=AGENT_NAME,
            findings=findings,
            summary=f"{len(findings)} growth signals found.",
        )
    except Exception as e:
        if status_queue:
            await status_queue.put((AGENT_NAME, "error"))
        return SubAgentOutput(agent_name=AGENT_NAME, error=str(e))
