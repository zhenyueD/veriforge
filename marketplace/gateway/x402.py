"""
x402 Pay-Per-Call gateway — thin shim over the canonical SDK.

As of Day 4 the x402 logic lives in the single-file SDK `sdk/veriforge.py`, which is
what skill authors copy to monetize their skill (per-skill payout + platform fee split
+ self-registration). This module re-exports the gate so any gateway-level code keeps
the same import path:

    from marketplace.gateway.x402 import attach_x402, verify_payment

For skills, prefer the one-liner:

    from veriforge import monetize
    monetize(app, skill_id="my-skill", price_usdc=0.02, pay_to="0xYourWallet")
"""
from __future__ import annotations

import os
import sys

# Make the single-file SDK importable regardless of CWD.
_SDK_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "sdk")
sys.path.insert(0, os.path.abspath(_SDK_DIR))

from veriforge import (  # noqa: E402  (path set up above)
    X402_MODE,
    attach_x402,
    compute_split,
    earnings_preview,
    verify_payment,
)

__all__ = ["X402_MODE", "attach_x402", "compute_split", "earnings_preview", "verify_payment"]
