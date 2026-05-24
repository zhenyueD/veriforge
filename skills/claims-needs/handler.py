"""claims-needs skill — wraps ClaimsForge needs_agent.discover()."""
from __future__ import annotations
import os, sys, time, uuid, hashlib, json
from typing import Optional, Any

CLAIMSFORGE = os.getenv("CLAIMSFORGE_PATH", "/Users/duan/code/claimsforge")
sys.path.insert(0, os.path.join(CLAIMSFORGE, "agents"))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from needs_agent import discover  # type: ignore
from schemas import Needs, Emotion, EmotionRisk, TurnRecord  # type: ignore

app = FastAPI(title="claims-needs skill", version="0.1.0")

# ── VeriForge: monetize this skill in one line ──
# x402 pay-per-call (per-creator payout + platform fee split) + marketplace listing.
# The SDK lives at /sdk in containers, ./sdk on host.
import os as _os, sys as _sys
_sys.path.insert(0, "/sdk")
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))), "sdk"))
from veriforge import monetize  # noqa: E402
monetize(app, skill_id="claims-needs", price_usdc=0.015, pay_to="0x72eb6d5c1be9854ff4739217d07eb177e27a9bf1", self_register=False)


class HistoryTurn(BaseModel):
    role: str
    content: str
    decision_summary: Optional[str] = None


class InvokeRequest(BaseModel):
    user_message: str = Field(max_length=4000)
    history: list[HistoryTurn] = Field(default_factory=list)
    emotion: Optional[dict] = None   # raw Emotion dict — we reconstruct if present


class InvokeResponse(BaseModel):
    surface_need: str = ""
    latent_need: str = ""
    emotional_need: str = ""
    retention_risk: float = 0.0
    upsell_signal: Optional[str] = None
    suggested_offer_bias: Optional[str] = None
    trace_id: str
    skill_id: str = "claims-needs"
    input_hash: str
    output_hash: str
    elapsed_ms: int


InvokeRequest.model_rebuild()


def _hash(o) -> str:
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()


def _reconstruct_emotion(e: Optional[dict]) -> Optional[Emotion]:
    if not e: return None
    return Emotion(
        score=e["score"],
        risk=EmotionRisk(e["risk"]),
        label=e.get("label", ""),
        triggers=e.get("triggers", []),
        escalation_signals=e.get("escalation_signals", []),
        suggested_tone=e.get("suggested_tone", ""),
    )


@app.get("/health")
def health(): return {"ok": True, "skill_id": "claims-needs"}


@app.post("/invoke", response_model=InvokeResponse)
def invoke(req: InvokeRequest):
    t0 = time.monotonic()
    history = [TurnRecord(role=t.role, content=t.content, decision_summary=t.decision_summary) for t in req.history] or None
    try:
        r: Needs = discover(req.user_message, history=history, emotion=_reconstruct_emotion(req.emotion))
    except Exception as e:
        raise HTTPException(502, f"discover failed: {e}")
    core = {
        "surface_need": r.surface_need or "",
        "latent_need": r.latent_need or "",
        "emotional_need": r.emotional_need or "",
        "retention_risk": r.retention_risk if r.retention_risk is not None else 0.0,
        "upsell_signal": (r.upsell_signal.value if hasattr(r.upsell_signal, "value") else r.upsell_signal) if r.upsell_signal else None,
        "suggested_offer_bias": (r.suggested_offer_bias.value if hasattr(r.suggested_offer_bias, "value") else r.suggested_offer_bias) if r.suggested_offer_bias else None,
    }
    return InvokeResponse(
        **core,
        trace_id=uuid.uuid4().hex,
        input_hash=_hash(req.model_dump()),
        output_hash=_hash(core),
        elapsed_ms=int((time.monotonic() - t0) * 1000),
    )
