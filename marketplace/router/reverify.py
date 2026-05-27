"""
Feature B — /re-verify: honest, type-aware re-verification of a finished session.

The existing audit /verify/{trace_id} only re-derives the SHA-256 chain. /re-verify
adds the two things that make attribution *trustless* and *honest*:

  1. Chain integrity   — every chained field (hashes, verify_passed, seq, skill_id)
                         is recomputed; tampering any breaks the link and names the seq.
  2. Attribution       — each entry's ed25519 signature is checked against the skill's
                         REGISTRY-published public key (operator can't swap keys), so the
                         output is provably attributable to that skill — without trusting us.

Then it dispatches by skill TYPE, because honesty is the product:

  · deterministic skill (e.g. claims-fraud-image) → re-EXECUTABLE: re-run with the same
    input yields an identical output_hash. With a `replay` input we prove it live.
  · LLM skill → NOT bit-reproducible. We never re-run-and-hash (that would false-positive
    as tampering). Instead we verify signature + chain + re-run the skill's pure invariant
    hook over the recorded output. We say exactly what we proved and what we did not.

Chain + attribution are complementary: the chain hashes input/output_hash + verify_passed,
the signature pins the raw response body's sha256 (carried in extra, NOT chained). So
tampering core fields trips the chain; tampering the signed body trips the signature.
"""
from __future__ import annotations

import json
import os
import urllib.request
from typing import Optional

import veriforge as vf  # ed25519 verify_signature
from router import load_registry

AUDIT_URL = os.getenv("AUDIT_URL", "http://localhost:8001")


def _get(url: str, timeout: int = 8) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _registry_index() -> dict[str, dict]:
    """skill_id -> {public_key, deterministic} from the published registry."""
    idx: dict[str, dict] = {}
    for s in load_registry().get("skills", []):
        idx[s["id"]] = {
            "public_key": s.get("public_key", ""),
            "deterministic": bool(s.get("deterministic", False)),
        }
    return idx


def _check_attribution(entry: dict, registry_pub: str) -> dict:
    """Verify the entry's ed25519 signature against the registry-published key."""
    sig = (entry.get("extra") or {}).get("signature") or {}
    pub = sig.get("public_key", "")
    key_matches = bool(pub) and pub == registry_pub
    stmt = f"{entry['skill_id']}|{sig.get('body_sha256','')}|{sig.get('signed_ts','')}".encode()
    sig_valid = vf.verify_signature(pub, stmt, sig.get("signature", ""))
    return {
        "signed": bool(sig.get("signature")),
        "key_matches_registry": key_matches,
        "signature_valid": sig_valid,
        "attributed": bool(sig.get("signature")) and key_matches and sig_valid,
        "body_sha256": sig.get("body_sha256", ""),
    }


def _skill_endpoint(skill_id: str) -> str:
    host_mode = os.getenv("ENDPOINT_HOST", "docker")
    for s in load_registry().get("skills", []):
        if s["id"] == skill_id:
            host = skill_id if host_mode == "docker" else "localhost"
            return s["endpoint"].replace("HOST", host)
    return ""


def _reexecute_deterministic(skill_id: str, replay_input: dict, stored_output_hash: str) -> dict:
    """Re-invoke a deterministic skill over HTTP (where its deps live) and compare
    output_hash — bit-equality proves the output is independently reproducible."""
    from executor import _exec_http, _mock_x_payment
    step = _exec_http(skill_id, replay_input, endpoint=_skill_endpoint(skill_id),
                      x_payment=_mock_x_payment(skill_id))
    if not step.ok:
        return {"attempted": True, "reproduced": False, "error": step.error[:200]}
    recomputed = step.output.get("output_hash", "")
    return {
        "attempted": True,
        "reproduced": bool(recomputed) and recomputed == stored_output_hash,
        "recomputed_output_hash": recomputed,
        "stored_output_hash": stored_output_hash,
    }


def _rerun_invariants(skill_id: str, replay_input: dict, replay_output: dict) -> dict:
    """Re-run the skill's pure verify() hook over a supplied output (LLM-safe)."""
    from executor import _run_verify
    passed, trust = _run_verify(skill_id, replay_input or {}, replay_output)
    return {"attempted": True, "invariants_passed": passed, "trust_score": trust}


def re_verify(trace_id: str, replay: Optional[dict] = None) -> dict:
    """
    Re-verify the full session a trace_id sits in. `replay` is an optional map
    {skill_id: {"input": {...}, "output": {...}}} to prove re-execution / invariants live.
    """
    chain = _get(f"{AUDIT_URL}/verify/{trace_id}")
    entries = chain.get("full_chain", [])
    chain_ok = bool(chain.get("chain_verified"))
    reg = _registry_index()
    replay = replay or {}

    results: list[dict] = []
    failed_skills: list[str] = []
    for e in entries:
        sid = e["skill_id"]
        meta = reg.get(sid, {"public_key": "", "deterministic": False})
        is_det = meta["deterministic"]
        attribution = _check_attribution(e, meta["public_key"])

        item = {
            "seq": e["seq"],
            "skill_id": sid,
            "type": "deterministic" if is_det else "llm",
            "attribution": attribution,
            "invariants_recorded": e.get("verify_passed"),  # chain-protected
            "trust_score": (e.get("extra") or {}).get("trust_score"),
        }

        rp = replay.get(sid) or {}
        if is_det:
            item["reproducibility"] = "bit-reproducible (pure function of input)"
            if rp.get("input"):
                item["re_execution"] = _reexecute_deterministic(sid, rp["input"], e["output_hash"])
        else:
            item["reproducibility"] = ("LLM output is not bit-reproducible; verified via "
                                       "signature + chain + invariants, NOT re-execution")
            if rp.get("output") is not None:
                item["invariants_rerun"] = _rerun_invariants(sid, rp.get("input"), rp["output"])

        if not attribution["attributed"]:
            failed_skills.append(sid)
        results.append(item)

    all_attributed = all(r["attribution"]["attributed"] for r in results) if results else False
    verified = chain_ok and all_attributed
    if verified:
        verdict = "VERIFIED — every step chain-intact + cryptographically attributed"
    elif not chain_ok:
        verdict = "TAMPERED — audit chain broken"
    else:
        verdict = f"ATTRIBUTION FAILED — {', '.join(failed_skills)}"

    return {
        "trace_id": trace_id,
        "session_id": chain.get("session_id"),
        "verified": verified,
        "verdict": verdict,
        "chain_verified": chain_ok,
        "chain_errors": chain.get("chain_errors", []),
        "all_attributed": all_attributed,
        "failed_skills": failed_skills,
        "n_entries": len(results),
        "entries": results,
    }
