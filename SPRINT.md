# SPRINT.md

**当前 sprint 状态。每日开工/下工双方都读 + 更新。**

---

## Day 4 — 2026-05-24（计划，Ryan 加入后第一天）

### 🎯 今日目标
- Ryan onboarded + verifies stack runs locally
- Vertex AI 部署 router + 2 个参考 skill (GCP sponsor track)
- Langfuse 接入，dashboard 公开 link
- skill 边 x402 middleware attach (从 executor-mock 升级到 skill-edge 真 enforcement)

### 📋 任务

#### 🟢 Done (Day 0.5 - Day 3, all by @duan)
- [x] Day 0.5 · KIMI router spike — `moonshot-v1-128k` 3/3 routing, 4-6s latency
- [x] Day 1 · ClaimsForge 拆解成 6 skill (intent/emotion/needs/damage-vision/compensation/verify) — 6/6 live PASS
- [x] Day 2 · KIMI registry-in-context router + executor + 3 horizontal skill + 9-skill registry
- [x] Day 2.5 · docker compose 10/10 services healthy
- [x] Day 3 · audit chain (SHA-256) + activity stream + x402 mock + vanilla HTML marketplace UI (13 services)

#### 🟡 In Progress
- [ ] Day 4 · Vertex AI deploy (router + 2 skills) — @TBD — ETA: day end — branch: `<owner>/vertex-deploy`
- [ ] Day 4 · Langfuse 接入 — @TBD — ETA: day end — branch: `<owner>/langfuse-wire`
- [ ] Day 4 · skill-edge x402 attach (attach_x402 middleware to all skill handlers) — @TBD

#### 🔴 Blocked
- [ ] Day 0.5 · x402 Base Sepolia wallet spike — blocker: @duan 还没 fund testnet wallet — need: `python -c "from eth_account import Account; print(Account.create().key.hex())"` + faucet
- [ ] Supabase 项目 setup (audit + activity 切到 SupabaseStore) — blocker: 需要 user 提供 SUPABASE_URL + service key

#### ⚪ Todo (Day 4-5)
- [ ] Day 4 stretch · claims-fraud-image skill (wraps `fraud.py` utility into facade)
- [ ] Day 5 · 3-min demo video (script in `PROJECT.md` 附录)
- [ ] Day 5 · README.md polish + JUDGING.md (用 `/evaluator-friendly-readme` skill)
- [ ] Day 5 · Cold-email MiroMind team (Redwood City + Singapore) — host sponsor 暗线
- [ ] Day 5 · UCWS 平台提交

### 🎯 Day-end demo target (Day 4)
Live URL public: `https://veriforge.example.dev` (Vertex) + Langfuse dashboard link.

### 📊 Sponsor 进度

| Sponsor | Owner | 状态 | 子目录 | 评委验证 |
|---|---|---|---|---|
| **KIMI** | @duan | 🟢 跑通 | `marketplace/router/` | `curl localhost:8000/route` ✅ |
| **MiroMind** | @duan | 🟢 跑通 | `marketplace/audit/` | `/verify/:trace_id` ✅ |
| **Google Cloud + Gemini** | @TBD (ryan?) | 🟡 Day 4 Vertex 部署 | `skills/claims-*` | Vertex public URL TBD |
| BytePlus / Baidu / Singtel | — | ⚪ 城市 pitch 备胎 | — | — |
| EPIC Connector / Canlah AI | — | ⚪ host，不强求集成 | — | — |

### ⏰ 状态信号

| 谁 | 状态 | 直到 |
|---|---|---|
| @duan | 🟢 deep work (continuing Day 4) | TBD |
| @ryan | ⚪ pending onboarding | — |

---

## 历史 sprint

### Day 0.5 - Day 3 — 2026-05-23 (压缩成一个 session)

5 个 day-equivalents 完成。详细见 `docs/spike-results.md` + `docs/day{2,3}-results.md`。

**核心达成**：
- 13 个 docker service all live
- KIMI router 准确率 3/3
- 6 skill 行为 1:1 ClaimsForge 验证过
- audit chain tamper detection 跑通
- vanilla HTML marketplace UI（9 个 skill cards + live demo + verify panel）

**关键决策**：见 `DECISIONS.md` (2026-05-23 一连串决定)。
