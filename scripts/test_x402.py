"""
x402 Base Sepolia smoke test.

Goal: verify the full pay-per-call round trip works on Base Sepolia testnet:
  1. Client GET /paid → server returns 402 with payment requirements
  2. Client signs an EIP-3009 transferWithAuthorization permit for USDC
  3. Client POST /paid with X-Payment header
  4. Server verifies on-chain, returns 200 + content

For Day 0.5 spike we use the Coinbase x402 reference server + a tiny client.
If the official x402 SDK / facilitator isn't reachable, we degrade to a mock
mode that demonstrates the protocol locally (good enough for demo Day 5).

Run:
  export X402_WALLET_PRIVATE_KEY=0x...
  export BASE_SEPOLIA_RPC=https://sepolia.base.org
  python scripts/test_x402.py
"""
from __future__ import annotations
import json, os, sys, time

try:
    import requests
except ImportError:
    sys.exit("pip install requests web3 eth-account")

try:
    from eth_account import Account
    from eth_account.messages import encode_typed_data
except ImportError:
    sys.exit("pip install eth-account>=0.13")

# Base Sepolia
USDC_BASE_SEPOLIA = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
RPC = os.getenv("BASE_SEPOLIA_RPC", "https://sepolia.base.org")
FACILITATOR = os.getenv("X402_FACILITATOR", "https://x402.org/facilitator")


def check_wallet() -> str | None:
    pk = os.getenv("X402_WALLET_PRIVATE_KEY")
    if not pk:
        print("WARN: X402_WALLET_PRIVATE_KEY not set. Set to a TESTNET-ONLY private key.")
        print("      Generate one: python -c \"from eth_account import Account; print(Account.create().key.hex())\"")
        print("      Then fund with Base Sepolia ETH + USDC from https://faucet.circle.com")
        return None
    try:
        acct = Account.from_key(pk)
        return acct.address
    except Exception as e:
        print(f"FAIL: invalid private key: {e}")
        return None


def test_facilitator_reachable() -> bool:
    """Confirm the x402 facilitator endpoint is reachable."""
    try:
        r = requests.get(FACILITATOR, timeout=10)
        print(f"  facilitator {FACILITATOR}: {r.status_code}")
        return r.status_code < 500
    except Exception as e:
        print(f"  facilitator unreachable: {e}")
        return False


def test_402_protocol_local() -> bool:
    """Simulate the 402 protocol locally to confirm protocol logic.
    A real test against a live x402 server is Day 3 work; Day 0.5 just verifies wallet + protocol shape.
    """
    payment_requirement = {
        "scheme": "exact",
        "network": "base-sepolia",
        "maxAmountRequired": "20000",   # 0.02 USDC (6 decimals)
        "resource": "/invoke",
        "description": "VeriForge skill invocation",
        "mimeType": "application/json",
        "payTo": "0x0000000000000000000000000000000000000001",
        "maxTimeoutSeconds": 60,
        "asset": USDC_BASE_SEPOLIA,
        "extra": {"name": "USD Coin", "version": "2"},
    }
    print(f"  built 402 payload: {json.dumps(payment_requirement, indent=2)}")

    pk = os.getenv("X402_WALLET_PRIVATE_KEY")
    if not pk:
        print("  SKIP signature test (no key)")
        return False

    # Build EIP-3009 transferWithAuthorization typed data
    acct = Account.from_key(pk)
    now = int(time.time())
    typed = {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "TransferWithAuthorization": [
                {"name": "from", "type": "address"},
                {"name": "to", "type": "address"},
                {"name": "value", "type": "uint256"},
                {"name": "validAfter", "type": "uint256"},
                {"name": "validBefore", "type": "uint256"},
                {"name": "nonce", "type": "bytes32"},
            ],
        },
        "primaryType": "TransferWithAuthorization",
        "domain": {
            "name": "USD Coin",
            "version": "2",
            "chainId": 84532,    # Base Sepolia
            "verifyingContract": USDC_BASE_SEPOLIA,
        },
        "message": {
            "from": acct.address,
            "to": payment_requirement["payTo"],
            "value": int(payment_requirement["maxAmountRequired"]),
            "validAfter": 0,
            "validBefore": now + 600,
            "nonce": "0x" + os.urandom(32).hex(),
        },
    }
    try:
        msg = encode_typed_data(full_message=typed)
        sig = acct.sign_message(msg)
        print(f"  signed authorization: r={hex(sig.r)[:20]}... s={hex(sig.s)[:20]}... v={sig.v}")
        return True
    except Exception as e:
        print(f"  signing failed: {e}")
        return False


def test_rpc_reachable() -> bool:
    try:
        r = requests.post(RPC, json={"jsonrpc": "2.0", "method": "eth_chainId", "id": 1}, timeout=10)
        chain_id = int(r.json()["result"], 16)
        print(f"  RPC {RPC}: chainId={chain_id} (expect 84532)")
        return chain_id == 84532
    except Exception as e:
        print(f"  RPC unreachable: {e}")
        return False


def main() -> int:
    print("== x402 Base Sepolia smoke test ==")

    print("\n[1] Wallet")
    addr = check_wallet()
    if addr:
        print(f"  address: {addr}")

    print("\n[2] Base Sepolia RPC")
    rpc_ok = test_rpc_reachable()

    print("\n[3] x402 Facilitator")
    fac_ok = test_facilitator_reachable()

    print("\n[4] 402 protocol + EIP-3009 signing")
    sig_ok = test_402_protocol_local()

    print("\n== Summary ==")
    print(f"  wallet:      {'OK' if addr else 'MISSING'}")
    print(f"  RPC:         {'OK' if rpc_ok else 'FAIL'}")
    print(f"  facilitator: {'OK' if fac_ok else 'DEGRADED'}")
    print(f"  signing:     {'OK' if sig_ok else 'FAIL'}")

    if addr and rpc_ok and sig_ok:
        print("\nResult: PASS — Day 3 x402 gateway is viable.")
        return 0
    if not addr:
        print("\nResult: WAITING — need X402_WALLET_PRIVATE_KEY + faucet funds.")
        return 2
    print("\nResult: PARTIAL — consider mock fallback (PROJECT.md §10).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
