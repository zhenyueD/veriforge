#!/usr/bin/env bash
# Seed REAL verifiable reputation by running the pipeline on a batch of varied claims.
# Every call is genuine: KIMI routes it, skills run (Gemini), each invocation is x402-paid,
# ed25519-signed, and SHA-256 audit-chained — so the reputation that ranks discovery is
# earned, not fabricated. This just bootstraps volume so the "proof beats relevance"
# ranking is visible in a demo instead of everyone sitting at trust=0.
#
# Usage:  bash scripts/seed_reputation.sh [ROUNDS]   (default 6)
set -euo pipefail
ROUTER="${ROUTER_URL:-http://localhost:8000}"
AUDIT="${AUDIT_URL:-http://localhost:8001}"
ROUNDS="${1:-6}"

# Varied e-commerce damage claims — all route through the claims chain (incl.
# claims-damage-vision), so those skills build a track record while skills nobody
# uses (fraud-image, the horizontal skills) stay unproven. That contrast IS the demo.
CLAIMS=(
  "My ceramic mug arrived cracked. Order ORD-1234."
  "The laptop screen was shattered in the box. Order ORD-2087."
  "Received a dented can of paint, lid bent. Order ORD-3310."
  "My headphones arrived with a snapped headband. Order ORD-4471."
  "The vase came in pieces, clearly broken in transit. Order ORD-5562."
  "Phone case melted/warped on arrival. Order ORD-6643."
  "Coffee table leg was split down the middle. Order ORD-7724."
  "Glass picture frame smashed, shards everywhere. Order ORD-8815."
)

echo "▶ seeding ${ROUNDS} rounds against ${ROUTER}"
n=0
for ((i=0; i<ROUNDS; i++)); do
  msg="${CLAIMS[$(( i % ${#CLAIMS[@]} ))]}"
  sid=$(curl -s --max-time 30 -X POST "${ROUTER}/run" \
        -H 'content-type: application/json' \
        -d "{\"user_input\": $(python3 -c "import json,sys;print(json.dumps(sys.argv[1]))" "$msg")}" \
        | python3 -c "import sys,json;print(json.load(sys.stdin).get('session_id','?'))")
  echo "  round $((i+1)): session $sid — \"${msg:0:42}…\""
  n=$((n+1))
  sleep 6   # stagger so we don't slam Gemini with ROUNDS*6 concurrent calls
done

echo "▶ waiting for pipelines to finish + audit to settle…"
sleep 20
echo ""
echo "▶ reputation now (calls per skill):"
curl -s --max-time 5 "${AUDIT}/reputation" | python3 -c "
import sys,json
rep=json.load(sys.stdin).get('skills',{})
for sid,r in sorted(rep.items(), key=lambda kv:-kv[1]['calls']):
    print(f\"  {sid:<22} calls={r['calls']:<3} verified_ok={r['verified_ok']:<3} pass={r.get('pass_rate')}\")
print('(skills not listed have 0 calls — unproven)')
"
