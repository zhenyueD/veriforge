"""
Optional Langfuse observability — best-effort, never blocks the pipeline.

Same contract as the audit + activity emitters: if Langfuse isn't installed or
LANGFUSE_PUBLIC_KEY isn't set, every call here is a no-op and the stack runs
exactly as before. So `docker compose up` always works; the dashboard is opt-in.

Enable it:
  1. docker compose -f docker-compose.langfuse.yml up -d   # self-host (or use cloud)
  2. add `langfuse` to the router's pip install in docker-compose.yml
  3. set LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_HOST on the router

Then traces show: one span per pipeline run, the KIMI route call as a generation
(model + tokens + cost), and a child span per skill invocation with latency.
"""
from __future__ import annotations

import contextlib
import os

ENABLED = False
_client = None

if os.getenv("LANGFUSE_PUBLIC_KEY"):
    try:
        from langfuse import get_client, observe as _lf_observe  # type: ignore
        _client = get_client()
        ENABLED = True
    except Exception:  # noqa: BLE001 — any import/init failure → stay disabled
        ENABLED = False


if ENABLED:
    observe = _lf_observe  # re-export the real decorator

    def update_generation(**kw) -> None:
        try:
            _client.update_current_generation(**kw)
        except Exception:  # noqa: BLE001
            pass

    def update_trace(**kw) -> None:
        try:
            _client.update_current_trace(**kw)
        except Exception:  # noqa: BLE001
            pass

    def score(name: str, value, data_type: str = "NUMERIC", **kw) -> None:
        try:
            _client.create_score(trace_id=_client.get_current_trace_id(),
                                  name=name, value=value, data_type=data_type, **kw)
        except Exception:  # noqa: BLE001
            pass

    def current_trace_id():
        try:
            return _client.get_current_trace_id()
        except Exception:  # noqa: BLE001
            return None

    def flush() -> None:
        try:
            _client.flush()
        except Exception:  # noqa: BLE001
            pass

    @contextlib.contextmanager
    def span(name: str, **kw):
        try:
            with _client.start_as_current_span(name=name, **kw) as s:
                yield s
        except Exception:  # noqa: BLE001
            yield None

else:
    def observe(*args, **kwargs):
        # Supports both @observe and @observe(name=..., as_type=...).
        if len(args) == 1 and callable(args[0]) and not kwargs:
            return args[0]
        def deco(fn):
            return fn
        return deco

    def update_generation(**kw) -> None:
        pass

    def update_trace(**kw) -> None:
        pass

    def score(name: str = "", value=None, data_type: str = "NUMERIC", **kw) -> None:
        pass

    def current_trace_id():
        return None

    def flush() -> None:
        pass

    @contextlib.contextmanager
    def span(name: str, **kw):
        yield None
