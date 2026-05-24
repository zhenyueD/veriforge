"""
Async HTTP forwarders to the VeriForge router. The MCP server is a thin proxy:
this module is the ONLY place that talks to the backend, and it talks to exactly
one backend (the router, which is itself the BFF over skills/audit/activity).
No business logic lives here — just forward + raise.
"""
from __future__ import annotations

import os
from typing import Any, Optional

import httpx

ROUTER_URL = os.getenv("VERIFORGE_ROUTER_URL", "http://localhost:8000")

_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(base_url=ROUTER_URL, timeout=90.0)
    return _client


async def list_skills() -> dict[str, Any]:
    r = await _get_client().get("/skills")
    r.raise_for_status()
    return r.json()


async def plan_skills(user_input: str) -> dict[str, Any]:
    r = await _get_client().post("/route", json={"user_input": user_input})
    r.raise_for_status()
    return r.json()


async def run_pipeline(user_input: str) -> dict[str, Any]:
    r = await _get_client().post("/run", json={"user_input": user_input})
    r.raise_for_status()
    return r.json()


async def get_result(session_id: str) -> dict[str, Any]:
    r = await _get_client().get(f"/result/{session_id}")
    r.raise_for_status()
    return r.json()
