# PQL Intelligence Agent

Streamlit app that researches any company + champion and produces a cited intelligence brief using Gemini 3.1 (Vertex AI) with Exa grounding.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Fill in GCP_PROJECT_ID, EXA_API_KEY in .env
gcloud auth application-default login
streamlit run streamlit_app.py
```

## Key env vars

| Var | Description |
|-----|-------------|
| `GCP_PROJECT_ID` | Your Google Cloud project ID |
| `GCP_LOCATION` | Vertex AI region (default: us-central1) |
| `EXA_API_KEY` | Exa API key |
| `GEMINI_MODEL` | Model name (default: gemini-3.1) |
| `DEMO_MODE` | `live` or `cached` |
| `GOOGLE_APPLICATION_CREDENTIALS_JSON` | Full service account JSON (Railway/cloud deploy) |

## Architecture

```
streamlit_app.py
    └── orchestrator.run_all_agents()        # asyncio.gather() → 5 parallel agents
            ├── company_intel.run()
            ├── champion_intel.run()
            ├── buying_committee.run()
            ├── competitive_signals.run()
            └── hiring_growth.run()
                    └── vertex_client.call_gemini_with_exa()  # Vertex AI + exaAiSearch
    └── synthesis.synthesize()               # Combines findings → AccountBrief
    └── cache.save() / cache.load()          # data/cached/{hash}/brief.json
```

Each agent call → Vertex AI REST API → Gemini reasons with Exa grounding → returns text + groundingMetadata (source URLs).

## Prompt iteration

Prompts live in `/prompts/`. Change prompt files, re-run to iterate. No code changes needed for prompt tuning.

## Caching

Results cached in `data/cached/{sha256(company+champion)[:16]}/brief.json`. Select "Cached" mode in UI to load without running agents.

## Railway deployment

1. Push to GitHub
2. Create Railway service, connect repo
3. Set env vars in Railway dashboard (including `GOOGLE_APPLICATION_CREDENTIALS_JSON`)
4. Railway uses `Procfile` to start: `streamlit run streamlit_app.py --server.port=$PORT --server.address=0.0.0.0`
