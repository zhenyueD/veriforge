# VeriForge

> **Verifiable, on-chain Skill Marketplace where any AI agent can discover, purchase, and execute composable skills — with cryptographic audit trails and MiroFlow-orchestrated verification.**
>
> Built for **UCWS Singapore Hackathon 2026 · Skills Track · Solo build · 5-day sprint**

**Naming alternatives** (locked unless rejected): `VeriForge` (recommended) · `SkillRails` · `MiraForge`

**Why VeriForge**: `Veri` = verification (MiroMind's core theme) + `Forge` = continuation of last week's `ClaimsForge` — the narrative arc *"ClaimsForge failed. I dissected it into VeriForge."* is the demo hook.

---

## Table of Contents
- [English](#english)
- [中文](#中文)

---

# English

## 1. Background

5 days ago, my hackathon project **ClaimsForge** (7-agent insurance claims processor with IAM supervisor + Trust Score + audit chain) shipped to a global hackathon — and did not win.

Postmortem revealed the root cause was not technical: it was **narrative**. Judges saw "another vertical agent" and could not see the reusable asset underneath.

**VeriForge** turns that autopsy into momentum: I dissect ClaimsForge into 7 independent, callable, billable, verifiable **skills**, then build the marketplace to host them — and any future skill, from anyone.

This is what "NO RULES. JUST CREATE." looks like when last week's failure becomes this week's raw material.

## 2. Problem

The AI agent ecosystem has a structural gap:

| Today | Gap |
|---|---|
| Every team builds vertical agents end-to-end | No way to monetize the agent's *components* |
| Skills (Anthropic, ChatGPT, etc) are free / closed / not interoperable | No protocol for cross-LLM skill execution |
| Agent outputs are black boxes | No verifiable audit trail buyers can independently check |
| Skill discovery is "ask the agent" | No semantic registry across providers |

Result: a flood of duplicate vertical agents, no composability, no market.

## 3. Solution

VeriForge is an open marketplace where:

1. **Anyone publishes** a skill (just `skill.yaml` + handler) — ClaimsForge's 7 dissected agents are launch inventory
2. **Any agent calls** it via standardized `x-skill` protocol — KIMI, Gemini, Claude, ERNIE all supported
3. **KIMI 256k context** holds the entire registry — semantic routing without RAG, picks skills via raw context
4. **MiroFlow** orchestrates multi-step skill chains with verification loops between steps
5. **Each call** is metered on-chain via x402 (USDC on Base) — instant micro-payments
6. **Every result** carries a SHA-256 audit hash anyone can verify via public `/verify/:trace_id` endpoint

The narrative arc: **App Store for verifiable AI agents.**

## 4. Key Features

- **Skill Registry** — YAML-defined, semantic-searchable, KIMI-hosted in-context
- **MiroFlow Router** — picks best skill chain for any input
- **Verification Layer** — each skill ships a `verify()` invariant hook
- **x402 Payments** — pay-per-call on Base testnet, no platform lock-in
- **Audit Chain** — SHA-256 chained hashes, public `/verify/:trace_id` endpoint
- **Live Activity Stream** — Supabase realtime, every step visible as it happens
- **Launch Inventory** — ClaimsForge's 7 claim-processing skills + 3 horizontal demo skills (translate / summarize / sentiment)

## 5. Architecture

```
┌────────────────────────────────────────────────────────────┐
│                         Frontend                           │
│   Activity Stream (Supabase realtime) + Verify Browser     │
└──────────────────────────┬─────────────────────────────────┘
                           │
            ┌──────────────▼─────────────────┐
            │   MiroFlow Orchestrator        │
            │   (multi-agent + verification) │
            └──────┬─────────────────────┬───┘
                   │                     │
          ┌────────▼──────────┐  ┌───────▼────────────┐
          │   KIMI Router     │  │  Verification Layer │
          │   (256k context)  │  │  (invariants +      │
          │   skill selection │  │   Trust Score)      │
          └────────┬──────────┘  └─────────────────────┘
                   │
            ┌──────▼──────┐
            │ x402 Gateway│ ────── Base testnet (USDC)
            │ (per-call)  │
            └──────┬──────┘
                   │
        ┌──────────▼──────────────┐
        │   Skill Pool            │
        │  - claims-intake        │ ┐
        │  - claims-fraud         │ │  ClaimsForge
        │  - claims-trust-score   │ │  dissected
        │  - claims-payout        │ │  (7 skills)
        │  - claims-coverage      │ │
        │  - claims-iam           │ │
        │  - claims-supervisor    │ ┘
        │  - text-summarize       │ ┐
        │  - text-translate       │ │  Horizontal
        │  - sentiment-analyze    │ ┘  demo skills
        └──────────┬──────────────┘
                   │
        ┌──────────▼──────────────┐
        │   Audit Chain           │
        │   (SHA-256 hash chain)  │
        │   public /verify/:id    │
        └─────────────────────────┘

        Deployed on Google Cloud (Vertex AI + Cloud Run)
        Observability via Langfuse (cost / latency p95 / accuracy)
```

## 6. Sponsor Integration

Three sponsors are **not "logos on README"** — each is a load-bearing architectural component. This is the direct counter to ClaimsForge's death cause (#2: sponsor integration not prominent).

### P0 — MiroMind (host + theme anchor)
- Fork [MiroFlow](https://github.com/MiroMindAI/MiroFlow) as orchestration core
- Each skill registers `verify_hook` aligned with MiroFlow's verification-centric protocol
- Public `/verify/:trace_id` = on-chain realization of MiroMind's "99% verifiable" promise
- **Outreach action (Day 5)**: cold-email MiroMind team in Redwood City + Singapore with demo link

### P0 — KIMI (Moonshot)
- 256k context window holds the **full skill registry** (~1000+ skills planned at scale)
- Router prompt = registry + user input → skill chain (zero RAG, zero embedding pipeline)
- **Why this is novel**: every other marketplace uses vector search; KIMI's window makes that obsolete

### P1 — Google Cloud + Gemini
- Vertex AI deploys MiroFlow Router + 2 reference skills
- Gemini Pro runs inside individual skills for multimodal reasoning
- Cloud Run + Cloud Build for autoscaling skill execution

### P3 — BytePlus / Baidu AI Cloud / Singtel / gopomelo
- Reserved for finalist round: city-specific pitch events (Shanghai / SG / Shenzhen / London / SV) may have side prizes

### Not pursued — Canlah AI (host)
- Direction (brand/marketing AI) does not fit core narrative
- Optional light integration after Day 6 if time permits

## 7. Task Checklist (5-Day Finalist Sprint)

### Day 0.5 (5/23 evening) — Feasibility spike (30 min)
- [ ] KIMI k2.6 long-context call with registry-size prompt — measure latency / cost
- [ ] x402 Base testnet 402 → USDC payment round-trip
- [ ] MiroFlow GitHub fork + `pip install` smoke test

### Day 1 (5/24) — Scaffold + ClaimsForge dissection
- [ ] Monorepo layout: `/marketplace`, `/skills`, `/sdk`, `/web`
- [ ] `skill.yaml` schema finalized (id, inputs, outputs, price, verify_hook)
- [ ] Dissect ClaimsForge into 7 skill directories
- [ ] `docker compose up` runs all 7 skills, behavior 1:1 with ClaimsForge
- [ ] **Red line**: dissect only, do not refactor

### Day 2 (5/25) — KIMI registry-in-context router
- [ ] `registry.json` with 10 skills (7 claims + 3 horizontal: translate / summarize / sentiment)
- [ ] `/router` service: registry + input → KIMI 256k → skill plan
- [ ] End-to-end: unseen input "car accident yesterday" → correct claim skill chain
- [ ] End-to-end: unrelated input "summarize this contract" → completely different chain (proves horizontal)

### Day 3 (5/26) — Activity stream + audit chain + x402
- [ ] Supabase project + `activity_log` table + RLS
- [ ] Frontend dashboard: live skill calls, cost, hash, verification status
- [ ] x402 middleware: every `POST /invoke` returns 402 + USDC Base address
- [ ] SHA-256 chain: each call appends prev hash

### Day 4 (5/27) — Verification layer + Vertex deploy
- [ ] Each skill ships `verify(input, output) -> VerifyResult` hook
- [ ] Public `/verify/:trace_id` endpoint returns full chain + invariant results
- [ ] Deploy router + 2 skills to Vertex AI / Cloud Run
- [ ] Langfuse integration; public dashboard link

### Day 5 (5/28) — Demo video + submission
- [ ] 3-minute demo video (script in README)
- [ ] README top: headline + 5-step judge path + architecture diagram
- [ ] `JUDGING.md` with 3 sponsor sections + copy-paste verify commands
- [ ] Backup demo recording (offline fallback for Demo Day)
- [ ] Submit + cold-email MiroMind team

## 8. Functional Modules to Build

| Module | Status | Day | New LOC est. |
|---|---|---|---|
| `skill.yaml` SDK + spec | New | 1 | ~200 |
| ClaimsForge dissector | 90% reuse | 1 | ~300 (wrappers) |
| Registry-in-context router (KIMI) | New | 2 | ~150 |
| MiroFlow integration | New | 2 | ~200 |
| Activity stream backend + frontend | Skill: `realtime-activity-stream` | 3 | ~400 |
| x402 gateway middleware | Skill: `x402-pay-per-query-endpoint` | 3 | ~150 |
| Audit chain (SHA-256) | Skill: `auditable-decision-chain` | 3 | ~100 |
| Invariant + verify hooks per skill | Skill: `invariant-testing-harness` | 4 | ~300 |
| Public `/verify/:trace_id` endpoint | New | 4 | ~80 |
| Vertex AI / Cloud Run deploy | Config | 4 | ~50 |
| Langfuse tracing | Skill: `langfuse-agent-tracing` | 4 | ~50 |
| Demo video + README + JUDGING.md | Skill: `evaluator-friendly-readme` + `hackathon-demo-video-script` | 5 | — |

**Total new LOC estimate**: ~2200 (reasonable for 5-day solo build with skill library assistance)

## 9. Success Metrics

| Metric | Target | Why |
|---|---|---|
| Finalist selection | Top 15-20 | Skills Track entry to Singapore Demo Day |
| Sponsor track wins | ≥1 of 3 P0 | $10k each |
| End-to-end demo runtime | <60s | Live demo must work first try |
| `/verify/:trace_id` self-serve verification | <30s | Judge can independently verify |
| MiroMind team response | ≥1 reply | Host sponsor 暗线 acknowledgment |

## 10. Risks & Fallbacks

| Risk | Fallback |
|---|---|
| KIMI 256k registry routing too slow (>10s) | HyDE hybrid RAG (skill: `hyde-hybrid-rag`); sponsor story → "KIMI runs skill internal inference" |
| x402 testnet flaky | Mock payment + standalone demo page |
| Vertex AI deploy fails | Vultr fallback (ClaimsForge has working deploy); GCP story → "Gemini powers skill inference" |
| ClaimsForge dissection breaks behavior | Drop to 3 claim skills + 3 horizontal; marketplace story still intact |
| README unclear in 30s pitch | Cut technical details, keep headline + judge path only |

---

# 中文

## 1. 背景

5 天前，我的上一个 hackathon 项目 **ClaimsForge**（7-agent 保险理赔系统 + IAM supervisor + Trust Score + audit chain）提交后未获奖。

复盘根因不在技术，而在**叙事**：评委看到的是"又一个 vertical agent"，看不到底下可复用的资产。

**VeriForge** 把这场失败正向转化：我把 ClaimsForge 解剖成 7 个独立、可调用、可计费、可验证的 skill，再造一个市场承载它们——以及任何人未来发布的 skill。

这是 "NO RULES. JUST CREATE." 在用上周失败做原料时长出来的样子。

## 2. 解决什么问题

AI agent 生态有结构性空洞：

| 现状 | 缺什么 |
|---|---|
| 每家都做端到端 vertical agent | agent 的"零件"无法变现 |
| Skill（Anthropic / ChatGPT 等）免费 / 封闭 / 不互通 | 没有跨 LLM 的 skill 调用协议 |
| Agent 输出是黑盒 | 没有买家可独立验证的审计链 |
| Skill 发现 = "问 agent" | 没有跨 provider 语义注册表 |

结果：vertical agent 泛滥，无可组合性，无市场。

## 3. 方案

VeriForge 开放市场：

1. **任何人发布** skill（一份 `skill.yaml` + handler）—— ClaimsForge 解剖的 7 个 agent 作为首批商品
2. **任何 agent 调用** 通过标准 `x-skill` 协议 —— KIMI / Gemini / Claude / 文心都支持
3. **KIMI 256k context** 一次装下整个 registry —— 不用 RAG，直接 context 做语义路由
4. **MiroFlow** 编排 skill 链，每步之间插 verification loop
5. **每次调用** 通过 x402 (Base USDC) 链上计费 —— 微支付
6. **每个结果** 带 SHA-256 audit hash —— 公开 `/verify/:trace_id` endpoint 任何人能查

叙事：**可验证 AI agent 的 App Store**。

## 4. 核心功能

- **Skill Registry** —— YAML 定义、语义可搜、装在 KIMI context 里
- **MiroFlow Router** —— 给任意输入挑最佳 skill 链
- **Verification Layer** —— 每个 skill 自带 `verify()` invariant hook
- **x402 Payments** —— 链上 USDC 按次付费，无平台锁定
- **Audit Chain** —— SHA-256 链式哈希，公开 `/verify/:trace_id` 端点
- **Live Activity Stream** —— Supabase realtime，每步操作实时可见
- **首批商品** —— ClaimsForge 的 7 个理赔 skill + 3 个 horizontal demo skill（翻译/摘要/情感分析）

## 5. 架构

（见上文英文版架构图，结构相同）

核心数据流：用户输入 → MiroFlow Orchestrator → KIMI Router（256k 装下全 registry，挑 skill）→ Verification Layer → x402 Gateway（链上收钱）→ Skill Pool（10 个 skill）→ Audit Chain（哈希链）→ 公开 `/verify/:trace_id`。

部署：Google Cloud Vertex AI + Cloud Run。监控：Langfuse（成本 / p95 延迟 / 准确率）。

## 6. Sponsor 联动

3 个 sponsor **不是 "logo 摆在 README"**，而是承重组件。这是 ClaimsForge 死因 #2（sponsor 集成不显眼）的直接对策。

### P0 — MiroMind（host + 主题锚）
- Fork [MiroFlow](https://github.com/MiroMindAI/MiroFlow) 做编排核心
- 每个 skill 注册 `verify_hook`，对齐 MiroFlow verification-centric 协议
- 公开 `/verify/:trace_id` = MiroMind "99% verifiable" 承诺的链上实现
- **Day 5 行动**：cold email MiroMind team（Redwood City + Singapore），附 demo 链接

### P0 — KIMI（Moonshot）
- 256k context 一次装下**完整 skill registry**（规模化后 1000+ skill）
- Router prompt = registry + user input → skill chain（零 RAG、零 embedding pipeline）
- **为什么新颖**：所有其他 marketplace 都用 vector search，KIMI 的 context window 让这套过时

### P1 — Google Cloud + Gemini
- Vertex AI 部署 MiroFlow Router + 2 个参考 skill
- Gemini Pro 跑 skill 内部多模态推理
- Cloud Run + Cloud Build 做自动扩缩容

### P3 — BytePlus / 百度智能云 / Singtel / gopomelo
- 入围后看城市 pitch event（上海 / SG / 深圳 / 伦敦 / 硅谷）是否有 side prize

### 不投入 — Canlah AI（host）
- 方向（brand/marketing AI）跟核心 narrative 不 fit
- Day 6+ 有时间做轻量集成（可选）

## 7. 5 天任务清单

### Day 0.5（5/23 晚）— 30 分钟可行性验证
- [ ] KIMI k2.6 长 context 调用（registry-size prompt），量 latency / 成本
- [ ] x402 Base testnet 402 → USDC 付款往返
- [ ] MiroFlow GitHub fork + `pip install` 跑通

### Day 1（5/24）— 骨架 + ClaimsForge 解剖
- [ ] Monorepo 布局：`/marketplace`、`/skills`、`/sdk`、`/web`
- [ ] `skill.yaml` schema 定稿（id, inputs, outputs, price, verify_hook）
- [ ] ClaimsForge 解剖成 7 个 skill 目录
- [ ] `docker compose up` 跑通 7 个 skill，行为 1:1
- [ ] **红线**：只拆不改

### Day 2（5/25）— KIMI registry-in-context router
- [ ] `registry.json` 10 个 skill（7 claims + 3 horizontal：translate / summarize / sentiment）
- [ ] `/router` service：registry + input → KIMI 256k → skill plan
- [ ] 端到端验证："car accident yesterday" → 正确 claim skill 链
- [ ] 端到端验证："summarize this contract" → 完全不同的链（证明 horizontal）

### Day 3（5/26）— Activity stream + audit chain + x402
- [ ] Supabase 项目 + `activity_log` 表 + RLS
- [ ] 前端 dashboard：实时显示 skill 调用 / 成本 / 哈希 / verification
- [ ] x402 中间件：`POST /invoke` 返回 402 + USDC Base 地址
- [ ] SHA-256 chain：每次调用 append 前哈希

### Day 4（5/27）— Verification layer + Vertex 部署
- [ ] 每个 skill 实现 `verify(input, output) -> VerifyResult`
- [ ] 公开 `/verify/:trace_id` 返回完整链 + invariant 结果
- [ ] Vertex AI / Cloud Run 部署 router + 2 个 skill
- [ ] Langfuse 接入；dashboard 公开链接

### Day 5（5/28）— Demo video + 提交
- [ ] 3 分钟 demo video
- [ ] README 顶部：headline + 评委 5 步路径 + 架构图
- [ ] `JUDGING.md`：3 个 sponsor 分段 + copy-paste verify 命令
- [ ] 录 backup demo（Demo Day 离线 fallback）
- [ ] 提交 + cold email MiroMind

## 8. 需要完成的功能模块

| 模块 | 状态 | Day | 新增 LOC |
|---|---|---|---|
| `skill.yaml` SDK + spec | 新建 | 1 | ~200 |
| ClaimsForge 解剖器 | 90% 复用 | 1 | ~300 (wrapper) |
| Registry-in-context router (KIMI) | 新建 | 2 | ~150 |
| MiroFlow 集成 | 新建 | 2 | ~200 |
| Activity stream 后端+前端 | Skill: `realtime-activity-stream` | 3 | ~400 |
| x402 gateway 中间件 | Skill: `x402-pay-per-query-endpoint` | 3 | ~150 |
| Audit chain (SHA-256) | Skill: `auditable-decision-chain` | 3 | ~100 |
| 每个 skill 的 invariant + verify hook | Skill: `invariant-testing-harness` | 4 | ~300 |
| 公开 `/verify/:trace_id` endpoint | 新建 | 4 | ~80 |
| Vertex AI / Cloud Run 部署 | 配置 | 4 | ~50 |
| Langfuse 追踪 | Skill: `langfuse-agent-tracing` | 4 | ~50 |
| Demo video + README + JUDGING.md | Skill: `evaluator-friendly-readme` + `hackathon-demo-video-script` | 5 | — |

**总新增 LOC 估算**：~2200（5 天 solo + skill 库辅助合理范围）

## 9. 成功指标

| 指标 | 目标 | 为什么 |
|---|---|---|
| 入围 finalist | Top 15-20 | Skills 赛道入场券去 Singapore Demo Day |
| Sponsor 专项奖 | ≥3 个 P0 中拿 1 个 | 每个 $10k |
| 端到端 demo 跑完时间 | <60s | Live demo 必须一次成功 |
| `/verify/:trace_id` 自助验证 | <30s | 评委可独立验证 |
| MiroMind team 回应 | ≥1 个回复 | host sponsor 暗线认可 |

## 10. 风险与 fallback

| 风险 | Fallback |
|---|---|
| KIMI 256k registry 路由太慢（>10s） | HyDE hybrid RAG（skill: `hyde-hybrid-rag`）；sponsor 故事改"KIMI 跑 skill 内部推理" |
| x402 testnet 不稳定 | Mock payment + 独立 demo page |
| Vertex AI 部署失败 | Vultr fallback（ClaimsForge 已有部署）；GCP 故事改"Gemini 跑 skill 推理" |
| ClaimsForge 解剖行为不一致 | 砍到 3 个 claim skill + 3 个 horizontal；marketplace 故事不变 |
| README 30 秒讲不清 | 砍技术细节，保 headline + 评委路径 |

---

## Appendix · Demo Video 3-Minute Script

| Time | Content |
|---|---|
| 0:00-0:15 | **Hook** — screen shows "ClaimsForge failed. Reason wasn't tech, it was narrative." → cut to "Today I dissected it. Each agent is now a skill. Anyone can call them." |
| 0:15-0:45 | **Live demo 1** — input "I got into a car accident yesterday" → right panel: KIMI router live-picks 3 skills → each call shows x402 payment ("$0.02 paid") → audit hash chains on-screen |
| 0:45-1:15 | **Live demo 2** — input "Summarize this contract" → same router picks completely different skills → proves marketplace is horizontal, not insurance-locked |
| 1:15-1:45 | **Verification moment** — judge's POV: copy trace_id → paste into `/verify/:trace_id` → returns full audit chain + invariants all pass. "This is what MiroMind verification-centric means in code." |
| 1:45-2:15 | **Sponsor showcase** — three split-screen panels: MiroFlow orchestration code · KIMI 256k registry call · Vertex AI deploy screenshot |
| 2:15-2:45 | **Business model** — creators earn per call → marketplace take rate → on-chain settlement borderless → "App Store for AI agents, but verifiable" |
| 2:45-3:00 | **Ask** — Skills Track champion + live pitch at Singapore Demo Day |

---

## Appendix · Capability Inventory Used

From the 22-skill hackathon arsenal, **9 skills directly load-bearing**:

| Skill | Used in |
|---|---|
| `hackathon-sponsor-packager` | Day 1 — packaging each skill as standalone subproduct |
| `realtime-activity-stream` | Day 3 — Supabase live UI |
| `auditable-decision-chain` | Day 3 — SHA-256 chain |
| `x402-pay-per-query-endpoint` | Day 3 — pay-per-call |
| `invariant-testing-harness` | Day 4 — verify() hooks |
| `langfuse-agent-tracing` | Day 4 — observability dashboard |
| `evaluator-friendly-readme` | Day 5 — README + JUDGING.md |
| `hackathon-demo-video-script` | Day 5 — video script |
| `recipe-execution-agent-split` | Day 2 — router/executor separation |
| `dual-model-intent-router` (optional) | Day 2 — Groq fast-path fallback if KIMI slow |
| `hyde-hybrid-rag` (fallback only) | Risk fallback if KIMI 256k routing too slow |

---

*Last updated: 2026-05-23 · UCWS Singapore Hackathon 2026 build*
