# Deploying VeriForge to Google Cloud Run

The "Best Use of GCP" track deploy: a real Artifact Registry build pipeline feeding
three Cloud Run services (`router`, `audit`, `activity`), wired together by their live
URLs. This is the public surface that makes the marketplace **discoverable by any agent**
(it's the prerequisite for remote MCP listing — see `marketplace/mcp/PUBLISH.md`).

## What gets deployed

| Service | Image | Public endpoints |
|---|---|---|
| `vf-router` | `marketplace/router/Dockerfile` | `/skills/search`, `/.well-known/*`, `/llms.txt`, `/skills/tools`, `/route`, `/run` |
| `vf-audit` | `marketplace/audit/Dockerfile` | `/verify/{trace_id}`, `/reputation`, `/append` |
| `vf-activity` | `marketplace/activity/Dockerfile` | `/emit`, `/stream/{session_id}` |

> **Scope:** this serves discovery + verification + planning. The full `/run` skill
> pipeline also needs the 9 skill containers + a reachable ClaimsForge; deploying those
> is a follow-up (they `sys.path` import `/claimsforge`). Discovery, `/route`, manifests,
> and `/verify` all work without them.

## Prerequisite — the one thing you must do (it's your identity, can't be scripted)

```bash
gcloud auth login                    # your Google account
gcloud auth application-default login # lets `gcloud builds submit` run
```

You also need a GCP **project with billing enabled** (Cloud Run + Cloud Build + Artifact
Registry have a free tier; a card on file is still required).

## Deploy — one command

```bash
PROJECT_ID=your-gcp-project bash scripts/deploy_cloudrun.sh
```

Optional env (auto-read from `.env` if present):

| Var | Effect if set |
|---|---|
| `REGION` | deploy region (default `asia-southeast1`, Singapore) |
| `GOOGLE_API_KEY` | router uses **Gemini embeddings** for search (else dependency-free lexical fallback) |
| `MOONSHOT_API_KEY` | enables KIMI `/route` planning |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` / `LANGFUSE_HOST` | router emits traces to Langfuse |

The script: enables APIs → ensures an Artifact Registry repo → builds 3 images via Cloud
Build → deploys `audit` + `activity` (one warm instance each, so the in-memory audit chain
survives a demo session) → deploys `router` wired to their URLs → prints all three URLs.

## Verify

```bash
curl "$ROUTER_URL/skills/search?q=faked%20photo&rank=verified"   # ranked, with on-chain trust
curl "$ROUTER_URL/.well-known/ai-plugin.json"                    # agent auto-discovery manifest
curl "$AUDIT_URL/reputation"                                     # cryptographic reputation
```

## After deploy — wire the rest

1. **Web UI** — point `ROUTER_URL` / `AUDIT_URL` / `ACTIVITY_URL` in `web/index.html` at
   the deployed URLs (they default to `localhost`).
2. **MCP listing** — set `veriforgeRouterUrl` in `marketplace/mcp/smithery.yaml`
   `exampleConfig`, and the remote `url` in `marketplace/mcp/server.json`, then follow
   `marketplace/mcp/PUBLISH.md` (Smithery + official MCP Registry).

## Observability (Langfuse)

The router image already includes `langfuse`; `marketplace/router/obs.py` traces the
pipeline (one span per run, KIMI route as a generation, a child span per skill) and is a
no-op until `LANGFUSE_*` is set. Self-host with `docker-compose.langfuse.yml`, or use
Langfuse Cloud, then pass the three `LANGFUSE_*` vars to the deploy script.

## Notes

- **State**: `audit` + `activity` use an in-memory store. `--min-instances=1` keeps it
  alive during a demo; for durability set `SUPABASE_URL` + `SUPABASE_SERVICE_KEY`
  (the stores already support a Supabase backend).
- **Local parity**: the Dockerfiles preserve the repo layout (`/app/marketplace/*`,
  `/app/sdk`) so `sys.path` and `registry_path()` resolve exactly as under
  `docker compose`. Verified: all three boot under Cloud Run's injected `$PORT`.
