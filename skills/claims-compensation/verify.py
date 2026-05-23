"""claims-compensation invariants."""
from __future__ import annotations
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
    invs: list[Invariant] = []
    offer = output.get("offer")
    reasons = output.get("escalate_reasons") or []

    # I1: amount_cents non-negative when offer present
    if offer:
        amt = offer.get("amount_cents")
        invs.append(Invariant("amount_non_negative",
                              isinstance(amt, int) and amt >= 0,
                              f"amount_cents={amt}"))
        invs.append(Invariant("offer_type_present",
                              bool(offer.get("offer_type")),
                              "offer_type missing"))
    else:
        invs.append(Invariant("must_escalate_when_no_offer",
                              len(reasons) > 0,
                              "offer is None but no escalate_reasons given"))

    # I2: amount should be capped (rough sanity — strict cap is in claims-verify)
    est_value = (input.get("estimated_value_cents") or 5000)
    if offer:
        amt = offer.get("amount_cents", 0)
        # No legitimate single-claim offer should exceed 5x the item value
        invs.append(Invariant("amount_within_5x_item_value",
                              amt <= est_value * 5,
                              f"amount {amt} > 5x estimated value {est_value}"))

    passed = all(i.passed for i in invs)
    pass_rate = sum(1 for i in invs if i.passed) / max(1, len(invs))
    return VerifyResult(passed=passed, invariants=invs, trust_score=round(pass_rate, 4))
