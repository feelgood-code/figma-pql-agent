# PQL Intelligence Agent — Implementation Plan

> **Project type:** Live agentic demo for a Head of RevOps interview at Figma
> **Build target:** Working Streamlit app deployable to Streamlit Cloud, runnable end-to-end in ~5 minutes for a live demo, with pre-cached fallback mode for reliability
> **Estimated build time:** 25–35 hours
> **Demo runtime per account:** ~60–120 seconds live, instant when cached

---

## 1. Project Premise & Demo Narrative

### The pitch in one sentence
> *"PQL scoring tells you that an account is interesting. The PQL Intelligence Agent tells you who they are, why now, and what to say — turning a flagged account into a deal-ready opportunity in 90 seconds."*

### The opening narrative (use verbatim in interview intro)
Figma already has PQL scoring — it has for years. When an account crosses the threshold, an AE gets a Salesforce notification with basic product usage data and starts a 30–45 minute manual research process: LinkedIn on the champion, news on the company, hiring data, competitive tool signals. Multiply by 500+ PQLs per week and you're looking at thousands of hours of AE research time, done inconsistently, often skipped under deadline pressure.

That research is a *reasoning task across heterogeneous data sources* — exactly what frontier LLMs with tool use can now do. The agent does it in 90 seconds, does it consistently, and surfaces patterns a human reviewer would miss.

### The three "wow moments" the demo MUST deliver

These are non-negotiable. Every other implementation choice serves these moments.

1. **The Enterprise Champion (Hero 1).** Agent discovers the PQL champion previously deployed Figma successfully at a larger past employer. An AE would catch this only with deep LinkedIn research.

2. **The Strategic Moment (Hero 2).** Agent connects a product usage spike to a public company event (funding round, leadership hire, strategic pivot). Demonstrates real cross-source synthesis.

3. **The Contrarian Risk Flag (Hero 3).** Agent disagrees with the PQL score. Surfaces competitive threat signals (competing-tool job postings, design leader departure) that mean an "expansion opportunity" is actually a churn risk. This is the moment that proves the agent has *judgment*, not just summarization ability.

---

## 2. System Architecture

### High-level flow

```
PQL Trigger (mock Salesforce payload)
        ↓
Orchestrator Agent (plans research strategy)
        ↓
[Parallel execution of 5 specialized sub-agents]
        ↓
    ┌─────────────────────────────────────────────┐
    │ • Company Intelligence Agent                │
    │ • Champion Intelligence Agent               │
    │ • Buying Committee Agent                    │
    │ • Competitive Signals Agent                 │
    │ • Hiring & Growth Agent                     │
    └─────────────────────────────────────────────┘
        ↓
Synthesis Agent (writes Account Brief + Outreach Email)
        ↓
Streamlit UI (live streaming + final brief card)
```

### Layer 1: Input — PQL Trigger
A JSON payload representing what a real Salesforce/Looker pipeline would emit. Three hand-crafted triggers (Hero 1/2/3) live in `/data/triggers/`.

### Layer 2: Orchestrator Agent
A single LLM call that receives the PQL trigger and outputs a JSON research plan: which sub-agents to run, what specific questions each must answer, what queries to prioritize. This is mostly cosmetic in v1 (sub-agents could run with a fixed plan) but **the live trace of the orchestrator "thinking" is a high-value visual moment in the demo**, so it earns its place.

### Layer 3: Five specialized sub-agents

Each sub-agent is a Python function that:
1. Takes the orchestrator's task brief as input
2. Calls Exa one or more times with category-appropriate queries
3. Optionally fetches full page content via Exa's contents API
4. Calls the LLM with the retrieved content to extract structured findings
5. Returns a Pydantic-validated JSON object with findings + source URLs

The five agents:

| Agent | Primary Exa category | Output schema |
|---|---|---|
| Company Intelligence | `company`, `news` | Funding events, leadership, strategic moves, recent news |
| Champion Intelligence | `people` | Career history, prior Figma exposure, recent activity, tenure |
| Buying Committee | `people` | Other relevant contacts at the company (design leads, procurement, IT/security) |
| Competitive Signals | `auto` (job boards, careers pages) | Competing-tool mentions in JDs, tech stack signals |
| Hiring & Growth | `auto` (job boards, news) | Design/PM hiring velocity, org expansion |

### Layer 4: Tool Layer (Exa primary, web fetch fallback)
- **Primary:** Exa Python SDK (`exa-py`) with category-targeted searches and structured outputs.
- **Fallback:** `httpx`-based generic web fetch for cases where Exa returns insufficient content (rare, but useful for fetching a specific known URL).
- **NO computer use.** Exa's people and company indexes cover what we'd otherwise need a browser for, faster and more reliably.

### Layer 5: Synthesis Agent
Single LLM call that receives:
- Original PQL trigger
- Outputs from all five sub-agents
- A structured synthesis prompt (see Section 5)

Produces the final Account Brief as structured JSON, plus a drafted outreach email.

### Layer 6: UI (Streamlit)
Four screens described in Section 7.

---

## 3. Tech Stack & Provider Choices

### Models
- **Primary LLM:** Gemini 2.5 Pro via the official `google-generativeai` SDK. Reasoning: user has free credits, model supports structured outputs and function calling, web-connected agent workflows are a documented strength.
- **Abstraction:** Use **LiteLLM** as the model gateway. This means the actual code never directly imports `google-generativeai` for inference — it calls `litellm.completion(model="gemini/gemini-2.5-pro", ...)`. Switching to Claude becomes a single config change.
- **Fallback model config:** `claude-sonnet-4-6` ready to swap in if Gemini fails on demo day. Both API keys configured in `.env`.

### Search & retrieval
- **Exa** (`exa-py` SDK) — primary research tool. Uses:
  - `category="company"` for company discovery
  - `category="people"` for champion and buying committee research
  - `category="news"` for recent strategic events
  - `type="auto"` for job postings, careers pages, general web
  - `type="deep"` with `output_schema` for high-confidence structured extraction on hero discoveries (use sparingly — slower and more expensive)
  - Use `contents={"highlights": True}` for token-efficient retrieval

### UI & runtime
- **Streamlit** for the demo UI
- **asyncio** with `asyncio.gather()` for parallel sub-agent execution
- **Pydantic** v2 for structured output validation
- **python-dotenv** for config

### Deployment
- **Streamlit Community Cloud** for the public demo URL (backup if local fails)
- **GitHub** for version control + the source of truth Streamlit Cloud deploys from

### What we are NOT using and why
- **No LangGraph / CrewAI / AutoGen.** They add abstraction layers, failure modes, and version churn. A 5-agent system with parallel execution is ~150 lines of plain Python with asyncio. Frameworks would slow this down.
- **No vector database.** No retrieval over historical data needed for v1.
- **No real Salesforce / Slack integrations.** Mock the payloads. The demo is about the intelligence layer; integration plumbing is a Phase 2 conversation.
- **No computer use / browser automation.** See Section 3a below — this is a deliberate, defensible choice, not a corner being cut.
- **No fine-tuning.** Prompt engineering carries the entire project.

### 3a. Why no browser use / LinkedIn automation

This is a question the interviewer may ask, and the answer matters because it shows judgment about when to use which tool.

**LinkedIn specifically is the worst possible target for browser automation.** LinkedIn has an aggressive anti-scraping team, sophisticated bot detection (browser fingerprinting, mouse-movement analysis, request-timing models), and a history of litigating against scrapers. Practically:
- Browser automation flows hit login walls, captchas, and "unusual activity" challenges within 1-3 navigations
- You cannot authenticate during a demo (personal account = ToS violation; throwaway account = phone-verification gate)
- Detection patterns rotate — what worked Tuesday may fail Thursday
- A browser stuck on a login screen mid-demo is worse than no demo at all

**Exa's people index already provides what we need:** 1B+ public LinkedIn profile data, including career history, current role, public posts, education, with the LinkedIn URL returned as a citable source. That's ~90% of what an account brief actually needs from LinkedIn. The remaining 10% (private connections, mutual contacts, who-viewed-whom) is gated behind LinkedIn Sales Navigator's API, which requires a legitimate partnership agreement — that's a Phase 3 production conversation, not a v1 demo concern.

**The credible answer for the interviewer if asked:**

> "Browser automation against LinkedIn is a trap — anti-bot defenses make it unreliable and the ToS issues create real legal exposure. In production you'd integrate Sales Navigator's API through a partnership. For this demo, Exa's people index gives me 90% of the signal with citations and zero fragility. Computer use is the right tool when there's truly no API alternative; for LinkedIn there is one."

**When computer use WOULD be appropriate (Phase 2/3 consideration):**
- Niche industry directories Exa doesn't cover well
- Internal/customer portals (e.g., a customer's status page or admin console)
- Specific company sites with heavy JS rendering that Exa contents can't parse cleanly

None of those apply to v1. Adding browser use for capability-display alone burns build time and adds demo fragility for no actual signal gain.

---

## 4. The Three Hero Scenarios (CRITICAL — validate before building)

> **The single highest-risk part of this project is choosing heroes whose "wow discoveries" are actually findable via Exa.** Spend Phase 1 entirely on validation. If a hero's discovery doesn't surface in 2–3 well-formed Exa queries, swap the hero.

### Hero design principles
- **Use real companies.** The web search returns real results, making the demo feel authentic. Be transparent in the demo intro that *product usage data is mocked*; everything else is real.
- **Pick champions whose public footprint is rich.** LinkedIn-active people with clear career histories work best. Avoid pseudonymous developers or people with common names.
- **The "wow discovery" must be discoverable in <5 Exa queries.** If you need 20 queries to find it, the agent won't either, and the demo will fail.

### Hero 1: The Enterprise Champion (Vercel scenario)

**The setup:**
- Account: Vercel
- Champion: A senior design leader who joined Vercel ~6–9 months ago from a known Figma Enterprise customer
- Mocked product signal: Workspace went from 0 → 14 editors in 3 weeks, heavy Dev Mode and Figma Make adoption

**The discovery the agent must surface:**
The champion's previous employer is a major Figma Enterprise account. They are running the same playbook again.

**Validation step (Phase 1):** Pick a specific real person who fits this pattern. Run these Exa queries manually:
- `category="people", query="Head of Design Vercel"`
- `category="people", query="<their name> previous companies"`
- Verify their LinkedIn history is in the top 3 results.
- Verify their prior employer is publicly known as a Figma customer (Figma case studies page, conference talks, etc.).

**If validation fails:** Swap to a different real design leader who recently moved between known Figma Enterprise customers. Browse Figma's customer logos page, then cross-reference design leadership moves on LinkedIn.

### Hero 2: The Strategic Moment (AI-native company scenario)

**The setup:**
- Account: A well-known AI company (e.g., a frontier model lab, AI tooling startup, etc.)
- Champion: Head of Design or Head of Product
- Mocked product signal: Existing workspace, usage tripled in 30 days, 9 new editors all with company email domain

**The discovery the agent must surface:**
The product usage spike correlates exactly with a public strategic event — funding round, product launch announcement, leadership hire pushing into a new market — and a wave of design/product hires.

**Validation step:** Pick a real company that has had a major announcement in the last 6 months AND has a visible hiring spike in design roles. Verify both via Exa:
- `category="news", query="<company> funding announcement 2026"`
- `query="<company> design hiring careers"`
- Check the company's careers page directly via Exa contents fetch.

### Hero 3: The Contrarian Risk Flag (existing customer expansion scenario)

**The setup:**
- Account: An existing Figma customer at moderate ARR (e.g., 200 seats)
- Champion: VP/Director of Design role (mocked as the existing exec sponsor)
- Mocked product signal: PQL fired on expansion (governance feature touches up). Surface-level looks positive.

**The discovery the agent must surface:**
At least two warning signs that contradict the score:
- Recent job postings on the company's careers page mention a competing design tool (Sketch, Adobe XD, Penpot, etc.) as required experience
- The design exec sponsor recently departed (LinkedIn shows new role at different company in last 60–90 days)

**Validation step:** This is the hardest hero to validate. Find a real company that has both signals present right now. Easier alternative: pick a real company where ONE signal is genuinely present, and lean on that as the contrarian flag rather than requiring both.

**Fallback plan if Hero 3 can't be validated with real data:** Frame the demo as "the system flagged this account, here's what the agent surfaced" and accept that some Hero 3 details are illustrative. Be honest about it in the interview — interviewers respect intellectual honesty more than they punish a softer Hero 3.

---

## 5. Prompt Engineering — The Core of the Project

> **80% of the quality of this demo lives in the prompts.** Plan to iterate each prompt at least 10 times. The code around the prompts is trivial by comparison.

### 5a. Source-tracking architecture (non-negotiable)

Every factual claim in every brief must have a traceable source URL. This is the single most important trust property of the system. Citations are enforced at three layers:

**Layer 1: Sub-agent output schemas (Pydantic).**
A finding is never a plain string. It's a typed object:

```python
class Finding(BaseModel):
    claim: str                              # The factual statement
    source_url: str                         # Must be a URL the agent actually retrieved
    source_title: str                       # Page title for display
    confidence: Literal["low", "medium", "high"]
    retrieved_at: datetime                  # When the source was fetched
```

If a sub-agent attempts to return a claim without a URL, Pydantic validation fails. The agent retries with an instruction to include sources. After 2 failed retries, the claim is dropped.

**Layer 2: Synthesis prompt enforcement.**
The synthesis prompt includes (verbatim):

> "Every factual claim must have a source URL inline, drawn from the sub-agent findings provided. You may rephrase and connect findings, but you may NOT introduce new facts not present in those findings. If you can't cite it, don't say it. If the sub-agent confidence is 'low', either downgrade the language to hedged ('appears to', 'suggests') or omit the claim."

**Layer 3: Post-synthesis verification pass.**
After the synthesis agent runs, a verification function scans the output:
- For each claim with an embedded URL, verify the URL appears in at least one sub-agent's findings.
- If a URL is in the brief but was never retrieved by a sub-agent → flag as hallucination, strip or re-run.
- If a sentence makes a strong factual claim but has no URL nearby → flag for manual review.

This is ~40 lines of code and is the difference between "demo that looks impressive" and "system the manager can imagine deploying."

### 5b. Citation flow through the system

```
Exa search → returns {text, url, title, published_date}
        ↓
Sub-agent prompt: "Extract findings, attach the URL each came from"
        ↓
Pydantic validates: every Finding has source_url
        ↓
Synthesis agent receives: list of Findings as structured input
        ↓
Synthesis prompt: "Every claim must reference a source_url from input"
        ↓
Output: Brief with [claim text] + source_url for every signal
        ↓
Verification pass: URLs in output ⊆ URLs from sub-agents
        ↓
UI: renders inline source links, opens in new tab
```

### 5c. UI rendering of citations

In the brief, every claim renders as:

```
Sarah Chen joined Vercel from Shopify 9 months ago, where she led
the design org during Figma's Enterprise rollout. [LinkedIn ↗] [Case study ↗]
```

The bracketed links are clickable. They open in a new tab. The interviewer can click any of them and verify — the fact that they *could* is what makes the brief trustworthy.

For the **drafted outreach email**, citations don't appear inside the email body (that would be strange). Instead, beneath the email is a collapsible "Sources referenced in this email" panel listing the specific findings the email draws from. This lets an AE verify before sending.

For **risk flags**, citations are mandatory and prominent — a contrarian flag without strong sources is worse than no flag at all.

### 5d. Handling low-confidence findings

Not every Exa search returns a clean answer. When a sub-agent has weak evidence:
- Set `confidence="low"` on the Finding
- The synthesis agent is prompted to hedge language for low-confidence findings ("appears to", "may have", "one source suggests") or omit them entirely
- Low-confidence findings never appear in the drafted email
- Low-confidence findings never trigger a risk flag

This costs some "wow density" but is the right call — a brief with one strong signal beats a brief with three sketchy ones.

### Prompt 1: Orchestrator

```
You are the Lead RevOps Intelligence Agent for Figma. A PQL has just fired
for an account. Your job is to design a research plan for five specialized
sub-agents who will investigate this account in parallel.

PQL Trigger:
{trigger_json}

Available sub-agents:
- company_intel: company news, funding, leadership changes, strategic events
- champion_intel: the specific user who's driving usage (career history,
  prior Figma exposure, recent public activity)
- buying_committee: other relevant stakeholders at the company
- competitive_signals: signs of competing tools or churn risk
- hiring_growth: hiring velocity, especially in design/product roles

For each sub-agent, output:
1. A 1-sentence research brief describing what they should find
2. 2-3 specific questions they must answer
3. Suggested Exa categories and query phrasings

Think hard about what would be most decision-relevant for an AE.
A "yes/no" finding is less valuable than a "here's what they're doing and why."

Output as JSON matching the schema provided.
```

### Prompt 2: Sub-agent (Champion Intelligence example — replicate pattern for others)

```
You are the Champion Intelligence sub-agent for Figma's RevOps team.

Your task: research {champion_name}, {champion_title} at {company}, who
appears to be driving Figma adoption.

Research questions from the orchestrator:
{orchestrator_questions}

You have access to the Exa search API. Use these query patterns:
- For their LinkedIn / career history: category="people"
- For their public talks, interviews, posts: category="auto" with name + role
- For their previous companies' Figma usage: category="company" with previous
  company name + "Figma case study" or "Figma customer"

HIGH-SIGNAL DISCOVERIES to flag explicitly:
- Has the champion used or championed Figma at a previous employer?
- Are they a "founder-mode" leader (CXO, VP) vs. an IC contributor?
- Have they recently posted/spoken about design tooling, design systems,
  or design ops? (Especially relevant if they joined recently.)
- How long have they been at the current company? (<12 months = high signal
  for tool-stack changes.)

Return a structured JSON object with fields:
- profile_summary (3 sentences)
- career_history (last 3 roles with dates)
- prior_figma_exposure (boolean + evidence + source URL)
- recent_public_activity (last 6 months, with URLs)
- tenure_at_current_company_months (integer)
- high_signal_findings (list of strings, each with source URL)
- confidence (low/medium/high)

If you cannot find the champion via Exa with 3 reasonable queries, return
confidence="low" and explain what's missing. Do NOT invent information.
```

### Prompt 3: Synthesis

```
You are the Synthesis Agent. Your output goes directly to a Figma Account
Executive who will read it before making first contact.

Quality bar: the AE should feel like a senior strategist did 2 hours of
research for them, and should have a credible reason to reach out *now*
with a *specific* angle that mentions things the prospect cares about.

Inputs:
- Original PQL trigger: {trigger_json}
- Sub-agent findings: {subagent_outputs_json}

Produce a structured Account Brief with these sections:

1. **Executive Summary** (3 sentences max). What is happening at this
   account, why does it matter, what should the AE do?

2. **Why Now** (top 3 signals with evidence). Each signal must:
   - State the signal in one line
   - Cite specific evidence (source URL inline)
   - Explain why it matters for an AE conversation

3. **Buying Committee** (key contacts). List up to 5 people, each with:
   - Name and role
   - Likely role in a Figma deal (champion / economic buyer / blocker /
     technical evaluator)
   - Source URL for the identification

4. **Risk Flags** (anything that could derail the deal). Be specific —
   "competitor tool detected" is not enough; say which tool, on which
   job posting, and why it matters.

5. **Drafted Outreach Email** (120 words max). Must reference at least 2
   specific findings from above. No generic openers. The opening line
   must NOT be "I noticed your team's Figma usage spiked..." — instead
   anchor on the strategic context (e.g., "Congrats on the Series C —
   I imagine the design team is scaling fast...").

6. **Suggested First-Call Talk Track** (3 bullets). Concrete topics, not
   generic ones. E.g., "Ask about the Shopify design system experience —
   she ran it. Position Figma Enterprise governance as the v2 of what she
   already loves." NOT "Build rapport."

RULES:
- Every factual claim must have a source URL inline. If you can't cite
  it, don't say it.
- If a sub-agent returned low-confidence findings, do NOT promote them
  to high-confidence statements.
- If the buying committee or competitive signals contradict the PQL's
  "expansion opportunity" framing, say so explicitly. The AE needs the
  truth, not validation.

Output as JSON matching the schema.
```

### Prompt iteration discipline
- Keep a `/prompts/` directory with versioned prompt files (`champion_intel_v3.txt`, etc.).
- For each prompt change, re-run all three heroes and check whether the wow moments still surface.
- Bad prompt changes that improve one hero but regress another are common — version-pin them and keep going.

---

## 6. Build Plan (Phased)

### Phase 0: Setup (1–2 hours)
- Create GitHub repo
- Set up Python 3.11 venv, install dependencies (see Section 9)
- Get Exa API key (free plan = 1,000 requests/month, plenty for build + demo)
- Verify Gemini API key works (and Anthropic as fallback)
- Set up LiteLLM with both providers configured

### Phase 1: Hero validation (3–4 hours) — DO NOT SKIP
For each of the three heroes:
1. Pick the real company and (where applicable) real champion
2. Manually run the Exa queries you expect the agent to run
3. Verify the wow discovery surfaces in <5 queries
4. Document the exact queries that worked and the URLs they returned
5. If validation fails, swap the hero before moving on

**Exit criterion:** A `/data/triggers/hero_X_validation.md` file for each hero documenting the wow discovery and the Exa queries that reliably surface it.

### Phase 2: First sub-agent end-to-end (4–6 hours)
Build ONLY the Champion Intelligence agent first. End-to-end means:
- Reads trigger from JSON file
- Calls Exa with people-category queries
- Calls LiteLLM with the champion intel prompt
- Returns Pydantic-validated structured output
- Logs all Exa queries and LLM calls to a JSONL file for debugging

Test against all three heroes. Iterate the prompt until the high-signal findings surface for each. This is the hardest engineering work in the project.

### Phase 3: Remaining sub-agents (4–6 hours)
Build the other four sub-agents. Each is largely a copy of the Champion agent with different prompt + Exa category + output schema. Test each in isolation.

### Phase 4: Orchestrator + parallel execution (2–3 hours)
Build the orchestrator. Wire sub-agents to run in parallel via `asyncio.gather()`. Verify total runtime is <90 seconds for a hero. If a sub-agent is slow (>30s), tune its Exa query strategy or use Exa's fast endpoint instead of deep.

### Phase 5: Synthesis agent (3–4 hours)
Build the synthesis layer. This is the second-most prompt-engineering-heavy part. Iterate until briefs are crisp, cited, and specific. Test against all three heroes.

### Phase 6: Streamlit UI (5–7 hours)
See Section 7 for screen specs. Aim for clean, not flashy.

### Phase 7: Pre-caching + reliability (2–3 hours)
For each hero:
1. Run the agent fully and save all intermediate outputs (sub-agent results, synthesis output) to `/data/cached/hero_X/`
2. Add a `DEMO_MODE` env var: `live` (real calls), `cached` (loads from disk), `hybrid` (live for one hero, cached for others)
3. Add a UI toggle so you can switch modes mid-demo if needed

**Critical:** In `hybrid` mode, the live run must complete in <90s reliably. Pre-test 5 times the day before the interview.

### Phase 8: Demo polish (3–4 hours)
- Record a screen capture as a final fallback (if everything else fails, you have a video)
- Write a 1-page architecture diagram (Excalidraw → PNG → embedded in app)
- Time the full demo end-to-end 5 times. Target 4:30, hard cap 5:00.
- Deploy to Streamlit Cloud
- Practice narration until smooth

---

## 7. Streamlit UI — Four Screens

### Screen 1: PQL Inbox (Home)
- Three cards, one per hero, showing the PQL trigger summary:
  - Company logo (fetched via Clearbit Logo API, free)
  - Account name
  - PQL score (mocked)
  - Top 3 triggering signals
  - "Run Intelligence Agent" button
- Top right: "Demo Mode" selector (Live / Cached / Hybrid)
- Below the cards: a small architecture diagram (collapsible)

### Screen 2: Live Agent View
**This is the highest-leverage screen for wow factor.** The interviewer watches the AI think.

Layout:
- Top: status banner ("Running Intelligence Agent on {company}...")
- Middle: 5 columns, one per sub-agent, each showing:
  - Agent name and icon
  - Current status (Planning / Searching / Synthesizing / Done)
  - Live-streaming log of what it's doing ("Searching Exa for 'Vercel design leadership LinkedIn'...")
  - Sources discovered (count + clickable list)
- Bottom: orchestrator's plan (collapsible)

Implementation notes:
- Use `st.status()` with `state="running"` then `state="complete"`
- Use `asyncio.Queue` to push updates from sub-agents to the UI
- Update with `st.rerun()` triggered by queue events, or use `st.write_stream` for token-level streaming on the synthesis step
- Don't optimize for true real-time — 1–2 second update latency is fine. The *impression* of live agentic work matters more than literal real-time.

### Screen 3: Account Brief (Final Output)
Layout:
- Header: company name, logo, PQL score, "Brief generated in {N}s"
- **Executive Summary** card (highlighted)
- **Why Now** — 3 numbered insight cards with source links
- **Buying Committee** — table with roles and identified people
- **Risk Flags** — red/yellow cards if any
- **Drafted Outreach Email** — in a `st.code()` block with a "Copy" button
- **First-Call Talk Track** — 3 bullets
- Footer: "Run again live" / "Show another account" / "Export to Salesforce" (mocked button)

Visual rules:
- Generous whitespace
- One accent color (Figma purple #A259FF works thematically)
- Every claim has a clickable source link
- Risk flags use red text/border so they're visually distinct

### Screen 4: About / Architecture
- The architecture diagram
- Tech stack summary
- Cost breakdown ("This brief cost $X in API calls")
- "Phase 2 / Phase 3 roadmap" — what this becomes in production
- Your contact info

This screen exists so that if the interviewer asks "how does this actually work" you have visuals ready.

---

## 8. Demo Script (5 minutes)

> Practice this verbatim until it's natural. The script earns points; ad-libbing loses them.

### 0:00–0:45 — Setup
> "PQL scoring tells you an account is interesting. It doesn't tell you who the champion is, why now, or what to say. That research is what an AE spends 30–45 minutes on per account — and it's exactly the kind of cross-source reasoning that frontier LLMs with tool use can now do in 90 seconds.
>
> I built a working version of this over the weekend. I'm going to run it live for one of three mock PQLs, then walk through two pre-cached examples. The product usage data is mocked; everything the agent finds about the company and the champion is real."

[Open PQL Inbox screen.]

> "Here are three PQLs that fired today. Let's run Vercel live."

### 0:45–2:30 — Hero 1 live run (Vercel)
[Click "Run Intelligence Agent" on Vercel. Screen 2 takes over.]

> "Five sub-agents are running in parallel. The orchestrator decided what each should investigate — company news, the champion's background, the buying committee, competitive signals, and hiring velocity. Each is using Exa for retrieval and Gemini for reasoning."

[Wait 60–90 seconds. Final brief appears.]

> "Here's the brief. The Executive Summary in three sentences. But this is what I want you to see — [point to Why Now item 1] — the agent figured out that the champion, [Name], was Director of Design at [Previous Company] until 9 months ago. [Previous Company] is one of Figma's largest Enterprise customers. She's running the same playbook at Vercel — and you can see the source link to her LinkedIn right there.
>
> No AE would catch this without 20 minutes of LinkedIn research. The agent caught it in [N] seconds. And look at the drafted email — it opens with that context, not with 'I noticed your usage spiked.'"

### 2:30–3:30 — Hero 2 cached (AI company)
[Switch to cached Hero 2 brief.]

> "Different pattern. This account had moderate usage for a year, suddenly tripled in 30 days. The agent connected the spike to two public events: their [funding/launch/leadership] announcement and 18 new design hires posted on their careers page in the last 60 days.
>
> This is the synthesis I care most about. Product data alone tells you something is happening. Combining it with public strategic context tells you *why*. The outreach the agent drafted references the specific event — that's what gets a response."

### 3:30–4:15 — Hero 3 cached (contrarian risk flag)
[Switch to cached Hero 3 brief.]

> "And here's the one I'm most proud of. The PQL system flagged this account as an expansion opportunity — governance features touched, looks bullish. The Intelligence Agent disagrees.
>
> [Point to Risk Flags.] Two design roles posted in the last 30 days listing [competing tool] as required. The design exec sponsor left 2 months ago. The agent overrode the score and flagged this as churn risk instead.
>
> That's the kind of judgment a senior account strategist would make. Now every AE has it on every PQL."

### 4:15–5:00 — Roadmap & close
> "This is Phase 1 — the intelligence layer on top of existing PQL scoring. Phase 2 is closing the loop: feeding AE feedback into the agent so brief quality improves over time. Phase 3 is the same engine generating QBR prep, renewal risk reports, and competitive battlecards on demand — same architecture, different triggers.
>
> The unit economics are absurd: about $0.50–$1.00 per brief in API costs against 30 minutes of AE time. At Figma's PQL volume, that's a six-figure annual time-savings for low-five-figure compute.
>
> I'd love to talk about what the Phase 1 rollout would look like at Figma — what data sources you'd want connected, where it lives in the AE workflow, and how we'd measure brief quality."

---

## 9. Repository Structure & Dependencies

```
pql-intelligence-agent/
├── README.md                          # Setup + run instructions
├── .env.example                       # API key template
├── requirements.txt
├── streamlit_app.py                   # Main UI entry point
├── pyproject.toml
│
├── src/
│   ├── __init__.py
│   ├── config.py                      # LiteLLM model config, demo mode
│   ├── models.py                      # Pydantic schemas for all outputs
│   ├── orchestrator.py                # Orchestrator agent
│   ├── synthesis.py                   # Final synthesis agent
│   ├── llm.py                         # LiteLLM wrapper, retry logic
│   ├── exa_client.py                  # Exa SDK wrapper with caching
│   └── agents/
│       ├── __init__.py
│       ├── base.py                    # Shared sub-agent logic
│       ├── company_intel.py
│       ├── champion_intel.py
│       ├── buying_committee.py
│       ├── competitive_signals.py
│       └── hiring_growth.py
│
├── prompts/                           # Versioned prompt files
│   ├── orchestrator_v1.txt
│   ├── champion_intel_v1.txt
│   ├── company_intel_v1.txt
│   ├── ... (one per agent)
│   └── synthesis_v1.txt
│
├── data/
│   ├── triggers/
│   │   ├── hero_1_vercel.json
│   │   ├── hero_2_ai_company.json
│   │   ├── hero_3_contrarian.json
│   │   └── hero_X_validation.md       # Manual validation notes
│   └── cached/
│       ├── hero_1/
│       │   ├── subagent_outputs.json
│       │   └── synthesis.json
│       ├── hero_2/
│       └── hero_3/
│
├── ui/
│   ├── pages/
│   │   ├── inbox.py
│   │   ├── live_agent.py
│   │   ├── brief.py
│   │   └── about.py
│   ├── components/
│   │   ├── account_card.py
│   │   ├── agent_status.py
│   │   └── brief_renderer.py
│   └── assets/
│       ├── architecture.png
│       └── logos/
│
└── tests/
    ├── test_agents.py
    ├── test_synthesis.py
    └── fixtures/                       # Mock Exa responses for offline testing
```

### requirements.txt

```
streamlit>=1.40
litellm>=1.50
google-generativeai>=0.8
anthropic>=0.40
exa-py>=1.2
pydantic>=2.8
python-dotenv>=1.0
httpx>=0.27
tenacity>=9.0           # retry logic
nest-asyncio>=1.6       # for asyncio in Streamlit
```

### .env.example
```
GEMINI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here   # fallback
EXA_API_KEY=your_key_here
DEMO_MODE=hybrid                  # live | cached | hybrid
PRIMARY_MODEL=gemini/gemini-2.5-pro
FALLBACK_MODEL=anthropic/claude-sonnet-4-6
```

---

## 10. Interview Defense — Anticipated Questions

| Question | Answer (have ready) |
|---|---|
| How is this different from Clay or Common Room? | Clay does enrichment with rigid pipelines. Common Room does community signals. Neither does agentic multi-step reasoning with cross-source synthesis. The wedge is the synthesis layer connecting product data to public strategic context. Figma's product data is uniquely yours. |
| Hallucinations — AEs can't trust unreliable briefs. | Every claim has a source URL enforced at three layers: Pydantic schema on sub-agents, synthesis prompt constraint, and a post-synthesis verification pass that strips claims whose URLs weren't actually retrieved. Low-confidence findings get hedged language or are dropped. Phase 2 adds AE feedback capture to detect hallucination patterns. |
| How does this scale to thousands of PQLs/week? | Per-brief cost is roughly $0.50–$1.00. At 500 PQLs/week that's ~$25K/year for what would otherwise be 100+ AE hours/week. Compute is cheap; the architecture is fully parallel. |
| Build vs buy? | The capability didn't exist 12 months ago. No vendor has it productized yet. In 18 months it'll be a feature in every CRM. The window to build internal capability as a strategic asset is now. |
| Why not use browser automation / computer use, especially for LinkedIn? | LinkedIn is the worst possible target — aggressive anti-bot defenses, ToS exposure, demo fragility. Exa's people index gives 90% of the LinkedIn signal with citations and zero fragility. In production, you'd integrate Sales Navigator's API through a partnership. Computer use is the right tool when there's no API alternative; for LinkedIn there is one. |
| What if AEs reject this? | Phase 2 is the human-in-the-loop. AEs rate briefs after outreach. Bad patterns get prompt-engineered out. The system improves precisely because AEs are using it. |
| MVP scope vs production? | MVP is this demo. Production needs: real-time Salesforce trigger integration, async job queue (Temporal or similar), embedded UI in Salesforce or Slack, feedback capture, monitoring dashboard for brief quality, per-AE cost controls, and a feedback retraining loop. 4–6 month build with a small team. |
| Why Gemini, not Claude? | I'm running it on Gemini for cost reasons in v1, but the code is provider-agnostic via LiteLLM. For production I'd likely run Claude on Opus for the synthesis step (highest reasoning quality) and Gemini Flash for the parallel sub-agents (cheap and fast). It's a routing decision, not an architecture one. |

---

## 11. Risk Mitigation

### Risk: Live demo fails (Exa down, Gemini down, network bad)
**Mitigation:** Hybrid demo mode with cached fallbacks pre-loaded. Recorded screen-capture video as final fallback. Streamlit Cloud public URL as backup if local laptop fails.

### Risk: One hero's wow discovery doesn't surface on the day
**Mitigation:** Pre-cache all three heroes. Demo Hero 1 live but with the option to switch to cached if it stalls. Heroes 2 and 3 are cached by default.

### Risk: Interviewer asks to run their own scenario
**Mitigation:** Have a "Custom Account" form ready (company + champion email). If it works, it's the strongest possible moment. If it fails, fall back to the hero set with: "Custom mode runs but with less reliable results since these triggers haven't been validated." Don't promise it works.

### Risk: Prompt regression breaks a hero late in build
**Mitigation:** Versioned prompts in `/prompts/`. After each prompt change, run all three heroes and snapshot outputs to `/data/cached/`. If a change improves one hero but breaks another, revert.

### Risk: Time overrun in interview
**Mitigation:** Demo is designed so Hero 1 alone delivers 80% of the impact. If you only get 2 minutes, do Hero 1. If you get 5, do all three.

### Risk: Hero 3 contrarian flag is "made up" looking
**Mitigation:** Validate Hero 3 with REAL data in Phase 1. If you can't find a real company with the contrarian signal, switch Hero 3 to a different "judgment" moment (e.g., agent ranks two competing PQLs and explains why one is hotter).

---

## 12. Time Budget Summary

| Phase | Hours |
|---|---|
| 0. Setup | 1–2 |
| 1. Hero validation | 3–4 |
| 2. First sub-agent end-to-end | 4–6 |
| 3. Remaining sub-agents | 4–6 |
| 4. Orchestrator + parallel exec | 2–3 |
| 5. Synthesis agent | 3–4 |
| 6. Streamlit UI | 5–7 |
| 7. Caching + reliability | 2–3 |
| 8. Demo polish + practice | 3–4 |
| **Total** | **27–39 hours** |

Realistic plan: one long weekend (15h) + 3 evenings (12h) + final polish day (4h).

---

## 13. Definition of Done

The project is demo-ready when ALL of the following are true:

- [ ] All three heroes have validated wow discoveries documented in `/data/triggers/hero_X_validation.md`
- [ ] Live mode runs all three heroes successfully in under 90 seconds each, three times in a row
- [ ] Cached mode loads all three heroes instantly from disk
- [ ] Hybrid mode (live for Hero 1, cached for Heroes 2/3) works reliably
- [ ] Every factual claim in every brief has a clickable source URL that opens in a new tab
- [ ] Post-synthesis verification pass is implemented and passes for all three heroes (no orphan URLs in briefs)
- [ ] Pydantic Finding schema enforced on all sub-agent outputs
- [ ] Low-confidence findings are visually distinct in the UI or omitted from the drafted email
- [ ] The drafted outreach email for each hero references at least 2 specific findings, with a "Sources referenced" panel below
- [ ] Hero 3's brief explicitly contradicts the PQL score with cited evidence
- [ ] Streamlit Cloud public URL deployed and tested
- [ ] Recorded video backup exists
- [ ] Demo timed at 4:30–5:00 minutes end-to-end, three times in a row
- [ ] Architecture diagram exists and is in the About page
- [ ] All 8 anticipated questions have a confident 30-second answer ready
- [ ] `README.md` lets a new person clone, install, and run in <10 minutes

---

## 14. Notes for Claude Code

If using Claude Code to implement this plan:

1. **Read `/data/triggers/hero_X_validation.md` first** before building any sub-agent. The validation notes tell you what queries should work.
2. **Build one sub-agent end-to-end before parallelizing.** Don't build all five then try to wire them together.
3. **Test against cached Exa responses where possible** (commit a `tests/fixtures/exa_responses/` directory) to keep iteration fast and avoid burning API quota during dev.
4. **Use LiteLLM from day 1**, not the Gemini SDK directly. Switching providers later is much harder than starting abstracted.
5. **Prompts go in `/prompts/`, not inline in code.** This is non-negotiable — the prompts are the product.
6. **Don't over-engineer the orchestrator.** v1 can be a fixed dispatch to all five sub-agents. The LLM-generated plan is mostly for show in the live UI. Save the dynamic-planning complexity for Phase 2.
7. **Streamlit's session state is fragile across reruns.** Use `st.session_state` carefully and prefer cached data over re-running expensive ops on every interaction.
8. **The `DEMO_MODE` env var is the most important config setting in the project.** Treat it as production-critical.
