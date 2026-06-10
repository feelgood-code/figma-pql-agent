from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone

from src.agents.base import load_prompt
from src.gemini_client import call_gemini
from src.models import (
    AccountBrief,
    BuyingCommitteeMember,
    ChampionProfile,
    CompanySnapshot,
    Finding,
    PainPointQuote,
    SubAgentOutput,
)


def _parse_json(text: str) -> dict:
    text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`")
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {}


def _agent(outputs: list[SubAgentOutput], name: str) -> SubAgentOutput | None:
    return next((o for o in outputs if o.agent_name == name), None)


def _build_context(
    company: str,
    champion: str,
    snapshot: CompanySnapshot | None,
    profile: ChampionProfile | None,
    committee: list[BuyingCommitteeMember],
    tech_stack: list[str],
    why_now: list[Finding],
    hiring_findings: list[Finding],
    risk_flags: list[Finding],
) -> str:
    parts: list[str] = []

    if snapshot:
        parts.append(f"COMPANY: {company}")
        parts.append(f"Description: {snapshot.description}")
        if snapshot.industry:
            parts.append(f"Industry: {snapshot.industry}")
        if snapshot.stage:
            parts.append(f"Stage: {snapshot.stage}")
        if snapshot.employees:
            parts.append(f"Employees: {snapshot.employees}")
        if snapshot.hq:
            parts.append(f"HQ: {snapshot.hq}")
        if snapshot.total_funding:
            parts.append(f"Total Funding: {snapshot.total_funding}")
        if snapshot.last_round:
            parts.append(f"Last Round: {snapshot.last_round}")
        if snapshot.key_products:
            parts.append(f"Products: {', '.join(snapshot.key_products)}")
    else:
        parts.append(f"COMPANY: {company}")

    if profile:
        parts.append(f"\nCHAMPION: {profile.name} — {profile.title}")
        if profile.tenure_months:
            parts.append(f"Tenure: {profile.tenure_months} months at {company}")
        if profile.career_history:
            parts.append("Career: " + " → ".join(profile.career_history[:3]))
        if profile.prior_tool_exposure:
            parts.append(f"Prior tool exposure: {profile.prior_tool_exposure}")
        if profile.high_signal_flags:
            parts.append(f"High-signal flags: {', '.join(profile.high_signal_flags)}")
        if profile.recent_activity:
            parts.append("Recent activity: " + "; ".join(profile.recent_activity[:2]))
    else:
        parts.append(f"\nCHAMPION: {champion}")

    if committee:
        parts.append(f"\nBUYING COMMITTEE ({len(committee)} identified):")
        for m in committee[:6]:
            email_note = f" <{m.email}>" if m.email else ""
            parts.append(f"  • {m.name} — {m.role} [{m.deal_role}]{email_note}")

    if tech_stack:
        parts.append(f"\nTECH STACK: {', '.join(tech_stack[:8])}")

    if why_now:
        parts.append("\nWHY NOW SIGNALS:")
        for f in why_now[:5]:
            parts.append(f"  [{f.confidence.upper()}] {f.claim}")

    if hiring_findings:
        parts.append("\nHIRING & GROWTH SIGNALS:")
        for f in hiring_findings[:4]:
            parts.append(f"  [{f.confidence.upper()}] {f.claim}")

    if risk_flags:
        parts.append("\nRISK / COMPETITIVE FLAGS:")
        for f in risk_flags[:3]:
            parts.append(f"  [{f.confidence.upper()}] {f.claim}")

    return "\n".join(parts)


def _sort_findings(findings: list[Finding]) -> list[Finding]:
    order = {"high": 0, "medium": 1, "low": 2}
    return sorted(findings, key=lambda f: order.get(f.confidence, 3))


def _sales_motion(segment: str | None) -> str:
    if not segment:
        return ""
    s = segment.lower()
    if "enterprise" in s:
        return (
            "Strategic AE motion — multi-thread at CPO + Head of Design level. "
            "Find mutual connections between Figma's network and theirs. "
            "Consider Figma exec sponsor or Champions call. Lead with security/SSO story for IT."
        )
    if "mid-market" in s or "mid market" in s:
        return (
            "AE-led, champion-centric — drive through Head of Design or VP Product. "
            "Lead with reference customer at similar stage. ROI case study and trial."
        )
    return (
        "PLG / email outreach — self-serve Figma trial, nurture through design content. "
        "Direct email to founder or design lead. Low-touch, high-velocity motion."
    )


def synthesize(company: str, champion: str, outputs: list[SubAgentOutput], start_time: float) -> AccountBrief:
    # Extract rich structured outputs from each agent
    company_out = _agent(outputs, "company_intel")
    champion_out = _agent(outputs, "champion_intel")
    committee_out = _agent(outputs, "buying_committee")
    competitive_out = _agent(outputs, "competitive_signals")
    hiring_out = _agent(outputs, "hiring_growth")
    pain_out = _agent(outputs, "pain_point_mining")

    snapshot: CompanySnapshot | None = company_out.company_snapshot if company_out else None
    profile: ChampionProfile | None = champion_out.champion_profile if champion_out else None
    committee: list[BuyingCommitteeMember] = committee_out.committee_members if committee_out else []
    tech_stack: list[str] = competitive_out.tech_stack if competitive_out else []
    pain_quotes: list[PainPointQuote] = pain_out.pain_quotes if pain_out else []

    why_now = _sort_findings(company_out.findings if company_out else [])[:5]
    hiring_findings = _sort_findings(hiring_out.findings if hiring_out else [])[:5]
    risk_flags = _sort_findings(competitive_out.findings if competitive_out else [])[:4]

    motion = _sales_motion(snapshot.segment if snapshot else None)

    context = _build_context(
        company, champion, snapshot, profile, committee, tech_stack,
        why_now, hiring_findings, risk_flags,
    )

    prompt = load_prompt("synthesis_v2").format(
        company=company,
        champion=champion,
        context=context,
    )
    text = call_gemini(prompt)
    data = _parse_json(text)
    if not data:
        text = call_gemini(prompt)
        data = _parse_json(text)

    talk_track = data.get("talk_track", [])
    if not isinstance(talk_track, list):
        talk_track = []

    outreach_angles = data.get("outreach_angles", [])
    if not isinstance(outreach_angles, list):
        outreach_angles = []

    return AccountBrief(
        company=company,
        champion=champion,
        company_snapshot=snapshot,
        champion_profile=profile,
        executive_summary=data.get("executive_summary", "Summary unavailable."),
        why_now=why_now,
        hiring_findings=hiring_findings,
        buying_committee=committee[:6],
        tech_stack=tech_stack,
        risk_flags=risk_flags,
        talk_track=[str(t) for t in talk_track[:5] if t],
        outreach_angles=[str(a) for a in outreach_angles[:3] if a],
        pain_quotes=pain_quotes[:5],
        sales_motion=motion,
        generated_at=datetime.now(timezone.utc),
        generation_seconds=round(time.time() - start_time, 1),
    )
