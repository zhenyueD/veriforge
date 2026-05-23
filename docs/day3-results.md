# Day 3 Results — 2026-05-23

## Architecture Delivered

```
              ┌─────────────────┐
              │   Web UI :3001   │
              │  (vanilla HTML)  │
              └────────┬─────────┘
                       │ poll
        ┌──────────────┼──────────────┐
        ↓              ↓              ↓
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ router :8000 │ │ activity :8002│ │ audit :8001  │
│ /run /route  │ │ /emit /session│ │ /append      │
└──────┬───────┘ │  /stream     │ │ /verify/:tid │
       │         └──────┬───────┘ └──────┬───────┘
       │ background     │                │
       │ task           │                │
       ↓                ↓                ↓
┌─────────────────────────────────────────────────┐
│            executor (in router)                  │
│  - emits events (session_started, skill_*)       │
│  - mock x402 payment dance per skill             │
│  - appends SHA-256 chain entries per skill       │
└────────┬─────────────────────────────────────────┘
         │ HTTP /invoke with X-Payment: mock:...
         ↓
┌──────────────────────────────────────────────────┐
│  9 skill containers (claims-* + horizontal-*)    │
│  each: handler.py + verify.py + Dockerfile       │
└──────────────────────────────────────────────────┘
```

## Components Built

### 1. Audit Chain — `marketplace/audit/`
- `chain.py` — SHA-256 hash chain primitives; `compute_chain_hash`, `make_entry`, `verify_chain`
- `store.py` — Pluggable: `InMemoryStore` (dev) / `SupabaseStore` (prod, table DDL in docstring)
- `main.py` — FastAPI: `POST /append`, `GET /session/:id`, `GET /verify/:trace_id`
- **Self-test PASS**: clean chain verifies; tampered entry detected by hash mismatch

### 2. Activity Stream — `marketplace/activity/`
- `store.py` — Same pluggable pattern. In-memory backend supports long-poll via `stream_session`.
- `main.py` — `POST /emit`, `GET /session/:id`, `GET /stream/:id?since=ts` (long-poll for UI)
- Event kinds: `session_started`, `route_planned`, `skill_started`, `skill_payment_settled`, `skill_completed`, `audit_appended`, `skill_failed`, `session_completed`

### 3. x402 Gateway — `marketplace/gateway/`
- `x402.py` — `attach_x402(app, price_usdc, paths)` FastAPI middleware
- Two modes via `VERIFORGE_X402_MODE`:
  - `mock` (default): any non-empty `X-Payment` header passes
  - `real`: verifies EIP-3009 signature against Base Sepolia facilitator
- **Current integration**: executor emits `X-Payment: mock:...` per skill call AND emits `skill_payment_settled` activity event. The middleware is wired but not yet attached to skill containers — Day 4 will attach to demonstrate the full 402 dance at the gateway level.

### 4. Web UI — `web/index.html`
- Vanilla HTML + JS, no framework, no build step
- Polling `/stream/:id` for live updates
- Three panels: customer input + KIMI plan + audit verify
- Click [verify] next to any trace_id to run `/verify/:trace_id`
- Safe DOM construction (no innerHTML for user-supplied data) — passes XSS hook

### 5. Executor Integration — `marketplace/router/executor.py`
- New `_run_pipeline` background task in `router/main.py`
- `POST /run` returns session_id immediately; pipeline runs in background
- Every skill call: emits 3 events (`started` / `payment_settled` / `completed` or `failed`) + appends audit chain entry
- Mock x402 payment generated via `_mock_x_payment(skill_id)`

## Docker Compose Updates

13 services total: 6 claims + 3 horizontal + router + audit + activity + web.

**Key env additions for `router`** (lesson learned):
- `NO_PROXY=audit,activity,router,claims-*,text-*,sentiment-analyze,localhost`
  - Docker Desktop auto-injects `HTTP_PROXY=host.docker.internal:7890`
  - Without `NO_PROXY` covering docker service names, intra-network calls return 502
- `ENDPOINT_HOST=docker` → executor remaps `HOST` placeholder in `registry.json` to service names

## What Day 3 Still Owes Day 4

1. **Attach `attach_x402()` middleware to skill containers** so the 402 dance happens at the skill edge, not just executor-side. Needs `/marketplace/gateway` mounted into skill containers + PYTHONPATH update.
2. **Switch audit & activity stores to Supabase** when user provides `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` (code already supports — just set env)
3. **Real x402** via `VERIFORGE_X402_MODE=real` once user runs `test_x402.py` and confirms Base Sepolia wallet works

## Pitfalls Hit (and Fixed)

| Pitfall | Fix |
|---|---|
| Pydantic `from __future__ import annotations` + spec loader → fwd-ref fails | Subprocess isolation per skill in dev tests |
| ClaimsForge agent returns `str` not `Enum` for some optional fields | `hasattr(x, "value") else x` defensive cast |
| Docker `localhost` ≠ host's `localhost` | `ENDPOINT_HOST=docker` + service-name URLs |
| Docker Desktop auto HTTP_PROXY leaks into containers | Explicit `NO_PROXY` covering all internal service names |
| Port 3000 already in use on host | Web UI moved to 3001 |

## How Judges Reproduce

```bash
cd ~/Desktop/UCWS-VeriForge
docker compose up -d
open http://localhost:3001    # UI

# Or pure-CLI:
curl -sX POST http://localhost:8000/run \
  -H 'content-type: application/json' \
  -d '{"user_input":"My mug arrived cracked. Order ORD-1234."}'
# → returns {session_id: "..."}; then:
curl -s http://localhost:8002/session/SESSION_ID    # full activity log
curl -s http://localhost:8001/session/SESSION_ID    # full audit chain
curl -s http://localhost:8001/verify/TRACE_ID       # independent chain verification
```
