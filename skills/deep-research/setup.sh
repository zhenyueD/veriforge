#!/usr/bin/env bash
# deep-research (the MiroMind skill) wraps MiroFlow, which is gitignored (not vendored
# into this repo to keep it lean). This clones MiroFlow into external/MiroFlow so the
# skill image can build. The core 10-skill demo does NOT need this — deep-research is
# the opt-in 11th, premium skill.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DEST="$ROOT/external/MiroFlow"

if [ -d "$DEST/src" ]; then
  echo "MiroFlow already present at $DEST"
else
  echo "Cloning MiroMind MiroFlow into $DEST ..."
  git clone --depth 1 https://github.com/MiroMindAI/MiroFlow "$DEST"
fi

# Pin MiroFlow's MiroThinker config to MiroMind's hosted model. Its shipped config
# hardcodes model_name "DUMMY_MODEL_NAME" (meant for a self-hosted SGLang server);
# we point it at MiroMind's hosted API model instead. base_url + key come from env
# (OAI_MIROTHINKER_BASE_URL / OAI_MIROTHINKER_API_KEY) — see docker-compose.yml.
MODEL="${MIROMIND_MODEL:-mirothinker-1-7-deepresearch}"
CFG="$DEST/config/agent_llm_mirothinker.yaml"
if [ -f "$CFG" ]; then
  python3 - "$CFG" "$MODEL" <<'PY'
import re, sys
path, model = sys.argv[1], sys.argv[2]
s = open(path).read()
s = re.sub(r'model_name:\s*"[^"]*"', f'model_name: "{model}"', s, count=1)
open(path, "w").write(s)
print(f"  patched model_name -> {model} in {path}")
PY
fi

echo
echo "Next (LLM = MiroMind MiroThinker, one key):"
echo "  1. Set MIROMIND_API (+ optional SERPER_API_KEY / JINA_API_KEY for tools) in .env"
echo "  2. docker compose build deep-research"
echo "  3. docker compose --profile deep-research up -d deep-research"
echo "  4. curl -sX POST localhost:7008/invoke -H 'content-type: application/json' \\"
echo "       -H 'X-Payment: mock:demo' -d '{\"task\":\"Who is the PM of Singapore?\"}'"
