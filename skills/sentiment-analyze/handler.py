"""sentiment-analyze — Gemini-backed sentiment classifier."""
import os, sys, time, uuid, hashlib, json

CLAIMSFORGE = os.getenv("CLAIMSFORGE_PATH", "/Users/duan/code/claimsforge")
sys.path.insert(0, os.path.join(CLAIMSFORGE, "agents"))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from gemini_client import chat, GeminiError  # type: ignore

app = FastAPI(title="sentiment-analyze skill", version="0.1.0")


class InvokeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10000)


class InvokeResponse(BaseModel):
    sentiment: str
    intensity: float
    emotions: list[str] = []
    trace_id: str
    skill_id: str = "sentiment-analyze"
    input_hash: str
    output_hash: str
    elapsed_ms: int


def _hash(o) -> str:
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()


SYSTEM = (
    "You are a sentiment analyst. Output ONLY valid JSON: "
    '{"sentiment": "positive"|"neutral"|"negative", "intensity": 0..1, '
    '"emotions": ["joy","anger",...]}. No prose. No markdown fences.'
)


def _strip(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = s.split("```", 2)[1]
        if s.startswith("json"):
            s = s[4:].lstrip()
        s = s.rsplit("```", 1)[0]
    return s.strip()


@app.get("/health")
def health(): return {"ok": True, "skill_id": "sentiment-analyze"}


@app.post("/invoke", response_model=InvokeResponse)
def invoke(req: InvokeRequest):
    t0 = time.monotonic()
    prompt = f"Analyze sentiment of:\n\"\"\"\n{req.text}\n\"\"\""
    try:
        raw = chat(prompt, system=SYSTEM, temperature=0.1, max_tokens=512)
    except GeminiError as e:
        raise HTTPException(502, f"Gemini failed: {e}")
    try:
        data = json.loads(_strip(raw))
        sentiment = data["sentiment"]
        intensity = float(data["intensity"])
        emotions = data.get("emotions", []) or []
    except Exception as e:
        raise HTTPException(502, f"JSON parse failed: {e}; raw={raw[:300]}")
    core = {"sentiment": sentiment, "intensity": intensity, "emotions": emotions}
    return InvokeResponse(
        **core,
        trace_id=uuid.uuid4().hex,
        input_hash=_hash(req.model_dump()),
        output_hash=_hash(core),
        elapsed_ms=int((time.monotonic() - t0) * 1000),
    )
