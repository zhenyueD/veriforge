"""text-translate invariants."""
from dataclasses import dataclass, field, asdict


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
    text_in = (input.get("text") or "").strip()
    text_out = (output.get("translated_text") or "").strip()
    invs = [
        Invariant("translated_non_empty", bool(text_out), "translated_text is empty"),
        Invariant("translation_actually_happened",
                  text_out.lower() != text_in.lower(),
                  "output identical to input — translation may have failed"),
    ]
    passed = all(i.passed for i in invs)
    pass_rate = sum(1 for i in invs if i.passed) / len(invs)
    return VerifyResult(passed=passed, invariants=invs, trust_score=round(pass_rate, 4))
