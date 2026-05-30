# VeriForge — Demo Day 一页 Pitch（中文版）

> **可验证 AI skill 的应用商店。**
> 一行代码包住任意函数 → 它就变成「可被发现、可被任意 LLM 调用、按次用 USDC 计费、
> 每次调用都密码学可审计」的商品。

---

## 叙事钩子（15 秒）

> *"ClaimsForge 上次 hackathon 没拿奖。败因不是技术，是叙事——一个谁都没法复用的、
> 垂直的 6-agent 保险 demo。我把它拆解成了 VeriForge：当初那 6 个 agent，现在每一个都是
> **任何人都能调用、付费、并验证的 skill**——垂直 demo 变成了横向协议。"*

---

## 四大支柱（每一根都是承重墙，不是贴 logo）

| # | 支柱 | 做什么 | 代码 |
|---|---|---|---|
| ① | **Marketplace + 跨 LLM 调用** | 11 个带价 skill；注册表可导出成 OpenAI/Anthropic 函数规范 *以及* MCP 工具——任何 agent 一个 curl 就能发现并调用 | `marketplace/router/main.py`（`/skills`、`/skills/tools`）、`marketplace/mcp/server.py` |
| ② | **零-RAG 路由 + 编排** | KIMI `moonshot-v1-128k` 把*整个*注册表塞进上下文直接选 skill 链——不用向量库。随后 executor 按链路 HTTP 执行 | `/route`、`/run`、`executor.py` |
| ③ | **x402 按次付费 + 收益分账** | 每次调用带 `X-Payment` 头；自动算创作者分成 + 平台抽成，UI 实时显示收益 | `sdk/veriforge.py`（`attach_x402`、`compute_split`） |
| ④ | **密码学审计（两层）** | (a) SHA-256 哈希链——改一条，后续每一环全断；(b) ed25519 **Proof-of-Skill** 签名——每个 skill 用注册表公示的私钥签自己的输出，运营方无法掉包结果。公开 `/verify/:trace_id` | `marketplace/audit/chain.py`、`marketplace/router/reverify.py` |

---

## 上架你自己的 skill —— 就这一行

```python
from fastapi import FastAPI
from veriforge import monetize

app = FastAPI()
monetize(app, skill_id="my-skill", price_usdc=0.02, pay_to="0xYourWallet")
# → x402 收费闸门 · 创作者 + 平台分账 · 自动注册进 marketplace
```

一行就给付费路径挂上 x402、配好分账、并通过 `POST /register` 自动登记 skill。
作者自托管自己的 endpoint，VeriForge 负责发现、路由、计费、审计。
（供给侧 demo：`examples/external-skill/`。）

---

## 30 秒现场演示

1. 打开 `http://localhost:3001` —— 11 个 skill 的 marketplace，每个带 USDC 单价。
2. 粘贴：**"My ceramic mug arrived cracked. Order ORD-1234."**
3. KIMI 路由出一串 claim skill → 实时 activity stream 显示每次调用 + USDC 分账。
4. 复制任意 `trace_id` → **/verify** 面板几秒内把 SHA-256 链验证为绿色。
5. 篡改任意一条（demo 故障注入器）→ 同一条链立刻变**红**并指出断点。

---

## 为什么能赢

- **直接对冲 ClaimsForge 败因**：叙事从"一个垂直 agent"跃迁到"一个可复用协议"。
- **每个 sponsor 都是结构性承重，不是装饰**：KIMI = 路由的大脑；MiroMind = verification-centric 审计 + MiroFlow `deep-research` skill；Google Gemini 2.5 Flash = skill 的推理引擎。
- **从构造上就最小化信任**：任何人都能独立验证任意结果——不需要信任 marketplace 运营方。

*UCWS Singapore Hackathon 2026 · Skills Track · @duan + @ryan + 双 Claude Code*
