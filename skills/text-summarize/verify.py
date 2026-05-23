"""text-summarize invariants."""
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
    bullets = output.get("bullets") or []
    tldr = output.get("tldr") or ""
    max_b = input.get("max_bullets", 5)
    invs = [
        Invariant("bullets_non_empty", len(bullets) > 0, f"got {len(bullets)} bullets"),
        Invariant("bullets_within_limit", len(bullets) <= max_b, f"{len(bullets)} > {max_b}"),
        Invariant("tldr_non_empty", bool(tldr.strip()), "tldr is empty"),
    ]
    passed = all(i.passed for i in invs)
    pass_rate = sum(1 for i in invs if i.passed) / len(invs)
    return VerifyResult(passed=passed, invariants=invs, trust_score=round(pass_rate, 4))
