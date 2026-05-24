"""
Behavior tests for claims-fraud-image (deterministic — no LLM/API needed).

Run: CLAIMSFORGE_PATH=/Users/duan/code/claimsforge \
     /Users/duan/code/claimsforge/.venv/bin/python skills/claims-fraud-image/tests/test_invoke.py
"""
from __future__ import annotations
import base64
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.getenv("CLAIMSFORGE_PATH", "/Users/duan/code/claimsforge"), "agents"))

from fastapi.testclient import TestClient
import handler
from handler import _assess


# ── Deterministic scoring (pure) ──
def test_clear_when_no_signals():
    score, verdict, signals = _assess("abc", {"status": "pass"}, None)
    assert score == 0.0 and verdict == "clear"


def test_cross_session_reuse_is_fraud():
    score, verdict, signals = _assess("abc", {"status": "pass"},
                                      {"_cross_session": True, "_hamming_distance": 2})
    assert score >= 0.6 and verdict == "fraud"
    assert "cross_session_image_reuse" in signals


def test_same_session_duplicate_is_suspicious():
    score, verdict, signals = _assess("abc", {"status": "pass"},
                                      {"_cross_session": False, "_hamming_distance": 0})
    assert verdict == "suspicious" and "same_session_duplicate" in signals


def test_old_photo_plus_reuse_caps_at_one():
    score, verdict, signals = _assess("abc", {"status": "fail"},
                                      {"_cross_session": True})
    assert score == 1.0 and verdict == "fraud"


def test_no_image_flagged():
    score, verdict, signals = _assess(None, {"status": "warn"}, None)
    assert "no_image_provided" in signals


# ── Endpoint ──
def test_invoke_no_image_is_clear():
    c = TestClient(handler.app)
    r = c.post("/invoke", json={"session_id": "s1"}, headers={"X-Payment": "mock:tok123"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["verdict"] == "clear"
    assert "no_image_provided" in body["signals"]
    assert body["phash"] is None


def test_invoke_with_image_computes_phash():
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (120, 80, 200)).save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    c = TestClient(handler.app)
    r = c.post("/invoke", json={"image_b64": b64, "session_id": "s1"},
               headers={"X-Payment": "mock:tok123"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["phash"] is not None
    assert 0.0 <= body["fraud_score"] <= 1.0


def test_gate_402_without_payment():
    c = TestClient(handler.app)
    r = c.post("/invoke", json={"session_id": "s1"})
    assert r.status_code == 402


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t(); print(f"PASS  {t.__name__}"); passed += 1
        except AssertionError as e:
            print(f"FAIL  {t.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            import traceback; traceback.print_exc()
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(tests)} passed")
    sys.exit(0 if passed == len(tests) else 1)
