"""text-translate — Gemini-backed translation with auto detection."""
import os, sys, time, uuid, hashlib, json

CLAIMSFORGE = os.getenv("CLAIMSFORGE_PATH", "/Users/duan/code/claimsforge")
sys.path.insert(0, os.path.join(CLAIMSFORGE, "agents"))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from gemini_client import chat, GeminiError  # type: ignore

app = FastAPI(title="text-translate skill", version="0.1.0")


class InvokeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=50000)
    target_language: str
    source_language: Optional[str] = None


class InvokeResponse(BaseModel):
    translated_text: str
    detected_source: Optional[str] = None
    trace_id: str
    skill_id: str = "text-translate"
    input_hash: str
    output_hash: str
    elapsed_ms: int


def _hash(o) -> str:
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()


SYSTEM = (
    "You are a professional translator. Output ONLY valid JSON: "
    '{"translated_text": "...", "detected_source": "ISO 639-1 code or null"}. '
    "Preserve formatting. No prose. No markdown fences."
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
def health(): return {"ok": True, "skill_id": "text-translate"}


@app.post("/invoke", response_model=InvokeResponse)
def invoke(req: InvokeRequest):
    t0 = time.monotonic()
    src_hint = f" (source language: {req.source_language})" if req.source_language else " (auto-detect source language)"
    prompt = (
        f"Translate the following text to {req.target_language}{src_hint}.\n\n"
        f"TEXT:\n\"\"\"\n{req.text}\n\"\"\""
    )
    try:
        raw = chat(prompt, system=SYSTEM, temperature=0.1, max_tokens=4096)
    except GeminiError as e:
        raise HTTPException(502, f"Gemini failed: {e}")
    try:
        data = json.loads(_strip(raw))
        translated = data["translated_text"]
        detected = data.get("detected_source")
    except Exception as e:
        raise HTTPException(502, f"JSON parse failed: {e}; raw={raw[:300]}")
    core = {"translated_text": translated, "detected_source": detected}
    return InvokeResponse(
        **core,
        trace_id=uuid.uuid4().hex,
        input_hash=_hash(req.model_dump()),
        output_hash=_hash(core),
        elapsed_ms=int((time.monotonic() - t0) * 1000),
    )
