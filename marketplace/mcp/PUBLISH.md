# Publishing the VeriForge MCP server (make it discoverable)

The MCP server (`server.py`) exposes the marketplace to any MCP-capable agent via four
tools: `search_skills`, `list_skills`, `plan_skills`, `run_pipeline` (+ `get_result`).
Listing it on public registries is what turns "callable if you know the URL" into
"**discoverable** by agents that have never heard of VeriForge."

This folder ships everything a registry needs:

| File | Purpose |
|---|---|
| `server.py` / `backend.py` | the MCP server (stdio + streamable-http) |
| `requirements.txt` | Python deps |
| `Dockerfile` | container image, serves http on `$PORT` at `/mcp` |
| `smithery.yaml` | Smithery deployment manifest |

> **Prerequisite for *remote* installs:** a remotely-installed MCP server runs on the
> registry's infra, so it needs a **publicly reachable router**. Deploy the router
> (Cloud Run / Fly / Render) and use that URL as `veriforgeRouterUrl`. For purely local
> use (Claude Desktop on your machine), the stdio config below talks to `localhost:8000`.

---

## A. Smithery (smithery.ai) — widest reach

```bash
# 1. one-time
npm install -g @smithery/cli
smithery login

# 2. from this folder
cd marketplace/mcp
smithery deploy        # builds Dockerfile, validates smithery.yaml, lists the server
```

Or via the web UI: smithery.ai → **Add Server** → point at the GitHub repo,
**base directory** `marketplace/mcp`. Smithery reads `smithery.yaml` + `Dockerfile`
automatically. Once green, anyone can install it into Claude Desktop / Cursor in one click.

## B. Official MCP Registry (registry.modelcontextprotocol.io)

```bash
# 1. one-time
npm install -g @modelcontextprotocol/registry   # provides `mcp-publish`
# 2. create server.json (name, description, repository, remotes/packages), then:
mcp-publish        # authenticates via GitHub and submits
```
See https://github.com/modelcontextprotocol/registry for the `server.json` schema.

## C. mcp.so / Glama / PulseMCP — community indexes

These mostly **auto-crawl** public GitHub repos that contain an MCP server, or accept a
"submit" form with the repo URL. Submit `https://github.com/zhenyueD/veriforge`
(base dir `marketplace/mcp`). No extra files needed beyond what's here.

---

## D. Local install (no registry) — Claude Desktop / Cursor

Add to `claude_desktop_config.json` (Claude Desktop) or your MCP client config:

```jsonc
{
  "mcpServers": {
    "veriforge": {
      "command": "python",
      "args": ["/ABSOLUTE/PATH/veriforge/marketplace/mcp/server.py"],
      "env": { "VERIFORGE_ROUTER_URL": "http://localhost:8000" }
    }
  }
}
```

Restart the client; you'll see the `search_skills` / `run_pipeline` tools. Make sure the
router is up (`docker compose up -d`, or `uvicorn main:app` in `marketplace/router`).

---

## Smoke-test the http transport locally before publishing

```bash
cd marketplace/mcp
pip install -r requirements.txt
MCP_TRANSPORT=streamable-http PORT=8081 VERIFORGE_ROUTER_URL=http://localhost:8000 python server.py
# → serves MCP at http://localhost:8081/mcp
```
