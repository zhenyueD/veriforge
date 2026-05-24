"""
deep-research skill — wraps MiroMind's MiroFlow research agent as a VeriForge skill.

This is a REAL MiroMind integration: /invoke runs MiroFlow's multi-step research
agent (LLM + serper web search + jina reading + wikipedia) as a subprocess, then
hash-chains MiroFlow's reproducible step trace into a verifiable chain (D2) — tying
MiroMind's reproducible-trace ethos to VeriForge's cryptographic verifiability.

LLM goes through MiroFlow's direct-OpenAI client (GPTOpenAIClient), so it needs only
OPENAI_API_KEY + SERPER_API_KEY + JINA_API_KEY (no OpenRouter).
"""
from __future__ import annotations
import hashlib
import json
import os
import subprocess
import time
import uuid

from fastapi import FastAPI
from pydantic import BaseModel, Field

from veriforge import monetize  # copied into the image next to this file

MIROFLOW_DIR = os.getenv("MIROFLOW_DIR", "/miroflow")
MIROFLOW_PY = os.getenv("MIROFLOW_PY", "/miroflow/.venv/bin/python")
MIROFLOW_CONFIG = os.getenv("MIROFLOW_CONFIG", "agent_llm_gpt4o")
MIROFLOW_TIMEOUT = int(os.getenv("MIROFLOW_TIMEOUT", "300"))

app = FastAPI(title="deep-research skill", version="0.1.0")

# ── VeriForge: monetize this skill in one line ──
monetize(app, skill_id="deep-research", price_usdc=0.25,
         pay_to="0x" + hashlib.sha256(b"veriforge:miromind-research").hexdigest()[:40],
         self_register=False)


class InvokeRequest(BaseModel):
    task: str = Field(max_length=4000, description="The research question.")
    task_file: str = ""


class TraceLink(BaseModel):
    seq: int
    step_name: str
    status: str
    prev: str
    hash: str


class InvokeResponse(BaseModel):
    answer: str
    status: str
    n_steps: int
    trace_chain_tip: str          # tip hash of the verifiable MiroFlow trace
    trace_chain: list[TraceLink]  # per-step SHA-256 chain
    engine: str = "miroflow"
    elapsed_ms: int
    # Audit chain fields
    trace_id: str
    skill_id: str = "deep-research"
    input_hash: str
    output_hash: str


def _hash(o) -> str:
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()


def _chain_trace(steps: list) -> tuple[list[dict], str]:
    """
    D2: SHA-256 hash-chain MiroFlow's reproducible step trace. Each link binds the
    step (name/status/timestamp + a hash of its message) to the previous link, so
    the whole research trajectory is tamper-evident — MiroMind's trace made verifiable.
    """
    prev = "0" * 64
    chain: list[dict] = []
    for i, s in enumerate(steps):
        body = {
            "step_name": s.get("step_name", ""),
            "status": s.get("status", ""),
            "ts": s.get("timestamp", ""),
            "msg_sha256": hashlib.sha256(str(s.get("message", "")).encode()).hexdigest(),
        }
        link = hashlib.sha256((prev + json.dumps(body, sort_keys=True)).encode()).hexdigest()
        chain.append({"seq": i, "step_name": body["step_name"], "status": body["status"],
                      "prev": prev, "hash": link})
        prev = link
    return chain, prev


@app.get("/health")
def health():
    return {"ok": True, "skill_id": "deep-research"}


@app.post("/invoke", response_model=InvokeResponse)
def invoke(req: InvokeRequest):
    t0 = time.monotonic()
    task_id = "vf-" + uuid.uuid4().hex[:12]
    cmd = [MIROFLOW_PY, "main.py", "trace",
           f"--config_file_name={MIROFLOW_CONFIG}", f"--task_id={task_id}", f"--task={req.task}"]
    if req.task_file:
        cmd.append(f"--task_file_name={req.task_file}")

    status = "completed"
    try:
        subprocess.run(cmd, cwd=MIROFLOW_DIR, capture_output=True, text=True, timeout=MIROFLOW_TIMEOUT)
    except subprocess.TimeoutExpired:
        status = "timeout"

    log_path = os.path.join(MIROFLOW_DIR, "logs", f"{task_id}.log")
    answer, steps = "", []
    if os.path.exists(log_path):
        try:
            data = json.load(open(log_path))
            answer = data.get("final_boxed_answer", "") or ""
            steps = data.get("step_logs", []) or []
            status = data.get("status", status)
        except Exception:  # noqa: BLE001
            status = "trace_parse_error"

    chain, tip = _chain_trace(steps)
    out_core = {"answer": answer, "status": status, "n_steps": len(steps), "trace_chain_tip": tip}
    return InvokeResponse(
        **out_core,
        trace_chain=[TraceLink(**c) for c in chain],
        elapsed_ms=int((time.monotonic() - t0) * 1000),
        trace_id=task_id,
        input_hash=_hash({"task": req.task, "task_file": req.task_file}),
        output_hash=_hash(out_core),
    )
