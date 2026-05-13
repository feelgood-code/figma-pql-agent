from __future__ import annotations

import asyncio

from src.agents.base import load_prompt, parse_rich_json
from src.exa_client import format_sources_for_prompt, multi_search
from src.gemini_client import call_gemini
from src.models import BuyingCommitteeMember, SubAgentOutput

AGENT_NAME = "buying_committee"


def _parse_members(data: dict, sources: list[dict]) -> list[BuyingCommitteeMember]:
    members: list[BuyingCommitteeMember] = []
    for item in data.get("members", []):
        if not isinstance(item, dict) or not item.get("name"):
            continue

        idx = item.get("source_index", -1)
        if isinstance(idx, int) and 0 <= idx < len(sources):
            src = sources[idx]
            url = src.get("url", "")
            title = src.get("title") or url
        else:
            url, title = "", ""
        if not url:
            continue

        deal_role = item.get("deal_role", "unknown")
        if deal_role not in ("champion", "economic buyer", "technical evaluator", "blocker", "unknown"):
            deal_role = "unknown"

        email = item.get("email") or None
        if email and "@" not in email:
            email = None
        email_conf = item.get("email_confidence", "unknown")
        if email_conf not in ("verified", "inferred", "unknown"):
            email_conf = "unknown"

        linkedin = item.get("linkedin_url") or None
        if linkedin and "linkedin.com" not in str(linkedin).lower():
            linkedin = None

        try:
            members.append(BuyingCommitteeMember(
                name=item["name"],
                role=item.get("role", ""),
                deal_role=deal_role,
                email=email,
                email_confidence=email_conf if email else "unknown",
                linkedin_url=linkedin,
                source_url=url,
                source_title=title,
            ))
        except Exception:
            continue
    return members


async def run(company: str, champion: str, status_queue: asyncio.Queue | None) -> SubAgentOutput:
    if status_queue:
        await status_queue.put((AGENT_NAME, "searching"))
    try:
        sources = await asyncio.to_thread(multi_search, [
            (f"{company} head of design chief design officer", "people"),
            (f"{company} VP design director design leadership", "people"),
            (f"{company} chief product officer head of product CPO", "people"),
            (f"{company} CTO chief technology officer VP engineering", "people"),
            (f"{company} VP procurement head of IT CISO security", "people"),
            (f"{company} design operations design systems lead", "people"),
            (f"{company} leadership team about executives", "company"),
            (f"{company} team page founders board directors", "company"),
            (f"{company} press release spokesperson contact", None),
            (f"{company} LinkedIn company employees leaders", "people"),
        ], 5)

        prompt = load_prompt("buying_committee_v2").format(
            company=company,
            champion=champion,
            sources=format_sources_for_prompt(sources),
        )
        text = await asyncio.to_thread(call_gemini, prompt)
        data = parse_rich_json(text)
        members = _parse_members(data, sources)

        if status_queue:
            await status_queue.put((AGENT_NAME, "done"))
        return SubAgentOutput(
            agent_name=AGENT_NAME,
            summary=f"Found {len(members)} buying committee members.",
            committee_members=members,
        )
    except Exception as e:
        if status_queue:
            await status_queue.put((AGENT_NAME, "error"))
        return SubAgentOutput(agent_name=AGENT_NAME, error=str(e))
