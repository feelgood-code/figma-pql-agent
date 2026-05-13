from __future__ import annotations

import asyncio

from src.agents.base import load_prompt, parse_rich_json
from src.exa_client import format_sources_for_prompt, multi_search
from src.gemini_client import call_gemini
from src.models import ChampionProfile, Finding, SubAgentOutput

AGENT_NAME = "champion_intel"


def _parse_profile(data: dict, sources: list[dict]) -> ChampionProfile | None:
    p = data.get("profile", {})
    if not p or not p.get("name"):
        return None

    # Resolve source_index for the profile's primary source
    idx = p.get("source_index", -1)
    source_url = ""
    if isinstance(idx, int) and 0 <= idx < len(sources):
        source_url = sources[idx].get("url", "")

    email = p.get("email") or None
    if email and "@" not in email:
        email = None

    linkedin = p.get("linkedin_url") or None
    if linkedin and "linkedin.com" not in linkedin.lower():
        linkedin = None

    try:
        return ChampionProfile(
            name=p.get("name", ""),
            title=p.get("title", ""),
            email=email,
            email_confidence=p.get("email_confidence", "unknown"),
            linkedin_url=linkedin,
            tenure_months=p.get("tenure_months") if isinstance(p.get("tenure_months"), int) else None,
            career_history=p.get("career_history", []),
            prior_tool_exposure=p.get("prior_tool_exposure"),
            high_signal_flags=p.get("high_signal_flags", []),
            recent_activity=p.get("recent_activity", []),
            source_url=source_url,
        )
    except Exception:
        return None


def _parse_signals(data: dict, sources: list[dict]) -> list[Finding]:
    findings = []
    for item in data.get("signals", []):
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
            (f'"{champion}" {company} career role title', None),
            (f'"{champion}" site:linkedin.com OR site:twitter.com OR site:x.com', None),
            (f'"{champion}" Figma design tools conference talk article blog', None),
            (f'"{champion}" interview podcast design product engineering', None),
            (f'"{champion}" {company} announcement hired promoted joined', "news"),
            (f'"{champion}" design systems design ops developer experience', None),
            (f'"{champion}" career history previous company background', None),
            (f'"{champion}" site:github.com OR site:medium.com OR site:substack.com', None),
        ], 6)

        prompt = load_prompt("champion_intel_v2").format(
            company=company,
            champion=champion,
            sources=format_sources_for_prompt(sources),
        )
        text = await asyncio.to_thread(call_gemini, prompt)
        data = parse_rich_json(text)

        profile = _parse_profile(data, sources)
        signals = _parse_signals(data, sources)

        if status_queue:
            await status_queue.put((AGENT_NAME, "done"))
        return SubAgentOutput(
            agent_name=AGENT_NAME,
            findings=signals,
            summary=f"Profile: {profile.title if profile else 'not found'}",
            champion_profile=profile,
        )
    except Exception as e:
        if status_queue:
            await status_queue.put((AGENT_NAME, "error"))
        return SubAgentOutput(agent_name=AGENT_NAME, error=str(e))
