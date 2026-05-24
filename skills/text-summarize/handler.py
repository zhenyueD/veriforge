"""text-summarize — Gemini-backed bullet summary."""
import os, sys, time, uuid, hashlib, json

# Reuse ClaimsForge's gemini_client wrapper (already configured)
CLAIMSFORGE = os.getenv("CLAIMSFORGE_PATH", "/Users/duan/code/claimsforge")
sys.path.insert(0, os.path.join(CLAIMSFORGE, "agents"))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Literal
from gemini_client import chat, GeminiError  # type: ignore

app = FastAPI(title="text-summarize skill", version="0.1.0")

# ── VeriForge: monetize this skill in one line ──
# x402 pay-per-call (per-creator payout + platform fee split) + marketplace listing.
# The SDK lives at /sdk in containers, ./sdk on host.
import os as _os, sys as _sys
_sys.path.insert(0, "/sdk")
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))), "sdk"))
from veriforge import monetize  # noqa: E402
monetize(app, skill_id="text-summarize", price_usdc=0.005, pay_to="0x49c34f8cc150ceaf78953b7aa4ad261136d2f839", self_register=False)


class InvokeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=50000)
    max_bullets: int = Field(default=5, ge=1, le=20)
    style: Literal["executive", "detailed", "casual"] = "executive"


class InvokeResponse(BaseModel):
    bullets: list[str]
    tldr: str
    trace_id: str
    skill_id: str = "text-summarize"
    input_hash: str
    output_hash: str
    elapsed_ms: int


def _hash(o) -> str:
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()


SYSTEM = (
    "You are a precise summarizer. Output ONLY valid JSON with two fields: "
    '{"bullets": ["...","..."], "tldr": "one-sentence summary"}. '
    "No prose. No markdown fences."
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
def health(): return {"ok": True, "skill_id": "text-summarize"}


@app.post("/invoke", response_model=InvokeResponse)
def invoke(req: InvokeRequest):
    t0 = time.monotonic()
    prompt = (
        f"Summarize the following text into exactly {req.max_bullets} {req.style}-style bullets "
        f"plus a one-sentence TLDR.\n\nTEXT:\n\"\"\"\n{req.text}\n\"\"\""
    )
    try:
        raw = chat(prompt, system=SYSTEM, temperature=0.2, max_tokens=1024)
    except GeminiError as e:
        raise HTTPException(502, f"Gemini failed: {e}")
    try:
        data = json.loads(_strip(raw))
        bullets = data["bullets"][: req.max_bullets]
        tldr = data["tldr"]
    except Exception as e:
        raise HTTPException(502, f"JSON parse failed: {e}; raw={raw[:300]}")
    core = {"bullets": bullets, "tldr": tldr}
    return InvokeResponse(
        **core,
        trace_id=uuid.uuid4().hex,
        input_hash=_hash(req.model_dump()),
        output_hash=_hash(core),
        elapsed_ms=int((time.monotonic() - t0) * 1000),
    )
