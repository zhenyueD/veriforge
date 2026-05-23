# CLAUDE.md

**Project single source of truth — both Claude Codes auto-read this on session start.**

## 项目定位

- **名称**: VeriForge — Verifiable, on-chain Skill Marketplace
- **Hackathon**: UCWS Singapore Hackathon 2026 (EPIC Connector + Canlah AI)
- **赛道**: **Skills Track** (cash prize $10k + Singapore Demo Day on 2026-06-13)
- **主题**: "NO RULES. JUST CREATE."
- **截止**: 2026-06-13 (Singapore Demo Day, 21 days from start)
- **团队**: @duan (China, GMT+8) + @ryan (Singapore, GMT+8) — **same timezone**
- **AI 队友**: 双 Claude Code

## 一句话描述

> **The App Store for verifiable AI skills.** Compose, pay-per-call, and cryptographically audit any agent skill across LLM providers — every invocation is paid in USDC and chained into a tamper-evident SHA-256 audit log anyone can verify.

## 叙事弧（demo hook）

> **"ClaimsForge failed. Reason wasn't tech — it was narrative. I dissected it into VeriForge: each agent is now a skill anyone can call."**

ClaimsForge 是 @duan 之前 hackathon 没获奖的项目（保险/e-commerce damage claims 6-agent system）。VeriForge 把它的 6 个 agent + 3 个 horizontal skill 重新封装成 marketplace 商品，叙事直接从 "vertical agent" 升级到 "可复用 protocol"。

## 评委 5 步路径（边写边维护）

1. `git clone <repo> && cd <repo> && cp .env.template .env` — 填 GOOGLE_API_KEY + MOONSHOT_API_KEY
2. `docker compose up -d` — 启动 13 service（6 claims + 3 horizontal + router + audit + activity + web）
3. Open `http://localhost:3001` — 看 marketplace UI（9 个 skill cards）
4. 试 input: *"My ceramic mug arrived cracked. Order ORD-1234."* — 看 KIMI router 选 6 skill + 实时 activity stream
5. 任何 trace_id 复制到 `/verify/:trace_id` panel — 30 秒内独立验证 SHA-256 audit chain

完整路径见 `JUDGING.md`。

## Sponsor 列表 + ownership

| Sponsor | 集成什么 | 子目录 / 文件 | Owner | 评委验证命令 | Priority |
|---|---|---|---|---|---|
| **KIMI (Moonshot)** | `moonshot-v1-128k` 装下整个 9-skill registry，零 RAG router | `marketplace/router/router.py` | @duan | `curl localhost:8000/route -d '{...}'` | **P0** |
| **MiroMind** | verification-centric 理念 → public `/verify/:trace_id` endpoint + audit chain | `marketplace/audit/` | @duan | `curl localhost:8001/verify/<trace>` | **P0** |
| **Google Cloud + Gemini** | 6 个 claim skill 用 Gemini 2.5 Flash + Gemini Vision (96.7% acc on labeled set) | `skills/claims-*/handler.py` | @ryan? | `docker exec vf-claims-damage-vision env \| grep GOOGLE_API_KEY` | **P0** (Day 4 Vertex 部署) |
| EPIC Connector / Canlah AI | host sponsor，brand/marketing AI; 可选轻量集成 | — | — | — | P3 |
| BytePlus / Baidu / Singtel | 城市 pitch 备胎 | — | — | — | P3 |

**规则**：每个 sponsor 集成是**架构承重组件**（不是 logo on README）。直接对冲 ClaimsForge 死因 #2 "sponsor 集成不显眼"。

## 架构

```
                  Web UI (vanilla HTML)
                       :3001
                         │
        ┌────────────────┼────────────────┐
        ↓                ↓                ↓
┌─────────────────┐ ┌──────────────┐ ┌──────────────┐
│ router :8000    │ │ activity :8002│ │ audit :8001  │
│ /route /run     │ │ /emit /stream │ │ /append      │
│ + executor      │ │  /session     │ │ /verify/:tid │
└──────┬──────────┘ └──────┬───────┘ └──────┬───────┘
       │ background task   │ events         │ chain
       ↓                   ↓                ↓
┌────────────────────────────────────────────────────────┐
│  executor (in router) — 9 skill HTTP chain, x402 mock  │
└────────┬───────────────────────────────────────────────┘
         │ POST /invoke + X-Payment: mock:...
         ↓
┌────────────────────────────────────────────────────────┐
│  9 skill containers:                                   │
│  · claims-intent (7001)   · claims-emotion (7002)      │
│  · claims-needs (7003)    · claims-damage-vision (7004)│
│  · claims-compensation (7005)  · claims-verify (7006)  │
│  · text-summarize (7011)  · text-translate (7012)      │
│  · sentiment-analyze (7013)                            │
└────────────────────────────────────────────────────────┘
         │
         └─→ sys.path import → /Users/duan/code/claimsforge
             (read-only volume mount in containers)
```

详细见 `PROJECT.md` (双语完整 plan)、`docs/day{0.5,2,3}-results.md`。

## Stack

| 层 | Tech | 选择理由 |
|---|---|---|
| Skill runtime | Python 3.12 + FastAPI + Pydantic 2 | ClaimsForge 已有，零迁移成本 |
| LLM 路由 | KIMI `moonshot-v1-128k` (256k context) | 装下整个 registry，零 RAG (P0 sponsor) |
| Skill 内部 LLM | Gemini 2.5 Flash + Gemini Vision | ClaimsForge 已用，96.7% Vision 准确率 (P0 sponsor) |
| 编排 | MiroFlow research framework (concept-aligned) | host sponsor 主题对齐 — verification-centric (P0 sponsor) |
| 容器 | docker compose (13 services) | one-command boot, 评委 30s 跑通 |
| Audit / Activity backend | InMemoryStore (dev) → SupabaseStore (prod) pluggable | 用户 Supabase key 就到位 |
| 链上 | x402 + Base Sepolia USDC (currently mock mode) | Day 4 切 real mode |
| 前端 | Vanilla HTML + JS (no framework, no build) | 评委 zero-dependency 体验 |
| 部署 | docker compose local (Day 3) → Vertex AI + Cloud Run (Day 4) | GCP sponsor track |
| 可观测性 | Langfuse (Day 4) | accuracy/latency/cost dashboard 给评委看 |

## 命名约定

- **目录名**: kebab-case (`claims-damage-vision/`, `marketplace/router/`)
- **文件名**: lowercase, snake_case 内部 (Python)；kebab-case external
- **函数名**: snake_case (Python)
- **环境变量**: `UPPER_SNAKE_CASE`
- **分支名**: `<owner>/<feat-name>` (e.g. `duan/vertex-deploy`, `ryan/langfuse-wire`)
- **commit prefix**: `feat:` / `fix:` / `chore:` / `wip:` / `docs:`

## 22 skill 武器库

所有 hackathon skill 在 `.claude/skills/` (vendor 后自动加载)。常用：

| Skill | 何时调 |
|---|---|
| `/hackathon-strategist` | 每日激活做 5 天作战图调度 |
| `/auditable-decision-chain` | 已用于 `marketplace/audit/chain.py` (SHA-256 链) |
| `/realtime-activity-stream` | 已用于 `marketplace/activity/` (Supabase realtime 兼容) |
| `/x402-pay-per-query-endpoint` | 已用于 `marketplace/gateway/x402.py` (mock + real mode) |
| `/langfuse-agent-tracing` | Day 4 接入 |
| `/invariant-testing-harness` | Day 4 attach 到每个 skill 的 verify() hook |
| `/hackathon-sponsor-packager` | 已用于 9 个 skill 独立打包模式 |
| `/evaluator-friendly-readme` | Day 5 写 README + JUDGING.md |
| `/hackathon-demo-video-script` | Day 5 录 90s demo |

## 协作 protocol

### Git 流
- 主分支 `main` 永远 demo-ready (docker compose up 一定能起)
- 改动走 `<owner>/<feat>` 分支 + PR
- PR 标签 `auto-merge` (CI green 自动 squash-merge)
- **不 require review approval**（2 人 hackathon，5 天）
- 不 push direct to main

### Decision protocol
- 架构 / sponsor 选型 / 命名约定 → 双方 sync 后写 `DECISIONS.md` (append-only)
- 实现细节 → 单方决定 + commit message 说明

### Daily ritual
- 开工：read `HANDOFF.md` + `SPRINT.md`
- 下工：写 `HANDOFF.md` + push (用 Claude Code 自动生成)
- Discord `#daily` channel 同步

## 当前 sprint 状态

见 [`SPRINT.md`](./SPRINT.md)。

## 已做决策

见 [`DECISIONS.md`](./DECISIONS.md)。

## 安全

- 不在 Discord / chat 贴 API key
- 所有 secret 通过 `.env` (gitignored) + GitHub Secrets
- 当前 .env 里有 KIMI key + Gemini key — 提交前确认 .env 在 .gitignore

## 反模式

- 不要在 main 直接 push
- 不要 require PR review approval (overhead)
- 不要把 sponsor 集成埋在主应用（违反 sponsor-packager 模式）
- 不要 demo video > 90 秒
- 不要 README 没"评委 5 步路径"
- 不要在 catch 里 swallow LLM error 装成 success
- **不要重新 vertical-lock 到保险/电商**——VeriForge 的灵魂是横向 marketplace
