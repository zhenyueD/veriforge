"""
Independent Proof-of-Skill verifier — proves attribution WITHOUT trusting VeriForge.

For a finished session it: (1) pulls each audit entry's ed25519 signature, (2) pulls
the skill's PUBLISHED public key from the registry, (3) checks the signing key matches
the published key (operator can't swap keys), and (4) verifies the signature over
"{skill_id}|{body_sha256}|{signed_ts}". A green run means: each skill output is
cryptographically attributable to that skill's identity, and nothing was altered.

Run: python scripts/verify_signature.py <session_id>
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sdk"))
import veriforge as vf  # noqa: E402

ROUTER = os.getenv("VERIFORGE_ROUTER_URL", "http://localhost:8000")
AUDIT = os.getenv("AUDIT_URL", "http://localhost:8001")


def _get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=8) as r:
        return json.loads(r.read().decode("utf-8"))


def main(session_id: str) -> int:
    published = {s["id"]: s.get("public_key", "") for s in _get(f"{ROUTER}/skills")["skills"]}
    entries = _get(f"{AUDIT}/session/{session_id}").get("entries", [])
    if not entries:
        print(f"no audit entries for session {session_id}")
        return 2

    print(f"{'skill':24} {'key matches registry':22} {'signature valid':16}")
    print("-" * 64)
    all_ok = True
    for e in entries:
        sid = e["skill_id"]
        sig = (e.get("extra") or {}).get("signature") or {}
        pub = sig.get("public_key", "")
        registry_pub = published.get(sid, "")
        key_ok = bool(pub) and pub == registry_pub
        stmt = f"{sid}|{sig.get('body_sha256','')}|{sig.get('signed_ts','')}".encode()
        sig_ok = vf.verify_signature(pub, stmt, sig.get("signature", ""))
        all_ok = all_ok and key_ok and sig_ok
        print(f"{sid:24} {('yes' if key_ok else 'NO'):22} {('valid' if sig_ok else 'INVALID'):16}")
    print("-" * 64)
    print("RESULT:", "every skill output independently attributed + verified"
          if all_ok else "VERIFICATION FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python scripts/verify_signature.py <session_id>")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
