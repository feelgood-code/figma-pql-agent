from __future__ import annotations

import asyncio

from src.agents.base import load_prompt, parse_findings, parse_rich_json
from src.exa_client import format_sources_for_prompt, multi_search
from src.gemini_client import call_gemini
from src.models import CompanySnapshot, SubAgentOutput

AGENT_NAME = "company_intel"


def _parse_snapshot(data: dict) -> CompanySnapshot | None:
    s = data.get("snapshot", {})
    if not s or not s.get("description"):
        return None
    try:
        return CompanySnapshot(
            description=s.get("description", ""),
            industry=s.get("industry", ""),
            stage=s.get("stage", ""),
            employees=s.get("employees", ""),
            hq=s.get("hq"),
            founded=s.get("founded"),
            total_funding=s.get("total_funding"),
            last_round=s.get("last_round"),
            key_products=s.get("key_products", []),
            website=s.get("website"),
        )
    except Exception:
        return None


async def run(company: str, champion: str, status_queue: asyncio.Queue | None) -> SubAgentOutput:
    if status_queue:
        await status_queue.put((AGENT_NAME, "searching"))
    try:
        sources = await asyncio.to_thread(multi_search, [
            (f"{company} funding round valuation 2024 2025 2026", "news"),
            (f"{company} company overview industry employees founded", "company"),
            (f"{company} CEO CPO CTO leadership team executives", "company"),
            (f"{company} product launch announcement strategy 2025 2026", "news"),
            (f"{company} design team product organization growth", "news"),
            (f"{company} customer case study enterprise", None),
            (f"{company} revenue growth ARR headcount", "news"),
            (f"{company} about company mission", "company"),
        ], 5)

        prompt = load_prompt("company_intel_v2").format(
            company=company,
            sources=format_sources_for_prompt(sources),
        )
        text = await asyncio.to_thread(call_gemini, prompt)
        data = parse_rich_json(text)
        snapshot = _parse_snapshot(data)

        # Parse why-now signals from "signals" key
        signals_raw = data.get("signals", [])
        findings = []
        for item in signals_raw:
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
                from src.models import Finding
                findings.append(Finding(
                    claim=item.get("claim", ""),
                    source_url=url,
                    source_title=src.get("title") or url,
                    confidence=confidence,
                ))
            except Exception:
                continue

        if status_queue:
            await status_queue.put((AGENT_NAME, "done"))
        return SubAgentOutput(
            agent_name=AGENT_NAME,
            findings=findings,
            summary=data.get("snapshot", {}).get("description", "")[:300],
            company_snapshot=snapshot,
        )
    except Exception as e:
        if status_queue:
            await status_queue.put((AGENT_NAME, "error"))
        return SubAgentOutput(agent_name=AGENT_NAME, error=str(e))
