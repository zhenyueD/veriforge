#!/usr/bin/env bash
# Deploy VeriForge's public surface (router + audit + activity) to Google Cloud Run.
# This is the "Best Use of GCP" track deploy: a real Artifact Registry build pipeline
# feeding three Cloud Run services, wired together by their live URLs.
#
# The ONLY thing you must do first (cannot be scripted — it's your identity):
#   gcloud auth login
#   gcloud auth application-default login    # for `gcloud builds submit`
#
# Then:
#   PROJECT_ID=your-gcp-project bash scripts/deploy_cloudrun.sh
#
# Optional env (auto-detected from .env if present):
#   REGION=asia-southeast1          # Singapore, default
#   GOOGLE_API_KEY=...              # enables Gemini-embedding semantic search (else lexical)
#   MOONSHOT_API_KEY=...            # enables KIMI /route planning
#   LANGFUSE_PUBLIC_KEY=... LANGFUSE_SECRET_KEY=... LANGFUSE_HOST=...   # enables tracing
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Pull optional keys from .env without exporting noise.
if [[ -f .env ]]; then set -a; source .env; set +a; fi

REGION="${REGION:-asia-southeast1}"
REPO="${REPO:-veriforge}"
: "${PROJECT_ID:?Set PROJECT_ID=your-gcp-project (and run 'gcloud auth login' first)}"

AR_HOST="${REGION}-docker.pkg.dev"
IMG_BASE="${AR_HOST}/${PROJECT_ID}/${REPO}"

echo "▶ project=${PROJECT_ID} region=${REGION} repo=${REPO}"
gcloud config set project "$PROJECT_ID" >/dev/null

echo "▶ enabling APIs (run, cloudbuild, artifactregistry)…"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com >/dev/null

echo "▶ ensuring Artifact Registry repo '${REPO}'…"
gcloud artifacts repositories describe "$REPO" --location "$REGION" >/dev/null 2>&1 || \
  gcloud artifacts repositories create "$REPO" --repository-format=docker \
    --location "$REGION" --description "VeriForge backend images"

echo "▶ building 3 images via Cloud Build…"
gcloud builds submit --config cloudbuild.yaml \
  --substitutions="_REGION=${REGION},_REPO=${REPO}" .

deploy() {  # name image port [extra args…]
  local name="$1" image="$2" port="$3"; shift 3
  gcloud run deploy "$name" \
    --image "$image" --region "$REGION" \
    --allow-unauthenticated --port "$port" "$@" >/dev/null
  gcloud run services describe "$name" --region "$REGION" --format='value(status.url)'
}

# audit + activity hold demo state in memory → keep one warm instance so the
# audit chain survives across a demo session (swap to Supabase for real persistence).
echo "▶ deploying audit…"
AUDIT_URL="$(deploy vf-audit "${IMG_BASE}/audit:latest" 8001 \
  --min-instances=1 --set-env-vars=VERIFORGE_DEMO=1)"
echo "  audit → $AUDIT_URL"

echo "▶ deploying activity…"
ACTIVITY_URL="$(deploy vf-activity "${IMG_BASE}/activity:latest" 8002 \
  --min-instances=1 --timeout=60)"
echo "  activity → $ACTIVITY_URL"

# Router env: wire the sibling URLs + optional keys.
ROUTER_ENV="AUDIT_URL=${AUDIT_URL},ACTIVITY_URL=${ACTIVITY_URL},VERIFORGE_X402_MODE=mock"
[[ -n "${GOOGLE_API_KEY:-}"   ]] && ROUTER_ENV+=",GOOGLE_API_KEY=${GOOGLE_API_KEY}"
[[ -n "${MOONSHOT_API_KEY:-}" ]] && ROUTER_ENV+=",MOONSHOT_API_KEY=${MOONSHOT_API_KEY}"
[[ -n "${LANGFUSE_PUBLIC_KEY:-}" ]] && ROUTER_ENV+=",LANGFUSE_PUBLIC_KEY=${LANGFUSE_PUBLIC_KEY},LANGFUSE_SECRET_KEY=${LANGFUSE_SECRET_KEY:-},LANGFUSE_HOST=${LANGFUSE_HOST:-}"

echo "▶ deploying router…"
ROUTER_URL="$(deploy vf-router "${IMG_BASE}/router:latest" 8000 \
  --set-env-vars="$ROUTER_ENV")"

# Second pass: tell the router its own public URL so /.well-known + /llms.txt
# advertise absolute, reachable links.
gcloud run services update vf-router --region "$REGION" \
  --update-env-vars="VERIFORGE_PUBLIC_URL=${ROUTER_URL}" >/dev/null
echo "  router → $ROUTER_URL"

cat <<EOF

✅ Deployed.
   router   : ${ROUTER_URL}
   audit    : ${AUDIT_URL}
   activity : ${ACTIVITY_URL}

Verify:
   curl "${ROUTER_URL}/skills/search?q=faked%20photo&rank=verified"
   curl "${ROUTER_URL}/.well-known/ai-plugin.json"
   curl "${AUDIT_URL}/reputation"

Next (publish — see marketplace/mcp/PUBLISH.md):
   • set veriforgeRouterUrl=${ROUTER_URL} in marketplace/mcp/smithery.yaml exampleConfig
   • set the remote url in marketplace/mcp/server.json to a deployed MCP endpoint
   • point the web UI's ROUTER/AUDIT/ACTIVITY_URL at the URLs above
EOF
