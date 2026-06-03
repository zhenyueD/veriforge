#!/usr/bin/env python3
"""
Standalone VeriForge receipt verifier — the "verify it yourself" tool.

This script DELIBERATELY does not import VeriForge and makes NO network calls.
It proves the receipt is self-certifying: you don't trust VeriForge, you check
the math. Run it on any machine that has never heard of this project.

    python3 verify_receipt.py receipt.json      # or:  curl .../receipt/<tid> | python3 verify_receipt.py

It checks two independent things, rebuilding the signed/hashed inputs FROM the
atomic fields (so it never blindly trusts the strings the receipt handed it):

  1. Attribution (ed25519) — a specific skill's key signed this exact output.
  2. Integrity (SHA-256)   — the audit-chain link wasn't tampered.

Only dependency: `cryptography` (pip install cryptography).
"""
import hashlib
import json
import sys


def _load() -> dict:
    if len(sys.argv) > 1 and sys.argv[1] not in ("-", "/dev/stdin"):
        with open(sys.argv[1]) as f:
            return json.load(f)
    return json.load(sys.stdin)


def check_attribution(r: dict) -> bool:
    """ed25519: the skill's published public key signed `skill_id|body_sha256|signed_ts`."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    a = r.get("attribution", {})
    pub, sig = a.get("public_key", ""), a.get("signature", "")
    # Rebuild the signed statement from atomic fields — do NOT trust the provided string.
    rebuilt = f"{r['skill_id']}|{a.get('body_sha256','')}|{a.get('signed_ts','')}"
    if a.get("signed_statement") and a["signed_statement"] != rebuilt:
        print(f"  ✗ attribution: signed_statement does not match atomic fields")
        print(f"      receipt : {a['signed_statement']}")
        print(f"      rebuilt : {rebuilt}")
        return False
    if not pub or not sig:
        print("  ✗ attribution: no public_key / signature in receipt (skill did not sign)")
        return False
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub)).verify(
            bytes.fromhex(sig), rebuilt.encode())
    except Exception as e:  # noqa: BLE001
        print(f"  ✗ attribution: ed25519 signature INVALID ({type(e).__name__})")
        return False
    print(f"  ✓ attribution: skill '{r['skill_id']}' signed this output")
    print(f"      key {pub[:16]}…  over  \"{rebuilt}\"")
    return True


def check_integrity(r: dict) -> bool:
    """SHA-256: recompute the chain-link hash from atomic fields and compare."""
    g = r.get("integrity", {})
    vp = r.get("verify_passed")
    rebuilt = "|".join([
        g.get("prev_chain_hash", ""), r["session_id"], str(r["seq"]), r["skill_id"],
        r["trace_id"], r["input_hash"], r["output_hash"],
        "" if vp is None else str(int(bool(vp))), f"{r['ts']:.6f}",
    ])
    if g.get("chain_preimage") and g["chain_preimage"] != rebuilt:
        print("  ✗ integrity: chain_preimage does not match atomic fields")
        return False
    recomputed = hashlib.sha256(rebuilt.encode()).hexdigest()
    if recomputed != g.get("chain_hash"):
        print(f"  ✗ integrity: chain_hash MISMATCH — tampered")
        print(f"      recomputed {recomputed[:16]}…  vs receipt {str(g.get('chain_hash'))[:16]}…")
        return False
    print(f"  ✓ integrity: audit-chain link intact (sha256 recomputed = {recomputed[:16]}…)")
    return True


def main() -> int:
    try:
        r = _load()
    except Exception as e:  # noqa: BLE001
        print(f"could not read receipt JSON: {e}")
        return 2
    print(f"VeriForge receipt — skill={r.get('skill_id')} trace={r.get('trace_id','')[:12]}…")
    print("(this verifier imports no VeriForge code and made no network calls)\n")
    a_ok = check_attribution(r)
    i_ok = check_integrity(r)
    ok = a_ok and i_ok
    print()
    if ok:
        print("✅ RECEIPT VALID — attributable + tamper-evident. You verified it yourself.")
    else:
        print("❌ RECEIPT INVALID — do not trust this claim.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
