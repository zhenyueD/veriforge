#!/usr/bin/env bash
# vendor-skills.sh
#
# Copies 8 hackathon-critical skills + hackathon-strategist agent
# from ~/.claude/skills/ (Duan's personal arsenal of 22) into the project's
# .claude/skills/ directory, so Ryan's Claude Code auto-loads them on clone.
#
# Run once after `git clone`. Re-run if skills are updated upstream.

set -euo pipefail

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
SOURCE_SKILLS="$HOME/.claude/skills"
SOURCE_AGENTS="$HOME/.claude/agents"
DEST_SKILLS="$PROJECT_ROOT/.claude/skills"
DEST_AGENTS="$PROJECT_ROOT/.claude/agents"

# 8 hackathon-critical skills (subset of Duan's 22)
SKILLS=(
  hackathon-sponsor-packager
  prompt-injection-shield
  auditable-decision-chain
  state-machine-agent-context-offload
  langfuse-agent-tracing
  llm-eval-yaml-harness
  hackathon-demo-video-script
  evaluator-friendly-readme
)

# Strategist agent (the brain that schedules the 22)
AGENTS=(
  hackathon-strategist
)

echo "→ Vendoring skills to $DEST_SKILLS"
mkdir -p "$DEST_SKILLS" "$DEST_AGENTS"

missing=()
for skill in "${SKILLS[@]}"; do
  src="$SOURCE_SKILLS/$skill"
  if [ -d "$src" ]; then
    rm -rf "$DEST_SKILLS/$skill"
    cp -R "$src" "$DEST_SKILLS/$skill"
    echo "  ✓ $skill"
  else
    missing+=("$skill")
    echo "  ✗ $skill (missing in $SOURCE_SKILLS)"
  fi
done

for agent in "${AGENTS[@]}"; do
  src="$SOURCE_AGENTS/$agent.md"
  if [ -f "$src" ]; then
    cp "$src" "$DEST_AGENTS/$agent.md"
    echo "  ✓ agent: $agent"
  else
    missing+=("agent:$agent")
    echo "  ✗ agent:$agent (missing in $SOURCE_AGENTS)"
  fi
done

if [ ${#missing[@]} -gt 0 ]; then
  echo
  echo "⚠ ${#missing[@]} item(s) missing. Are you running this on Duan's machine?"
  echo "  Ryan: ask Duan to push his arsenal to a shared repo, then clone to ~/.claude/skills/"
  exit 1
fi

echo
echo "✓ Vendored ${#SKILLS[@]} skills + ${#AGENTS[@]} agent to project"
echo "→ Commit them: git add .claude/ && git commit -m 'chore: vendor hackathon skills'"
echo "→ Ryan: clone repo + restart Claude Code → skills auto-load, zero config"
