"""
Prompt-injection shield — guards user_input before it reaches the KIMI router and
the skills' Gemini calls. 3-layer cascade, silent fallback (never blocks the
pipeline if the shield itself errors); only a genuine injection match flags.

  1. external service (SHIELD_URL/check, optional) — unreachable → fall through
  2. regex (11 patterns, zero-cost, always on)      — the demonstrable core
  3. classifier (optional, only if configured)      — skipped otherwise

Pattern set mirrors the Deals Machine "Lobster Trap". Self-contained (stdlib only).
"""
from __future__ import annotations

import json
import os
import re
import urllib.request

SHIELD_URL = os.getenv("VERIFORGE_SHIELD_URL", "")
SHIELD_SECRET = os.getenv("VERIFORGE_SHIELD_SECRET", "")

# 11 injection patterns. Keep this list as the single source for the inline shield.
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("ignore_previous",       re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|messages|context)", re.I)),
    ("disregard",             re.compile(r"disregard\s+(all\s+)?(previous|prior|above|your)\s+(instructions|rules|prompts)", re.I)),
    ("system_prompt_request", re.compile(r"(reveal|show|print|repeat|give me|tell me)\s+(your\s+)?(system\s+prompt|initial\s+prompt|instructions)", re.I)),
    ("jailbreak",             re.compile(r"\b(jailbreak|DAN\s+mode|developer\s+mode|do\s+anything\s+now)\b", re.I)),
    ("role_override",         re.compile(r"you\s+are\s+now\s+(a|an|my|the)\b", re.I)),
    ("override_role",         re.compile(r"override\s+(your\s+)?(role|instructions|system|prompt)", re.I)),
    ("mark_priority",         re.compile(r"^\s*(system|assistant|admin|developer)\s*[:：]", re.I | re.M)),
    ("reset_instructions",    re.compile(r"reset\s+(your\s+)?(instructions|context|memory|prompt)", re.I)),
    ("act_as",                re.compile(r"\bact\s+as\s+(if\s+)?(a|an|the)\b", re.I)),
    ("forget_everything",     re.compile(r"forget\s+(everything|all|your\s+instructions|what\s+you)", re.I)),
    ("new_instructions",      re.compile(r"(here\s+are|follow\s+these|your)\s+(new|updated)\s+instructions", re.I)),
]


def _safe(detector: str = "none") -> dict:
    return {"verdict": "safe", "detector": detector}


def _flagged(detector: str, matched_pattern: str = "", reason: str = "") -> dict:
    return {"verdict": "flagged", "detector": detector,
            "matched_pattern": matched_pattern, "reason": reason}


def _check_external(text: str) -> dict | None:
    if not SHIELD_URL:
        return None
    try:
        body = json.dumps({"input": text[:6000]}).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if SHIELD_SECRET:
            headers["x-lobster-secret"] = SHIELD_SECRET
        req = urllib.request.Request(f"{SHIELD_URL.rstrip('/')}/check", data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode("utf-8"))
        if data.get("flagged"):
            return _flagged("lobster_trap", data.get("matched_pattern", ""), data.get("reason", ""))
        return _safe("lobster_trap")
    except Exception:  # noqa: BLE001 — service down → fall through to regex
        return None


def _check_regex(text: str) -> dict | None:
    for name, rx in _PATTERNS:
        if rx.search(text):
            return _flagged("regex", name, f"matched {name}")
    return None


def check_input(text: str) -> dict:
    """Return {verdict: 'safe'|'flagged', detector, ...}. Never raises."""
    try:
        if not text or not text.strip():
            return _safe()
        ext = _check_external(text)
        if ext is not None:
            return ext
        hit = _check_regex(text)
        if hit is not None:
            return hit
        # Layer 3 (classifier) is optional and not configured here → treat as safe.
        return _safe("regex")
    except Exception:  # noqa: BLE001 — shield never blocks the cockpit
        return _safe("error")
