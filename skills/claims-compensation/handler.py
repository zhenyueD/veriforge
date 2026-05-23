"""claims-compensation skill — wraps ClaimsForge compensation_agent.propose()."""
from __future__ import annotations
import os, sys, time, uuid, hashlib, json
from typing import Optional

CLAIMSFORGE = os.getenv("CLAIMSFORGE_PATH", "/Users/duan/code/claimsforge")
sys.path.insert(0, os.path.join(CLAIMSFORGE, "agents"))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from compensation_agent import propose  # type: ignore
from schemas import (  # type: ignore
    DamageAssessment, DamageType, Emotion, EmotionRisk, Needs, TurnRecord,
)

app = FastAPI(title="claims-compensation skill", version="0.1.0")


class InvokeRequest(BaseModel):
    damage: dict
    emotion: Optional[dict] = None
    has_image: bool = False
    estimated_value_cents: int = 5000
    user_message: str = ""
    product_hint: Optional[str] = None
    needs: Optional[dict] = None
    history: list[dict] = Field(default_factory=list)


class InvokeResponse(BaseModel):
    offer: Optional[dict] = None
    escalate_reasons: list[str] = []
    trace_id: str
    skill_id: str = "claims-compensation"
    input_hash: str
    output_hash: str
    elapsed_ms: int


def _hash(o) -> str:
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()


def _reconstruct_damage(d: dict) -> DamageAssessment:
    # Strip skill-added fields (trace_id, hashes) before reconstruction
    return DamageAssessment(
        damage_type=DamageType(d["damage_type"]),
        severity=d["severity"],
        affected_parts=d.get("affected_parts", []),
        confidence=d.get("confidence", 0.5),
        reasoning=d.get("reasoning", ""),
        evidence_quote=d.get("evidence_quote"),
        detected_subject=d.get("detected_subject"),
        bounding_boxes=d.get("bounding_boxes", []),
    )


def _reconstruct_emotion(e: Optional[dict]) -> Optional[Emotion]:
    if not e: return None
    return Emotion(
        score=e["score"], risk=EmotionRisk(e["risk"]), label=e.get("label", ""),
        triggers=e.get("triggers", []), escalation_signals=e.get("escalation_signals", []),
        suggested_tone=e.get("suggested_tone", ""),
    )


def _reconstruct_needs(n: Optional[dict]) -> Optional[Needs]:
    if not n: return None
    # Needs has optional Enum fields — let Pydantic coerce
    return Needs.model_validate(n)


@app.get("/health")
def health(): return {"ok": True, "skill_id": "claims-compensation"}


@app.post("/invoke", response_model=InvokeResponse)
def invoke(req: InvokeRequest):
    t0 = time.monotonic()
    history = [TurnRecord(**h) for h in req.history] if req.history else None
    try:
        offer, reasons = propose(
            damage=_reconstruct_damage(req.damage),
            emotion=_reconstruct_emotion(req.emotion),
            has_image=req.has_image,
            estimated_value_cents=req.estimated_value_cents,
            user_message=req.user_message,
            product_hint=req.product_hint,
            needs=_reconstruct_needs(req.needs),
            history=history,
        )
    except Exception as e:
        raise HTTPException(502, f"propose failed: {e}")
    core = {
        "offer": offer.model_dump() if offer else None,
        "escalate_reasons": list(reasons),
    }
    return InvokeResponse(
        **core,
        trace_id=uuid.uuid4().hex,
        input_hash=_hash(req.model_dump()),
        output_hash=_hash(core),
        elapsed_ms=int((time.monotonic() - t0) * 1000),
    )
