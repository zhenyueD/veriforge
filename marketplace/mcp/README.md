# VeriForge MCP server — call the marketplace from any agent

This makes the VeriForge marketplace callable by any MCP-capable agent (Claude
Desktop, Claude Code, Cursor, OpenClaw). It's a **thin proxy** over the router —
no business logic, one backend.

Tools exposed: `list_skills`, `plan_skills`, `run_pipeline`, `get_result`.

## Run

```bash
cd marketplace/mcp
pip install -r requirements.txt
# point at a running VeriForge router (docker compose up -d first)
VERIFORGE_ROUTER_URL=http://localhost:8000 python server.py        # stdio
```

## Connect (Claude Desktop / Claude Code / OpenClaw)

```json
{
  "mcpServers": {
    "veriforge": {
      "command": "python",
      "args": ["server.py"],
      "cwd": "/absolute/path/to/veriforge/marketplace/mcp",
      "env": { "VERIFORGE_ROUTER_URL": "http://localhost:8000" }
    }
  }
}
```

Then ask the agent: *"List the VeriForge skills, then run the pipeline on
'My mug arrived cracked, order ORD-1234' and show me the audit trail."*

## Lightweight alternative (no MCP)

If you just want the skills as OpenAI/Anthropic function specs (for direct
LLM tool-calling), skip the MCP server and hit the router:

```bash
curl -s localhost:8000/skills/tools                 # OpenAI function format
curl -s 'localhost:8000/skills/tools?format=anthropic'   # Anthropic tool format
```

## Design

`backend.py` is the only module that talks to the backend, and only to the
router (which is the BFF over skills/audit/activity). `server.py` tools just
forward + wrap errors. Backend changes never break the agent integration.
