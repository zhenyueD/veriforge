"""
FastAPI audit chain service.

Endpoints:
  POST /append            — append a new entry to a session chain
  GET  /session/:id       — return all entries for a session
  GET  /verify/:trace_id  — fetch the entry + verify the full session chain it sits in

This is the public-facing /verify endpoint mentioned in PROJECT.md §8 —
judges paste a trace_id and get back the full audit + re-verification.

Run (with in-memory store, dev mode):
  uvicorn main:app --port 8001

Run (with Supabase):
  SUPABASE_URL=... SUPABASE_SERVICE_KEY=... uvicorn main:app --port 8001
"""
from __future__ import annotations
import os, sys, time, uuid
from typing import Optional

# Add this dir to path so `from chain import ...` works inside the service
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from chain import (
    AuditEntry, GENESIS_HASH,
    compute_chain_hash, make_entry, verify_chain,
)
from store import get_default_store

app = FastAPI(title="VeriForge Audit Chain", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)
store = get_default_store()


class AppendRequest(BaseModel):
    session_id: str
    seq: int = Field(ge=0)
    skill_id: str
    trace_id: str
    input_hash: str
    output_hash: str
    verify_passed: Optional[bool] = None
    elapsed_ms: int = 0
    extra: dict = Field(default_factory=dict)


class AppendResponse(BaseModel):
    chain_hash: str
    prev_chain_hash: str
    entry: dict


@app.get("/health")
def health():
    return {"ok": True, "service": "veriforge-audit", "backend": type(store).__name__}


@app.post("/append", response_model=AppendResponse)
def append_entry(req: AppendRequest):
    prior = store.get_session(req.session_id)
    if prior:
        if prior[-1].seq + 1 != req.seq:
            raise HTTPException(
                400,
                f"seq mismatch: expected {prior[-1].seq + 1}, got {req.seq}",
            )
        prev_hash = prior[-1].chain_hash
    else:
        if req.seq != 0:
            raise HTTPException(400, f"new session must start at seq=0, got {req.seq}")
        prev_hash = GENESIS_HASH

    entry = make_entry(
        session_id=req.session_id,
        seq=req.seq,
        skill_id=req.skill_id,
        trace_id=req.trace_id,
        input_hash=req.input_hash,
        output_hash=req.output_hash,
        verify_passed=req.verify_passed,
        elapsed_ms=req.elapsed_ms,
        extra=req.extra,
        prev_chain_hash=prev_hash,
    )
    store.append(entry)
    return AppendResponse(
        chain_hash=entry.chain_hash,
        prev_chain_hash=entry.prev_chain_hash,
        entry=entry.to_dict(),
    )


@app.get("/session/{session_id}")
def get_session(session_id: str):
    entries = store.get_session(session_id)
    return {
        "session_id": session_id,
        "n_entries": len(entries),
        "entries": [e.to_dict() for e in entries],
    }


class TamperRequest(BaseModel):
    session_id: str
    seq: int = Field(ge=0)
    target: str = "signature"  # signature | pubkey | output_hash


@app.post("/admin/tamper")
def admin_tamper(req: TamperRequest):
    """
    DEMO-ONLY: corrupt one stored audit field so /verify and /re-verify go red.
    Gated by VERIFORGE_DEMO=1 and in-memory store only (never touches prod data).
    """
    if os.getenv("VERIFORGE_DEMO", "0") != "1":
        raise HTTPException(403, "fault injection disabled (set VERIFORGE_DEMO=1)")
    if not hasattr(store, "tamper"):
        raise HTTPException(400, "tamper only supported on the in-memory store")
    entry = store.tamper(req.session_id, req.seq, req.target)
    if not entry:
        raise HTTPException(404, f"no entry at session={req.session_id} seq={req.seq}")
    return {"ok": True, "tampered": req.target, "skill_id": entry.skill_id, "seq": entry.seq}


@app.get("/verify/{trace_id}")
def verify_trace(trace_id: str):
    """
    The public judge-facing endpoint. Given a trace_id, find which session
    it belongs to and verify the full chain. Returns the chain + verification.
    """
    entry = store.get_by_trace(trace_id)
    if not entry:
        raise HTTPException(404, f"trace_id={trace_id!r} not found")
    full = store.get_session(entry.session_id)
    ok, errors = verify_chain(full)
    return {
        "trace_id": trace_id,
        "session_id": entry.session_id,
        "found_entry": entry.to_dict(),
        "chain_verified": ok,
        "chain_errors": errors,
        "full_chain": [e.to_dict() for e in full],
    }
