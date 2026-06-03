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

## Ready-to-run (the router is already live)

The router is deployed at **`https://vf-router-4plonm5r6a-as.a.run.app`** (Cloud Run,
Singapore), and `smithery.yaml` already defaults `veriforgeRouterUrl` to it — so a
Smithery-hosted MCP server works out of the box, no extra config.

**Recommended (one path): list on Smithery via the web UI.** Smithery deploys MCP servers
by connecting a GitHub repo — there is no `smithery deploy` publish command in the CLI
(the `smithery` CLI is a *consumer* tool for connecting to servers).

1. Go to **smithery.ai** → sign in with **GitHub**.
2. **Deploy a new MCP server** → connect repo **`zhenyueD/veriforge`**, base directory
   **`marketplace/mcp`**.
3. Smithery reads `smithery.yaml` + `Dockerfile`, builds, and hosts it (pointed at the
   live router by default). Once green, it's one-click installable into Claude Desktop / Cursor.

The official MCP Registry (section B) is **optional** and more involved (it needs the
server published as a package or a hosted remote URL first). mcp.so / Glama / PulseMCP
(section C) **auto-crawl** this public repo — no action needed.

---

## A. Smithery (smithery.ai) — widest reach

Smithery deploys by **connecting a GitHub repo via the web UI** (there is no publish
command in the `smithery` CLI — that CLI only *connects to* servers):

1. **smithery.ai** → sign in with GitHub.
2. **Deploy a new MCP server** → connect repo `zhenyueD/veriforge`, base directory
   `marketplace/mcp`.
3. Smithery reads `smithery.yaml` + `Dockerfile`, builds, and hosts it (pointed at the
   live router by default). Once green, one-click installable into Claude Desktop / Cursor.

## B. Official MCP Registry (registry.modelcontextprotocol.io) — optional

The official registry hosts **metadata only**, so it needs the server distributed as a
**package** (npm / PyPI / OCI image / MCPB) *or* a **hosted remote URL** (e.g. the
Smithery-hosted URL from section A) referenced in `server.json` first.

```bash
brew install mcp-publisher            # or download the prebuilt binary from the repo's releases
mcp-publisher login                   # GitHub OAuth — must log in as `zhenyueD`
                                      #   (namespace io.github.zhenyueD/* in server.json)
mcp-publisher publish                 # publishes server.json to the registry
```
Tool & guide: https://github.com/modelcontextprotocol/registry (`cmd/publisher`).

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
