# Tutorial — How We Work Together

> For Ryan. Read top to bottom once (~15 min). Skim back as reference later.

---

## 1. The 30-Second Context

You and Duan are doing a 5-day hackathon. You're both solo devs who happen to be on the same team. You're in Singapore (GMT+8), Duan is in mainland China (GMT+8). **Same timezone — huge advantage.**

Duan's English is OK but slower than yours. You will use **Discord with an auto-translate bot** so you can both write in your native language and the other side reads it instantly.

You both use **Claude Code** (the CLI tool from Anthropic). This is the secret weapon. We don't just collaborate human-to-human — we collaborate **human + human + 2 Claude Codes** that talk to each other via shared markdown files in the repo.

---

## 2. The Mental Model

Most teams sync via Slack messages and meetings. We sync via **markdown files in the repo**:

```
Your Claude Code  ──┐
                    ├──>  CLAUDE.md (architecture, conventions)
Duan's Claude Code ─┘     SPRINT.md (today's tasks)
                          DECISIONS.md (why we chose X)
                          HANDOFF.md (end-of-day baton pass)
```

When you start work in the morning, you `git pull` and your Claude Code reads `HANDOFF.md` + `SPRINT.md`. It knows everything Duan did yesterday + what's blocked + what's next. **No meeting required.**

When you finish at night, you ask your Claude Code to write `HANDOFF.md` for Duan. He wakes up, pulls, and his Claude Code knows your state.

This is the core insight: **two Claude Codes are async-collaborating teammates, with us humans driving them.** Markdown is the protocol.

---

## 3. First-Day Setup (do this once)

Detailed checklist is in **[SETUP.md](./SETUP.md)**. Quick version:

1. Install Claude Code + Node 20+ + gh CLI
2. `git clone <repo-url>` (Duan will send)
3. `cd <repo> && bash team-setup/vendor-skills.sh` — auto-loads 8 hackathon skills into project
4. Open Claude Code in the repo, type `Read CLAUDE.md`
5. Join Discord server (link from Duan)
6. Done. You're working.

The vendored skills give your Claude Code these superpowers automatically:

| Skill | What it does |
|---|---|
| `/hackathon-strategist` | The brain. Type this to get a 5-day battle plan + sponsor priority + demo path |
| `/auditable-decision-chain` | Add SHA-256 hash chain audit + signal floor to any LLM decision |
| `/prompt-injection-shield` | 3-layer LLM input safety (regex + classifier) |
| `/langfuse-agent-tracing` | 5-min Langfuse setup, show "accuracy / latency / cost" to judges |
| `/llm-eval-yaml-harness` | promptfoo yaml runs accuracy matrix |
| `/state-machine-agent-context-offload` | Multi-agent without chat history overflow |
| `/hackathon-sponsor-packager` | Each sponsor → independent subproduct (Docker + DEPLOY.md) |
| `/hackathon-demo-video-script` | 90s demo video with per-segment TTS, no time drift |
| `/evaluator-friendly-readme` | README with "judge 5-step path" + JUDGING.md |

Just type the slash command in Claude Code, it'll load and walk you through.

---

## 4. A Day in the Life (realistic walkthrough)

### Morning (you start work, ~9 AM SGT)

```bash
cd hackathon-repo
git pull
```

Your Claude Code session:

> **You**: Read HANDOFF.md and SPRINT.md, then summarize what Duan did yesterday and what I should do today.

> **Claude Code**: Duan finished the Vultr sponsor integration (PR #12, merged). Worker is now deployed at `worker.team.dev`. He started on the Speechmatics integration in branch `duan/speechmatics-init` but is blocked on a websocket connection issue. The handoff suggests you take over `frontend/pipeline.tsx` — adding the React Flow canvas. SPRINT.md priorities: 1) finish pipeline.tsx (you), 2) unblock speechmatics (he'll handle when he's back), 3) start JUDGING.md draft.

You post in Discord `#daily`:

> `🟢 Starting work. Taking pipeline.tsx today. ETA done by 6pm SGT.`

Bot auto-translates to Chinese, Duan sees it when he wakes up.

### Mid-day (Duan comes online, ~11 AM)

Voice channel call for 10 min. Discuss the websocket issue. He'll handle it after lunch.

You commit progress to `ryan/pipeline-canvas`:

```bash
git add . && git commit -m "feat: add React Flow base layout to pipeline.tsx"
git push -u origin ryan/pipeline-canvas
gh pr create --title "Frontend: pipeline canvas with React Flow" --label auto-merge
```

The `auto-merge` label means: if CI passes, GitHub auto-squash-merges. Vercel auto-deploys a preview URL. Duan sees the URL in `#code-sync`.

### When you decide something architectural

You're about to choose between Recharts vs Tremor for analytics dashboard. Don't just pick — make it visible:

In Claude Code:
> Add an entry to DECISIONS.md: I'm choosing Recharts over Tremor because we need custom node shapes for the agent pipeline, and Tremor's primitives don't support that. Owner: me. Date: today.

Claude Code appends the entry. Commit + push. Duan never has to ask "why Recharts not Tremor?" — it's recorded.

### Evening (you wrap, ~7 PM SGT)

```bash
git status   # make sure no uncommitted work
```

In Claude Code:
> Look at today's git log on my branches + my changes to SPRINT.md + DECISIONS.md. Write a HANDOFF.md from me to Duan. Include: what I finished, what's in progress with exact stop point, anything urgent, ideas I want to try tomorrow, and what context his Claude Code needs to know.

Review the generated HANDOFF.md. Edit anything wrong. Commit + push.

Record a 60-second screen recording of what you built today, drop in `#daily`:

> `🔴 Done for the day. Demo: <60s screen recording>. Off until 9am tomorrow.`

Bot translates. Duan watches on his morning.

---

## 5. Tool Deep Dives

### Discord (5 channels + auto-translate bot)

| Channel | Use |
|---|---|
| `#general` | Status signals: `🟢 deep work` / `🟡 available` / `🔴 sleeping` / `⚪ off` |
| `#code-sync` | Auto PR notifications, code questions, links to preview URLs |
| `#daily` | Morning "I'm starting" + Evening 60s demo + Handoff signal |
| `#sponsor-help` | "Stuck on Vultr API auth, anyone seen this?" type questions |
| `#voice` | Pair programming voice + screen share. No agenda needed, just join |

**Translate bot behavior**: any message in Chinese gets an English reply, any message in English gets a Chinese reply. As a reply in thread, not a new message — so it doesn't spam. Messages under 5 chars / commands / code blocks / URLs are skipped.

If you type purely in English, you'll see your message + a `🇨🇳` reply with the Chinese. Don't get confused — that's for Duan, not for you.

### Git Flow (branches + auto-merge)

```
main (always demo-ready, deployed to production)
 │
 ├── ryan/pipeline-canvas      ← your branch
 │     ↓ PR with 'auto-merge' label
 │     ↓ CI runs (lint, typecheck, test)
 │     ↓ Vercel deploys preview
 │     ↓ green CI → auto-squash-merge → main
 │
 └── duan/speechmatics-init    ← his branch
```

**Rules**:
- Never push directly to `main`
- Branch naming: `<your-name>/<feature>` (e.g. `ryan/frontend-pipeline`)
- Commit prefixes: `feat:` / `fix:` / `chore:` / `wip:`
- PRs need the `auto-merge` label to auto-merge (we don't require reviews)
- If CI fails, the PR sits in your court until green
- Preview URL appears in PR conversation, share in `#code-sync` if interesting

**Why no review approval?** 2-person hackathon time budget. We trust each other to write decent code; CI catches the obvious. If you want Duan's eyes on something tricky, tag him in `#code-sync` with the PR link.

### The 4 Markdown Files

| File | Who writes | When | Why |
|---|---|---|---|
| `CLAUDE.md` | Both | When architecture / convention changes | Permanent shared brain. Both Claude Codes auto-read on session start. |
| `SPRINT.md` | Both | Every day | Today's tasks + owners + blockers |
| `DECISIONS.md` | Both | Every decision | Append-only. Don't re-argue settled things. |
| `HANDOFF.md` | Person going offline | End of day | Hand the baton to the person coming online |

**Pro tip**: Don't write these by hand. Ask your Claude Code:

```
Read SPRINT.md + DECISIONS.md + my git log today. Update SPRINT.md with what I finished and what's still in progress.
```

Or:

```
Append a DECISIONS.md entry: I picked X over Y because Z.
```

Claude Code handles the format. You just stamp.

### Claude Code Best Practices for This Team

1. **Always open Claude Code in the repo root**, not subdirectories. It needs `CLAUDE.md` access.
2. **Use the slash commands** for the vendored skills. Don't reinvent.
3. **Before coding a new feature**, do `/hackathon-strategist` first — it'll suggest which skills to compose.
4. **For PR descriptions**, use `/commit` or just ask Claude Code to write the PR description from your branch diff.
5. **For debugging**, use `/investigate` — it forces root-cause analysis instead of guessing.

---

## 6. Common Scenarios (FAQ)

### "Duan and I edited the same file overnight. Merge conflict."

```bash
git pull --rebase origin main
# resolve conflicts in your editor
git rebase --continue
git push --force-with-lease   # safe force, won't clobber if remote changed
```

Or ask Claude Code:
> I have a merge conflict in `pipeline.tsx`. Show me the conflicting hunks and propose a resolution that preserves both intents.

### "I want to take over Duan's branch because he's offline"

```bash
git fetch origin
git checkout duan/speechmatics-init
git checkout -b ryan/speechmatics-continued
# do your work, commit, PR
```

Add an entry to `DECISIONS.md`: "Took over Duan's speechmatics work because the websocket fix is unblocking my pipeline."

### "I'm stuck on a sponsor's API"

Post in `#sponsor-help` with: error message + what you tried + relevant code link. Don't just say "stuck" — give Duan (or his Claude Code) enough to help.

If you've spent > 1 hour on it, **stop**. Switch tasks. Mark `🔴 Blocked` in `SPRINT.md`. Sponsor APIs are rarely worth grinding solo for > 1 hour.

### "I want to add a new sponsor mid-hackathon"

Don't do this without discussion. Open `DECISIONS.md` first:

```
## YYYY-MM-DD — Proposal: add Vercel sponsor track

Reason: <why>
Cost: <hours>
Owner if accepted: @ryan
```

Tag Duan in `#general`. Wait for him before starting. Adding sponsors mid-hackathon is the #1 way to miss the deadline.

### "Duan wrote a Chinese comment in code"

Reply in `#code-sync` with the file:line. He'll either translate or you can ask your Claude Code to translate inline. Going forward we should agree: **all code comments in English** (we don't have an auto-translator inside the editor).

### "Demo video time"

Day 4 evening at the latest. Use `/hackathon-demo-video-script`. The skill walks you through the 90s structure. Duan should be the one recording (he has the per-segment TTS workflow). You review the draft + write the README + JUDGING.md (use `/evaluator-friendly-readme`).

### "I disagree with a decision in DECISIONS.md"

Don't edit historical entries — they're append-only. Add a new entry:

```
## YYYY-MM-DD HH:MM — Reversing previous decision on <X>

Earlier we decided <Y> because <Z>. New evidence: <W>.
New decision: <V>. Owner: @ryan.
```

The history is preserved. New choice is visible.

---

## 7. Anti-Patterns (don't do these)

| Don't | Why |
|---|---|
| Push directly to `main` | Breaks the deployed app |
| Skip the `auto-merge` label | PR will sit forever; no one is checking |
| Edit `HANDOFF.md` from yesterday | It's a snapshot of that moment; just overwrite for today |
| Paste API keys in Discord | Use GitHub Secrets + `.env.example` |
| Commit `.env` | `.gitignore` it. Always. |
| Make architecture decisions silently | Other person + their Claude Code will be confused |
| Demo video > 90 seconds | Judges check out at 60s |
| Bury sponsor integration in main app | Each sponsor needs its own `sponsor-X/` directory (use the skill) |
| Add `git submodule` without `--init` | If you commit a submodule reference but the contents aren't there, judges see empty dirs |
| Mock data without README label | If `WarmLeads.tsx` shows fake data, README must say "leads UI is mocked, real integration in roadmap" |

---

## 8. Cheat Sheet

```bash
# Morning ritual
git pull
# (Claude Code) "Read HANDOFF.md + SPRINT.md, what should I do today?"

# Start a feature
git checkout -b ryan/feature-name

# During work
git add . && git commit -m "feat: <what>"
git push -u origin ryan/feature-name
gh pr create --title "<title>" --label auto-merge

# Made a decision
# (Claude Code) "Append DECISIONS.md: chose X over Y because Z"

# Stuck
# Post in #sponsor-help with error + what you tried

# Evening ritual
git status   # make sure clean
# (Claude Code) "Write HANDOFF.md from me to Duan from today's work"
git add HANDOFF.md && git commit -m "chore: handoff" && git push
# Record 60s demo, drop in #daily
# Status: 🔴 sleeping
```

## 9. Where to Ask for Help

1. **Duan directly** — Discord `#general` or voice channel
2. **Your Claude Code** — for code, architecture, skill usage
3. **`/hackathon-strategist`** — for "what should I do next" / sponsor priority
4. **`/investigate`** — for "why is this broken"

## Last thing

This setup is over-engineered for 2 people. That's intentional. The overhead is < 30 min total over 5 days, and the payoff is: **we never block each other**, every decision is auditable, and both Claude Codes have full context. Trust the system; if you find friction, ping Duan to iterate the protocol.

Welcome to the team. Let's win this thing.

— Generated for Ryan by Duan's Claude Code, 2026-05-23
