"""claims-damage-vision skill — wraps ClaimsForge damage_agent.assess() (Gemini Vision)."""
from __future__ import annotations
import os, sys, time, uuid, hashlib, json, base64
from typing import Optional

CLAIMSFORGE = os.getenv("CLAIMSFORGE_PATH", "/Users/duan/code/claimsforge")
sys.path.insert(0, os.path.join(CLAIMSFORGE, "agents"))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from damage_agent import assess  # type: ignore
from schemas import DamageAssessment  # type: ignore

app = FastAPI(title="claims-damage-vision skill", version="0.1.0")


class InvokeRequest(BaseModel):
    user_message: str = Field(max_length=4000)
    image_b64: Optional[str] = None
    image_mime: str = "image/jpeg"


class InvokeResponse(BaseModel):
    damage_type: str
    severity: int
    affected_parts: list[str]
    confidence: float
    reasoning: str
    evidence_quote: Optional[str] = None
    detected_subject: Optional[str] = None
    bounding_boxes: list = []
    trace_id: str
    skill_id: str = "claims-damage-vision"
    input_hash: str
    output_hash: str
    elapsed_ms: int


def _hash(o) -> str:
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()


@app.get("/health")
def health(): return {"ok": True, "skill_id": "claims-damage-vision"}


@app.post("/invoke", response_model=InvokeResponse)
def invoke(req: InvokeRequest):
    t0 = time.monotonic()
    image_bytes = base64.b64decode(req.image_b64) if req.image_b64 else None
    try:
        r: DamageAssessment = assess(req.user_message, image_bytes=image_bytes, image_mime=req.image_mime)
    except Exception as e:
        raise HTTPException(502, f"assess failed: {e}")
    core = {
        "damage_type": r.damage_type.value,
        "severity": r.severity,
        "affected_parts": list(r.affected_parts),
        "confidence": r.confidence,
        "reasoning": r.reasoning,
        "evidence_quote": r.evidence_quote,
        "detected_subject": r.detected_subject,
        "bounding_boxes": [bb.model_dump() if hasattr(bb, "model_dump") else bb for bb in (r.bounding_boxes or [])],
    }
    # Don't include base64 image in input_hash (too large) — hash the message + image hash separately
    img_fp = hashlib.sha256(image_bytes).hexdigest() if image_bytes else None
    return InvokeResponse(
        **core,
        trace_id=uuid.uuid4().hex,
        input_hash=_hash({"user_message": req.user_message, "image_sha256": img_fp, "image_mime": req.image_mime}),
        output_hash=_hash(core),
        elapsed_ms=int((time.monotonic() - t0) * 1000),
    )
