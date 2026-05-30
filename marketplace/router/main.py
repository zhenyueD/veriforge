"""
FastAPI router + execution endpoint.

  POST /route  — return KIMI's planned skill chain (no execution)
  POST /run    — route + execute the full chain in background;
                 returns session_id immediately so the UI can subscribe to
                 the activity stream for live updates.
  GET  /health
  GET  /registry

Run:
  uvicorn main:app --port 8000
"""
from __future__ import annotations
import os, sys, uuid
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "sdk"))

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from router import plan_skill_chain, load_registry, upsert_skill
from executor import execute_plan, emit_event
from veriforge import earnings_preview
import discovery  # semantic + verified-reputation skill search
import obs      # optional Langfuse tracing; no-op when not configured
import shield   # prompt-injection guard on user_input

SHIELD_BLOCK = os.getenv("VERIFORGE_SHIELD_BLOCK", "1") != "0"
PUBLIC_API_URL = os.getenv("VERIFORGE_PUBLIC_URL", "http://localhost:8000")

app = FastAPI(title="VeriForge Router", version="0.1.0")

# Allow the web UI (different origin) to call us
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


class RouteRequest(BaseModel):
    user_input: str


class RunRequest(BaseModel):
    user_input: str
    session_id: Optional[str] = None


class ReVerifyRequest(BaseModel):
    """Optional live-proof inputs: {skill_id: {"input": {...}, "output": {...}}}."""
    replay: dict = Field(default_factory=dict)


class RegisterRequest(BaseModel):
    """Skill manifest posted by the veriforge SDK on startup, or a 'List your skill' form."""
    id: str
    pay_to: str
    price_usdc: float = Field(ge=0)
    name: str = ""
    endpoint: str = ""
    description: str = ""
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    llm_compat: list[str] = Field(default_factory=list)
    public_key: str = ""   # ed25519 Proof-of-Skill key (creator-held; operator can't forge)


@app.get("/health")
def health():
    return {"ok": True, "service": "veriforge-router"}


@app.get("/registry")
def get_registry():
    return load_registry()


@app.get("/skills")
def list_skills():
    """Registry enriched with a computed earnings preview — the UI consumes this directly."""
    reg = load_registry()
    out = []
    for s in reg.get("skills", []):
        price = s.get("price_usdc", 0)
        out.append({
            "id": s["id"],
            "name": s.get("name", s["id"]),
            "description": s.get("description", ""),
            "price_usdc": price,
            "pay_to": s.get("pay_to", ""),
            "public_key": s.get("public_key", ""),   # ed25519 — verify Proof-of-Skill signatures
            "earnings_preview": earnings_preview(price),
            "endpoint": s.get("endpoint", ""),
            "tags": s.get("tags", []),
            "llm_compat": s.get("llm_compat", []),
        })
    return {"version": reg.get("version"), "updated_at": reg.get("updated_at"), "skills": out}


@app.post("/register")
def register(req: RegisterRequest):
    """Self-registration: insert or update a skill in the marketplace registry by id."""
    skill, created = upsert_skill(req.model_dump())
    return {"ok": True, "created": created, "skill_id": skill["id"], "skill": skill}


def _param_type(field: str) -> str:
    if field.startswith(("has_", "is_")):
        return "boolean"
    if field.endswith("_cents") or field in {"severity", "score", "intensity", "max_bullets", "prior_score"}:
        return "integer"
    return "string"


def _input_schema(skill: dict) -> dict:
    inputs = skill.get("inputs", [])
    props = {f: {"type": _param_type(f)} for f in inputs}
    required = [inputs[0]] if inputs else []
    return {"type": "object", "properties": props, "required": required}


@app.get("/skills/tools")
def skills_as_tools(format: str = "openai"):
    """
    Export the registry as LLM tool/function specs so ANY agent (OpenAI, Anthropic,
    or MCP) can discover and call these skills. The 'cross-LLM' promise, one curl away.
    Param schemas are derived from registry `inputs`; the authoritative schema per skill
    is its skill.yaml. format=openai (default) | anthropic.
    """
    reg = load_registry()
    tools = []
    for s in reg.get("skills", []):
        name = s["id"].replace("-", "_")
        desc = f"{s.get('description','')} [price {s.get('price_usdc',0)} USDC/call, pays {s.get('pay_to','')[:12]}…]"
        schema = _input_schema(s)
        if format == "anthropic":
            tools.append({"name": name, "description": desc, "input_schema": schema})
        else:
            tools.append({"type": "function",
                          "function": {"name": name, "description": desc, "parameters": schema}})
    return {"format": format, "count": len(tools), "tools": tools}


def _tool_spec(skill: dict, format: str) -> dict:
    """One skill → an LLM-callable tool spec (OpenAI function or Anthropic tool)."""
    name = skill["id"].replace("-", "_")
    desc = f"{skill.get('description','')} [price {skill.get('price_usdc',0)} USDC/call]"
    schema = _input_schema(skill)
    if format == "anthropic":
        return {"name": name, "description": desc, "input_schema": schema}
    return {"type": "function",
            "function": {"name": name, "description": desc, "parameters": schema}}


@app.get("/skills/search")
def skills_search(q: str, top_k: int = 5, rank: str = "relevance", format: str = "openai"):
    """
    Discover skills by natural-language task — the scalable alternative to dumping the
    whole registry into an agent's context. ANY agent asks "what can do X?" and gets back
    ranked, directly-callable tool specs.

      q       : the task, e.g. "detect if a product photo was tampered with"
      rank    : "relevance" (semantic match) | "verified" (blend match + on-chain
                verified reputation — discover the skill you can actually trust)
      format  : tool-spec dialect for the attached `tool` field (openai | anthropic)

    Semantic ranking uses Gemini embeddings when GOOGLE_API_KEY is set, else a
    dependency-free lexical fallback (see `method` in the response).
    """
    reg = load_registry()
    res = discovery.search(q, reg.get("skills", []), top_k=top_k, rank=rank)
    by_id = {s["id"]: s for s in reg.get("skills", [])}
    for r in res["results"]:
        r["tool"] = _tool_spec(by_id[r["id"]], format)  # ready to drop into a tool-call
    res["tool_format"] = format
    return res


# ─────────────────── self-describing manifests (zero-config discovery) ───────────────────
@app.get("/.well-known/ai-plugin.json")
def ai_plugin_manifest():
    """OpenAI-style plugin manifest so agent frameworks auto-discover the marketplace."""
    return {
        "schema_version": "v1",
        "name_for_model": "veriforge",
        "name_for_human": "VeriForge Skill Marketplace",
        "description_for_model": (
            "Discover, call, pay-per-use, and cryptographically verify AI skills. "
            "GET /skills/search?q=<task>&rank=verified to find skills ranked by relevance "
            "and on-chain verified reputation; each result includes a ready-to-call tool spec. "
            "GET /skills/tools for the full tool list. Every call is x402-paid and SHA-256 "
            "audit-chained; verify any result at GET /verify/<trace_id>."
        ),
        "description_for_human": "The App Store for verifiable AI skills.",
        "auth": {"type": "none"},
        "api": {"type": "openapi", "url": f"{PUBLIC_API_URL}/openapi.json"},
        "logo_url": f"{PUBLIC_API_URL}/logo.png",
    }


@app.get("/.well-known/agent.json")
def a2a_agent_card():
    """A2A (Agent2Agent) agent card — lets agent-to-agent runtimes discover capabilities."""
    reg = load_registry()
    return {
        "name": "VeriForge",
        "description": "Marketplace of verifiable, pay-per-call AI skills.",
        "url": PUBLIC_API_URL,
        "version": reg.get("version", "0.1.0"),
        "capabilities": {"streaming": False, "pushNotifications": False},
        "defaultInputModes": ["text"],
        "defaultOutputModes": ["application/json"],
        "skills": [
            {
                "id": s["id"],
                "name": s.get("name", s["id"]),
                "description": s.get("description", ""),
                "tags": s.get("tags", []),
            }
            for s in reg.get("skills", [])
        ],
    }


@app.get("/llms.txt", response_class=PlainTextResponse)
def llms_txt():
    """LLM-readable index (llms.txt convention) — a crawlable map of the marketplace."""
    reg = load_registry()
    lines = [
        "# VeriForge — The App Store for verifiable AI skills",
        "",
        "> Discover, call, pay-per-call (USDC), and cryptographically verify AI skills.",
        "> Every invocation is SHA-256 audit-chained and ed25519 Proof-of-Skill signed.",
        "",
        "## Discovery",
        f"- Semantic search: GET {PUBLIC_API_URL}/skills/search?q=<task>&rank=verified",
        f"- All tools (OpenAI/Anthropic): GET {PUBLIC_API_URL}/skills/tools?format=openai",
        f"- OpenAPI spec: GET {PUBLIC_API_URL}/openapi.json",
        f"- Public verification: GET {PUBLIC_API_URL.replace('8000','8001')}/verify/<trace_id>",
        "",
        "## Skills",
    ]
    for s in reg.get("skills", []):
        lines.append(f"- {s['id']} ({s.get('price_usdc',0)} USDC): {s.get('description','')}")
    return "\n".join(lines) + "\n"


@app.post("/route")
def route(req: RouteRequest):
    plan = plan_skill_chain(req.user_input)
    return plan.to_dict()


@obs.observe(name="skill-pipeline")
def _run_pipeline(user_input: str, session_id: str) -> None:
    import sys, traceback
    print(f"[run_pipeline] start session={session_id}", file=sys.stderr, flush=True)
    obs.update_trace(session_id=session_id, input={"user_input": user_input[:500]},
                     tags=["veriforge", "skill-pipeline"], metadata={"version": "0.2.0"})

    # Prompt-injection shield: scan user_input before it reaches KIMI or any skill's Gemini call.
    guard = shield.check_input(user_input)
    emit_event(session_id, "shield_check", data={"verdict": guard["verdict"], "detector": guard.get("detector")})
    if guard["verdict"] == "flagged" and SHIELD_BLOCK:
        emit_event(session_id, "shield_blocked", data=guard)
        obs.update_trace(metadata={"shield": "blocked", "matched_pattern": guard.get("matched_pattern")})
        obs.score("shield_blocked", 1, data_type="BOOLEAN")
        print(f"[run_pipeline] BLOCKED by shield: {guard}", file=sys.stderr, flush=True)
        obs.flush()
        return

    try:
        plan = plan_skill_chain(user_input)
        print(f"[run_pipeline] plan ok: n_skills={len(plan.skill_chain)} err={plan.error}", file=sys.stderr, flush=True)
        if plan.error:
            return
        r = execute_plan(plan.to_dict(), user_input, mode="http", session_id=session_id)
        n_ok = sum(1 for s in r.steps if s.ok)
        print(f"[run_pipeline] done: n_steps={len(r.steps)} ok={n_ok} total_ms={r.total_ms}", file=sys.stderr, flush=True)
        # Pipeline-level scores for the dashboard (latency always available).
        obs.score("pipeline_latency_ms", r.total_ms, data_type="NUMERIC")
        obs.score("skills_ok_ratio", (n_ok / len(r.steps)) if r.steps else 0.0, data_type="NUMERIC")
    except Exception as e:
        print(f"[run_pipeline] EXCEPTION: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)
    finally:
        obs.flush()  # background task ends here; flush or events are lost


@app.post("/run")
def run(req: RunRequest, background_tasks: BackgroundTasks):
    session_id = req.session_id or uuid.uuid4().hex[:12]
    background_tasks.add_task(_run_pipeline, req.user_input, session_id)
    return {"session_id": session_id, "status": "started"}


@app.get("/result/{session_id}")
def result(session_id: str):
    """
    BFF: fetch a finished pipeline's audit entries (with settlement + trust) for a
    session. Lets a single upstream (e.g. the MCP proxy) talk only to the router.
    """
    import urllib.request
    audit_url = os.getenv("AUDIT_URL", "http://localhost:8001")
    try:
        with urllib.request.urlopen(f"{audit_url}/session/{session_id}", timeout=5) as r:
            import json as _json
            return _json.loads(r.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001 — surface as a clean payload, don't 500
        return {"session_id": session_id, "entries": [], "error": str(e)}


@app.post("/re-verify/{trace_id}")
def re_verify_trace(trace_id: str, req: ReVerifyRequest | None = None):
    """
    Feature B — honest, type-aware re-verification. Chain integrity + ed25519
    attribution for every step; deterministic skills are re-executable (prove it
    live via `replay`), LLM skills are verified by signature + invariants, never by
    re-hashing (which would false-positive). Judge one-liner: POST with no body.
    """
    import reverify
    replay = req.replay if req else {}
    return reverify.re_verify(trace_id, replay=replay)


@app.post("/demo/seed")
def demo_seed():
    """Seed a real signed + audited session (deterministic fraud-image) so the
    cockpit can demo tamper → /re-verify naming the offending skill. Demo cockpit only."""
    import demo
    return demo.seed_audit_session()


@app.post("/demo/{scenario}")
def demo_scenario(scenario: str):
    """Run one 'catch the cheat' scenario server-side and return the real evidence."""
    import demo
    fn = demo.SCENARIOS.get(scenario)
    if not fn:
        return {"error": f"unknown scenario {scenario!r}", "available": list(demo.SCENARIOS)}
    return fn()
