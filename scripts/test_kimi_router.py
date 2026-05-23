"""
KIMI long-context router smoke test.

Goal: verify that KIMI k2.6 can hold a registry-sized prompt (~50 skills,
~30k chars / ~10k tokens) and produce correct skill-chain routing for
arbitrary user input.

Pass criteria:
  - latency < 10s (else fall back to HyDE RAG, per PROJECT.md §10)
  - cost < $0.10 per route call (else cache + batch)
  - routing accuracy 3/3 on hand-crafted inputs

Uses stdlib urllib (no openai SDK dependency — Python 3.14 stdlib is enough
and this machine's pip is broken on pyexpat).

Run:
  # Official KIMI:
  export MOONSHOT_API_KEY=...     # https://platform.moonshot.ai
  python3 scripts/test_kimi_router.py

  # SiliconFlow (3rd party hosting of KIMI):
  export MOONSHOT_API_KEY=sk-...
  export KIMI_BASE=https://api.siliconflow.cn/v1
  export KIMI_MODEL=Pro/moonshotai/Kimi-K2.6
  python3 scripts/test_kimi_router.py
"""
from __future__ import annotations
import json, os, sys, time, urllib.request, urllib.error
from dataclasses import dataclass

KIMI_BASE  = os.getenv("KIMI_BASE",  "https://api.moonshot.ai/v1")
KIMI_MODEL = os.getenv("KIMI_MODEL", "kimi-k2-0905-preview")
API_KEY    = os.getenv("MOONSHOT_API_KEY")

# ---- Fake registry (~50 skills) ----
def build_fake_registry(n_skills: int = 50) -> list[dict]:
    base = [
        # 7 ClaimsForge skills (dissected from /Users/duan/code/claimsforge/agents/)
        {"id": "claims-intent", "tags": ["vertical:ecom-aftersales", "nlp"],
         "description": "Classify customer intent on e-commerce support: claim_with_image / claim_text_only / general_inquiry / needs_clarification / followup_on_prior_claim. Extracts order_id. Multi-turn aware."},
        {"id": "claims-emotion", "tags": ["vertical:ecom-aftersales", "sentiment"],
         "description": "Grade customer affect on 0-10 scale with risk level (NORMAL/MEDIUM/HIGH/CRITICAL). Detects legal/regulator/media escalation signals. Bilingual EN+ZH."},
        {"id": "claims-needs", "tags": ["vertical:ecom-aftersales", "advisory"],
         "description": "Surface surface/latent/emotional needs, retention risk, upsell signals, suggested offer bias. Elevates system from policy executor to advisor."},
        {"id": "claims-damage-vision", "tags": ["vertical:ecom-aftersales", "vision", "gemini"],
         "description": "Assess damage from product photo using Gemini Vision: damage_type, severity 0-10, affected_parts, bounding_boxes, detected_subject. 96.7% accuracy on labeled eval set."},
        {"id": "claims-compensation", "tags": ["vertical:ecom-aftersales", "rag", "finance"],
         "description": "Pick matching policy from RAG over policy DSL + merchant wisdom KB + live precedent. Propose typed offer (refund/replacement/store-credit) with empathetic justification."},
        {"id": "claims-verify", "tags": ["vertical:ecom-aftersales", "verification"],
         "description": "Hard-cap amount to policy max, escalate on low evidence, request tone revision if justification too cold. Max 1 revision loop."},
        {"id": "claims-fraud", "tags": ["vertical:ecom-aftersales", "fraud"],
         "description": "Score fraud likelihood from text+image inconsistencies, customer history, and behavioral signals."},
        # 3 horizontal demo skills
        {"id": "text-summarize", "tags": ["horizontal", "nlp"],
         "description": "Summarize long text into key bullet points with configurable length."},
        {"id": "text-translate", "tags": ["horizontal", "nlp"],
         "description": "Translate text between languages with auto language detection."},
        {"id": "sentiment-analyze", "tags": ["horizontal", "nlp"],
         "description": "Analyze sentiment (positive/neutral/negative) with emotion breakdown."},
    ]
    synth_templates = [
        ("legal", "contract clause extraction and risk flagging"),
        ("medical", "symptom triage with red flag detection"),
        ("finance", "transaction categorization and anomaly scoring"),
        ("ecom", "product description generation from image and keywords"),
        ("hr", "resume parsing and skill extraction"),
    ]
    for i in range(n_skills - len(base)):
        domain, blurb = synth_templates[i % len(synth_templates)]
        base.append({
            "id": f"{domain}-skill-{i:03d}",
            "tags": [f"vertical:{domain}", "nlp"],
            "description": f"{blurb} (synthetic skill #{i} for context size test).",
        })
    return base


ROUTER_PROMPT = """You are the VeriForge skill router. You are given the full registry of available skills, and a user input. Your job is to output a JSON skill_call plan.

Rules:
1. Pick the minimum set of skills that fully serve the input.
2. Order them in execution sequence.
3. If the input does not match any skill, return an empty list.
4. Output ONLY valid JSON, no prose, no markdown fences.

Output format:
{"skill_chain": [{"skill_id": "...", "reason": "..."}], "input_summary": "..."}

REGISTRY:
%s

USER INPUT:
%s
"""


@dataclass
class TestCase:
    name: str
    input: str
    must_include: list
    must_exclude: list


CASES = [
    TestCase("ecom damage claim",
             "My mug arrived with a crack along the rim, can't use it. Order ORD-8821.",
             ["claims-intent", "claims-damage-vision", "claims-compensation"],
             ["text-translate"]),
    TestCase("horizontal summarize",
             "Summarize this 50-page contract into 10 bullet points.",
             ["text-summarize"],
             ["claims-intent", "claims-damage-vision", "claims-compensation"]),
    TestCase("angry escalation",
             "This is the third time I have written. My lawyer will hear about this.",
             ["claims-intent", "claims-emotion"],
             ["text-translate"]),
]


def call_kimi(prompt: str, system: str = "You output only valid JSON.") -> tuple[str, dict]:
    """Returns (content, usage_dict)."""
    body = {
        "model": KIMI_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
    }
    req = urllib.request.Request(
        f"{KIMI_BASE}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode("utf-8"))
    content = data["choices"][0]["message"]["content"]
    usage   = data.get("usage", {})
    return content, usage


def clean_json(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = s.split("```", 2)[1]
        if s.startswith("json"):
            s = s[4:].lstrip()
        s = s.rsplit("```", 1)[0]
    return s.strip()


def main() -> int:
    if not API_KEY:
        print("FAIL: MOONSHOT_API_KEY not set.")
        return 2

    print(f"Endpoint: {KIMI_BASE}")
    print(f"Model:    {KIMI_MODEL}")
    print()

    registry = build_fake_registry(50)
    registry_json = json.dumps(registry, ensure_ascii=False, indent=2)
    print(f"Registry: {len(registry)} skills, {len(registry_json)} chars (~{len(registry_json)//4} tokens est)")
    print()

    failures = 0
    timings = []

    for case in CASES:
        prompt = ROUTER_PROMPT % (registry_json, case.input)
        t0 = time.time()
        try:
            content, usage = call_kimi(prompt)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")[:400]
            print(f"  [{case.name}] HTTP {e.code}: {err_body}")
            failures += 1
            continue
        except Exception as e:
            print(f"  [{case.name}] error: {e}")
            failures += 1
            continue
        dt = time.time() - t0
        timings.append(dt)

        try:
            plan = json.loads(clean_json(content))
            chain_ids = [c.get("skill_id") for c in plan.get("skill_chain", [])]
        except Exception as e:
            print(f"  [{case.name}] JSON parse failed: {e}")
            print(f"     raw: {content[:300]}")
            failures += 1
            continue

        missing = [s for s in case.must_include if s not in chain_ids]
        leaked  = [s for s in case.must_exclude if s in chain_ids]
        status  = "PASS" if not missing and not leaked else "FAIL"
        if status == "FAIL":
            failures += 1

        in_tok  = usage.get("prompt_tokens", "?")
        out_tok = usage.get("completion_tokens", "?")
        print(f"  [{case.name}] {status} | {dt:.2f}s | in={in_tok} out={out_tok}")
        print(f"     chain: {chain_ids}")
        if missing: print(f"     MISSING: {missing}")
        if leaked:  print(f"     LEAKED:  {leaked}")
        print()

    print("---")
    if timings:
        print(f"Latency: avg {sum(timings)/len(timings):.2f}s · max {max(timings):.2f}s")
        if max(timings) > 10:
            print("WARN: max latency > 10s → consider HyDE RAG fallback (PROJECT.md §10)")
    print(f"Result: {len(CASES) - failures}/{len(CASES)} passed")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
