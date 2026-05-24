"""claims-fraud-image invariants."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict

VALID_VERDICTS = {"clear", "suspicious", "fraud"}


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
    score = output.get("fraud_score")
    verdict = output.get("verdict")
    signals = output.get("signals") or []
    cross = bool(output.get("cross_session", False))
    has_image = bool(input.get("image_b64"))

    invs.append(Invariant("fraud_score_in_range",
                          isinstance(score, (int, float)) and 0.0 <= score <= 1.0,
                          f"fraud_score={score}"))
    invs.append(Invariant("verdict_is_valid_enum", verdict in VALID_VERDICTS, f"verdict={verdict!r}"))
    # A cross-session photo reuse is the high-confidence fraud signal — score must reflect it.
    invs.append(Invariant("cross_session_implies_high",
                          (not cross) or (isinstance(score, (int, float)) and score >= 0.6),
                          f"cross_session but fraud_score={score} < 0.6"))
    if not has_image:
        invs.append(Invariant("no_image_flagged",
                              "no_image_provided" in signals,
                              "no image provided but 'no_image_provided' not in signals"))

    passed = all(i.passed for i in invs)
    pass_rate = sum(1 for i in invs if i.passed) / max(1, len(invs))
    return VerifyResult(passed=passed, invariants=invs, trust_score=round(pass_rate, 4))
