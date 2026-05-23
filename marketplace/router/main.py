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

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from router import plan_skill_chain, load_registry
from executor import execute_plan

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


@app.get("/health")
def health():
    return {"ok": True, "service": "veriforge-router"}


@app.get("/registry")
def get_registry():
    return load_registry()


@app.post("/route")
def route(req: RouteRequest):
    plan = plan_skill_chain(req.user_input)
    return plan.to_dict()


def _run_pipeline(user_input: str, session_id: str) -> None:
    import sys, traceback
    print(f"[run_pipeline] start session={session_id}", file=sys.stderr, flush=True)
    try:
        plan = plan_skill_chain(user_input)
        print(f"[run_pipeline] plan ok: n_skills={len(plan.skill_chain)} err={plan.error}", file=sys.stderr, flush=True)
        if plan.error:
            return
        r = execute_plan(plan.to_dict(), user_input, mode="http", session_id=session_id)
        print(f"[run_pipeline] done: n_steps={len(r.steps)} ok={sum(1 for s in r.steps if s.ok)} total_ms={r.total_ms}", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"[run_pipeline] EXCEPTION: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)


@app.post("/run")
def run(req: RunRequest, background_tasks: BackgroundTasks):
    session_id = req.session_id or uuid.uuid4().hex[:12]
    background_tasks.add_task(_run_pipeline, req.user_input, session_id)
    return {"session_id": session_id, "status": "started"}
