from __future__ import annotations

import asyncio

from src.agents.base import load_prompt, parse_rich_json
from src.exa_client import format_sources_for_prompt, multi_search
from src.gemini_client import call_gemini
from src.models import PainPointQuote, SubAgentOutput

AGENT_NAME = "pain_point_mining"


def _parse_quotes(data: dict, sources: list[dict]) -> list[PainPointQuote]:
    quotes = []
    for item in data.get("pain_quotes", []):
        if not isinstance(item, dict):
            continue
        idx = item.get("source_index", -1)
        if not (isinstance(idx, int) and 0 <= idx < len(sources)):
            continue
        src = sources[idx]
        url = src.get("url", "")
        if not url:
            continue
        quote_text = item.get("quote", "").strip()
        if not quote_text:
            continue
        # Verify quote fragment appears in source text (anti-hallucination)
        source_text = (src.get("text", "") + " " + src.get("title", "")).lower()
        quote_words = quote_text.lower().split()
        # Check at least 3 consecutive words from the quote appear in the source
        found = False
        for i in range(len(quote_words) - 2):
            chunk = " ".join(quote_words[i:i + 3])
            if chunk in source_text:
                found = True
                break
        if not found:
            continue
        try:
            quotes.append(PainPointQuote(
                quote=quote_text,
                speaker=item.get("speaker", f"{src.get('title', 'Source')} team"),
                source_url=url,
                source_title=src.get("title") or url,
                figma_capability=item.get("figma_capability", ""),
                ae_opener=item.get("ae_opener", ""),
            ))
        except Exception:
            continue
    return quotes


async def run(company: str, champion: str, status_queue: asyncio.Queue | None) -> SubAgentOutput:
    if status_queue:
        await status_queue.put((AGENT_NAME, "searching"))
    try:
        sources = await asyncio.to_thread(multi_search, [
            (f'"{company}" engineering blog "design system" OR "design process" OR "design workflow"', None),
            (f'"{company}" conference talk design product UX speakerdeck OR youtube', None),
            (f'"{company}" podcast interview design leader "the challenge" OR "the hard part"', None),
            (f'site:github.com "{company}" design figma tooling workflow', None),
            (f'site:news.ycombinator.com "{company}" design OR tooling', None),
            (f'"{company}" "we rebuilt" OR "we switched" OR "the challenge was" design OR tooling', None),
            (f'"{company}" "the problem" OR "pain point" OR "we needed" design OR workflow', None),
            (f'"{champion}" podcast OR interview design challenge OR "the problem" OR "we struggled"', None),
            (f'"{company}" glassdoor review design tool OR workflow', None),
            (f'"{company}" blog "design ops" OR "design systems" challenge OR friction OR problem', None),
        ], 6)

        prompt = load_prompt("pain_point_mining_v1").format(
            company=company,
            champion=champion,
            sources=format_sources_for_prompt(sources),
        )
        text = await asyncio.to_thread(call_gemini, prompt)
        data = parse_rich_json(text)
        quotes = _parse_quotes(data, sources)

        if status_queue:
            await status_queue.put((AGENT_NAME, "done"))
        return SubAgentOutput(
            agent_name=AGENT_NAME,
            pain_quotes=quotes,
            summary=f"{len(quotes)} pain quotes found.",
        )
    except Exception as e:
        if status_queue:
            await status_queue.put((AGENT_NAME, "error"))
        return SubAgentOutput(agent_name=AGENT_NAME, error=str(e))
