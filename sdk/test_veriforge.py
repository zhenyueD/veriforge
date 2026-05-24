"""
Behavior tests for the veriforge SDK (fee split + x402 gate + monetize).

Runs with plain asserts (no pytest dependency) inside any env that has FastAPI:
    /Users/duan/code/claimsforge/.venv/bin/python sdk/test_veriforge.py
Also pytest-compatible (test_* functions).
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.testclient import TestClient

import veriforge as vf


# ─── Fee split (pure) ────────────────────────────────────────────────────────
def test_split_basic():
    s = vf.compute_split(0.01, "0xCreator", fee_bps=200)
    assert s["gross"] == "10000"          # 0.01 USDC, 6 decimals
    assert s["platform_fee"] == "200"     # 2%
    assert s["creator_amount"] == "9800"
    assert s["pay_to"] == "0xCreator"
    assert s["fee_bps"] == 200


def test_split_invariant_creator_plus_fee_equals_gross():
    for price in (0.001, 0.01, 0.015, 0.02, 0.137, 1.0):
        for bps in (0, 50, 200, 1000, 3000):
            s = vf.compute_split(price, "0xC", fee_bps=bps)
            assert int(s["creator_amount"]) + int(s["platform_fee"]) == int(s["gross"]), (price, bps)


def test_split_zero_fee_creator_gets_all():
    s = vf.compute_split(0.02, "0xC", fee_bps=0)
    assert s["platform_fee"] == "0"
    assert s["creator_amount"] == s["gross"] == "20000"


def test_earnings_preview_human_readable():
    p = vf.earnings_preview(0.01, fee_bps=200)
    assert abs(p["creator_amount_usdc"] - 0.0098) < 1e-9
    assert abs(p["platform_fee_usdc"] - 0.0002) < 1e-9
    assert p["fee_bps"] == 200


# ─── x402 gate (via TestClient) ──────────────────────────────────────────────
def _app_with_gate():
    app = FastAPI()

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.post("/invoke")
    def invoke():
        return {"result": "done"}

    vf.attach_x402(app, price_usdc=0.01, paths=["/invoke"],
                   skill_id="demo-skill", pay_to="0xCreatorWallet", fee_bps=200)
    return app


def test_gate_402_without_payment():
    client = TestClient(_app_with_gate())
    r = client.post("/invoke", json={})
    assert r.status_code == 402
    body = r.json()
    req = body["payment_requirements"][0]
    assert req["payTo"] == "0xCreatorWallet"
    assert req["extra"]["split"]["creator_amount"] == "9800"
    assert req["extra"]["split"]["platform_fee"] == "200"


def test_gate_passes_with_payment_and_records_split():
    client = TestClient(_app_with_gate())
    r = client.post("/invoke", json={}, headers={"X-Payment": "mocktoken-abcdef"})
    assert r.status_code == 200
    assert r.json() == {"result": "done"}
    settled = json.loads(r.headers["X-Payment-Settled"])
    assert settled["pay_to"] == "0xCreatorWallet"
    assert settled["creator_amount"] == "9800"
    assert settled["platform_fee"] == "200"
    assert settled["skill_id"] == "demo-skill"


def test_health_passes_through_unpaid():
    client = TestClient(_app_with_gate())
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_monetize_one_liner_attaches_gate():
    app = FastAPI()

    @app.post("/invoke")
    def invoke():
        return {"result": "done"}

    vf.monetize(app, skill_id="demo", price_usdc=0.02, pay_to="0xAuthor",
                self_register=False)  # no network in tests
    client = TestClient(app)
    assert client.post("/invoke", json={}).status_code == 402
    r = client.post("/invoke", json={}, headers={"X-Payment": "tok-123456"})
    assert r.status_code == 200
    assert json.loads(r.headers["X-Payment-Settled"])["pay_to"] == "0xAuthor"


# ─── Plain runner (no pytest needed) ─────────────────────────────────────────
if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL  {t.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(tests)} passed")
    sys.exit(0 if passed == len(tests) else 1)
