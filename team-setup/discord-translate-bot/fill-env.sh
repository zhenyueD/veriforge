#!/usr/bin/env bash
# Interactive .env filler — values read silently, never in shell history.
set -euo pipefail

ENV_FILE="$(dirname "$0")/.env"

read -rsp "Paste DISCORD_BOT_TOKEN (input hidden): " DISCORD_BOT_TOKEN
echo
read -rsp "Paste ANTHROPIC_API_KEY (input hidden): " ANTHROPIC_API_KEY
echo

if [ -z "$DISCORD_BOT_TOKEN" ] || [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "ERROR: both values required, nothing written"
  exit 1
fi

cat > "$ENV_FILE" <<EOF
DISCORD_BOT_TOKEN=$DISCORD_BOT_TOKEN
ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY
MODEL=claude-haiku-4-5-20251001
MIN_LENGTH=5
EOF

chmod 600 "$ENV_FILE"
echo "✓ wrote $ENV_FILE"
awk -F= '/^DISCORD_BOT_TOKEN|^ANTHROPIC_API_KEY/{print $1 ": " length($2) " chars"}' "$ENV_FILE"
