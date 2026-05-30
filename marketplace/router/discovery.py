"""
VeriForge skill discovery — make the marketplace searchable by ANY agent.

Two ranking signals, fused:
  1. relevance  — semantic match between a natural-language task and each skill.
                  Uses Gemini `gemini-embedding-001` when GOOGLE_API_KEY is set;
                  falls back to a dependency-free lexical scorer otherwise, so the
                  /skills/search endpoint never hard-depends on network or a key.
  2. reputation — each skill's *cryptographically verifiable* track record, pulled
                  from the audit service (verified-pass ratio + call volume). This
                  is the moat: discovery ranked by proof, not vendor claims.

Whole module is stdlib-only (urllib + math). Embeddings are cached per registry
fingerprint so we embed each skill once, not per request.
"""
from __future__ import annotations

import json
import math
import os
import re
import time
import urllib.request
from typing import Optional

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
EMBED_MODEL = os.getenv("VERIFORGE_EMBED_MODEL", "gemini-embedding-001")
EMBED_ENABLED = os.getenv("VERIFORGE_EMBED", "1") != "0" and bool(GOOGLE_API_KEY)
AUDIT_URL = os.getenv("AUDIT_URL", "http://localhost:8001")

_TOKEN_RE = re.compile(r"[a-z0-9]+")


# ─────────────────────────── text helpers ───────────────────────────
def _skill_doc(s: dict) -> str:
    """The text we index for a skill: id + name + description + tags."""
    return " ".join([
        s.get("id", "").replace("-", " "),
        s.get("name", ""),
        s.get("description", ""),
        " ".join(s.get("tags", []) or []),
    ]).strip()


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


# ─────────────────────── Gemini embeddings (optional) ───────────────────────
def _embed(text: str, *, timeout: int = 12) -> Optional[list[float]]:
    """Embed one string via Gemini REST. Returns None on any failure (caller falls back)."""
    if not EMBED_ENABLED:
        return None
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{EMBED_MODEL}:embedContent?key={GOOGLE_API_KEY}"
    )
    body = json.dumps({
        "model": f"models/{EMBED_MODEL}",
        "content": {"parts": [{"text": text[:8000]}]},
    }).encode()
    req = urllib.request.Request(url, data=body, headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read())
        return data.get("embedding", {}).get("values")
    except Exception:  # noqa: BLE001 — never let discovery hard-fail on the embed call
        return None


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


# ─────────────────────── lexical fallback scorer ───────────────────────
def _lexical_score(query: str, doc: str) -> float:
    """Token-overlap cosine — works with zero deps when embeddings are unavailable."""
    q, d = _tokens(query), _tokens(doc)
    if not q or not d:
        return 0.0
    qset, dset = set(q), set(d)
    inter = qset & dset
    if not inter:
        return 0.0
    # cosine over term-presence vectors, lightly boosted by query coverage
    cos = len(inter) / math.sqrt(len(qset) * len(dset))
    coverage = len(inter) / len(qset)
    return 0.6 * cos + 0.4 * coverage


# ─────────────────────── embedding index (cached) ───────────────────────
_INDEX: dict = {"fingerprint": None, "method": "lexical", "vectors": {}}


def _fingerprint(skills: list[dict]) -> str:
    return str(hash(tuple((s.get("id", ""), _skill_doc(s)) for s in skills)))


def _ensure_index(skills: list[dict]) -> str:
    """Build/refresh the per-skill embedding cache. Returns the active method."""
    fp = _fingerprint(skills)
    if _INDEX["fingerprint"] == fp:
        return _INDEX["method"]

    vectors: dict[str, list[float]] = {}
    if EMBED_ENABLED:
        for s in skills:
            vec = _embed(_skill_doc(s))
            if vec is None:          # any miss → abandon embeddings for consistency
                vectors = {}
                break
            vectors[s["id"]] = vec

    _INDEX["fingerprint"] = fp
    _INDEX["vectors"] = vectors
    _INDEX["method"] = "embedding" if vectors else "lexical"
    return _INDEX["method"]


# ─────────────────────── reputation from audit chain ───────────────────────
def fetch_reputation(*, timeout: int = 5) -> dict[str, dict]:
    """{skill_id: {calls, verified_ok, pass_rate}} from the audit service. {} on failure."""
    try:
        with urllib.request.urlopen(f"{AUDIT_URL}/reputation", timeout=timeout) as r:
            return json.loads(r.read()).get("skills", {})
    except Exception:  # noqa: BLE001
        return {}


def _reputation_score(rep: Optional[dict]) -> float:
    """0..1 trust score: verified-pass ratio, dampened by low call volume (Wilson-ish)."""
    if not rep:
        return 0.0
    calls = rep.get("calls", 0) or 0
    ok = rep.get("verified_ok", 0) or 0
    if calls <= 0:
        return 0.0
    ratio = ok / calls
    confidence = calls / (calls + 5.0)   # few calls → discount toward 0
    return ratio * confidence


# ─────────────────────── public search ───────────────────────
def search(
    query: str,
    skills: list[dict],
    *,
    top_k: int = 5,
    rank: str = "relevance",     # "relevance" | "verified"
) -> dict:
    """
    Rank skills for a natural-language task.
      rank=relevance → pure semantic/lexical match.
      rank=verified  → blend relevance with on-chain verified reputation (0.7/0.3),
                       so an agent discovers the skill it can actually *trust*.
    """
    t0 = time.time()
    method = _ensure_index(skills)
    qvec = _embed(query) if method == "embedding" else None
    if method == "embedding" and qvec is None:
        method = "lexical"   # query embed failed → degrade gracefully this call

    rep_map = fetch_reputation() if rank == "verified" else {}

    scored = []
    for s in skills:
        if method == "embedding":
            relevance = _cosine(qvec, _INDEX["vectors"][s["id"]])
        else:
            relevance = _lexical_score(query, _skill_doc(s))

        rep = rep_map.get(s["id"])
        trust = _reputation_score(rep)
        final = 0.7 * relevance + 0.3 * trust if rank == "verified" else relevance

        scored.append({
            "id": s["id"],
            "name": s.get("name", s["id"]),
            "description": s.get("description", ""),
            "price_usdc": s.get("price_usdc", 0),
            "tags": s.get("tags", []),
            "endpoint": s.get("endpoint", ""),
            "relevance": round(relevance, 4),
            "trust": round(trust, 4),
            "score": round(final, 4),
            "reputation": rep or {"calls": 0, "verified_ok": 0, "pass_rate": None},
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return {
        "query": query,
        "rank": rank,
        "method": method,            # "embedding" (Gemini) or "lexical" (fallback)
        "count": min(top_k, len(scored)),
        "latency_ms": int((time.time() - t0) * 1000),
        "results": scored[:top_k],
    }
