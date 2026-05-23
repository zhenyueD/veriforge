# JUDGING.md

**For UCWS Singapore Hackathon 2026 judges. 5-minute end-to-end verification.**

> _Last updated Day 3. Will be finalized Day 5 once Vertex public URL is live._

---

## 60-Second Pitch

VeriForge is the **App Store for verifiable AI skills** — any AI agent can discover, invoke, and pay micro-fees for skills across LLM providers, with every call cryptographically audit-chained.

**Why it matters**: today every team rebuilds vertical agents end-to-end. There's no protocol for cross-LLM skill execution, no marketplace for monetizing skill components, no way for buyers to independently verify what an agent did.

**The story arc**: this repo's 6 ClaimsForge agents are a previous hackathon's project that didn't win. Postmortem revealed the cause wasn't tech — it was narrative ("another vertical agent"). VeriForge dissects them into 6 marketplace skills + 3 horizontal demo skills (translate / summarize / sentiment), routed by KIMI's 256k context (no RAG), paid via x402, audit-chained SHA-256, served on a public verify endpoint.

---

## 5-Step Reproduction Path

```bash
# 1. Clone + env
git clone <this-repo-url>
cd veriforge
cp .env.template .env
# Fill in MOONSHOT_API_KEY (KIMI) + GOOGLE_API_KEY (Gemini)

# 2. Boot 13 services
docker compose up -d
# Wait ~60s for first-time pip install. Subsequent boots are ~30s.

# 3. Open the marketplace
open http://localhost:3001

# 4. Try the example: "📦 e-commerce claim"
# Watch the right panel: KIMI router picks 6 claim skills,
# executor pays $0.02 USDC mock per call,
# audit chain entries fire in realtime.

# 5. Click [verify] next to any trace_id in the activity stream
# → SHA-256 chain independently verified. Try tampering — chain fails.
```

---

## Sponsor Track Verifications

### 🏆 Best Use of KIMI (Moonshot)

**Claim**: VeriForge's router is the only marketplace approach that uses KIMI's 256k context to hold the **entire skill registry in-prompt** — no embeddings, no RAG, no vector index.

**Verify**:
```bash
# Call the router with a claim-flavored input
curl -sX POST http://localhost:8000/route \
  -H 'content-type: application/json' \
  -d '{"user_input":"My ceramic mug arrived cracked. Order ORD-1234."}' \
  | python3 -m json.tool

# Expected:
# - skill_chain: 6 claim skills in correct dep order (intent → damage → emotion → needs → comp → verify)
# - input_tokens: ~1650 (full registry in prompt)
# - latency_ms: 4000-6000

# Now try a horizontal input — proves marketplace isn't vertical-locked
curl -sX POST http://localhost:8000/route \
  -H 'content-type: application/json' \
  -d '{"user_input":"Translate this to Chinese: Hello world"}' \
  | python3 -m json.tool

# Expected: skill_chain: [text-translate] — exactly one skill
```

**Source file**: `marketplace/router/router.py` (~150 LOC, the `ROUTER_PROMPT_TPL` + `_call_kimi`).

---

### 🏆 Best Use of MiroMind (Verification-Centric)

**Claim**: MiroMind's "99% verifiable" reasoning principle is implemented as a public `/verify/:trace_id` endpoint backed by a tamper-evident SHA-256 hash chain. **Anyone — not just the marketplace operator — can independently re-derive every chain hash.**

**Verify**:
```bash
# Run any pipeline first (creates trace_ids):
SESSION=$(curl -sX POST http://localhost:8000/run \
  -H 'content-type: application/json' \
  -d '{"user_input":"My mug arrived cracked. Order ORD-1234."}' \
  | python3 -c 'import json,sys;print(json.load(sys.stdin)["session_id"])')

# Wait ~15s for the pipeline to complete, then:
curl -s "http://localhost:8001/session/$SESSION" | python3 -m json.tool
# → returns 6 audit_entries, each with chain_hash linking to prev

# Pick any trace_id from the entries and verify:
TID=$(curl -s "http://localhost:8001/session/$SESSION" \
  | python3 -c 'import json,sys;print(json.load(sys.stdin)["entries"][0]["trace_id"])')
curl -s "http://localhost:8001/verify/$TID" | python3 -m json.tool

# Expected:
# - chain_verified: true
# - chain_errors: []
# - full_chain: 6 entries showing prev_chain_hash → chain_hash links
```

**Tamper test** (proves the chain isn't theater):
```bash
# Hash chain tamper detection self-test (no docker needed):
cd marketplace/audit && python3 chain.py
# Output:
#   clean chain verify: ok=True errs=[]
#   tampered chain verify: ok=False errs[0]=seq=1 chain_hash tampered (...)
```

**Source files**: `marketplace/audit/chain.py` (SHA-256 primitives), `marketplace/audit/main.py` (FastAPI `/verify` endpoint).

---

### 🏆 Best Use of Google Cloud + Gemini

**Claim**: The 6 ClaimsForge-derived skills use **Gemini 2.5 Flash + Gemini Vision** for actual inference. The `claims-damage-vision` skill is a Gemini Vision wrapper with 96.7% accuracy on a labeled eval set (from the prior ClaimsForge project — `eval/results/` shows the scores).

**Verify**:
```bash
# Each skill container has GOOGLE_API_KEY env passed through
docker exec vf-claims-damage-vision env | grep GOOGLE_API_KEY

# Test claims-damage-vision (text-only mode — Vision call happens when image_b64 provided):
curl -sX POST http://localhost:7004/invoke \
  -H 'content-type: application/json' \
  -d '{"user_message":"My ceramic mug has a 2cm crack along the rim."}' \
  | python3 -m json.tool

# Expected output:
#   damage_type: crack
#   severity: 7-8
#   detected_subject: ceramic mug
#   confidence: 0.5-0.9
#   reasoning: human-readable Gemini explanation
```

**Day 4 (in progress)**: Deploy `router` + `claims-intent` + `claims-damage-vision` to **Vertex AI / Cloud Run**. Public URL will land here.

**Source files**: `skills/claims-damage-vision/handler.py` (wraps `damage_agent.assess` Gemini Vision call).

---

## Architecture (60-second read)

See `CLAUDE.md` for full architecture diagram. TL;DR:

- **9 skill containers** on ports 7001-7013, each a FastAPI microservice with `/invoke` + `/health`
- **Router** (port 8000): calls KIMI 256k → returns skill_chain plan → BackgroundTask executes via HTTP through docker network
- **Audit** (port 8001): SHA-256 hash chain, pluggable InMemory/Supabase backend
- **Activity** (port 8002): event stream, 9 standard kinds, pluggable backend
- **Web** (port 3001): vanilla HTML marketplace UI

13 containers total. Brought up by **one command**: `docker compose up -d`.

## Source Code Map

| What | Path | LOC |
|---|---|---|
| Skill manifests | `skills/<id>/skill.yaml` | ~50/skill |
| Skill handlers | `skills/<id>/handler.py` | ~60-100/skill |
| Skill verify hooks (invariants) | `skills/<id>/verify.py` | ~40-90/skill |
| KIMI router | `marketplace/router/router.py` | 150 |
| Executor (subprocess + HTTP) | `marketplace/router/executor.py` | 250 |
| Audit chain primitives | `marketplace/audit/chain.py` | 180 |
| Audit / Activity stores | `marketplace/{audit,activity}/store.py` | 150 each |
| x402 gateway middleware | `marketplace/gateway/x402.py` | 110 |
| Web UI | `web/index.html` | 500 |
| ClaimsForge (original code, dissected) | `/Users/duan/code/claimsforge/agents/` (mounted ro) | ~3000 |

Total new code for VeriForge: **~2200 LOC** (excluding ClaimsForge reuse and dependencies).

## Built By

@duan + @ryan + 2 Claude Codes · 5 days · UCWS Singapore Hackathon 2026 Skills Track
