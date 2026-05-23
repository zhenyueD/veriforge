# team-setup — Hackathon Collaboration Kit

> For Ryan: **start with [TUTORIAL.md](./TUTORIAL.md)** (~15 min read).

A complete kit for human + human + dual Claude Code collaboration during a 5-day solo-ish hackathon. Copy these files into your hackathon repo and you're ready in 15 minutes.

## What's in here

| File | Purpose | Read order |
|---|---|---|
| [TUTORIAL.md](./TUTORIAL.md) | Full walkthrough — how we work together | **1st** (Ryan) |
| [SETUP.md](./SETUP.md) | 5-step setup checklist | 2nd |
| [CLAUDE.md.template](./CLAUDE.md.template) | Project root — shared brain for both Claude Codes | Fill in when project starts |
| [SPRINT.md.template](./SPRINT.md.template) | Today's tasks + ownership | Update daily |
| [DECISIONS.md.template](./DECISIONS.md.template) | Append-only decision log | Append per decision |
| [HANDOFF.md.template](./HANDOFF.md.template) | End-of-day baton pass | Write each evening |
| [vendor-skills.sh](./vendor-skills.sh) | One-shot: copy 8 hackathon skills + strategist agent into project | Run once after `git clone` |
| [discord-translate-bot/](./discord-translate-bot/) | Discord bot: auto CN ↔ EN translation | Deploy once before hackathon starts |
| [.github/workflows/](./.github/workflows/) | CI + auto-merge on green | Copy into your hackathon repo |

## How to use this kit for a new hackathon

```bash
# 1. Start your hackathon repo
gh repo create your-hackathon --public --clone
cd your-hackathon

# 2. Copy this kit's contents in
cp -r ~/code/team-setup/{TUTORIAL,SETUP,vendor-skills}.* .
cp ~/code/team-setup/CLAUDE.md.template ./CLAUDE.md
cp ~/code/team-setup/SPRINT.md.template ./SPRINT.md
cp ~/code/team-setup/DECISIONS.md.template ./DECISIONS.md
cp ~/code/team-setup/HANDOFF.md.template ./HANDOFF.md
cp -r ~/code/team-setup/.github .

# 3. Vendor 8 hackathon skills into the project
bash vendor-skills.sh

# 4. Fill in CLAUDE.md (hackathon name, theme, sponsors, etc)
$EDITOR CLAUDE.md

# 5. Commit + push + share repo URL with teammate
git add -A
git commit -m "chore: hackathon team setup + skill vendoring"
git push -u origin main

# 6. Deploy the Discord translate bot (one-time)
cd discord-translate-bot
# follow ./README.md for Discord bot creation + Railway deploy
```

## What this kit assumes

- **Both teammates use Claude Code** as their primary AI assistant
- **Both have Node 20+ / gh CLI / git** installed
- **One Discord server** with 5 channels (`#general` / `#code-sync` / `#daily` / `#sponsor-help` / `#voice`)
- **GitHub repo** with Vercel preview deploys
- **Anthropic API key** (for the translate bot, ~$0.60 / 5-day hackathon at Haiku 4.5 prices)

## What this kit does NOT include (intentionally)

- The hackathon project code itself
- Hackathon-specific sponsor integrations (use `/hackathon-sponsor-packager` skill instead)
- Documentation generation (use `/document-release` or `/evaluator-friendly-readme` skill)
- Eval / observability setup (use `/langfuse-agent-tracing` + `/llm-eval-yaml-harness` skills)

## Why this design

After studying 17 hackathon winning projects + running 3 autonomous research missions, the patterns are clear: winners synchronize asynchronously via markdown, vendor everything into the repo so teammates clone-and-go, and treat AI as a third teammate not a tool. This kit codifies all of that.

See [TUTORIAL.md § 2](./TUTORIAL.md#2-the-mental-model) for the philosophy.

## Iterating

This kit will evolve. If you hit friction during a real hackathon, send a PR back. Each hackathon teaches us something — that goes into v2.
