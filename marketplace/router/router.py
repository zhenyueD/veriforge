"""
VeriForge Router — KIMI registry-in-context skill chain planner.

Loads the entire skill registry into KIMI's context window (no RAG, no
embeddings) and asks it to plan a sequence of skill calls for any user
input. The "Best Use of KIMI" technical anchor.

Usage:
    from router import plan_skill_chain
    plan = plan_skill_chain(user_input="My mug is cracked", registry_path="...")
    # → SkillPlan(skill_chain=[...], input_summary="...", reasoning="...")
"""
from __future__ import annotations
import json, os, time, urllib.request
from dataclasses import dataclass, field
from typing import Optional


KIMI_BASE  = os.getenv("KIMI_BASE",  "https://api.moonshot.ai/v1")
KIMI_MODEL = os.getenv("KIMI_MODEL", "moonshot-v1-128k")
API_KEY    = os.getenv("MOONSHOT_API_KEY", "")


ROUTER_SYSTEM = (
    "You are the VeriForge skill router. "
    "You receive a registry of available skills and a user input. "
    "You output a JSON plan describing which skills to call in sequence. "
    "Output ONLY valid JSON. No prose. No markdown fences."
)


ROUTER_PROMPT_TPL = """Below is the full registry of available skills, then a user input.

Rules:
1. Pick the minimum set of skills that fully serve the input.
2. Order them in execution sequence (skills later in the chain may depend on
   outputs of earlier skills — see input fields).
3. If the input doesn't match any skill, return skill_chain=[].
4. For each pick include a brief `reason` (1 short sentence).
5. Output ONLY JSON of the form:
{
  "skill_chain": [{"skill_id": "...", "reason": "..."}],
  "input_summary": "1-sentence paraphrase of what the user wants",
  "reasoning": "1-2 sentence routing rationale"
}

REGISTRY:
%s

USER INPUT:
%s
"""


@dataclass
class SkillCall:
    skill_id: str
    reason: str = ""


@dataclass
class SkillPlan:
    skill_chain: list = field(default_factory=list)
    input_summary: str = ""
    reasoning: str = ""
    latency_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    raw_response: str = ""
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "skill_chain": [{"skill_id": c.skill_id, "reason": c.reason} for c in self.skill_chain],
            "input_summary": self.input_summary,
            "reasoning": self.reasoning,
            "latency_ms": self.latency_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "error": self.error,
        }


def _clean_json(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = s.split("```", 2)[1]
        if s.startswith("json"):
            s = s[4:].lstrip()
        s = s.rsplit("```", 1)[0]
    return s.strip()


def _call_kimi(prompt: str, system: str = ROUTER_SYSTEM, *, timeout: int = 60) -> tuple[str, dict]:
    if not API_KEY:
        raise RuntimeError("MOONSHOT_API_KEY not set")
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
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"], data.get("usage", {})


def registry_path(path: Optional[str] = None) -> str:
    return path or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "registry", "registry.json",
    )


def load_registry(path: Optional[str] = None) -> dict:
    with open(registry_path(path)) as f:
        return json.load(f)


def save_registry(registry: dict, path: Optional[str] = None) -> None:
    import datetime
    registry["updated_at"] = datetime.date.today().isoformat()
    with open(registry_path(path), "w") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)
        f.write("\n")


def upsert_skill(manifest: dict, path: Optional[str] = None) -> tuple[dict, bool]:
    """
    Insert or update a skill in the registry by id. Returns (skill, created).
    Self-registration entrypoint for the veriforge SDK and the "List your skill" form.
    """
    reg = load_registry(path)
    skills = reg.setdefault("skills", [])
    for i, s in enumerate(skills):
        if s["id"] == manifest["id"]:
            skills[i] = {**s, **manifest}   # merge: keep existing fields, override provided
            save_registry(reg, path)
            return skills[i], False
    skills.append(manifest)
    save_registry(reg, path)
    return manifest, True


def plan_skill_chain(user_input: str, registry: Optional[dict] = None) -> SkillPlan:
    if registry is None:
        registry = load_registry()
    # Slim registry down to fields the router needs (description is what matters)
    slim = [
        {
            "id": s["id"],
            "description": s["description"],
            "inputs": s.get("inputs", []),
            "outputs": s.get("outputs", []),
            "tags": s.get("tags", []),
            "price_usdc": s.get("price_usdc", 0),
        }
        for s in registry["skills"]
    ]
    registry_json = json.dumps(slim, ensure_ascii=False, indent=2)
    prompt = ROUTER_PROMPT_TPL % (registry_json, user_input)

    t0 = time.time()
    try:
        content, usage = _call_kimi(prompt)
    except Exception as e:
        return SkillPlan(error=f"KIMI call failed: {e}", latency_ms=int((time.time() - t0) * 1000))

    latency_ms = int((time.time() - t0) * 1000)
    try:
        parsed = json.loads(_clean_json(content))
    except Exception as e:
        return SkillPlan(
            error=f"JSON parse failed: {e}",
            raw_response=content[:500],
            latency_ms=latency_ms,
        )

    chain = [SkillCall(skill_id=c["skill_id"], reason=c.get("reason", "")) for c in parsed.get("skill_chain", [])]
    return SkillPlan(
        skill_chain=chain,
        input_summary=parsed.get("input_summary", ""),
        reasoning=parsed.get("reasoning", ""),
        latency_ms=latency_ms,
        input_tokens=usage.get("prompt_tokens", 0),
        output_tokens=usage.get("completion_tokens", 0),
        raw_response=content,
    )


if __name__ == "__main__":
    import sys
    user_input = sys.argv[1] if len(sys.argv) > 1 else "My mug arrived cracked, order ORD-1234"
    plan = plan_skill_chain(user_input)
    print(json.dumps(plan.to_dict(), indent=2, ensure_ascii=False))
