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

echo
echo "Next:"
echo "  1. Set OPENAI_API_KEY + SERPER_API_KEY + JINA_API_KEY in .env"
echo "  2. docker compose build deep-research"
echo "  3. docker compose up -d deep-research"
echo "  4. curl -sX POST localhost:7008/invoke -H 'content-type: application/json' \\"
echo "       -H 'X-Payment: mock:demo' -d '{\"task\":\"Who is the PM of Singapore?\"}'"
