from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator


class Finding(BaseModel):
    claim: str
    source_url: str
    source_title: str
    confidence: Literal["low", "medium", "high"]

    @field_validator("source_url")
    @classmethod
    def url_must_be_real(cls, v: str) -> str:
        if not v or v in ("unknown", "N/A", ""):
            raise ValueError("source_url must be a real URL")
        return v


class BuyingCommitteeMember(BaseModel):
    name: str
    role: str
    deal_role: Literal["champion", "economic buyer", "technical evaluator", "blocker", "unknown"]
    email: str | None = None
    email_confidence: Literal["verified", "inferred", "unknown"] = "unknown"
    linkedin_url: str | None = None
    source_url: str
    source_title: str


class CompanySnapshot(BaseModel):
    description: str
    industry: str = ""
    stage: str = ""
    employees: str = ""
    hq: str | None = None
    founded: str | None = None
    total_funding: str | None = None
    last_round: str | None = None
    key_products: list[str] = []
    website: str | None = None


class ChampionProfile(BaseModel):
    name: str
    title: str
    email: str | None = None
    email_confidence: Literal["verified", "inferred", "unknown"] = "unknown"
    linkedin_url: str | None = None
    tenure_months: int | None = None
    career_history: list[str] = []
    prior_tool_exposure: str | None = None
    high_signal_flags: list[str] = []
    recent_activity: list[str] = []
    source_url: str = ""


class SubAgentOutput(BaseModel):
    agent_name: str
    findings: list[Finding] = []
    summary: str = ""
    error: str | None = None
    # Rich structured outputs (replaces __dict__ hack)
    committee_members: list[BuyingCommitteeMember] = []
    champion_profile: ChampionProfile | None = None
    company_snapshot: CompanySnapshot | None = None
    tech_stack: list[str] = []


class AccountBrief(BaseModel):
    company: str
    champion: str
    company_snapshot: CompanySnapshot | None = None
    champion_profile: ChampionProfile | None = None
    executive_summary: str
    why_now: list[Finding]
    hiring_findings: list[Finding] = []
    buying_committee: list[BuyingCommitteeMember]
    tech_stack: list[str] = []
    risk_flags: list[Finding]
    talk_track: list[str]
    outreach_angles: list[str] = []
    generated_at: datetime
    generation_seconds: float
