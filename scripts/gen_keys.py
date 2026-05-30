#!/usr/bin/env python3
"""
Generate each bundled skill's OWN ed25519 keypair and sync the public keys into the
registry. Run this once at setup (it's idempotent — existing keys are kept).

Why this exists: VeriForge's Proof-of-Skill signatures used to derive every key from
a single shared master secret (which lived, by default, in the public repo — so anyone
could forge any skill). Now each skill holds its own private key; the operator only ever
sees public keys. This script materializes that model for the bundled skills:

  - private key  -> skills/<id>/.keys/<id>.ed25519   (gitignored; this IS the secret)
  - public  key  -> marketplace/registry/registry.json  ("public_key" field, committed)

Each skill container mounts ./skills/<id> at /app and signs from /app/.keys; host-side
tooling (tests, this script) runs from the repo root and uses ./.keys. So we write the
SAME private key to both locations — repo `.keys/<id>.ed25519` and
`skills/<id>/.keys/<id>.ed25519` — so the signer (skill, in either context) and the
registry's published public key always agree. A third-party (BYO) skill does the same in
its own directory — its private key never touches this repo.

Usage:
    python3 scripts/gen_keys.py            # generate missing keys + sync registry
    python3 scripts/gen_keys.py --force    # rotate ALL keys (overwrites existing)
"""
from __future__ import annotations

import json
import os
import sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY = os.path.join(REPO, "marketplace", "registry", "registry.json")
FORCE = "--force" in sys.argv


def _raw_private(key: Ed25519PrivateKey) -> bytes:
    return key.private_bytes(serialization.Encoding.Raw,
                             serialization.PrivateFormat.Raw,
                             serialization.NoEncryption())


def _pub_hex(key: Ed25519PrivateKey) -> str:
    return key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()


def _write_key(keyfile: str, raw: bytes) -> None:
    os.makedirs(os.path.dirname(keyfile), exist_ok=True)
    with open(keyfile, "wb") as f:
        f.write(raw)
    os.chmod(keyfile, 0o600)


def _load_or_create(keyfiles: list[str]) -> Ed25519PrivateKey:
    """Load the key from the first existing location, else generate one. Always
    mirror the (chosen) key into every location so host + container signers agree."""
    key = None
    if not FORCE:
        for kf in keyfiles:
            if os.path.exists(kf):
                with open(kf, "rb") as f:
                    key = Ed25519PrivateKey.from_private_bytes(f.read()[:32])
                break
    if key is None:
        key = Ed25519PrivateKey.generate()
    raw = _raw_private(key)
    for kf in keyfiles:
        _write_key(kf, raw)
    return key


def main() -> int:
    with open(REGISTRY) as f:
        reg = json.load(f)
    skills = reg.get("skills", [])

    changed = 0
    for s in skills:
        sid = s["id"]
        skill_dir = os.path.join(REPO, "skills", sid)
        if not os.path.isdir(skill_dir):
            # Skill source not bundled here (e.g. an external/BYO skill that
            # self-registers its own key at runtime). Skip — don't fabricate a key.
            print(f"  · {sid}: no skills/{sid}/ dir — skipped (self-registers its own key)")
            continue
        # Same key in two places: repo .keys (host tooling/tests) + skills/<id>/.keys
        # (the container's /app/.keys). Mirrored so every signer matches the registry.
        keyfiles = [
            os.path.join(REPO, ".keys", f"{sid}.ed25519"),
            os.path.join(skill_dir, ".keys", f"{sid}.ed25519"),
        ]
        existed = any(os.path.exists(kf) for kf in keyfiles) and not FORCE
        key = _load_or_create(keyfiles)
        pub = _pub_hex(key)
        if s.get("public_key") != pub:
            s["public_key"] = pub
            changed += 1
        verb = "kept" if existed else ("rotated" if FORCE else "created")
        print(f"  ✓ {sid}: {verb}  pub={pub[:16]}…")

    with open(REGISTRY, "w") as f:
        json.dump(reg, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"\nregistry synced: {changed} public key(s) updated in {os.path.relpath(REGISTRY, REPO)}")
    print("private keys are gitignored under skills/<id>/.keys/ — never commit them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
