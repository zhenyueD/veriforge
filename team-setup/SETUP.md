# Team Setup — Ryan onboarding 5 步

欢迎加入。这个 repo 是 setup 套件，把它的内容拷到你们正式的 hackathon repo 里就能用。

## 你需要装好的东西

- **Claude Code** (你和 Duan 都用同一个工具，最高带宽协作)
- **Discord** desktop + mobile
- **GitHub** account + git CLI
- **Node.js 20+** + **gh CLI** (`brew install gh && gh auth login`)
- **Vercel** account (前端 preview)

## Setup 5 步（< 15 分钟）

### Step 1: Clone repo + vendor skills

```bash
git clone <your-hackathon-repo-url>
cd <your-hackathon-repo>
bash team-setup/vendor-skills.sh
```

这会把 8 个 hackathon 必备 skill + hackathon-strategist agent 拷到 `.claude/skills/` 和 `.claude/agents/`。你的 Claude Code 启动时自动加载，无需配置。

### Step 2: 读 `CLAUDE.md`

项目根目录的 `CLAUDE.md` 是**双 Claude Code 的共享 memory**。架构、命名约定、sponsor 分工、决策都在这里。打开 Claude Code 之前先人工读一遍。

### Step 3: 加入 Discord server

链接：`<Duan 会发给你>`

5 个 channel:
- `#general` — 闲聊 / status signal
- `#code-sync` — PR / commit 通知 + 代码讨论
- `#daily` — 每日 micro-demo + handoff
- `#sponsor-help` — sponsor API 卡住的提问
- `#voice` — pair programming voice channel

翻译 bot 在所有 channel 自动跑：你打中文它翻英，你打英文它翻中。Threading reply，不刷屏。

### Step 4: 设置 GitHub PR + Vercel preview

```bash
# 给项目接上 Vercel preview
vercel link
# Vercel 会自动给每个 PR deploy preview URL，对方看效果用
```

### Step 5: 每日 ritual

**开工**：
1. Read 对方昨晚的 `HANDOFF.md`（git pull 后）
2. Read `SPRINT.md` 看今日任务 + 你 own 哪些
3. 在 `#daily` 发"我开工了，今天搞 X"

**下工**：
1. 写 `HANDOFF.md`（用 Claude Code 自动生成：`让 Claude Code 看今天的 git log 写 handoff`）
2. 录 60s micro-demo 发 `#daily`
3. commit + push handoff
4. 在 `#daily` 发"我睡了"

## 关键文件速查

| 文件 | 谁写 | 谁读 | 频率 |
|---|---|---|---|
| `CLAUDE.md` | 双方 | 双方 + 双 Claude Code | 偶尔（架构变了改） |
| `SPRINT.md` | 双方 | 双方 + 双 Claude Code | 每日 |
| `DECISIONS.md` | 双方（append-only） | 双方 + 双 Claude Code | 每次决策 |
| `HANDOFF.md` | 离线方 | 接班方 + 接班方 Claude Code | 每日下工 |
| `JUDGING.md` | Duan | 评委 | 最后一天写 |

## 协作原则

1. **AI 不是工具是第三个 teammate** — 双方 Claude Code 通过 markdown 文件异步通信
2. **PR 必走，但 auto-merge on green** — 不 require approval，PR 是为了 preview deploy
3. **Sponsor 1 人 1 个** — 不混着改，谁 own 谁负责
4. **决策日志 append-only** — 已决定的事不再吵
5. **不要在 chat 贴 API key** — 用 GitHub Secrets

## 22 skill 武器库速查

Duan 的 hackathon-strategist agent 内化了 63 招，按 9 个 tier 调度 22 个 skill。你的 Claude Code 一进项目就会自动有这些 skill。常用的：

- `/hackathon-strategist` — 总策略（每日激活）
- `/auditable-decision-chain` — LLM 决策审计
- `/prompt-injection-shield` — 3 层防御
- `/langfuse-agent-tracing` — 装监控
- `/llm-eval-yaml-harness` — 跑 accuracy 矩阵
- `/state-machine-agent-context-offload` — 多 agent 不爆 context
- `/hackathon-sponsor-packager` — sponsor 子目录
- `/hackathon-demo-video-script` — 90s demo 不漂移
- `/evaluator-friendly-readme` — README + JUDGING.md

需要全 22 个 skill 列表？看 `~/.claude/skills/`（Duan 那边）或问 Duan。

## 有问题

发 `#general`，或 voice channel 直接讲。
