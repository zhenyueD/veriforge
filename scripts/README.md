# Scripts

## Day 0.5 spike tests

### `test_kimi_router.py`
Verifies KIMI k2.6 can hold a registry-sized prompt (~50 skills, ~30k chars) and route correctly.

```bash
export MOONSHOT_API_KEY=...     # https://platform.moonshot.ai
pip install openai
python scripts/test_kimi_router.py
```

**Pass thresholds**:
- 3/3 routing cases correct
- max latency < 10s (else fall back to HyDE RAG)
- cost < $0.10 per route

### `test_x402.py`
Verifies wallet + Base Sepolia RPC + EIP-3009 USDC signing works. Doesn't yet hit a real facilitator (that's Day 3).

```bash
# Generate a TESTNET-ONLY wallet (never use mainnet keys):
python -c "from eth_account import Account; a=Account.create(); print(a.address); print(a.key.hex())"

# Fund with Base Sepolia ETH (gas) + USDC:
#   ETH:   https://www.alchemy.com/faucets/base-sepolia
#   USDC:  https://faucet.circle.com  (select Base Sepolia)

export X402_WALLET_PRIVATE_KEY=0x...
pip install requests web3 eth-account
python scripts/test_x402.py
```

**Pass thresholds**:
- wallet, RPC, signing all OK
- facilitator reachable (else use mock fallback)
