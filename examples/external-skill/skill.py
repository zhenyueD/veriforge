"""
A THIRD-PARTY skill that is NOT part of VeriForge — it lives outside skills/ to
simulate an external author. To monetize + list on the marketplace, the author
did exactly two things:

  1. Copied the single file `veriforge.py` next to this one.
  2. Added the one `monetize(...)` line below.

Boot it against a running VeriForge router and it self-registers — no PR, no
config in the marketplace repo. That is the supply side of the flywheel.

Run:
  pip install fastapi 'uvicorn[standard]'
  export VERIFORGE_REGISTRY_URL=http://localhost:8000
  uvicorn skill:app --port 7099
"""
from __future__ import annotations

import os
import re

from fastapi import FastAPI
from pydantic import BaseModel, Field

from veriforge import monetize  # the one file the author copied

app = FastAPI(title="community-readability skill", version="0.1.0")

# ── The only VeriForge-specific line an external author writes ──
monetize(
    app,
    skill_id="community-readability",
    price_usdc=0.003,
    pay_to="0xC0MMUN1TYa11ce0000000000000000000000bEEF",
    name="Readability Scorer",
    description="Flesch reading-ease + approximate grade level for any text. "
                "Pure-Python, language-agnostic word/sentence/syllable heuristics. "
                "Third-party community skill — self-registered via the VeriForge SDK.",
    endpoint=os.getenv("VF_ENDPOINT", "http://HOST:7099"),
    tags=["horizontal", "capability:nlp", "community"],
    llm_compat=["any"],
    registry=os.getenv("VERIFORGE_REGISTRY_URL"),  # self-register here on startup
    self_register=True,
)


class InvokeRequest(BaseModel):
    text: str = Field(max_length=20000)


class InvokeResponse(BaseModel):
    reading_ease: float
    grade_level: float
    word_count: int
    sentence_count: int


def _syllables(word: str) -> int:
    word = word.lower()
    groups = re.findall(r"[aeiouy]+", word)
    n = len(groups)
    if word.endswith("e") and n > 1:
        n -= 1
    return max(1, n)


@app.get("/health")
def health():
    return {"ok": True, "skill_id": "community-readability"}


@app.post("/invoke", response_model=InvokeResponse)
def invoke(req: InvokeRequest):
    words = re.findall(r"[A-Za-z']+", req.text)
    sentences = [s for s in re.split(r"[.!?]+", req.text) if s.strip()]
    nw = max(1, len(words))
    ns = max(1, len(sentences))
    syl = sum(_syllables(w) for w in words) or 1
    # Flesch reading ease + Flesch–Kincaid grade level.
    ease = 206.835 - 1.015 * (nw / ns) - 84.6 * (syl / nw)
    grade = 0.39 * (nw / ns) + 11.8 * (syl / nw) - 15.59
    return InvokeResponse(
        reading_ease=round(ease, 1),
        grade_level=round(grade, 1),
        word_count=len(words),
        sentence_count=len(sentences),
    )
