# Observability (Langfuse) — opt-in

VeriForge is instrumented for [Langfuse](https://langfuse.com): every pipeline run is a
trace, the KIMI routing call is a cost-attributed generation, and each skill invocation
is a latency span. **It's opt-in** — with no Langfuse configured, all tracing calls are
no-ops and the stack runs exactly as before (`marketplace/router/obs.py`, same best-effort
contract as the audit + activity emitters).

## What judges see

Open one trace and the tree expands:

```
skill-pipeline                         (root, tags: veriforge)
├── kimi-router            generation  model=moonshot-v1-128k  in/out tokens → $cost
├── skill:claims-intent    span        latency
├── skill:claims-emotion   span        latency
├── skill:claims-damage-vision span    latency
├── skill:claims-compensation  span    latency
└── skill:claims-verify    span        latency
```

Pipeline-level scores on every run: `pipeline_latency_ms`, `skills_ok_ratio`.
Accuracy is scored by the golden-set runner (below) → the dashboard shows the
**accuracy / p95 latency / cost-per-run** numbers to quote on Demo Day.

## Enable in 3 steps

```bash
# 1. Bring up the opt-in self-host stack (web + worker + postgres + clickhouse + redis + minio)
docker compose -f docker-compose.langfuse.yml up -d
open http://localhost:3000          # register admin → create project → copy pk-lf-... / sk-lf-...

# 2. Add langfuse to the router's deps + set keys. In docker-compose.yml, the router
#    command's pip install: add `langfuse`, and add to the router `environment:`
#      LANGFUSE_PUBLIC_KEY: pk-lf-...
#      LANGFUSE_SECRET_KEY: sk-lf-...
#      LANGFUSE_HOST: http://host.docker.internal:3000   # router container → host Langfuse
#    Also add langfuse hosts to the router's NO_PROXY.

# 3. Restart the router
docker compose up -d --force-recreate router
```

Cloud alternative: skip step 1, sign up at <https://cloud.langfuse.com>, set
`LANGFUSE_HOST=https://cloud.langfuse.com` with your keys.

## Golden-set accuracy

`scripts/langfuse_eval.py` POSTs a labelled set of inputs through `/run` and scores
`routing_accuracy` (did KIMI pick the expected skills?) per trace. Run it after the
stack + Langfuse are up:

```bash
python scripts/langfuse_eval.py        # needs the stack running + LANGFUSE_* set on this shell
```

## Notes

- Secrets in `docker-compose.langfuse.yml` are **dev-only** local self-host encryption
  keys — regenerate (`openssl rand -hex 32`) before any non-local deployment.
- The router degrades gracefully: if Langfuse is down or keys are wrong, traces are
  dropped, the pipeline still serves requests.
- PII: pipeline input is truncated to 500 chars in the trace; skill payloads aren't
  auto-captured. Tighten via `obs.update_trace(input=...)` if you add real user data.
