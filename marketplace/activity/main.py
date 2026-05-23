"""
FastAPI Activity Stream service.

  POST /emit           — emit an event (called by executor)
  GET  /session/:id    — replay all events for a session
  GET  /stream/:id     — long-poll (in-memory backend) or SSE — Day 3 dev uses
                         simple long-poll; the UI calls it on a loop.
  WS   /ws/:id         — websocket stream (optional, not used today)

In production, the frontend should subscribe to Supabase Realtime directly,
bypassing this service for stream reads. /emit + /session still go through here.

Run:
  uvicorn main:app --port 8002
"""
from __future__ import annotations
import os, sys, time
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from store import Event, EventKind, get_default_store

app = FastAPI(title="VeriForge Activity", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)
store = get_default_store()


class EmitRequest(BaseModel):
    session_id: str
    kind: str
    skill_id: Optional[str] = None
    trace_id: Optional[str] = None
    ts: Optional[float] = None
    data: dict = Field(default_factory=dict)


@app.get("/health")
def health():
    return {"ok": True, "service": "veriforge-activity", "backend": type(store).__name__}


@app.post("/emit")
def emit(req: EmitRequest):
    e = Event(
        session_id=req.session_id,
        kind=req.kind,
        skill_id=req.skill_id,
        trace_id=req.trace_id,
        ts=req.ts or time.time(),
        data=req.data,
    )
    store.emit(e)
    return {"ok": True, "ts": e.ts}


@app.get("/session/{session_id}")
def list_session(session_id: str):
    events = store.list_session(session_id)
    return {"session_id": session_id, "n_events": len(events),
            "events": [e.to_dict() for e in events]}


@app.get("/stream/{session_id}")
def stream(session_id: str, since: float = Query(default=0.0)):
    """
    Long-poll: returns new events since `since` (unix seconds), blocking up
    to 25s for at least one event. Frontend re-polls in a loop.
    Works only for InMemoryStore. Use Supabase Realtime directly for prod.
    """
    if not hasattr(store, "stream_session"):
        return {"events": [], "note": "Stream unavailable for this backend. Subscribe to Supabase Realtime instead."}
    events = store.stream_session(session_id, last_seen_ts=since, timeout=25.0)
    return {"events": [e.to_dict() for e in events],
            "now": time.time()}
