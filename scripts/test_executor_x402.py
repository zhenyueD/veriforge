"""
Tests for A6/A7: executor reads the real x402 settlement from a skill and records it.

Uses a tiny in-process HTTP server that mimics a monetized skill's x402 gate
(402 without X-Payment; 200 + X-Payment-Settled with payment). No Gemini/API needed.

Run: /Users/duan/code/claimsforge/.venv/bin/python scripts/test_executor_x402.py
"""
from __future__ import annotations

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

os.environ["VERIFORGE_TELEMETRY"] = "0"  # don't call audit/activity in tests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "marketplace", "router"))

import executor as E  # noqa: E402

SPLIT = {
    "mode": "mock", "txid": "0xmockdeadbeef",
    "gross": "10000", "creator_amount": "9800", "platform_fee": "200",
    "fee_bps": 200, "pay_to": "0xCreator", "platform_addr": "0xTreasury",
}


class _MockSkill(BaseHTTPRequestHandler):
    def log_message(self, *a):  # silence
        pass

    def do_POST(self):
        # Always drain the request body first, or the client socket gets reset.
        length = int(self.headers.get("Content-Length", 0))
        if length:
            self.rfile.read(length)
        if self.path != "/invoke":
            self.send_response(404); self.end_headers(); return
        if not self.headers.get("X-Payment"):
            self.send_response(402)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "payment_required"}).encode())
            return
        body = json.dumps({"result": "ok", "trace_id": "t-123"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Payment-Settled", json.dumps(SPLIT))
        self.end_headers()
        self.wfile.write(body)


def _serve():
    srv = HTTPServer(("127.0.0.1", 0), _MockSkill)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def test_exec_http_captures_settlement():
    srv, base = _serve()
    try:
        step = E._exec_http("mock", {"user_message": "hi"}, endpoint=base, x_payment="mock:tok")
        assert step.ok, step.error
        assert step.settlement["creator_amount"] == "9800"
        assert step.settlement["platform_fee"] == "200"
        assert step.settlement["pay_to"] == "0xCreator"
    finally:
        srv.shutdown()


def test_exec_http_402_without_payment_is_handled():
    srv, base = _serve()
    try:
        step = E._exec_http("mock", {"user_message": "hi"}, endpoint=base, x_payment=None)
        assert step.ok is False
        assert "402" in step.error
    finally:
        srv.shutdown()


def test_execute_plan_records_settlement_per_step():
    srv, base = _serve()
    try:
        registry = {"skills": [{"id": "mock", "endpoint": base}]}
        os.environ["ENDPOINT_HOST"] = "localhost-raw"  # we override endpoints below
        # execute_plan resolves endpoints by replacing HOST; our endpoint has no HOST,
        # so it stays as-is — exactly what we want.
        result = E.execute_plan([{"skill_id": "mock"}], "my mug cracked",
                                registry=registry, mode="http")
        assert len(result.steps) == 1
        s = result.steps[0]
        assert s.ok, s.error
        assert s.settlement["creator_amount"] == "9800"
        assert s.settlement["platform_fee"] == "200"
    finally:
        srv.shutdown()


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t(); print(f"PASS  {t.__name__}"); passed += 1
        except AssertionError as e:
            print(f"FAIL  {t.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            import traceback; traceback.print_exc()
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(tests)} passed")
    sys.exit(0 if passed == len(tests) else 1)
