"""claims-needs invariants."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict


@dataclass
class Invariant:
    name: str
    passed: bool
    message: str = ""


@dataclass
class VerifyResult:
    passed: bool
    invariants: list = field(default_factory=list)
    trust_score: float = 1.0
    notes: str = ""

    def to_dict(self):
        return {**asdict(self), "invariants": [asdict(i) for i in self.invariants]}


def verify(input: dict, output: dict) -> VerifyResult:
    invs: list[Invariant] = []
    rr = output.get("retention_risk")
    needs_any = any(output.get(k) for k in ("surface_need", "latent_need", "emotional_need"))

    invs.append(Invariant("retention_risk_in_range",
                          isinstance(rr, (int, float)) and 0 <= rr <= 1, f"rr={rr}"))
    invs.append(Invariant("at_least_one_need", needs_any,
                          "all need fields empty — agent produced no actionable insight"))

    passed = all(i.passed for i in invs)
    pass_rate = sum(1 for i in invs if i.passed) / len(invs)
    return VerifyResult(passed=passed, invariants=invs, trust_score=round(pass_rate, 4))
