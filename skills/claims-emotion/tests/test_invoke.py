"""claims-emotion behavior tests."""
from __future__ import annotations
import os, sys

CLAIMSFORGE = os.getenv("CLAIMSFORGE_PATH", "/Users/duan/code/claimsforge")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(CLAIMSFORGE, "agents"))

from handler import invoke, InvokeRequest


def test_calm_message():
    r = invoke(InvokeRequest(user_message="Hi, when will my order arrive?"))
    assert r.risk in ("LOW", "MEDIUM")
    assert 0 <= r.score <= 10


def test_legal_threat_escalates():
    r = invoke(InvokeRequest(
        user_message="This is the third time. My lawyer will contact you. I'm reporting to the regulator."
    ))
    # Must escalate to CRITICAL when escalation signals fire
    assert r.risk == "CRITICAL", f"expected CRITICAL, got {r.risk} (signals={r.escalation_signals})"
    assert len(r.escalation_signals) > 0


if __name__ == "__main__":
    test_calm_message(); print("calm PASS")
    test_legal_threat_escalates(); print("legal threat PASS")
