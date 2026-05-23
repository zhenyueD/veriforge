"""
x402 Pay-Per-Call Gateway middleware.

Two modes (env VERIFORGE_X402_MODE):
  - mock  (default): any non-empty X-Payment header passes verification.
    Demo-ready without on-chain dependencies. Suitable for Demo Day backup.
  - real: verify the EIP-3009 transferWithAuthorization signature against
    Base Sepolia (via x402 facilitator). Requires X402_FACILITATOR + RPC.

Wraps a FastAPI app:
    from fastapi import FastAPI
    from marketplace.gateway.x402 import attach_x402
    app = FastAPI()
    attach_x402(app, price_usdc=0.02, paths=["/invoke"])

On a paid path with no X-Payment header → returns 402 + payment_requirements.
With a valid X-Payment header → request proceeds; emits X-Payment-Settled
in the response.
"""
from __future__ import annotations
import json, os, time, uuid
from typing import Iterable, Optional
from fastapi import Request
from fastapi.responses import JSONResponse


X402_MODE         = os.getenv("VERIFORGE_X402_MODE", "mock")        # mock | real
X402_PAY_TO       = os.getenv("X402_PAY_TO", "0x0000000000000000000000000000000000000001")
X402_NETWORK      = os.getenv("X402_NETWORK", "base-sepolia")
X402_USDC         = os.getenv("X402_USDC_CONTRACT", "0x036CbD53842c5426634e7929541eC2318f3dCF7e")
X402_FACILITATOR  = os.getenv("X402_FACILITATOR", "https://x402.org/facilitator")


def _payment_requirements(price_usdc: float, resource: str, description: str = "") -> dict:
    return {
        "scheme": "exact",
        "network": X402_NETWORK,
        "maxAmountRequired": str(int(price_usdc * 1_000_000)),   # USDC 6 decimals
        "resource": resource,
        "description": description,
        "mimeType": "application/json",
        "payTo": X402_PAY_TO,
        "maxTimeoutSeconds": 60,
        "asset": X402_USDC,
        "extra": {"name": "USD Coin", "version": "2", "mode": X402_MODE},
    }


def _verify_payment_mock(header: str) -> tuple[bool, dict]:
    if not header or len(header) < 4:
        return False, {"reason": "empty X-Payment header"}
    return True, {
        "mode": "mock",
        "txid": f"0xmock{uuid.uuid4().hex[:56]}",
        "ts": time.time(),
    }


def _verify_payment_real(header: str) -> tuple[bool, dict]:
    """Hit the x402 facilitator /verify endpoint."""
    import urllib.request
    try:
        body = json.dumps({"payment": header, "network": X402_NETWORK}).encode("utf-8")
        req = urllib.request.Request(
            f"{X402_FACILITATOR}/verify",
            data=body, headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
        return bool(data.get("verified")), data
    except Exception as e:
        return False, {"error": str(e)}


def verify_payment(header: str) -> tuple[bool, dict]:
    if X402_MODE == "real":
        return _verify_payment_real(header)
    return _verify_payment_mock(header)


def attach_x402(app, *, price_usdc: float, paths: Iterable[str], skill_id: str = ""):
    """
    Attach the gateway middleware. Only requests matching `paths`
    are gated; everything else (e.g. /health) passes through.
    """
    paid_paths = set(paths)
    desc = f"VeriForge skill invocation: {skill_id}" if skill_id else "VeriForge skill invocation"

    @app.middleware("http")
    async def x402_gate(request: Request, call_next):
        if request.url.path not in paid_paths:
            return await call_next(request)

        x_pay = request.headers.get("x-payment") or request.headers.get("X-Payment")
        if not x_pay:
            return JSONResponse(
                status_code=402,
                content={
                    "error": "payment_required",
                    "payment_requirements": [
                        _payment_requirements(price_usdc, request.url.path, desc),
                    ],
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

        response = await call_next(request)
        response.headers["X-Payment-Settled"] = json.dumps(info)[:512]
        response.headers["X-Payment-Mode"] = X402_MODE
        return response
