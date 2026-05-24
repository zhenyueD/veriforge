"""
VeriForge MCP server — exposes the skill marketplace to any MCP-capable agent
(Claude Desktop, Claude Code, Cursor, OpenClaw, …).

Thin proxy discipline: every tool just validates args, forwards to the router
(backend.py), and wraps errors. No DB, no LLM, no business logic here.

Run:
  pip install -r requirements.txt
  VERIFORGE_ROUTER_URL=http://localhost:8000 python server.py        # stdio (default)
  MCP_TRANSPORT=streamable-http python server.py                     # http
"""
from __future__ import annotations

import os
from typing import Any

from mcp.server.fastmcp import FastMCP

import backend

mcp = FastMCP("veriforge")


@mcp.tool()
async def list_skills() -> dict[str, Any]:
    """List every skill on the VeriForge marketplace with its price, payout address,
    and per-call earnings split. Call this first to discover what you can invoke.

    Returns:
        { skills: [ { id, name, description, price_usdc, pay_to, earnings_preview, tags } ] }
    """
    try:
        return await backend.list_skills()
    except Exception as e:  # noqa: BLE001
        return {"error": True, "message": f"could not list skills: {e}"}


@mcp.tool()
async def plan_skills(user_input: str) -> dict[str, Any]:
    """Ask the KIMI router which skills (and in what order) would serve a request,
    WITHOUT executing or paying. Use to preview the plan.

    Args:
        user_input: The end-user request, e.g. "My mug arrived cracked. Order ORD-1234."
    Returns:
        { skill_chain: [{skill_id, reason}], input_summary, reasoning, latency_ms }
    """
    try:
        return await backend.plan_skills(user_input)
    except Exception as e:  # noqa: BLE001
        return {"error": True, "message": f"could not plan: {e}"}


@mcp.tool()
async def run_pipeline(user_input: str) -> dict[str, Any]:
    """Execute the full skill chain for a request: the router plans it, pays each
    skill per call (x402), and audit-chains every step. Returns immediately with a
    session_id; call get_result(session_id) after a few seconds for the outcome.

    Args:
        user_input: The end-user request to process.
    Returns:
        { session_id, status }
    """
    try:
        return await backend.run_pipeline(user_input)
    except Exception as e:  # noqa: BLE001
        return {"error": True, "message": f"could not run pipeline: {e}"}


@mcp.tool()
async def get_result(session_id: str) -> dict[str, Any]:
    """Fetch a finished pipeline's audit entries for a session: each skill's hashes,
    payment settlement (creator cut + platform fee), and trust score.

    Args:
        session_id: The id returned by run_pipeline.
    Returns:
        { session_id, n_entries, entries: [...] }
    """
    try:
        return await backend.get_result(session_id)
    except Exception as e:  # noqa: BLE001
        return {"error": True, "message": f"could not get result: {e}"}


if __name__ == "__main__":
    mcp.run(transport=os.getenv("MCP_TRANSPORT", "stdio"))
