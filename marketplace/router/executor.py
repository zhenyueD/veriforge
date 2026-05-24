"""
VeriForge Executor — runs a SkillPlan by calling each skill in sequence.

Two modes:
  - in_process (default for dev): subprocess per skill, sys.path import.
    No need to start uvicorn for every skill. Slow startup, isolates skills.
  - http: POST to each skill's endpoint (registry["endpoint"]/invoke).
    Used in production / Day 3+ when activity stream is wired up.

For Day 3+: emits activity events + appends audit chain entries while running.
Both are best-effort — failures are logged but don't block execution.

The executor handles input chaining: skills later in the chain may need
outputs from earlier skills. We use a simple rule-based mapping (per
skill_id) — Day 4 can replace this with a generic prompt-based remapper.
"""
from __future__ import annotations
import hashlib, json, os, subprocess, sys, time, textwrap, urllib.request, uuid
from dataclasses import dataclass, field
from typing import Optional

import obs  # optional Langfuse tracing; no-op when not configured

PY  = sys.executable or "/Users/duan/code/claimsforge/.venv/bin/python"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKILLS_DIR = os.path.join(ROOT, "skills")

# Day 3 integration endpoints (optional; degrade gracefully if down)
AUDIT_URL    = os.getenv("AUDIT_URL",    "http://localhost:8001")
ACTIVITY_URL = os.getenv("ACTIVITY_URL", "http://localhost:8002")
SEND_TELEMETRY = os.getenv("VERIFORGE_TELEMETRY", "1") != "0"
X402_MODE = os.getenv("VERIFORGE_X402_MODE", "mock")


def _post_json(url: str, body: dict, *, timeout: int = 5) -> Optional[dict]:
    try:
        req = urllib.request.Request(
            url, data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


def emit_event(session_id: str, kind: str, **kw) -> None:
    if not SEND_TELEMETRY:
        return
    _post_json(f"{ACTIVITY_URL}/emit", {
        "session_id": session_id,
        "kind": kind,
        "skill_id": kw.get("skill_id"),
        "trace_id": kw.get("trace_id"),
        "ts": kw.get("ts"),
        "data": kw.get("data", {}),
    })


def append_audit(*, session_id: str, seq: int, skill_id: str, trace_id: str,
                  input_hash: str, output_hash: str, verify_passed: Optional[bool],
                  elapsed_ms: int, extra: Optional[dict] = None) -> Optional[dict]:
    if not SEND_TELEMETRY:
        return None
    return _post_json(f"{AUDIT_URL}/append", {
        "session_id": session_id, "seq": seq, "skill_id": skill_id,
        "trace_id": trace_id, "input_hash": input_hash, "output_hash": output_hash,
        "verify_passed": verify_passed, "elapsed_ms": elapsed_ms, "extra": extra or {},
    })


@dataclass
class StepResult:
    skill_id: str
    ok: bool
    output: dict = field(default_factory=dict)
    error: str = ""
    elapsed_ms: int = 0
    settlement: dict = field(default_factory=dict)  # real x402 split from X-Payment-Settled


@dataclass
class ExecResult:
    steps: list = field(default_factory=list)
    aggregated: dict = field(default_factory=dict)
    total_ms: int = 0

    def to_dict(self):
        return {
            "steps": [
                {
                    "skill_id": s.skill_id, "ok": s.ok,
                    "output": s.output, "error": s.error, "elapsed_ms": s.elapsed_ms,
                }
                for s in self.steps
            ],
            "aggregated": self.aggregated,
            "total_ms": self.total_ms,
        }


# ─── Rule-based input wiring ──────────────────────────────
def build_input(skill_id: str, user_input: str, prior: dict, image_b64: Optional[str] = None) -> dict:
    """
    Given the skill_id and outputs of prior steps, construct the right payload
    for the next skill's POST /invoke. Keep these rules explicit — Day 4 can
    swap in a generalized remapper.
    """
    if skill_id == "claims-intent":
        return {"user_message": user_input, "has_image": bool(image_b64)}

    if skill_id == "claims-emotion":
        return {"user_message": user_input}

    if skill_id == "claims-needs":
        return {
            "user_message": user_input,
            "history": [],
            "emotion": _strip_audit(prior.get("claims-emotion", {})),
        }

    if skill_id == "claims-damage-vision":
        return {
            "user_message": user_input,
            "image_b64": image_b64,
        }

    if skill_id == "claims-compensation":
        return {
            "damage": _strip_audit(prior.get("claims-damage-vision", {})),
            "emotion": _strip_audit(prior.get("claims-emotion", {})),
            "needs": _strip_audit(prior.get("claims-needs", {})),
            "has_image": bool(image_b64),
            "estimated_value_cents": 5000,
            "user_message": user_input,
        }

    if skill_id == "claims-verify":
        comp = prior.get("claims-compensation", {})
        damage = prior.get("claims-damage-vision", {})
        emotion = prior.get("claims-emotion", {})
        offer = comp.get("offer") or {
            "offer_type": "full_refund", "amount_cents": 0, "currency": "CNY",
            "justification": "fallback", "policy_ids": [], "requires_return": False,
        }
        return {
            "offer": offer,
            "damage_severity": damage.get("severity", 5),
            "damage_confidence": damage.get("confidence", 0.5),
            "emotion_score": emotion.get("score", 5.0),
            "user_message": user_input,
        }

    # Horizontal skills
    if skill_id == "text-summarize":
        return {"text": user_input}
    if skill_id == "text-translate":
        return {"text": user_input, "target_language": "en"}
    if skill_id == "sentiment-analyze":
        return {"text": user_input}

    # Default: pass user_input only
    return {"user_message": user_input}


# Fields that are audit-only — strip before feeding to downstream skill
_AUDIT_FIELDS = {"trace_id", "skill_id", "input_hash", "output_hash", "elapsed_ms"}


def _strip_audit(d: dict) -> dict:
    return {k: v for k, v in d.items() if k not in _AUDIT_FIELDS} if d else {}


# ─── Execution backends ───────────────────────────────────
def _exec_in_process(skill_id: str, payload: dict, timeout: int = 60) -> StepResult:
    """Invoke skill via subprocess + sys.path. No uvicorn needed."""
    code = textwrap.dedent(f"""
        import json, os, sys
        sys.path.insert(0, {SKILLS_DIR!r} + '/' + {skill_id!r})
        sys.path.insert(0, os.environ.get('CLAIMSFORGE_PATH', '/Users/duan/code/claimsforge') + '/agents')
        from handler import invoke, InvokeRequest
        req = InvokeRequest(**json.loads({json.dumps(payload)!r}))
        resp = invoke(req)
        out = resp.model_dump() if hasattr(resp, 'model_dump') else dict(resp)
        print('::OUT::' + json.dumps(out, default=str))
    """)
    t0 = time.time()
    p = subprocess.run([PY, "-c", code], capture_output=True, text=True, timeout=timeout)
    elapsed = int((time.time() - t0) * 1000)
    if p.returncode != 0:
        last_err = "\n".join((p.stderr or "").strip().splitlines()[-5:])
        return StepResult(skill_id=skill_id, ok=False, error=last_err, elapsed_ms=elapsed)
    for line in p.stdout.splitlines():
        if line.startswith("::OUT::"):
            out = json.loads(line[len("::OUT::"):])
            return StepResult(skill_id=skill_id, ok=True, output=out, elapsed_ms=elapsed)
    return StepResult(skill_id=skill_id, ok=False, error="no ::OUT:: line", elapsed_ms=elapsed)


def _exec_http(skill_id: str, payload: dict, endpoint: str, timeout: int = 60,
               x_payment: Optional[str] = None) -> StepResult:
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if x_payment:
        headers["X-Payment"] = x_payment
    req = urllib.request.Request(
        f"{endpoint}/invoke", data=body, headers=headers, method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            out = json.loads(r.read().decode("utf-8"))
            settled_hdr = r.headers.get("X-Payment-Settled", "")
        elapsed = int((time.time() - t0) * 1000)
        settlement = {}
        if settled_hdr:
            try:
                settlement = json.loads(settled_hdr)
            except json.JSONDecodeError:
                settlement = {}
        return StepResult(skill_id=skill_id, ok=True, output=out,
                          elapsed_ms=elapsed, settlement=settlement)
    except urllib.error.HTTPError as e:
        elapsed = int((time.time() - t0) * 1000)
        body_err = e.read().decode("utf-8", errors="replace")[:300] if hasattr(e, "read") else ""
        return StepResult(skill_id=skill_id, ok=False,
                          error=f"HTTP {e.code}: {body_err}", elapsed_ms=elapsed)
    except Exception as e:
        elapsed = int((time.time() - t0) * 1000)
        return StepResult(skill_id=skill_id, ok=False, error=str(e), elapsed_ms=elapsed)


def _mock_x_payment(skill_id: str) -> str:
    """Generate an opaque mock payment token. Real mode would be an EIP-3009 sig."""
    return "mock:" + hashlib.sha256(f"{skill_id}:{uuid.uuid4()}".encode()).hexdigest()


# ─── Public entry point ───────────────────────────────────
def execute_plan(
    plan: dict | list,
    user_input: str,
    registry: Optional[dict] = None,
    *,
    mode: str = "in_process",
    image_b64: Optional[str] = None,
    session_id: Optional[str] = None,
) -> ExecResult:
    """
    `plan` is either a SkillPlan.to_dict() result OR a list of {skill_id}.
    `mode` ∈ {"in_process", "http"}.
    """
    chain = plan.get("skill_chain") if isinstance(plan, dict) else plan
    endpoints: dict[str, str] = {}
    if mode == "http":
        if registry is None:
            from router import load_registry
            registry = load_registry()
        # registry endpoints use placeholder HOST → resolve via env:
        #   ENDPOINT_HOST=docker → use skill_id as docker service hostname
        #   ENDPOINT_HOST=localhost → port-forwarded (host dev)
        host_mode = os.getenv("ENDPOINT_HOST", "docker")
        for s in registry["skills"]:
            tpl = s["endpoint"]
            host = s["id"] if host_mode == "docker" else "localhost"
            endpoints[s["id"]] = tpl.replace("HOST", host)

    session_id = session_id or uuid.uuid4().hex[:12]
    emit_event(session_id, "session_started", data={"user_input": user_input[:200], "n_skills": len(chain)})
    emit_event(session_id, "route_planned", data={
        "skill_chain": [c["skill_id"] if isinstance(c, dict) else c.skill_id for c in chain],
        "reasoning": (plan.get("reasoning") if isinstance(plan, dict) else "")[:200],
    })

    prior: dict[str, dict] = {}
    steps: list[StepResult] = []
    t0 = time.time()
    seq = 0

    for call in chain:
        sid = call["skill_id"] if isinstance(call, dict) else call.skill_id
        payload = build_input(sid, user_input, prior, image_b64=image_b64)

        emit_event(session_id, "skill_started", skill_id=sid, data={"seq": seq})

        # x402 payment dance: send X-Payment so the skill's gate lets us in, then
        # read the real settlement (split) the skill returns in X-Payment-Settled.
        # Each skill call is its own Langfuse span (latency per skill).
        with obs.span(name=f"skill:{sid}"):
            if mode == "http":
                x_pay = _mock_x_payment(sid)
                step = _exec_http(sid, payload, endpoint=endpoints.get(sid, ""), x_payment=x_pay)
            else:
                step = _exec_in_process(sid, payload)

        steps.append(step)

        if step.ok:
            prior[sid] = step.output
            trace_id = step.output.get("trace_id", uuid.uuid4().hex)
            input_hash  = step.output.get("input_hash")  or hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
            output_hash = step.output.get("output_hash") or hashlib.sha256(json.dumps(step.output, sort_keys=True, default=str).encode()).hexdigest()

            # Emit the real payment settlement (creator cut + platform fee).
            if step.settlement:
                emit_event(session_id, "skill_payment_settled", skill_id=sid, trace_id=trace_id,
                           data={
                               "mode": step.settlement.get("mode", X402_MODE),
                               "creator_amount": step.settlement.get("creator_amount"),
                               "platform_fee": step.settlement.get("platform_fee"),
                               "pay_to": step.settlement.get("pay_to"),
                               "txid": (step.settlement.get("txid") or "")[:18],
                           })

            emit_event(session_id, "skill_completed", skill_id=sid, trace_id=trace_id,
                       data={"elapsed_ms": step.elapsed_ms})
            audit_res = append_audit(
                session_id=session_id, seq=seq, skill_id=sid, trace_id=trace_id,
                input_hash=input_hash, output_hash=output_hash,
                verify_passed=None, elapsed_ms=step.elapsed_ms,
                extra={"settlement": step.settlement} if step.settlement else None,
            )
            if audit_res:
                emit_event(session_id, "audit_appended", skill_id=sid, trace_id=trace_id,
                           data={"chain_hash": audit_res.get("chain_hash", "")[:16]})
        else:
            emit_event(session_id, "skill_failed", skill_id=sid,
                       data={"error": step.error[:200]})
        seq += 1

    total_ms = int((time.time() - t0) * 1000)
    emit_event(session_id, "session_completed", data={"total_ms": total_ms, "n_ok": sum(1 for s in steps if s.ok)})

    return ExecResult(
        steps=steps,
        aggregated=prior,
        total_ms=total_ms,
    )


if __name__ == "__main__":
    from router import plan_skill_chain
    user_input = sys.argv[1] if len(sys.argv) > 1 else "My mug arrived cracked, order ORD-1234"
    print(f"[1/2] Planning skill chain for: {user_input!r}")
    plan = plan_skill_chain(user_input)
    print(json.dumps(plan.to_dict(), indent=2, ensure_ascii=False))
    mode = os.getenv("EXEC_MODE", "in_process")
    print(f"\n[2/2] Executing {len(plan.skill_chain)} skills via mode={mode}...\n")
    registry = None
    if mode == "http":
        from router import load_registry
        registry = load_registry()
    result = execute_plan(plan.to_dict(), user_input, registry=registry, mode=mode)
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False, default=str)[:3000])
