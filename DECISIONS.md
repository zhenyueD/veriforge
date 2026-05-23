# DECISIONS.md

**Append-only.** 已决定的事不再重新讨论。新决策追加在底部。

---

## 2026-05-23 · 项目立项 → VeriForge (Skills Track)

**决策**：参赛 UCWS Singapore Hackathon 2026 的 **Skills Track**，做"Verifiable Skill Marketplace"。  
**理由**：@duan 储备 22 hackathon skill + ClaimsForge 死亡资产 + Skills Track 最对齐 Anthropic skill 范式审美。  
**Owner**: @duan

---

## 2026-05-23 · 项目命名：VeriForge

**决策**：项目名 `VeriForge`（不是 SkillRails / MiraForge）。  
**理由**：`Veri` = verification (MiroMind 核心主题) + `Forge` = 接住 ClaimsForge 叙事弧 (上个 hackathon 没获奖的项目，dissect 重铸)。Demo Hook *"ClaimsForge failed. I dissected it into VeriForge."*  
**Owner**: @duan

---

## 2026-05-23 · 复用 ClaimsForge 60%（不是直接 pivot vertical）

**决策**：把 ClaimsForge 6 agent 拆成 6 个独立 skill (intent/emotion/needs/damage-vision/compensation/verify)，**不** 重新 vertical-pivot。  
**理由**：ClaimsForge 死因不是技术，是叙事——评委看到的是"又一个 vertical agent"。直接换 vertical 仍然死。**拆解成 marketplace skill 完全绕开死因**。  
**Owner**: @duan  
**Counter-evidence needed before reversing**: 如果发现 marketplace 叙事评委不买账。

---

## 2026-05-23 · LLM 路由选 `moonshot-v1-128k`，不是 `kimi-k2.6`

**决策**：KIMI router 用 `moonshot-v1-128k` (非 reasoning model)，不用 K2.6/K2.5。  
**理由**：spike test 数据：
- K2.6 (reasoning): 26-40s, output 674-1579 tokens (CoT) ❌
- K2.5 (reasoning): 28-51s ❌
- moonshot-v1-128k (non-reasoning): 4-6s, 3/3 routing ✅

routing 不需要 reasoning，需要快+准。moonshot-v1-128k 是 KIMI 主产品线（K2.x 是新的 reasoning 系列），sponsor 故事完全成立。  
**Owner**: @duan

---

## 2026-05-23 · ClaimsForge 共享 venv via sys.path import (不复制代码到每个 skill 容器)

**决策**：所有 6 个 claim skill 通过 `sys.path.insert(0, "/claimsforge/agents")` import ClaimsForge 纯函数 (`classify`, `assess`, `grade`, etc)；ClaimsForge 源码作为 read-only volume mount 进 docker container。  
**理由**：5 天 scope 优先；行为 1:1 保证最强；每个 skill 仍然有自己的 FastAPI `handler.py` + `skill.yaml` + `verify.py`，独立可发布的接口契约保留。  
**Trade-off**: skill 容器还是依赖 ClaimsForge 源码 mount，不是真正"completely standalone"。Day 4 时间允许的话改 self-contained 容器 (copy agent.py + deps in)。  
**Owner**: @duan

---

## 2026-05-23 · 跳过 claims-fraud-image（推迟到 Day 4 stretch）

**决策**：Day 1 拆解 6 个 skill 而不是 7 个；`fraud.py` 是 utility module (compute_phash / check_exif_age) 不是 agent，没有明显的 `classify()` 入口函数。  
**理由**：包 facade 需要自写组合逻辑，~300 LOC，Day 1 时间盘不够。  
**重启条件**：Day 4 vertex 部署完后，时间允许的话补上。Task #11 tracked.  
**Owner**: @duan

---

## 2026-05-23 · Executor 双模式：subprocess (dev) + HTTP (prod)

**决策**：`marketplace/router/executor.py` 支持两种 mode：
- `in_process`: 每个 skill subprocess 隔离 (sys.path import handler.py)，无 uvicorn 启动开销，Day 2 host dev 用
- `http`: POST 到 skill container HTTP endpoint，Day 3+ docker network 用 (production-shaped)

**理由**：Day 2 host 直接 import 9 个 skill 的 `handler.py` 会模块名冲突 (`handler` 重名)。subprocess 给每个 skill 干净 namespace。Production 用 HTTP 走真实 docker network。  
**Owner**: @duan

---

## 2026-05-23 · Audit / Activity store pluggable (InMemory + Supabase)

**决策**：audit chain 和 activity event store 都是 pluggable backend：
- `InMemoryStore`: dev default，无外部依赖，restart 丢数据
- `SupabaseStore`: 配 `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` 自动切换，持久化

**理由**：让 demo 路径无依赖（zero-Supabase 也能跑），同时给 production 升级路径。Supabase Realtime 还能让 UI 用前端 subscription 替代长轮询。  
**Owner**: @duan

---

## 2026-05-23 · x402 默认 mock 模式（Day 4 切 real）

**决策**：x402 gateway 中间件支持 mock + real 双模式。默认 mock：任何非空 X-Payment header 都 PASS。Real 模式需 `VERIFORGE_X402_MODE=real` + Base Sepolia wallet + facilitator 配置。  
**理由**：5 天 scope 优先 demo 完整性；real 链上付款是 Day 4 增量；mock 模式让评委也能看到完整 402 dance + skill_payment_settled 事件流，sponsor 故事不变。  
**Owner**: @duan

---

## 2026-05-23 · NO_PROXY 必须显式包含所有 docker service 名

**决策**：docker-compose router service env 必须显式列 `NO_PROXY=audit,activity,router,claims-*,text-*,sentiment-analyze,localhost,127.0.0.1`。  
**理由**：Docker Desktop 自动注入 `HTTP_PROXY=host.docker.internal:7890` 给 container（继承宿主 macOS 代理 7890）。如果 NO_PROXY 不覆盖内部 service 名，container 之间 HTTP call 全部 502 Bad Gateway。这是浪费 30 分钟才 debug 出来的。  
**Owner**: @duan

---

## 2026-05-23 · Sponsor 三轨深度 (不是双轨)

**决策**：KIMI + MiroMind + Google Cloud 三个 P0 sponsor，每个都是架构承重组件（不是 logo on README）。BytePlus/Baidu/Singtel 备胎。Canlah/EPIC host 不强求集成。  
**理由**：ClaimsForge 死因 #2 复盘——"sponsor 集成不显眼"。本案 KIMI router 是必经路径，MiroMind verification 理念实现 `/verify`，Gemini 是 6 个 skill 内部 LLM。任一缺失架构就崩。  
**Owner**: @duan  
**Trade-off**: 集成深度的代价是降低横向 sponsor 数量（BytePlus 等不投入）；这是正确的 trade-off。

---

## 2026-05-23 · UI 重做成 marketplace 风格（不是 hacker terminal）

**决策**：vanilla HTML UI 重写成"App Store for verifiable AI skills"风格：Hero + 9 个 skill cards (grid) + Live Demo + Verify + Sponsor footer。废弃之前的 black-on-black hacker terminal 风。  
**理由**：用户反馈"运行不了 + 很丑 + 还是客服不是 marketplace"。**叙事错位**——之前 UI 只有 input 框 + log，看不出"marketplace"的商品陈列感。重写后 9 个 skill 在首屏即可见，每个有 price + provider + tags + try button。  
**Owner**: @duan  
**Counter-evidence**: 如果 sponsor / 评委觉得 marketplace cards 太装饰、不像 dev tool，可以降级到更朴素的 list 视图。
