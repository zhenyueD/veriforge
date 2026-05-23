"""
claims-intent verify() — invariant checks against the agent's output.

Used by the marketplace's /verify/:trace_id endpoint to give judges an
independent check that this skill's output satisfies the contract.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict

VALID_LABELS = {
    "claim_with_image", "claim_text_only", "general_inquiry",
    "needs_clarification", "followup_on_prior_claim",
}


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

    def to_dict(self) -> dict:
        return {**asdict(self), "invariants": [asdict(i) for i in self.invariants]}


def verify(input: dict, output: dict) -> VerifyResult:
    invs: list[Invariant] = []

    # I1: label is a valid enum value
    label = output.get("label")
    invs.append(Invariant(
        "label_is_valid_enum",
        label in VALID_LABELS,
        f"label={label!r}",
    ))

    # I2: confidence within [0, 1]
    conf = output.get("confidence")
    invs.append(Invariant(
        "confidence_in_range",
        isinstance(conf, (int, float)) and 0.0 <= conf <= 1.0,
        f"confidence={conf}",
    ))

    # I3: needs_clarification ⇒ clarification_question is non-null/non-empty
    if label == "needs_clarification":
        q = output.get("clarification_question")
        invs.append(Invariant(
            "clarification_question_present",
            bool(q),
            "clarification_question must be a non-empty string when label=needs_clarification",
        ))

    # I4: claim_with_image but has_image=False should NOT occur (handler should downgrade)
    if label == "claim_with_image" and not input.get("has_image", False):
        invs.append(Invariant(
            "image_label_matches_attachment",
            False,
            "label=claim_with_image but has_image=False — should have been downgraded to claim_text_only",
        ))
    else:
        invs.append(Invariant(
            "image_label_matches_attachment",
            True,
        ))

    passed = all(i.passed for i in invs)
    # Trust score: 1.0 if all pass, scaled by confidence and invariant pass rate
    pass_rate = sum(1 for i in invs if i.passed) / len(invs)
    trust = pass_rate * (conf if isinstance(conf, (int, float)) else 0.0)
    return VerifyResult(
        passed=passed,
        invariants=invs,
        trust_score=round(trust, 4),
        notes="" if passed else f"{sum(1 for i in invs if not i.passed)} invariant(s) failed",
    )
