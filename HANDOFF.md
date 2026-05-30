# HANDOFF.md

**离线前最后一件事：写这个文件 + commit + push。接班方第一件事：git pull + read 这个文件。**

---

## 最新 handoff

### From: @duan (web Claude Code) → 本地 Claude Code
### Date: 2026-05-30 (GMT+8)
### 分支: `claude/friendly-mccarthy-C9hKd` → PR #8 (draft, 未合并)

本 session 全程在 **Claude Code on the web 云端沙箱**里做。所有改动已 commit + push 到上面这个分支,开了 **draft PR #8**。本地接班第一件事:`git fetch origin claude/friendly-mccarthy-C9hKd`。

#### ✅ 本 session 做完的核心工作:把"被任何 LLM 发现"做成真功能

新增 **agent-facing skill discovery**(这是本次主线,已在沙箱实跑验证):

1. **语义搜索 `GET /skills/search?q=<任务>&rank=relevance|verified&format=openai|anthropic`**
   - 新文件 `marketplace/router/discovery.py`。用 **Gemini `gemini-embedding-001`** 做真向量检索(~190ms),**无 key/无网自动降级**到零依赖关键词检索(`method=lexical`),永不硬失败。
   - 每条结果**自带可直接调用的 tool spec**(OpenAI/Anthropic 双格式)→ 搜索→调用一步到位。
   - 实测命中:"faked photo"→`claims-fraud-image`、"translate"→`text-translate`、"how upset"→`claims-emotion/needs`。

2. **可验证信誉排序 `rank=verified`**(差异化护城河)
   - 排序 = `0.7*语义相关 + 0.3*链上信誉`。信誉来自审计链新端点 **`GET /reputation`**(`marketplace/audit/main.py` + `store.py` 的 `InMemoryStore.reputation()`),聚合每个 skill 的 `calls / verified_ok / pass_rate`,**密码学可证**。
   - 实测:同一句 "analyze a damaged product photo",纯语义下 damage-vision(0.784) vs fraud-image(0.771)几乎并列;接入信誉(12/12 vs 1/3)后拉开成 0.760 vs 0.577。

3. **零配置自描述清单**(让 agent 框架自动发现):`marketplace/router/main.py` 新增
   `/.well-known/ai-plugin.json`、`/.well-known/agent.json`(A2A card)、`/llms.txt`;FastAPI 的 `/openapi.json` 自动收录全部新端点。

4. **MCP 同步**:`marketplace/mcp/server.py` + `backend.py` 新增 `search_skills` 工具;
   server 支持从 env 读 `HOST/PORT`(适配容器 http transport,stdio 不变)。

5. **MCP 上架包**(为公开注册表发现做准备):`marketplace/mcp/` 新增 `Dockerfile`、`smithery.yaml`、`PUBLISH.md`(Smithery / 官方 MCP Registry / mcp.so / 本地 Claude Desktop 全套操作步骤)。

6. **一键 demo 脚本** `scripts/demo_discovery.sh`:起好 router:8000 + audit:8001 后 `bash` 一下看五段实证。

另外还加了 **`PITCH.md` / `PITCH.zh.md`**(demo-day 一页 pitch:4 支柱 + BYO skill + 叙事 hook)和 **`docs/architecture.png`**(graphviz 架构图)。

#### 🚨 环境踩坑记录(本地/部署会遇到,务必看)

1. **KIMI/Moonshot 在云沙箱被网络 allowlist 拦死**(`api.moonshot.ai`/`.cn` 都 `403 Host not in allowlist`)→ 所以 `/route`、`/run` 在沙箱跑不了。**本地不受影响**(你本机能连 Moonshot)。发现功能不依赖 KIMI,照常工作。
2. **Gemini 可用**:`gemini-2.5-flash` + `gemini-embedding-001` 实测 OK(`generativelanguage.googleapis.com` 在 allowlist 内)。注意 `gemini-2.0-flash` 已对新 key 下线——claimsforge 用的是 2.5-flash,没踩坑。
3. **`cryptography` 系统包在容器里 rust 绑定崩溃**(pyo3 PanicException),要 `pip install --upgrade --force-reinstall cryptography` 才能 import ed25519。本地正常的话忽略。
4. **claimsforge 依赖**:所有 skill 都 `sys.path` import `/claimsforge`。沙箱里我 clone 到了 `/home/user/claimsforge`;本地用 `.env` 的 `CLAIMSFORGE_PATH` 指向你本机克隆路径。

#### 🟡 待办 / 需要你或人工授权的

1. **合并 PR #8 到 main** —— 我(web 端)能合,但等你确认。CI 目前无 workflow(check_runs=0)。
2. **发布到 Smithery / 官方 MCP Registry** —— 沙箱**做不了**(出网被拦 + 需要你的 Smithery/GitHub 登录授权)。命令都在 `marketplace/mcp/PUBLISH.md`,你本地贴一次授权即可。
   - 注:**mcp.so / Glama / PulseMCP 会自动爬公开 GitHub repo**,所以合并到 main + 仓库 public = 通过 git 就被这些索引发现,无需单独提交。
3. **remote MCP 安装需要公网 router** → 要把 router 部署到 Cloud Run/Fly/Render 才能对外。本地用 stdio 直连 `localhost:8000` 无需部署。
4. **可选**:把 `rank=verified` 这套"可发现性"实证写进 PITCH/README;给 router 补 Cloud Run 部署配置。

#### ⚠️ 安全提醒

本 session 用户在对话里**明文贴了两个真实 key**(Google + Moonshot),已写进 `.env`(gitignored,未进任何提交)。但 key 已暴露在聊天记录,**请尽快去两边后台 rotate/重置**。

#### 🗂️ 改动文件清单(PR #8)

- 新增: `marketplace/router/discovery.py`、`marketplace/mcp/{Dockerfile,smithery.yaml,PUBLISH.md}`、`scripts/demo_discovery.sh`、`PITCH.md`、`PITCH.zh.md`、`docs/architecture.png`
- 改动: `marketplace/router/main.py`(search + 3 manifests)、`marketplace/audit/{main.py,store.py}`(/reputation)、`marketplace/mcp/{server.py,backend.py}`(search_skills + host/port)

---

### From: @duan → @ryan (onboarding handoff)
### Date: 2026-05-23 22:30 (GMT+8)
### Until: ryan 加入后我们一起跑节奏

#### ✅ 已经做完的（5 个 day-equivalents 压缩成一个 session）

- **Day 0.5 spike**: KIMI router 用 `moonshot-v1-128k`，3/3 routing accuracy, 4-6s latency。详见 `docs/spike-results.md`
- **Day 1 拆解**: ClaimsForge 6 个 agent → 6 个 marketplace skill。每个 skill 是 FastAPI 微服务，sys.path import ClaimsForge 纯函数。6/6 live test PASS (real Gemini call)
- **Day 2 router**: KIMI registry-in-context router + executor (dual subprocess/HTTP mode) + 3 horizontal demo skills (translate/summarize/sentiment) + 9-skill registry.json
- **Day 2.5 docker**: 10 services healthy。fix 了 NO_PROXY 坑（docker desktop 自动注入 host proxy）
- **Day 3 audit/activity/x402/UI**: 13 services total，SHA-256 audit chain (tamper detection 验证过), activity event stream (9 种 event), x402 mock gateway, vanilla HTML marketplace UI

#### 🟡 还在跑 / 半成品

- **UI 第一版很丑**（black hacker terminal）。**第二版已经重写**成 marketplace 风格 (Hero + 9 skill cards + Live Demo + Verify + Sponsors footer)。还有空间继续 polish (hero stats 行 `9 0 0 100%` 排版挤了)。但主体可用。Screenshot 在 `/tmp/vf_new.png` (你 git pull 后跑 `docker compose up -d` 然后 `open http://localhost:3001` 看实物)
- **CORS 问题修过**：audit + activity service 之前没装 CORSMiddleware，浏览器直接 fetch 被拦。已加。还要确认每个 sponsor 独立 endpoint 都有 CORS

#### 🚨 你接班需要立刻处理（无紧急事项）

- **无 prod 火**，所有本机 docker stack 稳定
- 唯一阻塞：UCWS 协作 setup（这就是现在在做的事）

#### 💡 我想到但还没做的

1. **Vertex AI 部署**（Day 4 task #9）：router + 2 个 reference skill 部署到 GCP Cloud Run + Vertex AI。需要 GCP project (用户没确认是否有 credits)。**强烈适合 Ryan 接** —— GCP sponsor track 本来就是 P0。
2. **Langfuse 接入**（Day 4 task #9）：5 分钟 setup，每个 skill call 自动 trace，accuracy/cost/p95 dashboard 给评委看
3. **skill-edge x402 attach**（Day 4）：当前 x402 是 executor 端 mock-emit `skill_payment_settled` event。**真 enforcement 是把 `attach_x402(app, ...)` middleware attach 到每个 skill container 的 FastAPI app**。需要 mount `/marketplace/gateway` volume 进每个 skill container + PYTHONPATH adjust
4. **claims-fraud-image stretch**（Task #11）：包 `fraud.py` 的 `compute_phash` + `check_exif_age` 成第 10 个 skill
5. **Cold-email MiroMind team** (Redwood City + Singapore) 在 Day 5 提交 demo 后立刻发，附 demo URL —— host sponsor 暗线
6. **Demo 5 步路径录 90s 视频** (Day 5)

#### 🔑 关键 context（Ryan 的 Claude Code 应该知道的）

1. **MiroFlow 不是通用 orchestrator**——它是 research agent framework (FutureX/GAIA benchmark 跑分项目)。VeriForge 通过 hierarchical sub-agent + verification trace 理念对齐，**没有真的 fork MiroFlow 代码**。Day 4 可以真 fork + 把 skill chain 包装成 MiroFlow sub-agent task；现在的实现是 concept-aligned。
2. **ClaimsForge 在 `/Users/duan/code/claimsforge`** (Mac 本机)。Ryan 没法本地 mount 这个 path（除非他也克隆 ClaimsForge）。所以 Ryan 的本地 dev 要么：(a) 克隆 ClaimsForge 到对应路径，(b) 等 Vertex 部署后直接用 cloud endpoint
3. **三个 P0 sponsor 哪个 owner？** 我建议：KIMI + MiroMind owner = @duan (代码已写)，**Google Cloud / Gemini / Vertex deploy = @ryan** (Day 4 主线)。Ryan 把 GCP 跑通就直接 own 第三个 P0 track
4. **测试方式 vs production 方式**：本机 `python3 marketplace/router/executor.py "..."` 走 subprocess mode (host venv)；docker 里 `EXEC_MODE=http` 走 HTTP mode (docker network)。两种 mode 都有跑通的 test
5. **每个 skill 已经在 response 里 emit audit 字段** (`trace_id`, `input_hash`, `output_hash`, `elapsed_ms`)。Day 3 audit chain 直接 chain 这些，无需改 skill 代码

#### 📋 你接班的优先级建议（Ryan 进来后第一周）

1. **Day 1 (你的)** · onboarding — `docker compose up -d`，跑通 UI，理解 `marketplace/router/executor.py` + `audit/chain.py` 两个核心 file
2. **Day 2 (你的)** · 拿 GCP project + Gemini API key，跑 Vertex AI deploy of router + 2 个 skill (claims-intent + claims-damage-vision)。这是 Best Use of GCP track 的核心
3. **Day 3 (你的)** · Langfuse 接入。每个 skill call 自动 trace。准备给评委看的 dashboard
4. **Day 4 (你的 + 我的)** · demo video (你录 / 我审稿) + README polish (用 `/evaluator-friendly-readme` skill) + JUDGING.md 写 3 个 sponsor 验证命令
5. **Day 5** · 提交 UCWS + cold email MiroMind + 任意城市 pitch event 报名

#### 🗂️ 你需要 review 的 doc 顺序

1. `README.md` — 项目简介
2. `CLAUDE.md` — 项目协作 contract（这是 setup tutorial 说的 single source of truth）
3. `PROJECT.md` — 中英双语完整 plan（10 章 + 2 附录）
4. `DECISIONS.md` — 我们已经做的关键决策（避免你重新讨论已决定的）
5. `docs/day3-results.md` — Day 3 完整实施记录 + Day 4 carryover
6. `JUDGING.md` (Day 5 前我们一起写) — 评委验证清单

#### ⏰ 我会立刻给你 GitHub repo URL + 加你 collaborator

push 完发你 invite 链接。
