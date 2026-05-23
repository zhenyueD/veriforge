"""sentiment-analyze invariants."""
from dataclasses import dataclass, field, asdict

VALID = {"positive", "neutral", "negative"}


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
    s = output.get("sentiment")
    i = output.get("intensity")
    invs = [
        Invariant("sentiment_valid", s in VALID, f"sentiment={s!r}"),
        Invariant("intensity_in_range",
                  isinstance(i, (int, float)) and 0 <= i <= 1, f"intensity={i}"),
    ]
    passed = all(inv.passed for inv in invs)
    pass_rate = sum(1 for inv in invs if inv.passed) / len(invs)
    return VerifyResult(passed=passed, invariants=invs, trust_score=round(pass_rate, 4))
