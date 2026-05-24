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
from pydantic import BaseModel, Field

from router import plan_skill_chain, load_registry, upsert_skill
from executor import execute_plan
from veriforge import earnings_preview
import obs  # optional Langfuse tracing; no-op when not configured

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
