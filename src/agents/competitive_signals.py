from __future__ import annotations

import asyncio

from src.agents.base import load_prompt, parse_rich_json
from src.exa_client import format_sources_for_prompt, multi_search
from src.gemini_client import call_gemini
from src.models import Finding, SubAgentOutput

AGENT_NAME = "competitive_signals"


def _parse_output(data: dict, sources: list[dict]) -> tuple[list[str], list[Finding]]:
    tech_stack = data.get("tech_stack", [])
    if not isinstance(tech_stack, list):
        tech_stack = []

    risk_signals: list[Finding] = []
    for item in data.get("risk_signals", []):
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
            risk_signals.append(Finding(
                claim=item.get("claim", ""),
                source_url=url,
                source_title=src.get("title") or url,
                confidence=confidence,
            ))
        except Exception:
            continue

    return [t for t in tech_stack if isinstance(t, str)], risk_signals


async def run(company: str, champion: str, status_queue: asyncio.Queue | None) -> SubAgentOutput:
    if status_queue:
        await status_queue.put((AGENT_NAME, "searching"))
    try:
        sources = await asyncio.to_thread(multi_search, [
            (f"{company} jobs design Figma Sketch Adobe Penpot Framer tool requirement", None),
            (f"{company} engineering blog tech stack tools used", None),
            (f"{company} design team tools workflow case study", None),
            (f"{company} software tools stack Linear Notion Jira Figma", "company"),
            (f"{company} design tool evaluation switch competitor", "news"),
            (f'"{champion}" design tools Sketch Adobe preference', "people"),
            (f"{company} careers product designer UX tools", None),
            (f"{company} developer tools integrations API Figma", "company"),
        ], 5)

        prompt = load_prompt("competitive_signals_v2").format(
            company=company,
            champion=champion,
            sources=format_sources_for_prompt(sources),
        )
        text = await asyncio.to_thread(call_gemini, prompt)
        data = parse_rich_json(text)
        tech_stack, risk_signals = _parse_output(data, sources)

        if status_queue:
            await status_queue.put((AGENT_NAME, "done"))
        return SubAgentOutput(
            agent_name=AGENT_NAME,
            findings=risk_signals,
            summary=f"Tech stack: {', '.join(tech_stack[:4])}",
            tech_stack=tech_stack,
        )
    except Exception as e:
        if status_queue:
            await status_queue.put((AGENT_NAME, "error"))
        return SubAgentOutput(agent_name=AGENT_NAME, error=str(e))
