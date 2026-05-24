"""
Tests for A4: registry upsert + /register + /skills.

Run: /Users/duan/code/claimsforge/.venv/bin/python scripts/test_registry.py
upsert_skill is tested against a temp file; HTTP tests back up and restore the
real registry.json so they never corrupt it.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "marketplace", "router"))
sys.path.insert(0, os.path.join(ROOT, "sdk"))

import router as R  # noqa: E402


def test_upsert_creates_then_updates():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "registry.json")
        json.dump({"version": "0.1.0", "skills": []}, open(p, "w"))

        m = {"id": "my-skill", "pay_to": "0xAuthor", "price_usdc": 0.02, "name": "Mine"}
        skill, created = R.upsert_skill(m, path=p)
        assert created is True
        assert skill["pay_to"] == "0xAuthor"
        assert len(R.load_registry(p)["skills"]) == 1

        # Re-register same id with a new price -> update, not duplicate.
        skill, created = R.upsert_skill({"id": "my-skill", "pay_to": "0xAuthor", "price_usdc": 0.05}, path=p)
        assert created is False
        assert skill["price_usdc"] == 0.05
        assert skill["name"] == "Mine"  # untouched field preserved (merge)
        assert len(R.load_registry(p)["skills"]) == 1


def test_skills_endpoint_has_earnings_and_payto():
    from fastapi.testclient import TestClient
    from main import app  # noqa: E402
    client = TestClient(app)
    r = client.get("/skills")
    assert r.status_code == 200
    skills = r.json()["skills"]
    assert len(skills) >= 9
    s0 = skills[0]
    assert s0["pay_to"].startswith("0x") and len(s0["pay_to"]) == 42
    ep = s0["earnings_preview"]
    assert ep["creator_amount_usdc"] + ep["platform_fee_usdc"] == s0["price_usdc"]


def test_register_endpoint_roundtrip():
    from fastapi.testclient import TestClient
    from main import app  # noqa: E402
    reg_path = R.registry_path()
    backup = reg_path + ".bak"
    shutil.copy(reg_path, backup)
    try:
        client = TestClient(app)
        body = {
            "id": "external-translator", "pay_to": "0xExternalAuthor",
            "price_usdc": 0.02, "name": "External Translator",
            "endpoint": "http://HOST:7099", "description": "An indie skill",
            "tags": ["horizontal"], "llm_compat": ["any"],
        }
        r = client.post("/register", json=body)
        assert r.status_code == 200, r.text
        assert r.json()["created"] is True
        # It now shows up in /skills with an earnings preview.
        listed = {s["id"]: s for s in client.get("/skills").json()["skills"]}
        assert "external-translator" in listed
        assert listed["external-translator"]["pay_to"] == "0xExternalAuthor"
    finally:
        shutil.move(backup, reg_path)


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
            import traceback; traceback.print_exc()
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(tests)} passed")
    sys.exit(0 if passed == len(tests) else 1)
