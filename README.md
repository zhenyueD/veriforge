# VeriForge

**The App Store for verifiable AI skills.** Any FastAPI skill adds one line and gets pay-per-call billing (creator wallet + transparent platform fee), self-lists on the marketplace, and has every call cryptographically audit-chained. Routed by KIMI 256k (no RAG), paid via x402, verifiable by anyone.

> **For judges & AI graders:** start with **[`JUDGING.md`](./JUDGING.md)** — sponsor scoring hooks, copy-paste checks, and code map. Supply-side demo: [`examples/external-skill/`](./examples/external-skill/). Observability: [`LANGFUSE.md`](./LANGFUSE.md).

_UCWS Singapore Hackathon 2026 · Skills Track · sponsors: KIMI (Moonshot) · MiroMind · Google Cloud + Gemini_

## The one line that lists & monetizes any skill

```python
from veriforge import monetize

app = FastAPI()
monetize(app, skill_id="my-skill", price_usdc=0.02, pay_to="0xYourWallet")
# → x402 pay-per-call gate · creator payout + platform fee split · self-registers to the marketplace
```

## 5-step judge path

1. `git clone <repo> && cd veriforge && cp .env.template .env` — fill `MOONSHOT_API_KEY` (KIMI) + `GOOGLE_API_KEY` (Gemini)
2. `docker compose up -d` — boots 14 services (10 skills + router + audit + activity + web; ~60s first run)
3. Open `http://localhost:3001`
4. Try **"My ceramic mug arrived cracked. Order ORD-1234."** — watch KIMI route 6 claim skills, each call pay a creator+platform split, and the audit chain extend live
5. Copy any `trace_id` into the **[verify]** panel — the SHA-256 chain re-verifies. See **[`JUDGING.md`](./JUDGING.md)** for one-liner sponsor checks.

## Sponsor tracks

- **KIMI (Moonshot)** — `moonshot-v1-128k` holds the whole skill registry in-context to plan chains with no RAG. → [`marketplace/router/router.py`](./marketplace/router/router.py)
- **MiroMind** — the `deep-research` skill runs MiroMind's **MiroFlow** agent, and its step trace is SHA-256 hash-chained into a verifiable trace; the marketplace audit chain gives a public `/verify/:trace_id`. → [`skills/deep-research/`](./skills/deep-research/), [`marketplace/audit/`](./marketplace/audit/)
- **Google Cloud + Gemini** — Gemini 2.5 Flash + Vision power the 10 skills' inference. → [`skills/claims-damage-vision/handler.py`](./skills/claims-damage-vision/handler.py)

Per-sponsor verify commands: **[`JUDGING.md`](./JUDGING.md)**.

## What's inside

- **11 monetized skills** (`skills/`) — 7 ClaimsForge-derived (intent, emotion, needs, damage-vision, compensation, verify, fraud-image) + 3 horizontal (summarize, translate, sentiment) + `deep-research` (runs MiroMind MiroFlow; opt-in, see [`skills/deep-research/setup.sh`](./skills/deep-research/setup.sh))
- **Monetize SDK** (`sdk/veriforge.py`) — the single file an author copies; x402 gate + fee split + self-registration
- **Router + executor** (`marketplace/router/`) — KIMI planning, per-call payment, opt-in Langfuse tracing
- **Audit + activity** (`marketplace/audit/`, `marketplace/activity/`) — SHA-256 chain (+ revenue ledger) and live event stream

Full plan: [`PROJECT.md`](./PROJECT.md) · daily decisions: [`DECISIONS.md`](./DECISIONS.md) · Day 4 board: [`DAY4-TASKS.md`](./DAY4-TASKS.md).

## Built by

@duan + @ryan + 2 Claude Codes · UCWS Singapore Hackathon 2026 · Skills Track
