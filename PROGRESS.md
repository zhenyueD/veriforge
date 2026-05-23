# PROGRESS · 2026-05-23 Session Complete

> Snapshot of where the project stands at end of today's session.
> Next session resumes Day 4. Read this + HANDOFF.md to pick up.

## TL;DR

5 day-equivalents done in one session. 13 docker containers running locally. 2 public GitHub repos pushed. 4 collaboration docs in place. Ready for Day 4 (Vertex AI deploy + Langfuse).

## Done (in chronological order)

| Day | What | Outcome |
|---|---|---|
| 0.5 | KIMI router spike — picked `moonshot-v1-128k` over K2.6 | 4-6s latency, 3/3 routing accuracy |
| 1 | Dissected 6 ClaimsForge agents into FastAPI skill microservices | 6/6 live PASS via real Gemini |
| 2 | KIMI registry-in-context router + executor + 3 horizontal skills | 9-skill registry, dual-mode executor (subprocess + HTTP) |
| 2.5 | docker compose 10 services up | All healthy in ~60s |
| 3 | SHA-256 audit chain + activity stream + x402 mock + marketplace UI | 13 containers, tamper-detection verified, `/verify/:trace_id` public endpoint live |
| 3.5 | Git init + 4 collab docs + 2 public GitHub repos + Ryan onboarding pack | <https://github.com/zhenyueD/veriforge> |

## Stack Currently Live (13 containers)

| Service | Port | What |
|---|---|---|
| claims-intent | 7001 | Intent classifier (Gemini 2.5 Flash) |
| claims-emotion | 7002 | Emotion grader (0-10, CRITICAL escalation) |
| claims-needs | 7003 | Need discovery + retention risk |
| claims-damage-vision | 7004 | Gemini Vision damage assessment |
| claims-compensation | 7005 | Policy-RAG offer proposer |
| claims-verify | 7006 | Hard-cap + escalation verifier |
| text-summarize | 7011 | Horizontal demo skill |
| text-translate | 7012 | Horizontal demo skill |
| sentiment-analyze | 7013 | Horizontal demo skill |
| router | 8000 | KIMI router + `/run` background executor |
| audit | 8001 | SHA-256 chain + `/verify/:trace_id` |
| activity | 8002 | Event stream + `/stream/:session` long-poll |
| web | 3001 | Vanilla HTML marketplace UI |

Before resting: `docker compose down` to free ~500MB-1GB RAM. Image cache persists. Next boot ~30s.

## Open Tasks (sorted by Day, picked up next session)

- **Day 4 main thread** (task #9):
  - Vertex AI / Cloud Run deploy of router + 2 reference skills → **suggested owner: @ryan** (Google Cloud sponsor track)
  - Langfuse integration (accuracy/latency/cost dashboard public URL)
  - skill-edge x402 attach (move from executor-side mock to skill-side `attach_x402()` middleware)
  - Supabase store wiring (audit + activity persistence) once user provides `SUPABASE_URL` + `SUPABASE_SERVICE_KEY`
- **Day 4 stretch** (task #11): claims-fraud-image facade skill
- **Day 5** (task #10):
  - 3-min demo video per script in `PROJECT.md` appendix
  - README polish + JUDGING.md final pass
  - Cold-email MiroMind team (Redwood City + Singapore HQ) — host sponsor outreach
  - Submit on UCWS platform

## Architectural Decisions Locked (see DECISIONS.md)

1. Project name: **VeriForge** (story arc from ClaimsForge)
2. Dissect-not-pivot: turn ClaimsForge into marketplace skills, do NOT vertical-pivot
3. Router model: `moonshot-v1-128k` not K2.6 (K2 is reasoning, 30-50s)
4. Skill packaging: thin wrapper via sys.path + docker volume mount
5. Executor: dual subprocess (dev) + HTTP (prod)
6. Storage: InMemory (default) + Supabase (env-driven swap)
7. x402: mock default, real on Day 4
8. NO_PROXY must enumerate all docker service names (Docker Desktop auto-injects host proxy)
9. Three P0 sponsors are load-bearing: KIMI + MiroMind + Google Cloud
10. UI redesigned marketplace-first (vs. earlier hacker-terminal UI)

## Recurring Pitfalls (don't trip on them tomorrow)

- Docker Desktop injects `HTTP_PROXY` → must explicitly set NO_PROXY for all internal service names
- `from __future__ import annotations` + `spec_from_file_location` + Pydantic 2 = forward-ref hell. Use subprocess for isolation in dev tests.
- ClaimsForge agents sometimes return `str` not `Enum` for optional fields → handlers use `hasattr(x, "value") else x`
- Skill `handler.py` files share the name "handler" — Python module cache will collide if you sys.path import multiple in one process

## Repos

- VeriForge: <https://github.com/zhenyueD/veriforge> (76 files · main · public)
- ClaimsForge: <https://github.com/zhenyueD/claimsforge> (mount source · public)

## Next Session Resume Command

> "Read PROGRESS.md + HANDOFF.md + SPRINT.md, then start Day 4 — Vertex deploy + Langfuse + skill-edge x402 attach."
