# VeriForge

> Verifiable, on-chain Skill Marketplace where any AI agent can discover, purchase, and execute composable skills — with cryptographic audit trails and MiroFlow-orchestrated verification.

**Status**: Day 0.5 (Feasibility Spike) · See [PROJECT.md](./PROJECT.md) for full plan.

## Quick Start (Judges' 5-Step Path)

1. `git clone` this repo
2. `cp .env.template .env` and fill in `MOONSHOT_API_KEY`, `GOOGLE_API_KEY`, `BASE_SEPOLIA_RPC`
3. `docker compose up` — starts router + 10 skills + Supabase emulator
4. Open `http://localhost:3000` — see the live activity stream UI
5. Try input: *"I got into a car accident yesterday"* — watch KIMI route to claim skills, x402 collect $0.02, audit hash chain

For full sponsor verification commands, see [JUDGING.md](./JUDGING.md).

## Architecture

See [PROJECT.md §5](./PROJECT.md#5-architecture).

## Built by

1 developer + Claude Code · 5 days · UCWS Singapore Hackathon 2026 · Skills Track
