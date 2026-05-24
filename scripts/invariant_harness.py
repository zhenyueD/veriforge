"""
Invariant harness — runs every skill's verify(input, output) hook against a
good fixture (must pass) and a violating fixture (must be caught). Proves the
skill.yaml invariants actually bite, and prints a trust-score table for the demo.

Deterministic, no LLM/API/stack needed (verify modules only import dataclasses).

Run: /Users/duan/code/claimsforge/.venv/bin/python scripts/invariant_harness.py
"""
from __future__ import annotations

import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (skill_id, good=(input, output), bad=(input, output) or None)
FIXTURES = {
    "claims-intent": (
        ({"has_image": False}, {"label": "claim_text_only", "confidence": 0.9, "clarification_question": None}),
        ({"has_image": False}, {"label": "claim_with_image", "confidence": 1.2}),
    ),
    "claims-emotion": (
        ({}, {"score": 6, "risk": "MEDIUM", "escalation_signals": []}),
        ({}, {"score": 6, "risk": "LOW", "escalation_signals": ["legal_threat"]}),
    ),
    "claims-needs": (
        ({}, {"retention_risk": 0.4, "surface_need": "refund", "latent_need": "", "emotional_need": ""}),
        ({}, {"retention_risk": 1.5, "surface_need": "", "latent_need": "", "emotional_need": ""}),
    ),
    "claims-damage-vision": (
        ({"image_b64": "x"}, {"damage_type": "crack", "severity": 7, "confidence": 0.8}),
        ({}, {"damage_type": "crack", "severity": 7, "confidence": 0.9}),
    ),
    "claims-compensation": (
        ({"estimated_value_cents": 5000}, {"offer": {"amount_cents": 3000, "offer_type": "partial_refund"}}),
        ({"estimated_value_cents": 5000}, {"offer": {"amount_cents": 100000, "offer_type": "full_refund"}}),
    ),
    "claims-verify": (
        ({"offer": {"amount_cents": 3000}}, {"verdict": "approve", "revised_offer": None}),
        ({"offer": {"amount_cents": 3000}}, {"verdict": "approve", "revised_offer": {"amount_cents": 5000}}),
    ),
    "claims-fraud-image": (
        ({"image_b64": "x"}, {"fraud_score": 0.1, "verdict": "clear", "signals": ["weak_image_provenance"], "cross_session": False}),
        ({}, {"fraud_score": 0.2, "verdict": "clear", "signals": [], "cross_session": True}),
    ),
    "text-summarize": (
        ({"max_bullets": 5}, {"bullets": ["a", "b"], "tldr": "x"}),
        ({"max_bullets": 2}, {"bullets": ["a", "b", "c"], "tldr": ""}),
    ),
    "text-translate": (
        ({"text": "hello"}, {"translated_text": "bonjour"}),
        ({"text": "hello"}, {"translated_text": "hello"}),
    ),
    "sentiment-analyze": (
        ({}, {"sentiment": "positive", "intensity": 0.8}),
        ({}, {"sentiment": "happy", "intensity": 2}),
    ),
    "deep-research": (
        ({"task": "x"}, {"status": "completed", "answer": "Singapore, 6.12M", "n_steps": 3,
                         "trace_chain_tip": "a" * 64, "trace_chain": [{}, {}, {}]}),
        ({"task": "x"}, {"status": "completed", "answer": "", "n_steps": 0,
                         "trace_chain_tip": "xyz", "trace_chain": []}),
    ),
}


def _load_verify(skill_id: str):
    path = os.path.join(ROOT, "skills", skill_id, "verify.py")
    name = f"verify_{skill_id.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # register so dataclass annotations resolve
    spec.loader.exec_module(mod)
    return mod.verify


def main() -> int:
    print(f"{'skill':24} {'invs':>4} {'good':>5} {'bad-caught':>11} {'trust':>6}")
    print("-" * 56)
    all_ok = True
    for skill_id, (good, bad) in FIXTURES.items():
        verify = _load_verify(skill_id)
        gr = verify(good[0], good[1])
        good_ok = gr.passed
        bad_caught = "n/a"
        if bad is not None:
            br = verify(bad[0], bad[1])
            bad_caught = "yes" if not br.passed else "NO"
            if br.passed:
                all_ok = False
        if not good_ok:
            all_ok = False
        print(f"{skill_id:24} {len(gr.invariants):>4} {('pass' if good_ok else 'FAIL'):>5} "
              f"{bad_caught:>11} {gr.trust_score:>6.2f}")
    print("-" * 56)
    print("RESULT:", "all invariants behave correctly" if all_ok else "SOME INVARIANTS BROKEN")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
