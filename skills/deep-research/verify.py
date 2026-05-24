"""deep-research invariants."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict

VALID_STATUS = {"completed", "timeout", "trace_parse_error", "failed"}


@dataclass
class Invariant:
    name: str; passed: bool; message: str = ""


@dataclass
class VerifyResult:
    passed: bool; invariants: list = field(default_factory=list)
    trust_score: float = 1.0; notes: str = ""

    def to_dict(self):
        return {**asdict(self), "invariants": [asdict(i) for i in self.invariants]}


def _is_sha256(h) -> bool:
    return isinstance(h, str) and len(h) == 64 and all(c in "0123456789abcdef" for c in h)


def verify(input: dict, output: dict) -> VerifyResult:
    invs: list[Invariant] = []
    status = output.get("status")
    answer = output.get("answer") or ""
    n_steps = output.get("n_steps", 0)
    tip = output.get("trace_chain_tip", "")
    chain = output.get("trace_chain") or []

    invs.append(Invariant("status_is_valid", status in VALID_STATUS, f"status={status!r}"))
    invs.append(Invariant("trace_chain_tip_is_sha256", _is_sha256(tip), f"tip={tip[:16]}..."))
    invs.append(Invariant("chain_length_matches_steps", len(chain) == n_steps,
                          f"chain {len(chain)} != steps {n_steps}"))
    # A completed research run must produce an answer and at least one traced step.
    if status == "completed":
        invs.append(Invariant("completed_has_answer", bool(answer.strip()), "completed but empty answer"))
        invs.append(Invariant("completed_has_steps", n_steps > 0, "completed but no trace steps"))

    passed = all(i.passed for i in invs)
    pass_rate = sum(1 for i in invs if i.passed) / max(1, len(invs))
    return VerifyResult(passed=passed, invariants=invs, trust_score=round(pass_rate, 4))
