# VeriForge — Demo Day 一页 Pitch（中文版）

> **agent 经济的信任与结算层 —— 长在 MCP 上的「AI skill 版 Stripe」。**
> 一行代码包住任意函数 → 任何 agent 都能发现它、按次付费、拿走一张谁都能离线验真的收据。

---

## 15 秒 hook

> *"ClaimsForge 上个 hackathon 没获奖——输的不是技术,是叙事:一个没人能复用的垂直 6-agent
> 保险 demo。我把它拆成了 VeriForge。现在每个 agent 都是一个**任何 agent 都能调用、付费、验证的
> skill**,而且验证凭证跟着它走。"*

---

## 它到底是什么(定位)

当 agent 开始**跨平台互相付费**调用 skill 时,它们会需要人类当年需要的东西:一个中立的方式去
**信任、结算、了结纠纷**——在机器速度下、跨厂商边界。这层现在还不存在。

VeriForge 在建它:**不是又一个跟 OpenAI 竞争的 skill 商店,而是商店之间的中立层**——Visa/Stripe
的位置。它骑在已经赢了的 agent–工具连接协议(**MCP**)上,补上 MCP 留下的洞:*这个 skill 靠谱吗?
怎么付钱?出纠纷时拿什么裁?*

**巨头为什么不直接做?** 技术他们一周就能写——那不是护城河。他们不会做**中立、跨厂商**的版本,
因为那拆自己的锁定、帮对手(OpenAI 不会让 GPT skill 在 Claude 里一样能调、还能带走信誉)。信任
基础设施天然由**非参与方**运营——Visa 不是银行,Experian 不是放贷方,Sigstore 是中立基金会。
**那个位置才是护城河,而单一 LLM 厂商坐不进去。**

---

## 四根承重柱(每根都是结构,不是 logo)

| # | 柱 | 做什么 | 代码 |
|---|---|---|---|
| ① | **一行 monetize + 跨 LLM 调用** | 任意 FastAPI skill 加 `monetize(...)`;registry 导出成 OpenAI/Anthropic function spec **和** MCP 工具——任何 agent 一条 curl 就能发现并调用 | `sdk/veriforge.py`、`marketplace/router/main.py`、`marketplace/mcp/server.py` |
| ② | **零 RAG 路由 + 编排** | KIMI `moonshot-v1-128k` 把**整个** registry 装进 context 规划 skill 链——无向量库;executor 走 HTTP 执行 | `/route`、`/run`、`executor.py` |
| ③ | **x402 按次付费 + 收益分成** | 每次调用带 `X-Payment` 头;创作者分账 + 平台费自动算;UI 实时显示收益 | `sdk/veriforge.py`(`attach_x402`、`compute_split`) |
| ④ | **自验证收据(护城河的具象)** | 每次调用产出一张可携带收据:ed25519 **Proof-of-Skill** 签名(创作者自持密钥——运营方**伪造不了**)+ SHA-256 审计链。**你不用信 VeriForge——你验数学。** | `marketplace/audit/`(`/receipt/:tid`)、`scripts/verify_receipt.py` |

外加飞轮:每次验证过的调用变成**信誉**,发现按信誉排序(`/skills/search?rank=verified`)——
市场**学会该信任哪个 skill**,被证明的 skill 更易被发现。**越用越强。**

---

## 自带 skill —— 就这一行

```python
from fastapi import FastAPI
from veriforge import monetize

app = FastAPI()
monetize(app, skill_id="my-skill", price_usdc=0.02, pay_to="0xYourWallet")
# → x402 按次付费门 · 创作者+平台分成 · 自注册 · 每次输出自动签名
```

作者自己托管端点、自己持签名私钥;VeriForge 管发现、路由、计费、可验证收据。(供给侧 demo:`examples/external-skill/`)

---

## 30 秒现场 demo

1. 开 `http://localhost:3001` —— 11 个带价 skill 的市场。
2. **搜索** *"detect a faked or damaged product photo"* → 切 **Relevance ↔ Trust-ranked**:
   最"亮眼"的那个下沉,**被证明过**的爬升(▲)。发现靠**证据**排序,不靠感觉。
3. 输入 **"My ceramic mug arrived cracked. Order ORD-1234."** → KIMI 路由 skill 链;
   实时流显示每次调用付一笔创作者+平台分成、审计链增长。
4. 点某步的 **[receipt]** → 存下 JSON → 在一台**从没听过 VeriForge 的机器**上跑
   `scripts/verify_receipt.py`:**✅ 通过**。改任一字段 → **❌**——被数学抓出。

---

## 为什么赢

- **解决 ClaimsForge 死因:** 叙事从"一个垂直 agent"跃到"中立的协议层"。
- **每个 sponsor 都是承重:** KIMI = 零 RAG registry-in-context 路由;MiroMind = verification-centric 审计 + MiroFlow `deep-research` skill;Google Cloud + Gemini = skill 推理 + embedding 排序发现,**已上 Cloud Run(新加坡)实时运行**。
- **诚实的护城河:** 密码学可复制,但**中立、跨厂商的位置**不可复制——而那正是围墙花园结构上不愿坐的位置。

*UCWS Singapore Hackathon 2026 · Skills Track · @duan + @ryan + 2 Claude Codes*
