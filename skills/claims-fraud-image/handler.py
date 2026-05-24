"""
claims-fraud-image skill — wraps ClaimsForge fraud.py image-provenance primitives.

Deterministic (no LLM): perceptual-hash collision detection (catches re-used /
recycled claim photos across sessions) + EXIF age check (catches stale photos
for a "just arrived broken" claim). Composes into a fraud_score + verdict.
"""
from __future__ import annotations
import os, sys, time, uuid, hashlib, json, base64
from typing import Optional

CLAIMSFORGE = os.getenv("CLAIMSFORGE_PATH", "/Users/duan/code/claimsforge")
sys.path.insert(0, os.path.join(CLAIMSFORGE, "agents"))

from fastapi import FastAPI
from pydantic import BaseModel, Field
from fraud import compute_phash, check_exif_age, find_collision  # type: ignore

app = FastAPI(title="claims-fraud-image skill", version="0.1.0")

# ── VeriForge: monetize this skill in one line ──
# x402 pay-per-call (per-creator payout + platform fee split) + marketplace listing.
# The SDK lives at /sdk in containers, ./sdk on host.
import os as _os, sys as _sys
_sys.path.insert(0, "/sdk")
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))), "sdk"))
from veriforge import monetize  # noqa: E402
monetize(app, skill_id="claims-fraud-image", price_usdc=0.04, pay_to="0x72eb6d5c1be9854ff4739217d07eb177e27a9bf1", self_register=False)


class InvokeRequest(BaseModel):
    image_b64: Optional[str] = None
    image_mime: str = "image/jpeg"
    session_id: str = "anon"
    user_message: str = Field(default="", max_length=4000)


class InvokeResponse(BaseModel):
    phash: Optional[str] = None
    exif: dict
    collision_found: bool
    collision_distance: Optional[int] = None
    cross_session: bool = False
    fraud_score: float
    verdict: str            # clear | suspicious | fraud
    signals: list[str]
    # Audit chain fields
    trace_id: str
    skill_id: str = "claims-fraud-image"
    input_hash: str
    output_hash: str
    elapsed_ms: int


def _hash(o) -> str:
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()


def _assess(phash: Optional[str], exif: dict, collision: Optional[dict]) -> tuple[float, str, list[str]]:
    """Deterministic fraud score from provenance signals. Additive, capped at 1.0."""
    score = 0.0
    signals: list[str] = []
    if collision:
        if collision.get("_cross_session"):
            score += 0.7
            signals.append("cross_session_image_reuse")
        else:
            score += 0.25
            signals.append("same_session_duplicate")
    if exif.get("status") == "fail":
        score += 0.3
        signals.append("photo_too_old")
    elif exif.get("status") == "warn":
        score += 0.1
        signals.append("weak_image_provenance")
    if not phash:
        signals.append("no_image_provided")
    score = min(1.0, round(score, 3))
    verdict = "fraud" if score >= 0.6 else "suspicious" if score >= 0.25 else "clear"
    return score, verdict, signals


@app.get("/health")
def health():
    return {"ok": True, "skill_id": "claims-fraud-image"}


@app.post("/invoke", response_model=InvokeResponse)
def invoke(req: InvokeRequest):
    t0 = time.monotonic()
    image_bytes = base64.b64decode(req.image_b64) if req.image_b64 else b""

    phash = compute_phash(image_bytes) if image_bytes else None
    exif = check_exif_age(image_bytes)
    collision = find_collision(phash, req.session_id) if phash else None

    score, verdict, signals = _assess(phash, exif, collision)
    img_fp = hashlib.sha256(image_bytes).hexdigest() if image_bytes else None
    core = {
        "phash": phash,
        "exif": exif,
        "collision_found": bool(collision),
        "collision_distance": collision.get("_hamming_distance") if collision else None,
        "cross_session": bool(collision and collision.get("_cross_session")),
        "fraud_score": score,
        "verdict": verdict,
        "signals": signals,
    }
    return InvokeResponse(
        **core,
        trace_id=uuid.uuid4().hex,
        input_hash=_hash({"image_sha256": img_fp, "session_id": req.session_id}),
        output_hash=_hash(core),
        elapsed_ms=int((time.monotonic() - t0) * 1000),
    )
