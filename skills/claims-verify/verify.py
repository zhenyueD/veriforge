"""claims-verify invariants."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict

VALID_VERDICTS = {"approve", "revise", "escalate_to_human"}


@dataclass
class Invariant:
    name: str; passed: bool; message: str = ""


@dataclass
class VerifyResult:
    passed: bool; invariants: list = field(default_factory=list)
    trust_score: float = 1.0; notes: str = ""

    def to_dict(self):
        return {**asdict(self), "invariants": [asdict(i) for i in self.invariants]}


def verify(input: dict, output: dict) -> VerifyResult:
    invs: list[Invariant] = []
    verdict = output.get("verdict")
    revised = output.get("revised_offer")
    orig_amt = (input.get("offer") or {}).get("amount_cents", 0)

    invs.append(Invariant("verdict_is_valid_enum",
                          verdict in VALID_VERDICTS, f"verdict={verdict!r}"))
    if revised:
        rev_amt = revised.get("amount_cents", 0)
        invs.append(Invariant("revised_amount_not_increased",
                              rev_amt <= orig_amt,
                              f"revised {rev_amt} > original {orig_amt}"))

    passed = all(i.passed for i in invs)
    pass_rate = sum(1 for i in invs if i.passed) / max(1, len(invs))
    return VerifyResult(passed=passed, invariants=invs, trust_score=round(pass_rate, 4))
