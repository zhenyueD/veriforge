"""
Golden-set routing accuracy for the KIMI router → Langfuse scores.

Calls plan_skill_chain() in-process on a labelled set and checks whether KIMI
picked (at least) the expected skills. Each case is its own trace with a
BOOLEAN `routing_accuracy` score, so the Langfuse dashboard shows the accuracy
number to quote on Demo Day. Prints local accuracy regardless of whether
Langfuse is configured.

Only the KIMI router runs here (no skill execution) — so it needs MOONSHOT_API_KEY
but NOT Gemini, and is cheap to run.

Run:
  set -a && source .env && set +a
  python scripts/langfuse_eval.py
  # to also push scores: export LANGFUSE_PUBLIC_KEY/SECRET_KEY/HOST first
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "marketplace", "router"))

import obs  # noqa: E402
from router import plan_skill_chain  # noqa: E402

# Each case: input → skills that MUST appear in the planned chain (subset check).
GOLDEN = [
    {"input": "Translate 'good morning everyone' into French.",
     "expected": ["text-translate"]},
    {"input": "Summarize this for me: the quarterly report covers revenue, churn, and hiring across three regions.",
     "expected": ["text-summarize"]},
    {"input": "How positive is this review: 'Absolutely love it, best purchase this year!'",
     "expected": ["sentiment-analyze"]},
    {"input": "My ceramic mug arrived cracked along the rim. Order ORD-1234.",
     "expected": ["claims-intent"]},
    {"input": "This is the third time my order is broken and I'm absolutely furious. ORD-9999.",
     "expected": ["claims-intent", "claims-emotion"]},
    {"input": "What is your return policy for opened items?",
     "expected": ["claims-intent"]},
]


@obs.observe(name="eval-case")
def run_case(case: dict) -> bool:
    plan = plan_skill_chain(case["input"])
    got = [c.skill_id for c in plan.skill_chain]
    ok = set(case["expected"]).issubset(set(got))
    obs.update_trace(input={"input": case["input"]},
                     metadata={"expected": case["expected"], "got": got},
                     tags=["eval", "routing"])
    obs.score("routing_accuracy", 1 if ok else 0, data_type="BOOLEAN")
    mark = "OK  " if ok else "MISS"
    print(f"  [{mark}] expected⊆got? {case['expected']} ⊆ {got}")
    return ok


def main() -> int:
    if not os.getenv("MOONSHOT_API_KEY"):
        print("MOONSHOT_API_KEY not set — source .env first.")
        return 2
    print(f"Langfuse enabled: {obs.ENABLED}")
    print(f"Running {len(GOLDEN)} golden routing cases through KIMI...\n")
    results = [run_case(c) for c in GOLDEN]
    obs.flush()
    acc = sum(results) / len(results)
    print(f"\nrouting_accuracy = {acc:.0%}  ({sum(results)}/{len(results)})")
    if obs.ENABLED:
        print("Scores pushed to Langfuse — open the dashboard to see the trend.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
