"""
claims-intent skill — FastAPI wrapper around ClaimsForge's intent_agent.classify().

Thin wrapper: imports the pure function from ClaimsForge via sys.path,
exposes POST /invoke with skill.yaml-defined input/output schemas.

Run locally:
  CLAIMSFORGE_PATH=/Users/duan/code/claimsforge \
  uvicorn handler:app --port 7001
"""
from __future__ import annotations
import os, sys, time, uuid, hashlib, json
from typing import Optional

CLAIMSFORGE = os.getenv("CLAIMSFORGE_PATH", "/Users/duan/code/claimsforge")
sys.path.insert(0, os.path.join(CLAIMSFORGE, "agents"))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Imported from ClaimsForge — these power the actual classification
from intent_agent import classify  # type: ignore
from schemas import IntentLabel, IntentResult, TurnRecord  # type: ignore

app = FastAPI(title="claims-intent skill", version="0.1.0")


# ─── Request / response models match skill.yaml schemas ───
class HistoryTurn(BaseModel):
    role: str
    content: str
    decision_summary: Optional[str] = None


class InvokeRequest(BaseModel):
    user_message: str = Field(max_length=4000)
    has_image: bool = False
    history: list[HistoryTurn] = Field(default_factory=list)


class InvokeResponse(BaseModel):
    label: str
    order_id: Optional[str] = None
    product_hint: Optional[str] = None
    confidence: float
    clarification_question: Optional[str] = None
    # Audit chain fields
    trace_id: str
    skill_id: str = "claims-intent"
    input_hash: str
    output_hash: str
    elapsed_ms: int


InvokeRequest.model_rebuild()


def _hash(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


@app.get("/health")
def health():
    return {"ok": True, "skill_id": "claims-intent"}


@app.post("/invoke", response_model=InvokeResponse)
def invoke(req: InvokeRequest):
    t0 = time.monotonic()
    trace_id = uuid.uuid4().hex
    history = [
        TurnRecord(role=t.role, content=t.content, decision_summary=t.decision_summary)
        for t in req.history
    ] if req.history else None

    try:
        result: IntentResult = classify(
            user_message=req.user_message,
            has_image=req.has_image,
            history=history,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"classify failed: {e}")

    out = InvokeResponse(
        label=result.label.value,
        order_id=result.order_id,
        product_hint=result.product_hint,
        confidence=result.confidence,
        clarification_question=result.clarification_question,
        trace_id=trace_id,
        input_hash=_hash(req.model_dump()),
        output_hash=_hash({
            "label": result.label.value,
            "order_id": result.order_id,
            "confidence": result.confidence,
        }),
        elapsed_ms=int((time.monotonic() - t0) * 1000),
    )
    return out
