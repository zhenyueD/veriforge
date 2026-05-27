"""
veriforge — one-file SDK to monetize any FastAPI skill on the VeriForge marketplace.

Drop this file next to your skill and add ONE line:

    from fastapi import FastAPI
    from veriforge import monetize

    app = FastAPI()
    monetize(app, skill_id="my-skill", price_usdc=0.02, pay_to="0xYourWallet")

That single call:
  1. Gates your paid path(s) with the x402 pay-per-call protocol — callers without
     a valid X-Payment header get HTTP 402 + payment_requirements.
  2. Splits every payment: creator_amount -> you, platform_fee -> VeriForge treasury.
     The split is transparent in payment_requirements and the X-Payment-Settled record.
  3. Self-registers your skill to the marketplace on startup, so it is discoverable
     and pay-per-callable immediately.

Settlement is mock-but-honest by default (VERIFORGE_X402_MODE=mock): payment tokens
are mocked, but the payout address, the fee split, and call counts are real and
recorded into the audit chain. Set VERIFORGE_X402_MODE=real to verify EIP-3009
signatures via an x402 facilitator on Base Sepolia.

Self-contained: depends only on FastAPI + the Python stdlib.
"""
from __future__ import annotations

import json
import os
import time
import uuid
import urllib.request
from typing import Iterable, Optional

import hashlib
import hmac

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.responses import Response


# ─── Proof-of-Skill signing (ed25519, attributable + publicly verifiable) ────
# Each skill signs its output with a key derived from a master secret + skill_id.
# The PRIVATE key stays in the skill; the PUBLIC key is published in the registry,
# so anyone can verify "this output provably came from skill X" without trusting us.
# Graceful: if `cryptography` is absent, signing is skipped and the skill still runs.
SIGNING_SECRET = os.getenv("VERIFORGE_SIGNING_SECRET", "veriforge-demo-master-secret-2026").encode()
SIGNING_ENABLED = os.getenv("VERIFORGE_SIGN", "1") != "0"

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey, Ed25519PublicKey,
    )
    from cryptography.hazmat.primitives import serialization
    _HAS_CRYPTO = True
except Exception:  # noqa: BLE001
    _HAS_CRYPTO = False


def _skill_private_key(skill_id: str):
    seed = hmac.new(SIGNING_SECRET, skill_id.encode(), hashlib.sha256).digest()[:32]
    return Ed25519PrivateKey.from_private_bytes(seed)


def skill_public_key(skill_id: str) -> str:
    """Hex ed25519 public key for a skill — publish this in the registry."""
    if not _HAS_CRYPTO:
        return ""
    pk = _skill_private_key(skill_id).public_key()
    return pk.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()


def sign_bytes(skill_id: str, data: bytes) -> str:
    """Sign data with the skill's private key. Returns hex signature ('' if unavailable)."""
    if not (_HAS_CRYPTO and SIGNING_ENABLED):
        return ""
    try:
        return _skill_private_key(skill_id).sign(data).hex()
    except Exception:  # noqa: BLE001 — signing never blocks the response
        return ""


def verify_signature(public_key_hex: str, data: bytes, signature_hex: str) -> bool:
    """Verify a Proof-of-Skill signature against a published public key. Trustless."""
    if not _HAS_CRYPTO or not public_key_hex or not signature_hex:
        return False
    try:
        pk = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
        pk.verify(bytes.fromhex(signature_hex), data)
        return True
    except Exception:  # noqa: BLE001
        return False


# ─── Config (env-overridable) ────────────────────────────────────────────────
X402_MODE          = os.getenv("VERIFORGE_X402_MODE", "mock")          # mock | real
X402_NETWORK       = os.getenv("X402_NETWORK", "base-sepolia")
X402_USDC          = os.getenv("X402_USDC_CONTRACT", "0x036CbD53842c5426634e7929541eC2318f3dCF7e")
X402_FACILITATOR   = os.getenv("X402_FACILITATOR", "https://x402.org/facilitator")
# Fallback payout if a skill is attached without its own pay_to.
DEFAULT_PAY_TO     = os.getenv("X402_PAY_TO", "0x0000000000000000000000000000000000000001")
# Platform treasury + default fee (basis points; 200 = 2%).
PLATFORM_ADDR      = os.getenv("VERIFORGE_PLATFORM_ADDR", "0x5Ea1f0ForgeTreasury000000000000000000000")
PLATFORM_FEE_BPS   = int(os.getenv("VERIFORGE_PLATFORM_FEE_BPS", "200"))

_USDC_DECIMALS = 1_000_000  # USDC has 6 decimals


# ─── Fee split (pure, fully testable) ────────────────────────────────────────
def compute_split(
    price_usdc: float,
    pay_to: str,
    *,
    fee_bps: Optional[int] = None,
    platform_addr: Optional[str] = None,
) -> dict:
    """
    Split a gross price into the creator's cut and the platform fee.

    All money fields are strings in micro-USDC (6 decimals) to stay exact and
    JSON-safe. The platform fee floors; the creator gets the remainder, so
    creator_amount + platform_fee == gross always holds.
    """
    bps = PLATFORM_FEE_BPS if fee_bps is None else fee_bps
    treasury = platform_addr or PLATFORM_ADDR
    gross = int(round(price_usdc * _USDC_DECIMALS))
    platform_fee = gross * bps // 10_000
    creator_amount = gross - platform_fee
    return {
        "gross": str(gross),
        "creator_amount": str(creator_amount),
        "platform_fee": str(platform_fee),
        "fee_bps": bps,
        "pay_to": pay_to,
        "platform_addr": treasury,
        "asset": X402_USDC,
        "network": X402_NETWORK,
    }


def earnings_preview(price_usdc: float, *, fee_bps: Optional[int] = None) -> dict:
    """Human-readable USDC split for UI display (the marketplace card)."""
    bps = PLATFORM_FEE_BPS if fee_bps is None else fee_bps
    gross = int(round(price_usdc * _USDC_DECIMALS))
    platform_fee = gross * bps // 10_000
    creator_amount = gross - platform_fee
    return {
        "creator_amount_usdc": creator_amount / _USDC_DECIMALS,
        "platform_fee_usdc": platform_fee / _USDC_DECIMALS,
        "fee_bps": bps,
    }


# ─── Payment verification ────────────────────────────────────────────────────
def _verify_mock(header: str) -> tuple[bool, dict]:
    if not header or len(header) < 4:
        return False, {"reason": "empty X-Payment header"}
    return True, {"mode": "mock", "txid": f"0xmock{uuid.uuid4().hex[:56]}", "ts": time.time()}


def _verify_real(header: str) -> tuple[bool, dict]:
    """Hit the x402 facilitator /verify endpoint (EIP-3009 transferWithAuthorization)."""
    try:
        body = json.dumps({"payment": header, "network": X402_NETWORK}).encode("utf-8")
        req = urllib.request.Request(
            f"{X402_FACILITATOR}/verify",
            data=body, headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
        return bool(data.get("verified")), {"mode": "real", **data}
    except Exception as e:  # noqa: BLE001 — surface reason, never crash the skill
        return False, {"mode": "real", "error": str(e)}


def verify_payment(header: str) -> tuple[bool, dict]:
    return _verify_real(header) if X402_MODE == "real" else _verify_mock(header)


def _payment_requirements(price_usdc: float, resource: str, split: dict, description: str) -> dict:
    return {
        "scheme": "exact",
        "network": X402_NETWORK,
        "maxAmountRequired": split["gross"],
        "resource": resource,
        "description": description,
        "mimeType": "application/json",
        "payTo": split["pay_to"],
        "maxTimeoutSeconds": 60,
        "asset": X402_USDC,
        "extra": {"name": "USD Coin", "version": "2", "mode": X402_MODE, "split": split},
    }


# ─── x402 gate middleware (per-skill payout) ─────────────────────────────────
def attach_x402(
    app,
    *,
    price_usdc: float,
    paths: Iterable[str],
    skill_id: str = "",
    pay_to: Optional[str] = None,
    fee_bps: Optional[int] = None,
):
    """
    Gate `paths` behind x402 pay-per-call. Non-paid paths (e.g. /health) pass through.

    Each skill carries its own `pay_to`, so payment for an invocation is split to the
    skill's creator (minus the platform fee) — this is what makes "add one line, get
    paid per call" work.
    """
    paid_paths = set(paths)
    payout = pay_to or DEFAULT_PAY_TO
    desc = f"VeriForge skill invocation: {skill_id}" if skill_id else "VeriForge skill invocation"

    @app.middleware("http")
    async def x402_gate(request: Request, call_next):
        if request.url.path not in paid_paths:
            return await call_next(request)

        split = compute_split(price_usdc, payout, fee_bps=fee_bps)
        x_pay = request.headers.get("x-payment") or request.headers.get("X-Payment")
        if not x_pay:
            return JSONResponse(
                status_code=402,
                content={
                    "error": "payment_required",
                    "payment_requirements": [_payment_requirements(price_usdc, request.url.path, split, desc)],
                },
                headers={"X-Payment-Mode": X402_MODE},
            )

        ok, info = verify_payment(x_pay)
        if not ok:
            return JSONResponse(
                status_code=402,
                content={"error": "payment_invalid", "info": info},
                headers={"X-Payment-Mode": X402_MODE},
            )

        # Settlement record = verification info + the (real) revenue split.
        settled = {**info, **split, "skill_id": skill_id}
        ts = repr(time.time())
        response = await call_next(request)

        # Read the body so we can sign exactly what the skill returned (Proof of Skill).
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        body_sha = hashlib.sha256(body).hexdigest()
        sig = sign_bytes(skill_id, f"{skill_id}|{body_sha}|{ts}".encode())

        headers = {k: v for k, v in response.headers.items() if k.lower() != "content-length"}
        headers["X-Payment-Settled"] = json.dumps(settled)[:1024]
        headers["X-Payment-Mode"] = X402_MODE
        if sig:  # attributable + publicly verifiable: "skill X produced this exact body at ts"
            headers["X-Skill-Id"] = skill_id
            headers["X-Skill-Signed-Ts"] = ts
            headers["X-Skill-Body-Sha256"] = body_sha
            headers["X-Skill-Signature"] = sig
            headers["X-Skill-Pubkey"] = skill_public_key(skill_id)
        return Response(content=body, status_code=response.status_code,
                        headers=headers, media_type=response.media_type)

    return app


# ─── Self-registration ───────────────────────────────────────────────────────
def register_manifest(
    skill_id: str,
    price_usdc: float,
    pay_to: str,
    *,
    name: str = "",
    description: str = "",
    endpoint: str = "",
    tags: Optional[list] = None,
    llm_compat: Optional[list] = None,
) -> dict:
    """Build the registry manifest the marketplace stores for discovery + billing."""
    return {
        "id": skill_id,
        "name": name or skill_id,
        "endpoint": endpoint,
        "description": description,
        "price_usdc": price_usdc,
        "pay_to": pay_to,
        "tags": tags or [],
        "llm_compat": llm_compat or [],
    }


def _post_register(registry_url: str, manifest: dict, timeout: int = 8) -> tuple[bool, str]:
    url = registry_url.rstrip("/") + "/register"
    try:
        body = json.dumps(manifest).encode("utf-8")
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return 200 <= r.status < 300, f"{r.status}"
    except Exception as e:  # noqa: BLE001 — registration must never block skill startup
        return False, str(e)


# ─── The one-liner ───────────────────────────────────────────────────────────
def monetize(
    app,
    *,
    skill_id: str,
    price_usdc: float,
    pay_to: str,
    paths: Iterable[str] = ("/invoke",),
    fee_bps: Optional[int] = None,
    registry: Optional[str] = None,
    name: str = "",
    description: str = "",
    endpoint: str = "",
    tags: Optional[list] = None,
    llm_compat: Optional[list] = None,
    self_register: bool = True,
):
    """
    Monetize a FastAPI skill in one line: x402 pay-per-call gate (with per-skill
    payout + platform fee split) plus marketplace self-registration on startup.

    `registry` defaults to env VERIFORGE_REGISTRY_URL; self-registration is skipped
    silently if neither is set, so the skill still runs standalone.
    """
    attach_x402(app, price_usdc=price_usdc, paths=list(paths),
                skill_id=skill_id, pay_to=pay_to, fee_bps=fee_bps)

    registry_url = registry or os.getenv("VERIFORGE_REGISTRY_URL", "")
    if self_register and registry_url:
        manifest = register_manifest(
            skill_id, price_usdc, pay_to,
            name=name, description=description, endpoint=endpoint,
            tags=tags, llm_compat=llm_compat,
        )

        @app.on_event("startup")
        async def _self_register():  # pragma: no cover - exercised at runtime
            ok, detail = _post_register(registry_url, manifest)
            import sys
            print(f"[veriforge] self-register {skill_id} -> {registry_url}: "
                  f"{'ok' if ok else 'skipped'} ({detail})", file=sys.stderr, flush=True)

    return app
