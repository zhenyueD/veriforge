# Day 4 Task Board — 2026-05-24

> Hand-off for @ryan. `git pull` to see this. Owner column is a proposal — ping in Discord to swap.
> The headline shift today: the planned "x402 skill-edge attach" chore is upgraded into the **Monetize SDK** — the marketplace's supply/demand flywheel. One line on any skill → it lists itself + earns USDC per call, with a transparent platform fee, all recorded in the verifiable audit chain.

## Decisions locked this session (append to DECISIONS.md)

- **Settlement = mock-but-honest.** Payment tokens are mocked (no wallet/facilitator dependency), but per-skill payout address, fee split, and call counts are all **real and recorded** into the SHA-256 audit chain. Demo labels it `mock-settled, testnet-ready`. No overselling "uncircumventable."
- **Platform fee is in now.** Every settlement records `creator_amount` + `platform_fee` (default 2% / 200 bps). This turns the MiroMind audit chain into a verifiable *revenue ledger* — a second use of the same primitive.
- **Trust model (say this to judges):** the x402 gate lives in the author's own code. We don't *force* payment — we are the rails + discovery + verifiability. An author keeps the one-line SDK because removing it = invisible on the marketplace + unpaid. Same logic as Stripe.

## Full Day 4 task list

### Track A — Monetize SDK (headline; x402 skill-edge) — mostly @duan, UI to @ryan
| ID | Task | Owner |
|---|---|---|
| A1 | `attach_x402` per-skill `pay_to` (drop global-only) | duan |
| A2 | settlement records split: `gross / creator_amount / platform_fee / fee_bps / pay_to / platform_addr` | duan |
| A3 | `sdk/veriforge.py` — self-contained one-file SDK, `monetize(...)` | duan |
| A4 | router `POST /register` + `GET /skills` + `pay_to` in registry — **interface contract, see below** | duan |
| A5 | wire `monetize()` into 9 skills (demo payout addresses) | duan |
| A6 | executor: real skill-side x402 dance (drop mock-emit) | duan |
| A7 | audit chain records revenue split (verifiable revenue ledger) | duan |
| **A8** | **UI: each skill card shows price + "creator earns $X/call" + platform fee** | **ryan** |
| **A9** | **UI: "List your skill" page — shows the one-line SDK snippet + copy button (supply-side acquisition)** | **ryan** |

### Track B — Langfuse observability — @duan
| ID | Task |
|---|---|
| B1 | docker-compose self-host Langfuse (server + postgres) |
| B2 | `@observe()` on router (/route + /run) |
| B3 | `@observe()` on executor + each skill call — **touches executor.py, same as A6; sequenced after A6** |
| B4 | `langfuse.score()` accuracy hook (eval set) |
| B5 | public dashboard screenshot/link → JUDGING.md |

### Track C — GCP Vertex / Cloud Run (sponsor track) — owner TBD (see open question)
| ID | Task |
|---|---|
| C1 | install gcloud SDK + auth + create project — **independent, can start anytime** |
| C2 | router → Cloud Run |
| C3 | claims-intent → Cloud Run (reference skill 1) |
| C4 | claims-damage-vision → Cloud Run (reference skill 2, shows Gemini Vision) |
| C5 | route Gemini calls via Vertex AI endpoint (deeper integration than bare API key) |
| C6 | public URLs → JUDGING.md |

### Track D — Supabase persistence — @duan, blocked on keys
| ID | Task |
|---|---|
| D0 | provide `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` (external input) |
| D1 | audit store → Supabase |
| D2 | activity store → Supabase |

### Track E — fraud-image facade (stretch) — @duan
| ID | Task |
|---|---|
| E1 | `claims-fraud-image` skill wrapping `fraud.py` |
| E2 | add to registry + UI |

## Coupling map

```
A1 ─→ A3 ─→ A5 ─→ A6 ─┐
                       ├─ executor.py (same file) ─ B3   ⚠ sequence A6 before B3
A4 ─→ A3               │
A2 ─→ A7               │
A4 schema ─→ A8 / A9   ⚠ FRONT/BACK CONTRACT — defined below, then parallel-safe
C2..C6 ── depend on ── A+B code stable   (deploy after code settles)
C1 independent · B1 independent · E independent · D blocked on keys
```

**Strongly coupled (sequence / contract):**
- A internal chain `A1→A3→A5→A6` — one owner, do in order.
- `A6 ↔ B3` both edit `executor.py` — A6 first.
- `A4 schema ↔ A8/A9` — front/back contract (below). Define once, then parallel.

**Downstream:** Track C deploy depends on A+B being stable. But **C1 (gcloud setup) is independent — start it anytime.**

**Fully independent / parallelizable:** C1, B1, E1/E2, D (once keys arrive).

## A4 — Registry schema contract (this is what @ryan's UI consumes)

Each skill entry in `marketplace/registry/registry.json` gains `pay_to`:

```json
{
  "id": "claims-intent",
  "name": "Claims Intent Classifier",
  "endpoint": "http://HOST:7001",
  "description": "...",
  "inputs": ["user_message", "has_image", "history"],
  "outputs": ["label", "order_id", "confidence", "..."],
  "price_usdc": 0.01,
  "pay_to": "0xA11CE...",          // NEW — creator payout address
  "tags": ["..."],
  "llm_compat": ["gemini"]
}
```

`GET /skills` returns the list enriched with a computed earnings preview (so the UI doesn't do fee math):

```json
{
  "skills": [
    {
      "id": "claims-intent",
      "name": "Claims Intent Classifier",
      "description": "...",
      "price_usdc": 0.01,
      "pay_to": "0xA11CE...",
      "earnings_preview": {
        "creator_amount_usdc": 0.0098,
        "platform_fee_usdc": 0.0002,
        "fee_bps": 200
      },
      "endpoint": "http://HOST:7001",
      "tags": ["..."]
    }
  ]
}
```

`POST /register` body (self-registration — what the SDK posts, and what a "List your skill" form posts):

```json
{
  "id": "my-skill",
  "name": "My Skill",
  "endpoint": "http://HOST:7099",
  "description": "...",
  "price_usdc": 0.02,
  "pay_to": "0xAUTHOR...",
  "tags": ["..."],
  "llm_compat": ["gemini"]
}
```

Settlement record (in `X-Payment-Settled` header + each audit event — A8 can show this live per call):

```json
{
  "gross": "10000",            // micro-USDC, 6 decimals (0.01 USDC)
  "creator_amount": "9800",
  "platform_fee": "200",
  "fee_bps": 200,
  "pay_to": "0xA11CE...",
  "platform_addr": "0xTREASURY...",
  "asset": "0x036CbD...",
  "network": "base-sepolia",
  "mode": "mock",
  "txid": "0xmock..."
}
```

## Open questions for @duan ⇄ @ryan

1. **Who owns Track C (Vertex)?** Ryan was the suggested owner, but he's on frontend (A8/A9). Options: Ryan picks up C after frontend; or duan takes C. C1 can start independently regardless.
2. Ryan: confirm the A4 schema above works for your card layout, or request fields.

## How to run after pulling
Unchanged: `cp .env.template .env` → fill keys → `docker compose up -d` → `http://localhost:3001`.
