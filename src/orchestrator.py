from __future__ import annotations

import asyncio

from src.agents import (
    buying_committee,
    champion_intel,
    company_intel,
    competitive_signals,
    hiring_growth,
    pain_point_mining,
)
from src.models import SubAgentOutput


async def run_all_agents(
    company: str,
    champion: str,
    status_queue: asyncio.Queue | None = None,
) -> list[SubAgentOutput]:
    results = await asyncio.gather(
        company_intel.run(company, champion, status_queue),
        champion_intel.run(company, champion, status_queue),
        buying_committee.run(company, champion, status_queue),
        competitive_signals.run(company, champion, status_queue),
        hiring_growth.run(company, champion, status_queue),
        pain_point_mining.run(company, champion, status_queue),
        return_exceptions=True,
    )

    outputs = []
    for r in results:
        if isinstance(r, Exception):
            outputs.append(
                SubAgentOutput(
                    agent_name="unknown",
                    findings=[],
                    summary="",
                    error=str(r),
                )
            )
        else:
            outputs.append(r)
    return outputs
