from __future__ import annotations

import asyncio
import re
import time

import nest_asyncio
import streamlit as st

nest_asyncio.apply()

from src import cache, orchestrator, synthesis
from src.models import AccountBrief, BuyingCommitteeMember, ChampionProfile, CompanySnapshot, Finding

st.set_page_config(
    page_title="PQL Intelligence Agent — Figma",
    page_icon="🟣",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Figma brand: #A259FF purple, #1E1E1E black, #F24822 red, #1BC47D green ────
STYLE = """
<style>
/* ── Base ── */
[data-testid="stAppViewContainer"] { background: #F8F7FF; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] { display: none; }
.block-container { max-width: 860px !important; padding: 2rem 1.5rem 4rem; }

/* ── Page header ── */
.pql-wordmark {
    font-size: 0.72rem; font-weight: 700; letter-spacing: 0.14em;
    text-transform: uppercase; color: #A259FF; margin-bottom: 2px;
}
.pql-title { font-size: 2rem; font-weight: 700; color: #1E1E1E; line-height: 1.15; margin-bottom: 4px; }
.pql-subtitle { font-size: 0.93rem; color: #6B6B6B; }

/* ── Section divider + label ── */
.section-label {
    font-size: 0.68rem; font-weight: 700; letter-spacing: 0.12em;
    text-transform: uppercase; color: #A259FF;
    margin: 2.2rem 0 0.7rem;
    padding-bottom: 6px; border-bottom: 1px solid #E8E0FF;
}

/* ── Brief header banner ── */
.brief-header {
    background: #1E1E1E; border-radius: 10px; padding: 20px 24px; margin-bottom: 8px;
}
.bh-company { font-size: 1.5rem; font-weight: 700; color: #FFFFFF; }
.bh-champion { font-size: 0.9rem; color: #A0A0A0; margin-top: 2px; }
.bh-meta { font-size: 0.78rem; color: #686868; margin-top: 10px; }
.bh-meta span { color: #A259FF; font-weight: 600; }

/* ── Summary card ── */
.summary-card {
    background: #F0EBFF; border-left: 3px solid #A259FF;
    border-radius: 6px; padding: 16px 20px; margin: 4px 0 8px;
    color: #1E1E1E; font-size: 0.97rem; line-height: 1.65;
}

/* ── Snapshot fact grid ── */
.snap-grid {
    display: grid; grid-template-columns: repeat(2, 1fr);
    gap: 8px; margin: 6px 0;
}
.snap-cell {
    background: #FFFFFF; border: 1px solid #E6E0FF;
    border-radius: 8px; padding: 12px 14px;
}
.snap-label {
    font-size: 0.65rem; font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; color: #A259FF; margin-bottom: 4px;
}
.snap-value { font-size: 0.92rem; color: #1E1E1E; font-weight: 500; line-height: 1.4; }

/* ── Signal cards (Why Now / Hiring) ── */
.signal-card {
    background: #FFFFFF; border: 1px solid #E6E0FF;
    border-radius: 8px; padding: 13px 16px; margin: 6px 0;
}
.signal-num {
    font-size: 0.63rem; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; color: #A259FF; margin-bottom: 5px;
    display: flex; align-items: center; gap: 6px;
}
.signal-text { font-size: 0.93rem; color: #1E1E1E; line-height: 1.55; }
.signal-source { font-size: 0.78rem; margin-top: 7px; }
.signal-source a { color: #A259FF !important; text-decoration: none; }
.signal-source a:hover { text-decoration: underline; }

/* ── Confidence badges ── */
.conf-high   { background:#E3F9EE; color:#0A5E35; font-size:0.68rem; font-weight:700; padding:2px 7px; border-radius:10px; }
.conf-medium { background:#FFF4D9; color:#7A5200; font-size:0.68rem; font-weight:700; padding:2px 7px; border-radius:10px; }
.conf-low    { background:#FFE8E0; color:#922000; font-size:0.68rem; font-weight:700; padding:2px 7px; border-radius:10px; }

/* ── Risk cards ── */
.risk-card {
    background: #FFF2EE; border-left: 3px solid #F24822;
    border-radius: 6px; padding: 13px 16px; margin: 6px 0;
}
.risk-label {
    font-size: 0.63rem; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; color: #F24822; margin-bottom: 5px;
}
.risk-text { font-size: 0.93rem; color: #1E1E1E; line-height: 1.55; }
.risk-source { font-size: 0.78rem; margin-top: 7px; }
.risk-source a { color: #F24822 !important; text-decoration: none; }

/* ── No-signal card ── */
.clean-card {
    background: #EDFBF3; border-left: 3px solid #1BC47D;
    border-radius: 6px; padding: 13px 16px; margin: 6px 0;
    font-size: 0.93rem; color: #1E1E1E;
}

/* ── Champion profile ── */
.champ-grid {
    display: grid; grid-template-columns: repeat(2, 1fr);
    gap: 8px; margin: 6px 0 12px;
}
.champ-cell {
    background: #FFFFFF; border: 1px solid #E6E0FF;
    border-radius: 8px; padding: 12px 14px;
}
.champ-label {
    font-size: 0.65rem; font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; color: #A259FF; margin-bottom: 4px;
}
.champ-value { font-size: 0.9rem; color: #1E1E1E; font-weight: 500; line-height: 1.4; }
.champ-value a { color: #A259FF !important; text-decoration: none; }
.champ-value a:hover { text-decoration: underline; }
.career-item {
    font-size: 0.88rem; color: #1E1E1E; padding: 5px 0;
    border-bottom: 1px solid #F0F0F0;
}
.career-item:last-child { border-bottom: none; }
.flag-chip {
    display: inline-block; background: #FFF4D9; color: #7A5200;
    font-size: 0.75rem; font-weight: 700; padding: 3px 10px;
    border-radius: 12px; margin: 3px 4px 3px 0;
}
.activity-item { font-size: 0.88rem; color: #1E1E1E; padding: 4px 0; }

/* ── Buying committee table ── */
.bc-table { width: 100%; border-collapse: collapse; margin-top: 4px; font-size: 0.88rem; }
.bc-table th {
    font-size: 0.65rem; font-weight: 700; letter-spacing: 0.09em;
    text-transform: uppercase; color: #6B6B6B;
    padding: 8px 10px; border-bottom: 2px solid #E6E0FF; text-align: left;
}
.bc-table td { padding: 11px 10px; border-bottom: 1px solid #F0F0F0; vertical-align: top; color: #1E1E1E; }
.bc-table tr:last-child td { border-bottom: none; }
.bc-name { font-weight: 600; color: #1E1E1E; }
.bc-role { color: #6B6B6B; font-size: 0.82rem; margin-top: 2px; }
.deal-badge { font-size: 0.7rem; font-weight: 700; padding: 3px 9px; border-radius: 10px; white-space: nowrap; }
.deal-champion    { background:#F0EBFF; color:#6B2FD9; }
.deal-economic    { background:#E3F9EE; color:#0A5E35; }
.deal-technical   { background:#E8F0FF; color:#1A4DB0; }
.deal-blocker     { background:#FFE8E0; color:#C23600; }
.deal-unknown     { background:#F5F5F5; color:#6B6B6B; }
.email-chip { font-family: monospace; font-size: 0.78rem; background: #F5F2FF; padding: 2px 7px; border-radius: 4px; color: #1E1E1E; }
.email-verified { color: #0A5E35; font-size: 0.7rem; font-weight: 600; }
.email-inferred { color: #7A5200; font-size: 0.7rem; font-weight: 600; }
.li-link a { color: #0077B5 !important; font-size: 0.8rem; text-decoration: none; }
.li-link a:hover { text-decoration: underline; }

/* ── Tech stack chips ── */
.stack-confirmed { display:inline-block; background:#E3F9EE; color:#0A5E35;
    font-size:0.8rem; font-weight:600; padding:4px 12px; border-radius:14px; margin:4px 4px 4px 0; }
.stack-inferred  { display:inline-block; background:#FFF4D9; color:#7A5200;
    font-size:0.8rem; font-weight:600; padding:4px 12px; border-radius:14px; margin:4px 4px 4px 0; }
.stack-historical{ display:inline-block; background:#F5F5F5; color:#6B6B6B;
    font-size:0.8rem; font-weight:600; padding:4px 12px; border-radius:14px; margin:4px 4px 4px 0; }

/* ── Talk track / outreach ── */
.tt-item {
    background: #FFFFFF; border: 1px solid #E6E0FF; border-radius: 6px;
    padding: 12px 16px; margin: 6px 0; font-size: 0.92rem; color: #1E1E1E; line-height: 1.6;
}
.tt-num { color: #A259FF; font-weight: 700; margin-right: 6px; }
.angle-item {
    background: #F0EBFF; border-radius: 6px;
    padding: 12px 16px; margin: 6px 0; font-size: 0.92rem; color: #1E1E1E; line-height: 1.6;
}
.angle-bullet { color: #A259FF; font-weight: 700; margin-right: 6px; }

/* ── Agent status cards ── */
.agent-grid { display:flex; gap:10px; margin-bottom:16px; }
.agent-card {
    flex:1; background:#FFFFFF; border:1px solid #E6E0FF; border-radius:10px;
    padding:14px 10px; text-align:center;
}
.agent-icon { font-size:1.5rem; line-height:1; }
.agent-name {
    font-size:0.68rem; font-weight:700; letter-spacing:0.06em;
    text-transform:uppercase; color:#6B6B6B; margin:6px 0 4px;
}
.agent-status-waiting  { font-size:0.82rem; color:#A0A0A0; }
.agent-status-running  { font-size:0.82rem; color:#A259FF; font-weight:600; }
.agent-status-done     { font-size:0.82rem; color:#1BC47D; font-weight:600; }
.agent-status-error    { font-size:0.82rem; color:#F24822; font-weight:600; }

/* Hide Streamlit's 'Press Enter to apply / submit form' hint inside inputs */
[data-testid="InputInstructions"] { display: none !important; }

/* ── Buttons (st.button and st.form_submit_button) ── */
.stButton > button, .stFormSubmitButton > button {
    border-radius: 6px; font-weight: 600;
}
.stButton > button[kind="primary"],
.stFormSubmitButton > button {
    background: #A259FF !important; border: none !important; color: #FFFFFF !important;
}
.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button:hover { background: #8A3EE8 !important; }

div[data-testid="stExpander"] { border: 1px solid #E6E0FF; border-radius: 8px; }
div[data-testid="stExpander"] a { color: #A259FF !important; text-decoration: underline; }
div[data-testid="stExpander"] p,
div[data-testid="stExpander"] li { color: #1E1E1E !important; }

/* ── Output preview chips ── */
.output-chip {
    background: #F0EBFF; color: #6B2FD9;
    font-size: 0.78rem; font-weight: 600;
    padding: 4px 11px; border-radius: 14px;
}
</style>
"""
st.markdown(STYLE, unsafe_allow_html=True)


# ── Constants ─────────────────────────────────────────────────────────────────
AGENTS = [
    ("company_intel",       "🏢", "Company"),
    ("champion_intel",      "🧑", "Champion"),
    ("buying_committee",    "👥", "Committee"),
    ("competitive_signals", "⚔️", "Competitive"),
    ("hiring_growth",       "📈", "Growth"),
]

DEAL_ROLE_CLASS = {
    "champion":           "deal-champion",
    "economic buyer":     "deal-economic",
    "technical evaluator":"deal-technical",
    "blocker":            "deal-blocker",
    "unknown":            "deal-unknown",
}
CONF_CLASS = {"high": "conf-high", "medium": "conf-medium", "low": "conf-low"}
CONF_LABEL = {"high": "HIGH", "medium": "MED", "low": "LOW"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _src(url: str, title: str) -> str:
    short = (title[:48] + "…") if len(title) > 48 else title
    return f'<a href="{url}" target="_blank">{short} ↗</a>'


def _categorize_stack(entries: list[str]) -> tuple[list[str], list[str], list[str]]:
    confirmed, inferred, historical = [], [], []
    for entry in entries:
        low = entry.lower()
        if "confirmed" in low:
            confirmed.append(entry)
        elif "historical" in low:
            historical.append(entry)
        else:
            inferred.append(entry)
    return confirmed, inferred, historical


def _tool_name(entry: str) -> str:
    m = re.match(r"^([^(]+)", entry)
    return m.group(1).strip() if m else entry


# ── Section renderers ─────────────────────────────────────────────────────────

def _render_header(brief: AccountBrief) -> None:
    ts = brief.generated_at.strftime("%b %d, %Y · %H:%M UTC")
    st.markdown(
        f"""<div class="brief-header">
            <div class="bh-company">🟣 {brief.company}</div>
            <div class="bh-champion">Champion: {brief.champion}</div>
            <div class="bh-meta">
                Generated {ts} &nbsp;·&nbsp; <span>{brief.generation_seconds}s</span>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )


def _render_summary(brief: AccountBrief) -> None:
    st.markdown('<div class="section-label">Executive Summary</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="summary-card">{brief.executive_summary}</div>', unsafe_allow_html=True)


def _render_snapshot(snap: CompanySnapshot) -> None:
    st.markdown('<div class="section-label">Company Snapshot</div>', unsafe_allow_html=True)

    cells = []
    if snap.description:
        cells.append(("About", snap.description))
    if snap.industry:
        cells.append(("Industry", snap.industry))
    if snap.stage:
        cells.append(("Stage", snap.stage))
    if snap.employees:
        cells.append(("Employees", snap.employees))
    if snap.hq:
        cells.append(("HQ", snap.hq))
    if snap.founded:
        cells.append(("Founded", snap.founded))
    if snap.total_funding:
        cells.append(("Total Funding", snap.total_funding))
    if snap.last_round:
        cells.append(("Last Round", snap.last_round))
    if snap.key_products:
        cells.append(("Key Products", " · ".join(snap.key_products)))
    if snap.website:
        cells.append(("Website", f'<a href="{snap.website}" target="_blank">{snap.website}</a>'))

    if not cells:
        return

    grid_html = '<div class="snap-grid">'
    for label, value in cells:
        grid_html += (
            f'<div class="snap-cell">'
            f'<div class="snap-label">{label}</div>'
            f'<div class="snap-value">{value}</div>'
            f'</div>'
        )
    grid_html += "</div>"
    st.markdown(grid_html, unsafe_allow_html=True)


def _render_why_now(findings: list[Finding]) -> None:
    if not findings:
        return
    st.markdown('<div class="section-label">Why Now</div>', unsafe_allow_html=True)
    for i, f in enumerate(findings, 1):
        cc = CONF_CLASS.get(f.confidence, "conf-low")
        cl = CONF_LABEL.get(f.confidence, "LOW")
        st.markdown(
            f"""<div class="signal-card">
                <div class="signal-num">Signal {i} &nbsp;<span class="{cc}">{cl}</span></div>
                <div class="signal-text">{f.claim}</div>
                <div class="signal-source">{_src(f.source_url, f.source_title)}</div>
            </div>""",
            unsafe_allow_html=True,
        )


def _render_champion(profile: ChampionProfile) -> None:
    st.markdown(f'<div class="section-label">Champion: {profile.name}</div>', unsafe_allow_html=True)

    cells = []
    cells.append(("Title", profile.title or "—"))
    tenure_str = f"{profile.tenure_months} months" if profile.tenure_months else "—"
    cells.append(("Tenure", tenure_str))

    if profile.email:
        conf_map = {"verified": "✓ verified", "inferred": "~ inferred"}
        note = conf_map.get(profile.email_confidence, "")
        conf_cls = f"email-{profile.email_confidence}" if profile.email_confidence in ("verified", "inferred") else ""
        cells.append(("Email", f'<span class="email-chip">{profile.email}</span> <span class="{conf_cls}">{note}</span>'))
    else:
        cells.append(("Email", "—"))

    if profile.linkedin_url:
        cells.append(("LinkedIn", f'<a href="{profile.linkedin_url}" target="_blank">View profile ↗</a>'))
    else:
        cells.append(("LinkedIn", "—"))

    grid_html = '<div class="champ-grid">'
    for label, value in cells:
        grid_html += (
            f'<div class="champ-cell">'
            f'<div class="champ-label">{label}</div>'
            f'<div class="champ-value">{value}</div>'
            f'</div>'
        )
    grid_html += "</div>"
    st.markdown(grid_html, unsafe_allow_html=True)

    if profile.career_history:
        st.markdown("**Career History**")
        career_html = ""
        for item in profile.career_history:
            career_html += f'<div class="career-item">• {item}</div>'
        st.markdown(career_html, unsafe_allow_html=True)

    if profile.high_signal_flags:
        flags_html = "".join(f'<span class="flag-chip">{flag}</span>' for flag in profile.high_signal_flags)
        st.markdown(f'<div style="margin-top:8px">{flags_html}</div>', unsafe_allow_html=True)

    if profile.prior_tool_exposure:
        st.markdown(f"**Tool Exposure:** {profile.prior_tool_exposure}")

    if profile.recent_activity:
        st.markdown("**Recent Activity**")
        for item in profile.recent_activity:
            st.markdown(f'<div class="activity-item">• {item}</div>', unsafe_allow_html=True)


def _render_committee(members: list[BuyingCommitteeMember]) -> None:
    if not members:
        return
    st.markdown('<div class="section-label">Buying Committee</div>', unsafe_allow_html=True)

    rows = ""
    for m in members:
        dc = DEAL_ROLE_CLASS.get(m.deal_role, "deal-unknown")
        deal_label = m.deal_role.replace("_", " ").title()

        email_html = "—"
        if m.email:
            conf_map = {"verified": "✓ verified", "inferred": "~ inferred"}
            note = conf_map.get(m.email_confidence, "")
            conf_cls = f"email-{m.email_confidence}" if m.email_confidence in ("verified", "inferred") else ""
            email_html = f'<span class="email-chip">{m.email}</span><br><span class="{conf_cls}">{note}</span>'

        li_html = "—"
        if m.linkedin_url:
            li_html = f'<span class="li-link"><a href="{m.linkedin_url}" target="_blank">LinkedIn ↗</a></span>'
        elif m.source_url:
            li_html = f'<span class="li-link"><a href="{m.source_url}" target="_blank">Source ↗</a></span>'

        rows += f"""<tr>
            <td>
                <div class="bc-name">{m.name}</div>
                <div class="bc-role">{m.role}</div>
            </td>
            <td><span class="deal-badge {dc}">{deal_label}</span></td>
            <td>{email_html}</td>
            <td>{li_html}</td>
        </tr>"""

    st.markdown(
        f"""<table class="bc-table">
            <thead><tr>
                <th>Person</th><th>Deal Role</th><th>Email</th><th>LinkedIn / Source</th>
            </tr></thead>
            <tbody>{rows}</tbody>
        </table>""",
        unsafe_allow_html=True,
    )


def _render_tech_stack(tech_stack: list[str]) -> None:
    if not tech_stack:
        return
    st.markdown('<div class="section-label">Tech Stack</div>', unsafe_allow_html=True)

    confirmed, inferred, historical = _categorize_stack(tech_stack)

    html = ""
    if confirmed:
        html += '<div style="margin-bottom:8px"><span style="font-size:0.75rem;font-weight:700;color:#0A5E35;letter-spacing:0.08em;text-transform:uppercase;">Confirmed</span><br>'
        html += "".join(f'<span class="stack-confirmed">{_tool_name(e)}</span>' for e in confirmed)
        html += "</div>"
    if inferred:
        html += '<div style="margin-bottom:8px"><span style="font-size:0.75rem;font-weight:700;color:#7A5200;letter-spacing:0.08em;text-transform:uppercase;">Likely / Inferred</span><br>'
        html += "".join(f'<span class="stack-inferred">{_tool_name(e)}</span>' for e in inferred)
        html += "</div>"
    if historical:
        html += '<div style="margin-bottom:8px"><span style="font-size:0.75rem;font-weight:700;color:#6B6B6B;letter-spacing:0.08em;text-transform:uppercase;">Historical</span><br>'
        html += "".join(f'<span class="stack-historical">{_tool_name(e)}</span>' for e in historical)
        html += "</div>"

    st.markdown(html, unsafe_allow_html=True)


def _render_risk_flags(findings: list[Finding]) -> None:
    st.markdown('<div class="section-label">Competitive Landscape & Risk Flags</div>', unsafe_allow_html=True)
    if not findings:
        st.markdown(
            '<div class="clean-card">✓ No competing design tool signals or deal risks detected in public sources.</div>',
            unsafe_allow_html=True,
        )
        return
    for f in findings:
        cc = CONF_CLASS.get(f.confidence, "conf-low")
        cl = CONF_LABEL.get(f.confidence, "LOW")
        st.markdown(
            f"""<div class="risk-card">
                <div class="risk-label">Risk &nbsp;<span class="{cc}">{cl}</span></div>
                <div class="risk-text">{f.claim}</div>
                <div class="risk-source">{_src(f.source_url, f.source_title)}</div>
            </div>""",
            unsafe_allow_html=True,
        )


def _render_hiring(findings: list[Finding]) -> None:
    if not findings:
        return
    st.markdown('<div class="section-label">Hiring & Growth</div>', unsafe_allow_html=True)
    for i, f in enumerate(findings, 1):
        cc = CONF_CLASS.get(f.confidence, "conf-low")
        cl = CONF_LABEL.get(f.confidence, "LOW")
        st.markdown(
            f"""<div class="signal-card">
                <div class="signal-num">Growth {i} &nbsp;<span class="{cc}">{cl}</span></div>
                <div class="signal-text">{f.claim}</div>
                <div class="signal-source">{_src(f.source_url, f.source_title)}</div>
            </div>""",
            unsafe_allow_html=True,
        )


def _render_outreach(talk_track: list[str], outreach_angles: list[str]) -> None:
    if not talk_track and not outreach_angles:
        return
    st.markdown('<div class="section-label">Outreach Recommendations</div>', unsafe_allow_html=True)

    if talk_track:
        st.markdown("**First-Call Talk Track**")
        for i, bullet in enumerate(talk_track, 1):
            st.markdown(
                f'<div class="tt-item"><span class="tt-num">{i}.</span>{bullet}</div>',
                unsafe_allow_html=True,
            )

    if outreach_angles:
        st.markdown("<br>**Personalized Openers**", unsafe_allow_html=True)
        for angle in outreach_angles:
            st.markdown(
                f'<div class="angle-item"><span class="angle-bullet">→</span>{angle}</div>',
                unsafe_allow_html=True,
            )


def _render_sources(brief: AccountBrief) -> None:
    seen: dict[str, str] = {}
    for f in brief.why_now + brief.hiring_findings + brief.risk_flags:
        if f.source_url not in seen:
            seen[f.source_url] = f.source_title
    for m in brief.buying_committee:
        if m.source_url and m.source_url not in seen:
            seen[m.source_url] = m.source_title

    if seen:
        st.markdown("")
        with st.expander(f"All sources ({len(seen)})", expanded=False):
            for url, title in seen.items():
                st.markdown(f"- [{title}]({url})")


def render_brief(brief: AccountBrief) -> None:
    _render_header(brief)
    _render_summary(brief)

    if brief.company_snapshot:
        _render_snapshot(brief.company_snapshot)

    _render_why_now(brief.why_now)

    if brief.champion_profile:
        _render_champion(brief.champion_profile)

    _render_committee(brief.buying_committee)
    _render_tech_stack(brief.tech_stack)
    _render_risk_flags(brief.risk_flags)
    _render_hiring(brief.hiring_findings)
    _render_outreach(brief.talk_track, brief.outreach_angles)
    _render_sources(brief)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("← New search", key="new_search"):
        del st.session_state["brief"]
        st.rerun()


# ── Agent status HTML ─────────────────────────────────────────────────────────

def _agent_card_html(icon: str, label: str, status: str) -> str:
    cls_map = {
        "waiting":   ("agent-status-waiting",  "—"),
        "searching": ("agent-status-running",   "searching…"),
        "done":      ("agent-status-done",      "✓ done"),
        "error":     ("agent-status-error",     "✗ error"),
    }
    cls, text = cls_map.get(status, ("agent-status-waiting", status))
    return (
        f'<div class="agent-card">'
        f'<div class="agent-icon">{icon}</div>'
        f'<div class="agent-name">{label}</div>'
        f'<div class="{cls}">{text}</div>'
        f'</div>'
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    st.markdown(
        """<div style="margin-bottom:1.6rem;">
            <div class="pql-wordmark">Figma RevOps</div>
            <div class="pql-title">PQL Intelligence Agent</div>
            <div class="pql-subtitle">
                Enter the <strong>target company</strong> and your <strong>champion's full name</strong>
                — e.g. head of design, VP Product, or any key contact at the account.<br>
                Five AI research agents run in parallel on live web data and return a complete cited brief in ~60–90 seconds.
            </div>
            <div style="margin-top:10px;display:flex;flex-wrap:wrap;gap:6px;">
                <span class="output-chip">🏢 Company snapshot</span>
                <span class="output-chip">⚡ Why-now signals</span>
                <span class="output-chip">🧑 Champion profile + email</span>
                <span class="output-chip">👥 Buying committee</span>
                <span class="output-chip">🔧 Tech stack</span>
                <span class="output-chip">⚔️ Competitive risks</span>
                <span class="output-chip">✉️ Outreach openers</span>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    if "brief" in st.session_state:
        render_brief(st.session_state["brief"])
        return

    with st.form("search_form", clear_on_submit=False):
        c1, c2, c3 = st.columns([4, 4, 2])
        with c1:
            company = st.text_input("Company", placeholder="e.g. Vercel")
        with c2:
            champion = st.text_input("Champion / Key contact", placeholder="e.g. Lee Robinson")
        with c3:
            st.markdown("<br>", unsafe_allow_html=True)
            run = st.form_submit_button("Run →", type="primary", use_container_width=True)

    if not run:
        return
    if not company.strip() or not champion.strip():
        st.warning("Please enter both a company name and champion name.")
        return

    company, champion = company.strip(), champion.strip()

    # ── Agent status grid ──────────────────────────────────────────────────
    agent_ph = st.empty()
    statuses: dict[str, str] = {key: "waiting" for key, _, _ in AGENTS}

    def _refresh_agents() -> None:
        grid = '<div class="agent-grid">'
        for key, icon, label in AGENTS:
            grid += _agent_card_html(icon, label, statuses[key])
        grid += "</div>"
        agent_ph.markdown(grid, unsafe_allow_html=True)

    _refresh_agents()
    progress = st.progress(0.0)

    start = time.time()

    async def _run() -> list:
        q: asyncio.Queue = asyncio.Queue()
        task = asyncio.create_task(orchestrator.run_all_agents(company, champion, q))
        while not task.done():
            await asyncio.sleep(0.35)
            while not q.empty():
                key, status = await q.get()
                statuses[key] = status
                _refresh_agents()
                done_count = sum(1 for s in statuses.values() if s in ("done", "error"))
                progress.progress(min(done_count / 5, 1.0))
        return await task

    # Mark all as searching at the start
    for key, _, _ in AGENTS:
        statuses[key] = "searching"
    _refresh_agents()

    outputs = asyncio.run(_run())

    progress.progress(1.0)
    for key in statuses:
        if statuses[key] not in ("done", "error"):
            statuses[key] = "done"
    _refresh_agents()

    agent_ph.markdown(
        '<div style="background:#F0EBFF;border-left:3px solid #A259FF;border-radius:8px;'
        'padding:18px 22px;font-size:1rem;color:#1E1E1E;font-weight:500;">'
        '⏳&nbsp; All research complete — preparing your AE brief...'
        '</div>',
        unsafe_allow_html=True,
    )
    with st.spinner("Preparing brief…"):
        brief = synthesis.synthesize(company, champion, outputs, start)

    cache.save(brief)
    st.session_state["brief"] = brief
    st.rerun()


if __name__ == "__main__":
    main()
