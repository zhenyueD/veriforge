"""
Day 1 acceptance: smoke-test all 6 skills locally via ClaimsForge venv.

Runs each skill in a SUBPROCESS to keep Python's sys.modules clean —
otherwise sys.path-imported handler.py files for different skills clash
on the module name `handler`.

Run:
  cd /Users/duan/code/claimsforge && .venv/bin/python \
    /Users/duan/Desktop/UCWS-VeriForge/scripts/test_all_skills_local.py
"""
from __future__ import annotations
import json, os, subprocess, sys, time, textwrap

PY = sys.executable or "/Users/duan/code/claimsforge/.venv/bin/python"
BASE = "/Users/duan/Desktop/UCWS-VeriForge/skills"
os.environ.setdefault("CLAIMSFORGE_PATH", "/Users/duan/code/claimsforge")


def run_skill(skill_id: str, payload: dict) -> dict | None:
    """Invoke one skill in a clean subprocess. Returns the response dict."""
    code = textwrap.dedent(f"""
        import json, os, sys
        sys.path.insert(0, {BASE!r} + '/' + {skill_id!r})
        sys.path.insert(0, os.environ['CLAIMSFORGE_PATH'] + '/agents')
        from handler import invoke, InvokeRequest
        payload = json.loads({json.dumps(payload)!r})
        req = InvokeRequest(**payload)
        resp = invoke(req)
        out = resp.model_dump() if hasattr(resp, 'model_dump') else dict(resp)
        print('::RESULT::' + json.dumps(out, default=str))
    """)
    t0 = time.time()
    p = subprocess.run([PY, "-c", code], capture_output=True, text=True, timeout=120)
    dt = time.time() - t0
    if p.returncode != 0:
        print(f"  {skill_id:25s} FAIL ({dt:.2f}s)")
        # last 8 lines of stderr usually carry the real cause
        for line in (p.stderr or "").strip().splitlines()[-8:]:
            print("    │", line)
        return None
    # Find the result line
    for line in p.stdout.splitlines():
        if line.startswith("::RESULT::"):
            data = json.loads(line[len("::RESULT::"):])
            # Brief summary line
            summary = {k: v for k, v in data.items() if k in
                       {"label","risk","score","damage_type","severity","verdict","retention_risk"}}
            print(f"  {skill_id:25s} PASS ({dt:.2f}s) {summary}")
            return data
    print(f"  {skill_id:25s} PASS ({dt:.2f}s)  (no ::RESULT:: line)")
    return None


def main():
    print("=== VeriForge Day 1 — all skills live smoke test ===\n")

    intent = run_skill("claims-intent", {
        "user_message": "My mug arrived cracked. Order ORD-1234.",
        "has_image": False,
    })

    emotion = run_skill("claims-emotion", {
        "user_message": "This is the third time. My lawyer will hear about this.",
    })

    emo_for_downstream = (
        {k: v for k, v in emotion.items() if k in
         {"score","risk","label","triggers","escalation_signals","suggested_tone"}}
        if emotion else None
    )

    needs = run_skill("claims-needs", {
        "user_message": "My mug arrived cracked. It was a birthday gift for my sister this Friday.",
        "emotion": emo_for_downstream,
    })

    damage = run_skill("claims-damage-vision", {
        "user_message": "My mug has a 2cm crack along the rim.",
        "image_b64": None,
    })

    comp = None
    if damage:
        damage_for_comp = {k: v for k, v in damage.items() if k in
                           {"damage_type","severity","affected_parts","confidence","reasoning",
                            "evidence_quote","detected_subject","bounding_boxes"}}
        comp = run_skill("claims-compensation", {
            "damage": damage_for_comp,
            "emotion": emo_for_downstream,
            "has_image": False,
            "estimated_value_cents": 5000,
            "user_message": "My mug has a 2cm crack along the rim.",
        })

    offer_in = (comp or {}).get("offer") or {
        "offer_type": "full_refund", "amount_cents": 3000,
        "currency": "CNY", "justification": "Crack visible, replacement preferred.",
        "policy_ids": [], "requires_return": False,
    }
    run_skill("claims-verify", {
        "offer": offer_in,
        "damage_severity": (damage or {}).get("severity", 5),
        "damage_confidence": (damage or {}).get("confidence", 0.5),
        "emotion_score": (emotion or {}).get("score", 5.0),
        "user_message": "My mug has a crack",
    })

    print("\n=== done ===")


if __name__ == "__main__":
    main()
