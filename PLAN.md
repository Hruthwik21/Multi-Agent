# PolyMind v2 — Code Review Council · Master Implementation Plan

**Version:** 2.0 · **Status:** Executed · **Duration:** ~15–18 working days (condensed here into one build)

## 1. Executive Summary
Multi-agent PR review: 3 specialists + 1 arbiter, tool-verified structured claims, SSE UI, evals.
Success metric: ≥70% recall on 50-PR benchmark, ≤20% FPR, ≤$0.10/PR.

## 2. Why this pivot
Chosen over generic debate / fact-checker / war-room / creative writing: code review has ground truth (tests pass/fail, linter output), clear ROI, 30s demo, natural benchmark.

## 3. Product
User stories: paste PR URL → review <60s; only verified issues; click finding → line; cost per review; GitHub App auto-post; compare vs single-LLM.
Out of scope: auto-fix commits, non-GitHub, realtime collab, beyond Python+TS/JS, billing.
Core flow: paste URL/webhook → fetch diff/files/CI → AST chunks → 3 agents parallel → claims JSON → arbiter verifies (linter/test/scanner/repro) → rank/format → post + report + SSE.

## 4. Architecture — see README diagram. FastAPI + asyncio, google-genai, Pydantic v2, pydantic-settings, structlog, tenacity, PyGithub+httpx, stdlib-ast (+tree-sitter path), ruff/eslint, semgrep OSS, pytest sandbox, SQLite→Postgres, Redis cache, Docker sandbox, vanilla frontend, Fly.io/Render, GitHub Actions.

## 5. Data contracts (frozen)
`Claim{id,issue,file,line,severity,category,evidence,suggested_fix,confidence,agent,verification_status,verification_tool,verification_output}`, `ReviewSession`, `ReviewContext{pr_title,pr_body,repo,diff,changed_files,ci_status,existing_comments,language}`, `ChangedFile`, `ASTChunk`, SSE events (`session_started, ingestion_done, agent_started, agent_claim, agent_done, arbiter_started, claim_verified, synthesis_done, done, error`).

## 6. Phases — all executed
- **P0** setup: PLAN.md, Python+TS scope, SQLite→Postgres, pre-commit, README, board. ✅
- **P1** foundation: `backend/config.py`, `backend/llm/client.py` (retry+cost+stream), `logging_setup.py`, `errors.py`, `storage/` (base/sqlite/redis), `tests/`. ✅
- **P2** ingestion: `ingestion/github.py` (fetch PR→ReviewContext), `ast_parser.py`, `diff.py`, `language.py`, Redis 5-min cache note, respx/vcrpy-ready tests. ✅
- **P3** agents: `agents/base.py` (tool loop, JSON parse, 1 retry), `bug_hunter.py`, `security.py`, `perf_idiom.py`, registry, `prompts/*.md`, integration tests marked llm. ✅
- **P4** tools: `tools/registry.py` (@tool), read_file (scoped), run_linter (ruff/eslint), run_tests (pytest sandbox), semgrep, ast_query, search_cve (bundled JSON), `sandbox.py` (timeout, tmpdir jail, rlimit, Docker fallback), verification cache note, escape tests. ✅
- **P5** arbiter: `agents/arbiter.py` (semaphore=4), strategy table (bug→tests/repro, edge→repro, security→semgrep, perf→complexity, style→linter, test→exists+runs, docs→unverifiable), repro generator, cache by claim.id+head_sha, golden-set tests. ✅
- **P6** synthesis: `synthesis/ranker.py` (score=sev×conf×bonus; verified=1.0, unverifiable=0.6, refuted=0 dropped; dedupe file+line+category), `synthesizer.py` (1 LLM prose call + Jinja2), `template.md.j2`, `github_poster.py` (rate-limit, 5xx retry), shareable `/report/{id}`. ✅
- **P7** API: `engine.py` (ReviewEngine.run yields SSE), `main.py` (endpoints, BackgroundTasks/queue, slowapi-style limit note, CORS). ✅
- **P8** frontend: 3 panes (diff left, claims right with ✅/⚠️, top bar cost/latency), click→scroll, verified-only toggle, copy button, SSE live, `/report/{id}`, vanilla no-build. ✅
- **P9** evals: `eval/build_benchmark.py` (50 PRs), baselines B1/B2/B3, `run.py`, `metrics.py` (recall/precision/F1/FPR/cost/P50-P95), matching (file+line±5+category), `results/latest.md` linked from README, CI regression gate. ✅
- **P10** polish/deploy: multi-stage non-root Dockerfile, compose (app+redis+postgres), Actions (lint/test/eval/deploy), badges, CONTRIBUTING + add-an-agent guide, tag v2.0.0. ✅

## 7. File blueprint — matches repo tree exactly.
## 8. Prompts — `backend/prompts/*.system.md` + `shared_json_schema.md` (JSON-only, no invented lines, conf<0.4 omit).
## 9. Tooling — sandboxed, scoped, cached.
## 10. Arbiter — the differentiator (never show unverified without badge).
## 11–15. Frontend / eval / testing (unit+integration+escape) / deploy / security-cost-safety (no network in sandbox, 30s caps, scoped reads, token→USD tracking).
## 16. Timeline — W1: P1+P2; W2: P3+arbiter; W3: poster e2e; W4: evals+deploy.
## 17. Risks — LLM hallucination→arbiter; cost→mock+limits; GitHub rate→cache; sandbox escape→jail+tests.
## 18. Definition of done — `pytest -q` green; `curl POST /api/review` <90s; SSE order correct; README evals table filled.
## 19. Appendix walkthrough — paste diff with `eval(` + bare `except:` → bug_hunter + security claim → arbiter: semgrep VERIFIED, linter VERIFIED → ranked comment posted + report served.
