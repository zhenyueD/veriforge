# VeriForge — Demo Day One-Pager

> **The App Store for verifiable AI skills.**
> Wrap any function in one line → it becomes discoverable, callable by *any* LLM,
> billed per-call in USDC, and cryptographically audited on every invocation.

---

## The hook (15 seconds)

> *"ClaimsForge failed at the last hackathon. The reason wasn't the tech — it was the
> narrative: a vertical 6-agent insurance demo nobody could reuse. I dissected it into
> VeriForge. Now every one of those agents is a **skill anyone can call, pay for, and verify** —
> the vertical demo became a horizontal protocol."*

---

## Four pillars (each is load-bearing, not a logo)

| # | Pillar | What it does | Code |
|---|---|---|---|
| ① | **Marketplace + cross-LLM calling** | 11 priced skills; registry exports as OpenAI/Anthropic function specs *and* MCP tools — any agent discovers & calls them with one curl | `marketplace/router/main.py` (`/skills`, `/skills/tools`), `marketplace/mcp/server.py` |
| ② | **Zero-RAG routing + orchestration** | KIMI `moonshot-v1-128k` holds the *whole* registry in-context and picks the skill chain — no vector DB. Then the executor runs the chain over HTTP. | `/route`, `/run`, `executor.py` |
| ③ | **x402 pay-per-call + revenue split** | Every call carries an `X-Payment` header; creator payout + platform fee computed automatically. UI shows live earnings. | `sdk/veriforge.py` (`attach_x402`, `compute_split`) |
| ④ | **Cryptographic audit (two layers)** | (a) SHA-256 hash chain — tamper one entry, every later link breaks. (b) ed25519 **Proof-of-Skill** signatures — each skill signs its own output with a key published in the registry, so the operator can't swap results. Public `/verify/:trace_id`. | `marketplace/audit/chain.py`, `marketplace/router/reverify.py` |

---

## Bring your own skill — the one line

```python
from fastapi import FastAPI
from veriforge import monetize

app = FastAPI()
monetize(app, skill_id="my-skill", price_usdc=0.02, pay_to="0xYourWallet")
# → x402 pay-per-call gate · creator + platform fee split · self-registers to the marketplace
```

One line gates the paid path with x402, splits revenue, and self-registers the skill via
`POST /register`. Authors host their own endpoint; VeriForge handles discovery, routing,
billing, and audit. (Supply-side demo: `examples/external-skill/`.)

---

## 30-second live demo

1. Open `http://localhost:3001` — marketplace of 11 skills, each with a USDC price.
2. Paste: **"My ceramic mug arrived cracked. Order ORD-1234."**
3. KIMI routes a chain of claim skills → live activity stream shows each call + USDC split.
4. Copy any `trace_id` → **/verify** panel re-verifies the SHA-256 chain green in seconds.
5. Tamper one entry (demo fault injector) → the same chain goes **red** and names the broken link.

---

## Why it wins

- **Directly fixes ClaimsForge's death cause:** narrative jumps from "a vertical agent" to "a reusable protocol."
- **Every sponsor is structural, not decorative:** KIMI = the router's brain; MiroMind = the verification-centric audit + MiroFlow `deep-research` skill; Google Gemini 2.5 Flash = the skills' inference.
- **Trust-minimized by construction:** anyone can independently verify any result — no need to trust the marketplace operator.

*UCWS Singapore Hackathon 2026 · Skills Track · @duan + @ryan + 2 Claude Codes*
