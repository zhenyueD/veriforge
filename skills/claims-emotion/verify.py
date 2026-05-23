"""claims-emotion invariants."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict

VALID_RISKS = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


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
    score = output.get("score")
    risk = output.get("risk")
    sigs = output.get("escalation_signals") or []

    invs.append(Invariant("score_in_range",
                          isinstance(score, (int, float)) and 0 <= score <= 10,
                          f"score={score}"))
    invs.append(Invariant("risk_is_valid_enum", risk in VALID_RISKS, f"risk={risk!r}"))
    invs.append(Invariant("escalation_promotes_critical",
                          (not sigs) or (risk == "CRITICAL"),
                          "escalation_signals non-empty but risk != CRITICAL"))

    passed = all(i.passed for i in invs)
    pass_rate = sum(1 for i in invs if i.passed) / len(invs)
    trust = round(pass_rate * 1.0, 4)
    return VerifyResult(passed=passed, invariants=invs, trust_score=trust,
                        notes="" if passed else "some invariants failed")
