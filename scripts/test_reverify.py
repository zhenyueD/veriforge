"""
Unit tests for Feature B re-verify logic — no running stack required.

We stub the audit fetch with a synthetic chain and sign entries with each skill's
OWN creator-held key (the same key whose public half is published in the registry —
run scripts/gen_keys.py first), so a clean chain verifies and a tampered one names
the offending skill. Run:

    python3 scripts/gen_keys.py    # ensure keys + registry pubkeys exist
    /Users/duan/code/claimsforge/.venv/bin/python scripts/test_reverify.py
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "marketplace", "router"))
sys.path.insert(0, os.path.join(ROOT, "sdk"))

import veriforge as vf  # noqa: E402
import reverify  # noqa: E402

LLM_SKILL = "claims-intent"          # registry type: llm
DET_SKILL = "claims-fraud-image"     # registry type: deterministic


def _signed_entry(seq: int, skill_id: str, body_sha: str = "abc123", ts: str = "1716000000.0") -> dict:
    sig = vf.sign_bytes(skill_id, f"{skill_id}|{body_sha}|{ts}".encode())
    return {
        "seq": seq, "skill_id": skill_id, "trace_id": f"t{seq}",
        "input_hash": f"i{seq}", "output_hash": f"o{seq}", "verify_passed": True,
        "extra": {"signature": {
            "public_key": vf.skill_public_key(skill_id),
            "signature": sig, "body_sha256": body_sha, "signed_ts": ts,
        }},
    }


def _stub_chain(entries, *, chain_verified=True, errors=None):
    def _get(url, timeout=8):
        return {"trace_id": "t0", "session_id": "sess-1",
                "chain_verified": chain_verified, "chain_errors": errors or [],
                "full_chain": entries}
    reverify._get = _get  # monkeypatch the audit fetch


def test_clean_session_verifies():
    _stub_chain([_signed_entry(0, LLM_SKILL), _signed_entry(1, DET_SKILL)])
    r = reverify.re_verify("t0")
    assert r["verified"] is True, r["verdict"]
    assert r["all_attributed"] is True
    assert r["chain_verified"] is True
    types = {e["skill_id"]: e["type"] for e in r["entries"]}
    assert types[LLM_SKILL] == "llm" and types[DET_SKILL] == "deterministic", types
    for e in r["entries"]:
        assert e["attribution"]["attributed"] is True, e
    print("ok  clean session verifies + types correct")


def test_tampered_signature_names_skill():
    bad = _signed_entry(1, DET_SKILL)
    bad["extra"]["signature"]["body_sha256"] = "deadbeef0000"  # break the signed statement
    _stub_chain([_signed_entry(0, LLM_SKILL), bad])
    r = reverify.re_verify("t0")
    assert r["verified"] is False
    assert DET_SKILL in r["failed_skills"], r["failed_skills"]
    assert "ATTRIBUTION FAILED" in r["verdict"] and DET_SKILL in r["verdict"], r["verdict"]
    print("ok  tampered signature -> attribution fails + names skill")


def test_swapped_pubkey_fails():
    bad = _signed_entry(0, LLM_SKILL)
    bad["extra"]["signature"]["public_key"] = vf.skill_public_key(DET_SKILL)  # operator key swap
    _stub_chain([bad])
    r = reverify.re_verify("t0")
    assert r["verified"] is False
    assert r["entries"][0]["attribution"]["key_matches_registry"] is False
    print("ok  swapped pubkey -> key mismatch detected")


def test_broken_chain_is_tampered():
    _stub_chain([_signed_entry(0, LLM_SKILL)], chain_verified=False,
                errors=["seq=0 chain_hash tampered"])
    r = reverify.re_verify("t0")
    assert r["verified"] is False
    assert r["verdict"].startswith("TAMPERED"), r["verdict"]
    print("ok  broken chain -> TAMPERED verdict")


if __name__ == "__main__":
    tests = [test_clean_session_verifies, test_tampered_signature_names_skill,
             test_swapped_pubkey_fails, test_broken_chain_is_tampered]
    for t in tests:
        t()
    print(f"\n{len(tests)}/{len(tests)} passed")
