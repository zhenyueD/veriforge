"""claims-verify skill — wraps ClaimsForge verifier_agent.verify()."""
from __future__ import annotations
import os, sys, time, uuid, hashlib, json
from typing import Optional

CLAIMSFORGE = os.getenv("CLAIMSFORGE_PATH", "/Users/duan/code/claimsforge")
sys.path.insert(0, os.path.join(CLAIMSFORGE, "agents"))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from verifier_agent import verify as verifier_run  # type: ignore
from schemas import CompensationOffer, OfferType  # type: ignore

app = FastAPI(title="claims-verify skill", version="0.1.0")


class OfferIn(BaseModel):
    offer_type: str
    amount_cents: int
    currency: str = "CNY"
    justification: str
    policy_ids: list[str] = []
    requires_return: bool = False


class InvokeRequest(BaseModel):
    offer: OfferIn
    damage_severity: int
    damage_confidence: float
    emotion_score: float
    user_message: str = ""


class InvokeResponse(BaseModel):
    verdict: str
    reason: str
    revised_offer: Optional[dict] = None
    trace_id: str
    skill_id: str = "claims-verify"
    input_hash: str
    output_hash: str
    elapsed_ms: int


InvokeRequest.model_rebuild()


def _hash(o) -> str:
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()


@app.get("/health")
def health(): return {"ok": True, "skill_id": "claims-verify"}


@app.post("/invoke", response_model=InvokeResponse)
def invoke(req: InvokeRequest):
    t0 = time.monotonic()
    co = CompensationOffer(
        offer_type=OfferType(req.offer.offer_type),
        amount_cents=req.offer.amount_cents,
        currency=req.offer.currency,
        justification=req.offer.justification,
        policy_ids=req.offer.policy_ids,
        requires_return=req.offer.requires_return,
    )
    try:
        r = verifier_run(
            offer=co,
            damage_severity=req.damage_severity,
            damage_confidence=req.damage_confidence,
            emotion_score=req.emotion_score,
            user_message=req.user_message,
        )
    except Exception as e:
        raise HTTPException(502, f"verify failed: {e}")
    core = {
        "verdict": r.verdict.value,
        "reason": r.reason,
        "revised_offer": r.revised_offer.model_dump() if r.revised_offer else None,
    }
    return InvokeResponse(
        **core,
        trace_id=uuid.uuid4().hex,
        input_hash=_hash(req.model_dump()),
        output_hash=_hash(core),
        elapsed_ms=int((time.monotonic() - t0) * 1000),
    )
