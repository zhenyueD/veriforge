# Day 2 Results — 2026-05-23

## Deliverables

| Artifact | Path | Status |
|---|---|---|
| Skill registry (9 skills) | `marketplace/registry/registry.json` | ✅ |
| KIMI router service | `marketplace/router/router.py` + `main.py` | ✅ |
| Executor (subprocess + HTTP) | `marketplace/router/executor.py` | ✅ |
| 3 horizontal skills (summarize / translate / sentiment) | `skills/text-* + sentiment-*` | ✅ |
| Live E2E test | `executor.py` `__main__` | ✅ PASS |

## Live Test Evidence

### Routing accuracy

| Input | Routed chain | Latency | Tokens (in/out) |
|---|---|---|---|
| `"My mug arrived cracked, order ORD-1234"` | 6 claim skills, correct dep order | 5.8s | 1646/280 |
| `"Translate this paragraph to Chinese"` | `[text-translate]` only | 2.4s | 1649/87 |

### End-to-end execution (claim input)

```
claims-intent          1.8s   label=claim_text_only · order=ORD-1234 · conf=1.0
claims-damage-vision   2.1s   crack · severity=8 · "ceramic mug" · bbox
claims-emotion         2.5s   LOW · score=3.0 · "inconvenienced"
claims-needs           ~2.5s  replacement · retention_risk=0.2
claims-compensation    ~3.0s  offer + escalate_reasons
claims-verify          ~2.5s  verdict
```

Total E2E (router + 6 skills): ~20s. Acceptable for live demo with activity stream UI.

## Engineering Decisions Made Today

1. **Registry-in-context** (not RAG): full slim registry (~5KB) goes into KIMI prompt. Saves embedding pipeline complexity. Sponsor story: only KIMI's 128k window makes this viable.
2. **`moonshot-v1-128k`** picked over K2.6 (reasoning model): non-reasoning model gives 4-6s latency vs 30-50s. Same sponsor (Moonshot).
3. **Subprocess executor** for dev mode: avoids `handler.py` module name collisions across 9 skills. HTTP mode reserved for Day 3+.
4. **Rule-based input wiring** in `build_input(skill_id, ...)`: explicit per-skill mapping. Cleaner than generic remapper for the 6 known claim skills; horizontal skills just take `text`.
5. **Audit fields on every skill response** already in place (Day 1): `trace_id`, `input_hash`, `output_hash`, `elapsed_ms`. Day 3 audit chain just chains these.

## Carryover to Day 3

- ✅ Audit hash fields already emitted by every skill — no skill-side changes needed
- ⚠️ User still needs to supply Supabase URL + keys
- ⚠️ User still needs to run `scripts/test_x402.py` locally with testnet wallet
- ⚠️ Need to decide: web UI framework (raw HTML + Supabase JS SDK vs React)

## Risks Watched (PROJECT.md §10)

| Risk | Status |
|---|---|
| KIMI 256k registry routing too slow | ✅ Resolved — `moonshot-v1-128k` is 4-6s, well within budget |
| x402 testnet flaky | ⏳ Not yet tested |
| Vertex AI deploy fails | ⏳ Day 4 |
| ClaimsForge dissection breaks behavior | ✅ Day 1 verified — 6/6 live PASS |
| README unclear in 30s pitch | ⏳ Day 5 |
