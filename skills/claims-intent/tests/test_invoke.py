"""Behavior tests for claims-intent. Used by Day 4 invariant harness."""
from __future__ import annotations
import os, sys

# These tests run inside ClaimsForge venv (has all deps + GOOGLE_API_KEY)
CLAIMSFORGE = os.getenv("CLAIMSFORGE_PATH", "/Users/duan/code/claimsforge")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(CLAIMSFORGE, "agents"))

from handler import invoke, InvokeRequest


def test_text_only_claim():
    req = InvokeRequest(
        user_message="My mug arrived with a crack along the rim, can't use it. Order ORD-8821.",
        has_image=False,
    )
    r = invoke(req)
    assert r.label == "claim_text_only"
    assert r.order_id == "ORD-8821"
    assert 0.0 <= r.confidence <= 1.0


def test_general_inquiry():
    req = InvokeRequest(
        user_message="What is your return policy?",
        has_image=False,
    )
    r = invoke(req)
    assert r.label == "general_inquiry"


def test_image_downgrade():
    req = InvokeRequest(
        user_message="Look at this damaged item",
        has_image=False,   # no image attached — must NOT be claim_with_image
    )
    r = invoke(req)
    assert r.label != "claim_with_image", \
        f"Should not emit claim_with_image when has_image=False, got {r.label}"


if __name__ == "__main__":
    test_text_only_claim(); print("text-only claim PASS")
    test_general_inquiry(); print("general inquiry PASS")
    test_image_downgrade(); print("image downgrade PASS")
