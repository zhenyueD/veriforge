# Skill Specification v0

A **skill** in VeriForge is a self-contained, callable, billable, verifiable unit of AI capability. Every skill is defined by a `skill.yaml` manifest + a handler module.

## Directory Layout

```
skills/<skill-id>/
├── skill.yaml          # Manifest (this spec)
├── handler.py          # Entry point: def invoke(input: dict) -> dict
├── verify.py           # Entry point: def verify(input, output) -> VerifyResult
├── Dockerfile          # Container build (one per skill)
└── tests/
    └── test_invoke.py  # Behavior tests (used by invariant harness)
```

## `skill.yaml` Schema

```yaml
id: claims-intake                  # globally unique, kebab-case
version: 0.1.0
name: "Claims Intake"
description: >
  Parses unstructured first-notice-of-loss text into a structured claim record.

owner:
  name: "Duan Zhenyue"
  contact: "duanzhenyue@gmail.com"
  wallet: "0x..."                  # x402 payout address

inputs:
  schema:                          # JSON Schema for input
    type: object
    required: [text]
    properties:
      text: { type: string, maxLength: 4000 }

outputs:
  schema:                          # JSON Schema for output
    type: object
    required: [claim_type, severity, parties]
    properties:
      claim_type: { type: string, enum: [auto, property, liability, other] }
      severity: { type: number, minimum: 0, maximum: 1 }
      parties: { type: array, items: { type: string } }

price:
  amount_usdc: 0.02                # per-call cost in USDC
  chain: base-sepolia              # testnet for hackathon

verify_hook:
  module: verify
  function: verify                 # (input, output) -> VerifyResult
  invariants:
    - "output.claim_type must be in input.text"   # human-readable for docs
    - "output.severity within [0,1]"
    - "output.parties non-empty for liability claims"

llm_compat:                        # Which LLM clients this skill works with
  - kimi
  - claude
  - gemini
  - ernie

tags:
  - vertical:insurance
  - capability:nlp
  - capability:structured-extraction

reuse_from:                        # Provenance: ClaimsForge dissection trace
  source: claimsforge
  agent: intake_agent
```

## Handler Contract

```python
# handler.py
def invoke(input: dict, *, context: dict | None = None) -> dict:
    """
    Execute the skill.
    `input` is validated against skill.yaml inputs.schema before being passed.
    Returns dict matching outputs.schema.
    Raises SkillError on unrecoverable failure.
    `context` carries trace_id, caller_agent, payment_proof, etc.
    """
```

## Verify Contract

```python
# verify.py
from dataclasses import dataclass

@dataclass
class VerifyResult:
    passed: bool
    invariants: list[dict]          # each: {name, passed, message}
    trust_score: float              # 0..1 (MiroMind verification-centric)
    notes: str | None = None

def verify(input: dict, output: dict) -> VerifyResult: ...
```

## VerifyResult Aggregation

The marketplace `/verify/:trace_id` endpoint aggregates per-skill VerifyResults:

- `passed = all(r.passed for r in results)`
- `trust_score = min(r.trust_score for r in results)` (worst-link Trust)
- `audit_chain` = SHA-256 chain over (skill_id, input_hash, output_hash, prev_hash)

## Skill Lifecycle

| Phase | Action |
|---|---|
| Publish | `vf publish ./skills/<id>` → registers in `registry.json` (Day 2: in-memory; later: Supabase) |
| Discover | KIMI router reads full `registry.json` in 256k context |
| Invoke | POST `/invoke` → x402 402 → pay → execute → emit audit hash |
| Verify | GET `/verify/:trace_id` → returns per-step VerifyResult + chain |
