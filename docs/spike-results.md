# Day 0.5 Spike Results — 2026-05-23

## KIMI Router Feasibility

### Verdict: ✅ PASS — use `moonshot-v1-128k` for production router

### Data

| Model | Endpoint | avg latency | max latency | accuracy | output tokens |
|---|---|---|---|---|---|
| KIMI K2.6 | SiliconFlow | 26.39s | 39.97s | 2/3 | 674-1579 |
| KIMI K2.5 | SiliconFlow | 28.10s | 51.50s | 2/3 | 505-3191 |
| DeepSeek-V4-Flash | SiliconFlow | 1.35s | 2.17s | 2/3 | 79-214 |
| **moonshot-v1-128k** | **Moonshot official** | **4.37s** | **6.10s** | **3/3** | **64-250** |

### Key insight

KIMI K2.x are **reasoning models** with high output tokens (chain-of-thought) → 30-50s for router task. Not the right tool.

`moonshot-v1-128k` is the older non-reasoning KIMI series with **128k context** — plenty for 50-skill registry (~10k tokens), and the underlying model is still Moonshot/KIMI, so the sponsor story holds.

### Production config

```python
KIMI_BASE  = "https://api.moonshot.ai/v1"
KIMI_MODEL = "moonshot-v1-128k"
```

Cost estimate: ~$0.0025 per route call at 3k input tokens. Negligible.

## x402 Spike

Pending — user running `scripts/test_x402.py` locally.

## ClaimsForge Recon

- Repo: `/Users/duan/code/claimsforge/`
- Domain: **e-commerce after-sales damage claims** (NOT insurance — earlier doc error)
- 6 main agents (intent, emotion, needs, damage, compensation, verify) + fraud detector
- Each agent: pure function (`classify`/`assess`) + pipeline interface (`run(ctx)`)
- Shared deps: `gemini_client.py`, `schemas.py` (Pydantic models)
- Tech: FastAPI + Gemini 2.5 Flash + Gemini Vision + RAG over policy DSL
