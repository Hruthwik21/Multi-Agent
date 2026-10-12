# PolyMind v2 🧠 — Code Review Council

> A council of specialized AI agents reviews your GitHub PR, verifies each finding with real tools (linters, tests, scanners), and posts a single prioritized comment with only the issues that survived verification.

![CI](https://img.shields.io/badge/CI-passing-green) ![Python](https://img.shields.io/badge/Python-3.11%2B-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.111-teal)

## One-liner
Paste a PR URL (or raw diff) → 3 specialist agents (bug-hunter, security, perf/idiom) emit structured **Claims (JSON)** in parallel → **Arbiter** verifies each claim with executed tool evidence → ranked markdown comment (+ shareable report).

## Quickstart (offline-friendly, no keys required)
```bash
python -m venv venv && venv\Scripts\activate   # or source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn backend.main:app --port 8000
# open http://127.0.0.1:8000
```
Mock LLM mode runs automatically when `GEMINI_API_KEY` is empty, so the full loop works end-to-end without network.

With a key:
```
GEMINI_API_KEY=...  GITHUB_TOKEN=...  # in .env
```

## API
- `POST /api/review` `{pr_url, diff?, post_to_github?}` → `{session_id, stream_url}`
- `GET /api/stream/{id}` — SSE: `session_started → ingestion_done → agent_started/claim/done (×3) → arbiter_started → claim_verified → synthesis_done → done`
- `GET /api/sessions/{id}`, `GET /api/report/{id}`, `POST /webhook/github`, `GET /health`

## Architecture
```
PR URL/diff → IngestionService (diff, AST, CI) → AgentPool ×3 (tools) → Arbiter (verify)
→ Synthesizer (rank+dedupe+comment) → GitHub poster + report + SSE
```
| Component | Owns | Does NOT own |
|---|---|---|
| IngestionService | PR fetch, AST, CI | LLM calls |
| AgentPool | parallel claims | verification |
| ArbiterService | tool verification | severity |
| Synthesizer | rank/dedupe/format | verification |

## Evals
See `eval/results/latest.md`. Run:
```bash
python -m eval.build_benchmark
python -m eval.run
pytest -q
```
Target: ≥70% recall, ≤20% FPR, ≤$0.10/PR.

## Repo layout
`backend/` (config, llm, ingestion, agents, tools, synthesis, storage, prompts, engine, main) · `frontend/` (vanilla + SSE) · `eval/` · `tests/` · `PLAN.md`
