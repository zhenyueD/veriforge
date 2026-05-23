// Discord auto-translate bot — 中文/英文双向自动翻译
// 监听所有 channel，检测主要语言后翻译成另一语言，threading reply

const DISCORD_BOT_TOKEN = process.env.DISCORD_BOT_TOKEN;
const ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY;
const MODEL = process.env.MODEL || 'claude-haiku-4-5-20251001';
const MIN_LENGTH = Number(process.env.MIN_LENGTH || 5);
const PROXY_URL = process.env.HTTPS_PROXY || process.env.https_proxy;
const SOCKS_PROXY = process.env.SOCKS_PROXY;  // socks5://host:port — used for ws gateway (more reliable than HTTP CONNECT for long-lived WSS)

if (!DISCORD_BOT_TOKEN || !ANTHROPIC_API_KEY) {
  console.error('FATAL: DISCORD_BOT_TOKEN and ANTHROPIC_API_KEY required in env');
  process.exit(1);
}

// Proxy setup MUST run before importing discord.js (so the patched `ws` is in
// require.cache when discord.js's internal CJS code calls require('ws')).
if (PROXY_URL) {
  const { createRequire } = await import('module');
  const require = createRequire(import.meta.url);

  const OriginalWS = require('ws');
  let wsAgent;
  if (SOCKS_PROXY) {
    const { SocksProxyAgent } = require('socks-proxy-agent');
    wsAgent = new SocksProxyAgent(SOCKS_PROXY);
    console.log(`✓ ws via SOCKS5: ${SOCKS_PROXY}`);
  } else {
    const { HttpsProxyAgent } = require('https-proxy-agent');
    wsAgent = new HttpsProxyAgent(PROXY_URL);
    console.log(`✓ ws via HTTP CONNECT: ${PROXY_URL}`);
  }

  function ProxiedWebSocket(address, protocols, options) {
    // Normalize: ws(url, options) vs ws(url, protocols, options)
    if (protocols && typeof protocols === 'object' && !Array.isArray(protocols) && !(protocols instanceof Buffer)) {
      return new OriginalWS(address, { ...protocols, agent: wsAgent });
    }
    return new OriginalWS(address, protocols, { ...(options || {}), agent: wsAgent });
  }
  Object.setPrototypeOf(ProxiedWebSocket.prototype, OriginalWS.prototype);
  Object.setPrototypeOf(ProxiedWebSocket, OriginalWS);
  // Don't Object.assign — ws has read-only statics (CONNECTING/OPEN/CLOSING/CLOSED).
  // setPrototypeOf above makes static lookups fall through to OriginalWS.

  // @discordjs/ws uses `import { WebSocket } from 'ws'` (named export).
  // ws's index.js does `WebSocket.WebSocket = WebSocket` for that named export.
  // We must override the named export too, else discord.js gets OriginalWS.
  ProxiedWebSocket.WebSocket = ProxiedWebSocket;
  ProxiedWebSocket.default = ProxiedWebSocket;

  // Replace ws module's exported default with our proxy-aware constructor
  const wsPath = require.resolve('ws');
  require.cache[wsPath].exports = ProxiedWebSocket;

  // Undici handles REST API calls + any fetch() — route via proxy too
  const { setGlobalDispatcher, ProxyAgent } = await import('undici');
  setGlobalDispatcher(new ProxyAgent(PROXY_URL));

  console.log(`✓ proxy enabled (ws + undici): ${PROXY_URL}`);
}

// Dynamic imports so patching above runs first
const { Client, GatewayIntentBits, Partials } = await import('discord.js');

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
  ],
  partials: [Partials.Channel, Partials.Message],
});

// Simple LRU cache: same message → same translation (saves cost)
const cache = new Map();
const CACHE_MAX = 500;

function detectLanguage(text) {
  const cjkChars = (text.match(/[一-鿿]/g) || []).length;
  const totalChars = text.replace(/\s/g, '').length;
  if (totalChars === 0) return 'unknown';
  return cjkChars / totalChars > 0.3 ? 'zh' : 'en';
}

function shouldSkip(msg) {
  if (msg.author.bot) return 'bot';
  if (!msg.content || msg.content.length < MIN_LENGTH) return 'too-short';
  if (msg.content.startsWith('!') || msg.content.startsWith('/')) return 'command';
  if (msg.content.startsWith('```')) return 'code-block';
  if (/^https?:\/\/\S+$/.test(msg.content.trim())) return 'pure-url';
  if (msg.content.length > 2000) return 'too-long';
  return null;
}

// Plain fetch instead of @anthropic-ai/sdk — SDK headers trigger 403 from certain egress IPs.
async function translate(text, targetLang) {
  const cacheKey = `${targetLang}:${text}`;
  if (cache.has(cacheKey)) return cache.get(cacheKey);

  const targetName = targetLang === 'zh' ? '简体中文' : 'English';
  const res = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'x-api-key': ANTHROPIC_API_KEY,
      'anthropic-version': '2023-06-01',
      'content-type': 'application/json',
    },
    body: JSON.stringify({
      model: MODEL,
      max_tokens: 500,
      messages: [{
        role: 'user',
        content: `Translate the following message to ${targetName}. Output ONLY the translation, no preamble, no quotes, no explanation. Preserve code, URLs, @mentions, and emoji as-is.\n\n---\n${text}\n---`,
      }],
    }),
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`anthropic ${res.status}: ${body.slice(0, 200)}`);
  }

  const data = await res.json();
  const translation = data?.content?.[0]?.text?.trim() || '(translation failed)';

  if (cache.size >= CACHE_MAX) cache.delete(cache.keys().next().value);
  cache.set(cacheKey, translation);

  return translation;
}

client.on('messageCreate', async (msg) => {
  const skip = shouldSkip(msg);
  if (skip) return;

  const sourceLang = detectLanguage(msg.content);
  if (sourceLang === 'unknown') return;
  const targetLang = sourceLang === 'zh' ? 'en' : 'zh';

  try {
    const translation = await translate(msg.content, targetLang);
    if (translation === msg.content.trim()) return;

    const flag = targetLang === 'zh' ? '🇨🇳' : '🇬🇧';
    await msg.reply({
      content: `${flag} ${translation}`,
      allowedMentions: { repliedUser: false, parse: [] },
    });
  } catch (err) {
    console.error('translate error:', err?.message || err);
  }
});

client.once('clientReady', () => {
  console.log(`✓ logged in as ${client.user.tag}`);
});

client.on('error', (err) => console.error('client error:', err?.message || err));

client.login(DISCORD_BOT_TOKEN);
