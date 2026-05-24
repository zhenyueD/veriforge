#!/usr/bin/env bash
# Demo: a third-party skill self-registers onto a running VeriForge marketplace.
#
# Prereq: the VeriForge stack is up (docker compose up -d) → router on :8000.
# This boots an EXTERNAL skill (this dir is outside skills/) that copied veriforge.py
# and added one monetize() line. On startup it self-registers; then it shows up in
# GET /skills and is gated by x402 — with zero changes to the marketplace repo.
set -euo pipefail

ROUTER="${VERIFORGE_REGISTRY_URL:-http://localhost:8000}"
PORT=7099
PY="${PY:-/Users/duan/code/claimsforge/.venv/bin/python}"
cd "$(dirname "$0")"

echo "1) skills before:"
curl -s "$ROUTER/skills" | "$PY" -c "import sys,json; print('   ', len(json.load(sys.stdin)['skills']), 'skills')"

echo "2) booting external skill on :$PORT (self-registers to $ROUTER) ..."
VERIFORGE_REGISTRY_URL="$ROUTER" VF_ENDPOINT="http://localhost:$PORT" \
  "$PY" -m uvicorn skill:app --port "$PORT" --log-level warning &
UVPID=$!
trap 'kill $UVPID 2>/dev/null || true' EXIT

for i in $(seq 1 20); do
  sleep 1
  curl -sf "http://localhost:$PORT/health" >/dev/null 2>&1 && break
done

echo "3) skills after (should include community-readability):"
curl -s "$ROUTER/skills" | "$PY" -c "
import sys,json
sk=json.load(sys.stdin)['skills']
print('   ', len(sk), 'skills')
m=[s for s in sk if s['id']=='community-readability']
print('   community-readability listed:', bool(m), '| earnings:', m[0]['earnings_preview'] if m else None)
"

echo "4) x402 gate on the external skill (no payment → 402):"
curl -s -o /dev/null -w "   HTTP %{http_code}\n" -X POST "http://localhost:$PORT/invoke" \
  -H 'content-type: application/json' -d '{"text":"The cat sat on the mat. It was a sunny day."}'

echo "5) paid call (with X-Payment → 200):"
curl -s -X POST "http://localhost:$PORT/invoke" -H 'content-type: application/json' \
  -H 'X-Payment: mock:demo-token-123' \
  -d '{"text":"The cat sat on the mat. It was a sunny day."}'
echo
echo "done. (the marketplace repo was never modified — this is the supply side.)"
