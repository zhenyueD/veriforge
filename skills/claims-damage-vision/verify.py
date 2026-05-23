"""claims-damage-vision invariants."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict

VALID_DAMAGE = {"crack", "scratch", "tear", "dent", "stain", "missing_part",
                "water_damage", "defect", "unclear"}


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
    sev = output.get("severity")
    conf = output.get("confidence")
    dt = output.get("damage_type")
    has_image = bool(input.get("image_b64"))

    invs.append(Invariant("damage_type_is_valid", dt in VALID_DAMAGE, f"dt={dt!r}"))
    invs.append(Invariant("severity_in_range",
                          isinstance(sev, int) and 0 <= sev <= 10, f"sev={sev}"))
    invs.append(Invariant("confidence_in_range",
                          isinstance(conf, (int, float)) and 0 <= conf <= 1, f"conf={conf}"))
    invs.append(Invariant("no_image_caps_confidence",
                          has_image or (isinstance(conf, (int, float)) and conf <= 0.55),
                          f"no image but conf={conf} > 0.55 — overconfident"))

    passed = all(i.passed for i in invs)
    pass_rate = sum(1 for i in invs if i.passed) / len(invs)
    trust = round(pass_rate * (conf if isinstance(conf, (int, float)) else 0.0), 4)
    return VerifyResult(passed=passed, invariants=invs, trust_score=trust)
