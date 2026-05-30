#!/usr/bin/env bash
# VeriForge discovery demo — semantic skill search + verifiable-reputation ranking.
# Prereq: router on :8000 and audit on :8001 are up
#   (docker compose up -d, or run uvicorn in marketplace/router and marketplace/audit).
# Usage: bash scripts/demo_discovery.sh
set -euo pipefail

ROUTER="${ROUTER_URL:-http://localhost:8000}"
AUDIT="${AUDIT_URL:-http://localhost:8001}"

hr(){ printf '\n\033[36m════ %s ════\033[0m\n' "$1"; }

# ── health ──
curl -sf -m 5 "$ROUTER/health" >/dev/null || { echo "✗ router down at $ROUTER (start it first)"; exit 1; }
curl -sf -m 5 "$AUDIT/health"  >/dev/null || { echo "✗ audit down at $AUDIT (start it first)";  exit 1; }
echo "✓ router & audit up"

show(){ python3 -c '
import sys, json
d = json.load(sys.stdin)
print("  method=%s rank=%s latency=%sms" % (d["method"], d["rank"], d["latency_ms"]))
for r in d["results"]:
    extra = ""
    if d["rank"] == "verified":
        rep = r["reputation"]
        extra = "   [rel=%.2f trust=%.2f  verified %s/%s]" % (
            r["relevance"], r["trust"], rep.get("verified_ok", 0), rep.get("calls", 0))
    print("   %.3f  %-22s %s%s" % (r["score"], r["id"], r["description"][:40], extra))
'; }

search(){ curl -s -G "$ROUTER/skills/search" --data-urlencode "q=$1" -d "top_k=${2:-3}" -d "rank=${3:-relevance}"; }

hr "① Semantic search — describe the TASK, never name a skill"
echo '  q: "check whether a product photo has been faked or edited"'
search "check whether a product photo has been faked or edited" | show
echo '  q: "translate text into another language"'
search "translate text into another language" | show
echo '  q: "how upset is the customer in this message"'
search "how upset is the customer in this message" | show

hr "② Seed a verifiable track record into the audit chain"
sha(){ printf '%s' "$1" | sha256sum | cut -c1-64; }
seed(){ # skill n_ok n_fail
  for k in $(seq 1 "$2"); do s="rep-$1-ok-$k"; curl -s "$AUDIT/append" -H 'content-type: application/json' \
    -d "{\"session_id\":\"$s\",\"seq\":0,\"skill_id\":\"$1\",\"trace_id\":\"t-$s\",\"input_hash\":\"$(sha "$s")\",\"output_hash\":\"$(sha "o$s")\",\"verify_passed\":true}" >/dev/null; done
  for k in $(seq 1 "$3"); do s="rep-$1-no-$k"; curl -s "$AUDIT/append" -H 'content-type: application/json' \
    -d "{\"session_id\":\"$s\",\"seq\":0,\"skill_id\":\"$1\",\"trace_id\":\"t-$s\",\"input_hash\":\"$(sha "$s")\",\"output_hash\":\"$(sha "o$s")\",\"verify_passed\":false}" >/dev/null; done
}
seed claims-damage-vision 12 0   # strong: 12/12 verified
seed claims-fraud-image    1 2   # weak:   1/3 verified
curl -s "$AUDIT/reputation" | python3 -c '
import sys, json
for k, v in json.load(sys.stdin)["skills"].items():
    print("   %-22s verified %s/%s  pass_rate=%s" % (k, v["verified_ok"], v["calls"], v["pass_rate"]))'

hr "③ Same query, ranking FLIPS when you weigh on-chain verified reputation"
Q="analyze a damaged product photo from a customer claim"
echo "  rank=relevance (pure semantic):"
search "$Q" 3 relevance | show
echo "  rank=verified  (semantic + verifiable trust):"
search "$Q" 3 verified | show

hr "④ A result is a ready-to-call tool spec (search → call, one hop)"
search "detect image fraud" 1 relevance | python3 -c '
import sys, json
print(json.dumps(json.load(sys.stdin)["results"][0]["tool"], indent=2)[:520])'

hr "⑤ Zero-config self-describing manifests (any agent framework auto-discovers)"
for p in "/.well-known/ai-plugin.json" "/.well-known/agent.json" "/llms.txt"; do
  code=$(curl -s -o /dev/null -w '%{http_code}' "$ROUTER$p"); echo "   $code  $ROUTER$p"
done
echo
echo "Done. Try your own:  curl -sG '$ROUTER/skills/search' --data-urlencode 'q=YOUR TASK' -d rank=verified | python3 -m json.tool"
