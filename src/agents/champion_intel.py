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
    if isinstance(idx, str):
        try:
            idx = int(idx)
        except (ValueError, TypeError):
            idx = -1
    source_url = ""
    if isinstance(idx, int) and 0 <= idx < len(sources):
        src = sources[idx]
        source_text = (src.get("text", "") + " " + src.get("title", "")).lower()
        name_parts = [part for part in p.get("name", "").lower().split() if len(part) > 2]
        # Only use source URL if person's name actually appears in the source
        if not name_parts or any(part in source_text for part in name_parts):
            source_url = src.get("url", "")

    email = p.get("email") or None
    if email and "@" not in str(email):
        email = None

    email_conf = p.get("email_confidence", "unknown")
    if email_conf not in ("verified", "inferred", "unknown"):
        email_conf = "unknown"

    linkedin = p.get("linkedin_url") or None
    if linkedin and "linkedin.com" not in str(linkedin).lower():
        linkedin = None

    career = p.get("career_history", [])
    if not isinstance(career, list):
        career = []
    career = [str(item) for item in career if item is not None]

    flags = p.get("high_signal_flags", [])
    if not isinstance(flags, list):
        flags = []
    flags = [str(item) for item in flags if item is not None]

    activity = p.get("recent_activity", [])
    if not isinstance(activity, list):
        activity = []
    activity = [str(item) for item in activity if item is not None]

    prior = p.get("prior_tool_exposure")
    if prior is not None and not isinstance(prior, str):
        prior = str(prior) if prior else None

    tenure = p.get("tenure_months")
    if not isinstance(tenure, int):
        if isinstance(tenure, str):
            try:
                tenure = int(tenure)
            except (ValueError, TypeError):
                tenure = None
        else:
            tenure = None

    try:
        return ChampionProfile(
            name=str(p.get("name", "")),
            title=str(p.get("title", "")),
            email=email,
            email_confidence=email_conf,
            linkedin_url=linkedin,
            tenure_months=tenure,
            career_history=career,
            prior_tool_exposure=prior,
            high_signal_flags=flags,
            recent_activity=activity,
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
        text = await asyncio.to_thread(call_gemini, prompt, 8192)
        data = parse_rich_json(text)

        profile = _parse_profile(data, sources)
        signals = _parse_signals(data, sources)

        # Fallback: ensure champion section always renders with at least a name
        if profile is None and champion:
            try:
                profile = ChampionProfile(name=champion, title="")
            except Exception:
                pass

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
