# VeriForge — Demo Day One-Pager

> **The trust & settlement layer for the agent economy — Stripe for AI skills, on MCP.**
> Wrap any function in one line → any agent can discover it, pay per call, and walk away
> with a receipt anyone can verify without trusting us.

---

## The hook (15 seconds)

> *"ClaimsForge failed at the last hackathon — not the tech, the narrative: a vertical
> 6-agent demo nobody could reuse. I dissected it into VeriForge. Now every agent is a
> **skill any agent can call, pay, and verify** — and the verification travels with it."*

---

## What it really is (the positioning)

As agents start **paying each other** for skills across every platform, they need what
humans needed when strangers began trading: a neutral way to **trust, settle, and resolve
disputes** — at machine speed, across vendor boundaries. That layer doesn't exist yet.

VeriForge is building it: **not another skill store competing with OpenAI, but the neutral
layer between the stores** — the Visa/Stripe role. It rides the protocol already winning
for agent–tool connection (**MCP**) and fills the part MCP leaves open: *is this skill
legit, how do I pay it, and what do we show when one side disputes?*

**Why won't the big platforms just build this?** They can build the *tech* in a weekend —
it's not the moat. They won't build the *neutral, cross-vendor* version, because it breaks
their lock-in and helps their rivals (OpenAI won't make GPT skills equally callable and
portable to Claude). Trust infrastructure is run by **non-participants** — Visa isn't a
bank, Experian isn't a lender, Sigstore is a neutral foundation. That seat is the moat, and
no single LLM vendor can sit in it.

---

## Four pillars (each load-bearing, not a logo)

| # | Pillar | What it does | Code |
|---|---|---|---|
| ① | **One-line monetize + cross-LLM calling** | Any FastAPI skill adds `monetize(...)`; registry exports as OpenAI/Anthropic function specs **and** MCP tools — any agent discovers & calls it with one curl | `sdk/veriforge.py`, `marketplace/router/main.py`, `marketplace/mcp/server.py` |
| ② | **Zero-RAG routing + orchestration** | KIMI `moonshot-v1-128k` holds the *whole* registry in-context and plans the skill chain — no vector DB; the executor runs it over HTTP | `/route`, `/run`, `executor.py` |
| ③ | **x402 pay-per-call + revenue split** | Every call carries an `X-Payment` header; creator payout + platform fee computed automatically; UI shows live earnings | `sdk/veriforge.py` (`attach_x402`, `compute_split`) |
| ④ | **Self-verifiable receipts (the moat made concrete)** | Every call yields a portable receipt: ed25519 **Proof-of-Skill** signature (creator-held key — the operator *can't* forge it) + SHA-256 audit-chain link. **You don't trust VeriForge — you verify the math.** | `marketplace/audit/` (`/receipt/:tid`), `scripts/verify_receipt.py` |

Plus the flywheel: every verified call becomes **reputation**, and discovery is ranked by
it (`/skills/search?rank=verified`) — so the marketplace *learns which skill to trust* and
the proven skill becomes more discoverable. Use it → it gets stronger.

---

## Bring your own skill — the one line

```python
from fastapi import FastAPI
from veriforge import monetize

app = FastAPI()
monetize(app, skill_id="my-skill", price_usdc=0.02, pay_to="0xYourWallet")
# → x402 pay-per-call gate · creator + platform fee split · self-registers · signs every output
```

Authors host their own endpoint and hold their own signing key; VeriForge handles
discovery, routing, billing, and verifiable receipts. (Supply-side demo: `examples/external-skill/`.)

---

## 30-second live demo

1. Open `http://localhost:3001` — marketplace of 11 priced skills.
2. **Search** *"detect a faked or damaged product photo"* → flip **Relevance ↔ Trust-ranked**:
   the flashiest match drops, the **proven** skill climbs (▲). Discovery ranks by *proof*, not vibes.
3. Paste **"My ceramic mug arrived cracked. Order ORD-1234."** → KIMI routes a chain;
   live stream shows each call pay a creator+platform split and extend the audit chain.
4. Click **[receipt]** on a step → save the JSON → run `scripts/verify_receipt.py` on a
   machine that's never heard of VeriForge: **✅ valid**. Tamper one field → **❌** — caught by math.

---

## Why it wins

- **Fixes ClaimsForge's death cause:** narrative jumps from "a vertical agent" to "the neutral protocol layer."
- **Every sponsor is structural:** KIMI = zero-RAG registry-in-context router; MiroMind = verification-centric audit + MiroFlow `deep-research` skill; Google Cloud + Gemini = the skills' inference + embedding-ranked discovery, **live on Cloud Run** (Singapore).
- **Honest moat:** the crypto is copyable; the **neutral, cross-vendor seat** is not — and it's the seat the walled gardens are structurally disincentivized to take.

*UCWS Singapore Hackathon 2026 · Skills Track · @duan + @ryan + 2 Claude Codes*
