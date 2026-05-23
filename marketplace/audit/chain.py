"""
VeriForge Audit Chain — SHA-256 hash chain over skill invocations.

Each skill invocation emits an AuditEntry. The chain links them by
including the previous chain_hash in the next hash computation, so
tampering with any entry breaks every subsequent link.

This is the MiroMind "verification-centric" principle realized in code:
any judge can independently verify the chain by replaying the hashes.

Schema:
    chain_hash_N = sha256(
        prev_chain_hash + skill_id + input_hash + output_hash + ts + verify_ok
    )

The chain is anchored per session_id (or per trace_root) so multi-skill
plans get their own self-contained sub-chain.
"""
from __future__ import annotations
import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from typing import Optional


GENESIS_HASH = "0" * 64  # all-zero parent for the first entry in a chain


@dataclass
class AuditEntry:
    session_id: str                  # anchors a sub-chain
    seq: int                         # 0-indexed step within session
    skill_id: str
    trace_id: str                    # skill's own trace_id (one-shot uuid)
    input_hash: str                  # sha256 of validated skill input
    output_hash: str                 # sha256 of skill output (core fields)
    verify_passed: Optional[bool]    # None if no verify_hook ran yet
    prev_chain_hash: str             # hash of the previous entry in this session
    chain_hash: str                  # sha256 of (above) — this entry's link
    ts: float                        # unix seconds
    elapsed_ms: int = 0
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def compute_chain_hash(
    *,
    prev_chain_hash: str,
    session_id: str,
    seq: int,
    skill_id: str,
    trace_id: str,
    input_hash: str,
    output_hash: str,
    verify_passed: Optional[bool],
    ts: float,
) -> str:
    payload = "|".join([
        prev_chain_hash,
        session_id,
        str(seq),
        skill_id,
        trace_id,
        input_hash,
        output_hash,
        "" if verify_passed is None else str(int(bool(verify_passed))),
        f"{ts:.6f}",
    ])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def make_entry(
    *,
    session_id: str,
    seq: int,
    skill_id: str,
    trace_id: str,
    input_hash: str,
    output_hash: str,
    prev_chain_hash: str,
    verify_passed: Optional[bool] = None,
    elapsed_ms: int = 0,
    extra: Optional[dict] = None,
    ts: Optional[float] = None,
) -> AuditEntry:
    t = ts if ts is not None else time.time()
    ch = compute_chain_hash(
        prev_chain_hash=prev_chain_hash,
        session_id=session_id,
        seq=seq,
        skill_id=skill_id,
        trace_id=trace_id,
        input_hash=input_hash,
        output_hash=output_hash,
        verify_passed=verify_passed,
        ts=t,
    )
    return AuditEntry(
        session_id=session_id,
        seq=seq,
        skill_id=skill_id,
        trace_id=trace_id,
        input_hash=input_hash,
        output_hash=output_hash,
        verify_passed=verify_passed,
        prev_chain_hash=prev_chain_hash,
        chain_hash=ch,
        ts=t,
        elapsed_ms=elapsed_ms,
        extra=extra or {},
    )


def verify_chain(entries: list[AuditEntry]) -> tuple[bool, list[str]]:
    """
    Re-derive each entry's chain_hash from prev + content and compare.
    Returns (all_ok, errors_per_entry).
    """
    errors: list[str] = []
    prev = GENESIS_HASH
    expected_seq = 0
    for e in entries:
        # Recompute from canonical inputs
        if e.prev_chain_hash != prev:
            errors.append(f"seq={e.seq} prev_chain_hash mismatch (got {e.prev_chain_hash[:12]}..., expected {prev[:12]}...)")
        if e.seq != expected_seq:
            errors.append(f"seq={e.seq} out of order (expected {expected_seq})")
        recomputed = compute_chain_hash(
            prev_chain_hash=e.prev_chain_hash,
            session_id=e.session_id,
            seq=e.seq,
            skill_id=e.skill_id,
            trace_id=e.trace_id,
            input_hash=e.input_hash,
            output_hash=e.output_hash,
            verify_passed=e.verify_passed,
            ts=e.ts,
        )
        if recomputed != e.chain_hash:
            errors.append(f"seq={e.seq} chain_hash tampered (recomputed {recomputed[:12]}..., found {e.chain_hash[:12]}...)")
        prev = e.chain_hash
        expected_seq += 1
    return len(errors) == 0, errors


if __name__ == "__main__":
    # Self-test: 3-entry chain, verify pass, then tamper one and verify fail.
    s = "demo-session"
    e0 = make_entry(session_id=s, seq=0, skill_id="claims-intent",
                    trace_id="t0", input_hash="i0", output_hash="o0",
                    prev_chain_hash=GENESIS_HASH, verify_passed=True)
    e1 = make_entry(session_id=s, seq=1, skill_id="claims-damage-vision",
                    trace_id="t1", input_hash="i1", output_hash="o1",
                    prev_chain_hash=e0.chain_hash, verify_passed=True)
    e2 = make_entry(session_id=s, seq=2, skill_id="claims-verify",
                    trace_id="t2", input_hash="i2", output_hash="o2",
                    prev_chain_hash=e1.chain_hash, verify_passed=True)
    ok, errs = verify_chain([e0, e1, e2])
    print(f"clean chain verify: ok={ok} errs={errs}")
    # Tamper: change output_hash but keep the chain_hash, should detect
    e1_tampered = AuditEntry(**{**e1.to_dict(), "output_hash": "TAMPERED"})
    ok2, errs2 = verify_chain([e0, e1_tampered, e2])
    print(f"tampered chain verify: ok={ok2} errs[0]={errs2[0] if errs2 else None}")
