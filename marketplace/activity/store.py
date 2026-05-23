"""
Activity event store — pluggable backend.

InMemoryStore: ring buffer (last 1000 events), useful for dev and demo-day fallback.
SupabaseStore: writes to Supabase `activity_events` table; the frontend
  subscribes via Supabase Realtime.

Event schema:
  {
    "id": int,                # auto
    "session_id": str,
    "trace_id": str,          # nullable; links to a skill invocation
    "kind": str,              # see EventKind below
    "skill_id": str | None,
    "ts": float,              # unix seconds
    "data": dict,             # event-specific payload
  }
"""
from __future__ import annotations
import json, os, threading, time, urllib.request
from dataclasses import asdict, dataclass, field
from typing import Iterable, Optional


# Standard event kinds emitted by the executor
class EventKind:
    SESSION_STARTED       = "session_started"        # user input received
    ROUTE_PLANNED         = "route_planned"          # KIMI returned a SkillPlan
    SKILL_PAYMENT_REQUIRED = "skill_payment_required" # gateway returned 402
    SKILL_PAYMENT_SETTLED  = "skill_payment_settled"  # gateway accepted X-Payment
    SKILL_STARTED         = "skill_started"          # POST /invoke sent
    SKILL_COMPLETED       = "skill_completed"        # got response
    SKILL_FAILED          = "skill_failed"
    AUDIT_APPENDED        = "audit_appended"         # chain entry written
    VERIFY_COMPLETED      = "verify_completed"
    SESSION_COMPLETED     = "session_completed"


@dataclass
class Event:
    session_id: str
    kind: str
    skill_id: Optional[str] = None
    trace_id: Optional[str] = None
    ts: float = field(default_factory=time.time)
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class InMemoryStore:
    def __init__(self, max_events: int = 1000):
        self.max = max_events
        self._events: list[Event] = []
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)

    def emit(self, event: Event) -> None:
        with self._cond:
            self._events.append(event)
            if len(self._events) > self.max:
                self._events = self._events[-self.max:]
            self._cond.notify_all()

    def list_session(self, session_id: str) -> list[Event]:
        with self._lock:
            return [e for e in self._events if e.session_id == session_id]

    def stream_session(self, session_id: str, last_seen_ts: float = 0.0, timeout: float = 25.0) -> Iterable[Event]:
        """
        Long-poll: yield events since last_seen_ts. Blocks up to `timeout` seconds
        waiting for new events, then returns (empty if nothing arrives).
        """
        deadline = time.time() + timeout
        while True:
            with self._cond:
                new = [e for e in self._events if e.session_id == session_id and e.ts > last_seen_ts]
                if new:
                    return new
                remaining = deadline - time.time()
                if remaining <= 0:
                    return []
                self._cond.wait(timeout=remaining)


class SupabaseStore:
    """
    Table DDL (run in Supabase SQL editor):

      create table if not exists activity_events (
        id bigserial primary key,
        session_id text not null,
        trace_id text,
        kind text not null,
        skill_id text,
        ts double precision not null,
        data jsonb default '{}'::jsonb,
        created_at timestamptz default now()
      );
      alter table activity_events enable row level security;
      create policy "read-all" on activity_events for select using (true);
      -- enable realtime in the supabase dashboard for this table
    """
    def __init__(self, url: Optional[str] = None, service_key: Optional[str] = None):
        self.url = url or os.getenv("SUPABASE_URL") or ""
        self.key = service_key or os.getenv("SUPABASE_SERVICE_KEY") or ""
        if not self.url or not self.key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY required")

    def _headers(self) -> dict:
        return {
            "apikey": self.key, "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json", "Prefer": "return=minimal",
        }

    def emit(self, event: Event) -> None:
        body = json.dumps(event.to_dict()).encode("utf-8")
        req = urllib.request.Request(
            f"{self.url}/rest/v1/activity_events",
            data=body, headers=self._headers(), method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            _ = r.read()

    def list_session(self, session_id: str) -> list[Event]:
        q = (f"{self.url}/rest/v1/activity_events"
             f"?session_id=eq.{session_id}&order=ts.asc")
        req = urllib.request.Request(q, headers={
            "apikey": self.key, "Authorization": f"Bearer {self.key}",
        })
        with urllib.request.urlopen(req, timeout=10) as r:
            rows = json.loads(r.read().decode("utf-8"))
        return [Event(**{k: v for k, v in r.items() if k in Event.__dataclass_fields__})
                for r in rows]


def get_default_store():
    if os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_KEY"):
        return SupabaseStore()
    return InMemoryStore()
