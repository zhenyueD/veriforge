"""claims-emotion skill — wraps ClaimsForge emotion_agent.grade()."""
from __future__ import annotations
import os, sys, time, uuid, hashlib, json
from typing import Optional

CLAIMSFORGE = os.getenv("CLAIMSFORGE_PATH", "/Users/duan/code/claimsforge")
sys.path.insert(0, os.path.join(CLAIMSFORGE, "agents"))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from emotion_agent import grade  # type: ignore
from schemas import Emotion  # type: ignore

app = FastAPI(title="claims-emotion skill", version="0.1.0")

# ── VeriForge: monetize this skill in one line ──
# x402 pay-per-call (per-creator payout + platform fee split) + marketplace listing.
# The SDK lives at /sdk in containers, ./sdk on host.
import os as _os, sys as _sys
_sys.path.insert(0, "/sdk")
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))), "sdk"))
from veriforge import monetize  # noqa: E402
monetize(app, skill_id="claims-emotion", price_usdc=0.01, pay_to="0x72eb6d5c1be9854ff4739217d07eb177e27a9bf1", self_register=False)


class InvokeRequest(BaseModel):
    user_message: str = Field(max_length=4000)
    prior_score: Optional[float] = None


class InvokeResponse(BaseModel):
    score: float
    risk: str
    label: str
    triggers: list[str]
    escalation_signals: list[str]
    suggested_tone: str
    trace_id: str
    skill_id: str = "claims-emotion"
    input_hash: str
    output_hash: str
    elapsed_ms: int


def _hash(o) -> str:
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()


@app.get("/health")
def health(): return {"ok": True, "skill_id": "claims-emotion"}


@app.post("/invoke", response_model=InvokeResponse)
def invoke(req: InvokeRequest):
    t0 = time.monotonic()
    try:
        r: Emotion = grade(req.user_message, prior_score=req.prior_score)
    except Exception as e:
        raise HTTPException(502, f"grade failed: {e}")
    out_core = {
        "score": r.score, "risk": r.risk.value, "label": r.label,
        "triggers": list(r.triggers), "escalation_signals": list(r.escalation_signals),
        "suggested_tone": r.suggested_tone,
    }
    return InvokeResponse(
        **out_core,
        trace_id=uuid.uuid4().hex,
        input_hash=_hash(req.model_dump()),
        output_hash=_hash(out_core),
        elapsed_ms=int((time.monotonic() - t0) * 1000),
    )
