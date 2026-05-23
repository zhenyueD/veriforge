# Discord Translate Bot (中文 ↔ English)

监听所有 channel 消息，自动检测语言，翻译成另一语言，threading reply。

## Setup (10 分钟)

### Step 1: 创建 Discord bot

1. 打开 https://discord.com/developers/applications
2. 点 **New Application** → 命名 `TeamTranslate`
3. 左侧 **Bot** → **Reset Token** → 复制 token 存好
4. **Privileged Gateway Intents** → 打开 **MESSAGE CONTENT INTENT**
5. 左侧 **OAuth2** → **URL Generator** → 勾 `bot` scope + `Send Messages` `Read Message History` `Read Messages/View Channels` permissions
6. 复制生成的 URL → 浏览器打开 → 邀请 bot 进你的 server

### Step 2: 本机跑（最简）

```bash
cd discord-translate-bot
npm install
bash fill-env.sh    # 交互式填 DISCORD_BOT_TOKEN + ANTHROPIC_API_KEY（不进 shell history）
node --env-file=.env index.js
```

跑起来后看到 `✓ logged in as TeamTranslate#XXXX`，Discord channel 里任何消息会被自动翻译。

### Step 3 (推荐): 用 PM2 守护

```bash
npm install -g pm2
pm2 start index.js --name translate-bot --node-args="--env-file=.env"
pm2 save
pm2 startup  # 一次性配置开机自启
```

### Step 4 (可选): 部署到 Railway

```bash
brew install railway
railway login && railway init
railway variables set DISCORD_BOT_TOKEN=xxx ANTHROPIC_API_KEY=yyy
railway up
```

免费 tier 500 hours/月，hackathon 5 天 = 120 小时，绰绰有余。

## 中国大陆部署的 7 个坑（必读）

如果你在中国大陆部署，下面是 2026-05-23 实战踩过的所有坑 + 修法。海外用户可跳过。

### 坑 1: Discord gateway WSS 直连被墙

**修法**：在 `.env` 里加：
```
HTTPS_PROXY=http://127.0.0.1:7890     # undici REST 走 HTTP CONNECT
SOCKS_PROXY=socks5://127.0.0.1:7891   # ws gateway 走 SOCKS5（关键）
```
端口按你 Clash / V2Ray 的配置改。

**为什么 ws 用 SOCKS5 不用 HTTP**：HTTP CONNECT 对 Discord gateway 的长连接 WSS 不友好，handshake 阶段就 30s timeout。SOCKS5 是 raw TCP tunnel，对 WSS 完全透明。

### 坑 2: `@anthropic-ai/sdk` 在代理后 403

某些代理出口 IP + SDK 的 stainless headers 组合触发 Anthropic 的 abuse policy。本 bot **已经改用 raw fetch**，不再用 SDK。如果你想用 SDK，先 curl 测一下：

```bash
curl --proxy http://127.0.0.1:7890 https://api.anthropic.com/v1/messages \
  -H "x-api-key: $YOUR_KEY" -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-haiku-4-5-20251001","max_tokens":20,"messages":[{"role":"user","content":"hi"}]}'
```
返回 200 = key 和代理都 OK，可放心。

### 坑 3: Discord 网页版被 Chrome 自动翻译破坏

Chrome 把整个 Discord 网页（含 React 输入框）翻译，导致按 Enter 消息发不出。

**修法**：地址栏 Google Translate 图标 → **Never translate this site**。或换 Safari，或装 Discord desktop app。

### 坑 4: Discord 客户端本身要走代理

bot 走我们 hardcode 的 proxy，但 **Discord 桌面/网页客户端不知道**。开 **Clash TUN 模式**接管所有系统流量，或在 macOS System Settings → Network → Proxies 设全局 HTTP/HTTPS proxy。

### 坑 5: GitHub Actions push 需要 workflow scope

如果你想把 `.github/workflows/` 推到 GitHub 但被拒：
```bash
gh auth refresh -h github.com -s workflow
```

### 坑 6: git push via HTTPS proxy 不稳定

`curl` 通 GitHub 但 `git push` 反复 timeout 时，绕过 git 用 `gh api`：
```bash
content_b64=$(base64 -i file)
gh api -X PUT "repos/owner/repo/contents/path" -f content="$content_b64" -f message="msg"
```

### 坑 7: ws monkey-patch 必须覆盖 named export

如果你自己改这个 bot 或写类似项目，patch `ws` 的时候不要只换 `module.exports`，还要：
```js
ProxiedWebSocket.WebSocket = ProxiedWebSocket;  // @discordjs/ws 用 named import
```
`index.js` 里已经处理好了。

详细技术分析见 [@duan 的 Obsidian 笔记](#)（China 部署陷阱完整时间线）。

## 行为细节

- **跳过翻译**：bot 消息 / < 5 字 / `!` `/` 开头（命令）/ ` ``` ` 开头（代码块）/ 纯 URL / > 2000 字
- **语言检测**：CJK 字符比例 > 30% → 翻译成英文，否则翻译成中文
- **缓存**：LRU 500 entries，同消息不重复调 API
- **回复**：threading reply，`🇨🇳` / `🇬🇧` 标签
- **失败**：API 失败 silent fallback（不打断聊天），错误打 stderr

## 成本估算

Claude Haiku 4.5: ~$1/M input + $5/M output。每条消息约 100 in + 100 out tokens ≈ $0.0006。

每天 200 条消息 = $0.12/day。Hackathon 5 天 = **$0.60**。

## 调试

```bash
pm2 logs translate-bot --lines 30
tail -f ~/.pm2/logs/translate-bot-out.log
tail -f ~/.pm2/logs/translate-bot-error.log
```

## 配置项（`.env`）

| 变量 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `DISCORD_BOT_TOKEN` | ✓ | — | Discord dev portal 拿 |
| `ANTHROPIC_API_KEY` | ✓ | — | console.anthropic.com 拿 |
| `MODEL` | | `claude-haiku-4-5-20251001` | 翻译模型 |
| `MIN_LENGTH` | | `5` | 短于这个长度的消息不翻译 |
| `HTTPS_PROXY` | 中国用户必填 | — | undici REST 代理（`http://...`） |
| `SOCKS_PROXY` | 中国用户必填 | — | ws gateway 代理（`socks5://...`，比 HTTP 稳） |

## 已知限制

- 不能翻译图片 OCR / 文件附件
- 不识别第三种语言（粤语 / 日文 / 韩文等会被当英文翻成中文）
- 多人同时打字时 reply 顺序可能错乱（无 transaction，但实际几乎不会）

## License

MIT.
