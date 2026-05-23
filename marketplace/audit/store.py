"""
Pluggable audit storage.

Two backends:
  - InMemoryStore: dict in process. For dev / Demo Day fallback.
  - SupabaseStore: writes to Supabase `audit_entries` table.
    Use when SUPABASE_URL + SUPABASE_SERVICE_KEY are set.
"""
from __future__ import annotations
import os, json, urllib.request
from typing import Optional
from chain import AuditEntry  # type: ignore


class InMemoryStore:
    def __init__(self):
        # session_id -> list[AuditEntry]
        self._sessions: dict[str, list[AuditEntry]] = {}

    def append(self, entry: AuditEntry) -> None:
        self._sessions.setdefault(entry.session_id, []).append(entry)

    def get_session(self, session_id: str) -> list[AuditEntry]:
        return list(self._sessions.get(session_id, []))

    def get_by_trace(self, trace_id: str) -> Optional[AuditEntry]:
        for entries in self._sessions.values():
            for e in entries:
                if e.trace_id == trace_id:
                    return e
        return None


class SupabaseStore:
    """
    Minimal Supabase REST client — POST /rest/v1/audit_entries with
    apikey + service_role JWT, GET with eq filters.

    Table DDL (run in Supabase SQL editor):

      create table if not exists audit_entries (
        id bigserial primary key,
        session_id text not null,
        seq int not null,
        skill_id text not null,
        trace_id text not null,
        input_hash text not null,
        output_hash text not null,
        verify_passed boolean,
        prev_chain_hash text not null,
        chain_hash text not null,
        ts double precision not null,
        elapsed_ms int default 0,
        extra jsonb default '{}'::jsonb,
        created_at timestamptz default now(),
        unique (session_id, seq)
      );
      alter table audit_entries enable row level security;
      create policy "read-all" on audit_entries for select using (true);
    """
    def __init__(self, url: Optional[str] = None, service_key: Optional[str] = None):
        self.url = url or os.getenv("SUPABASE_URL") or ""
        self.key = service_key or os.getenv("SUPABASE_SERVICE_KEY") or ""
        if not self.url or not self.key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY required")

    def _headers(self) -> dict:
        return {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }

    def append(self, entry: AuditEntry) -> None:
        body = json.dumps(entry.to_dict()).encode("utf-8")
        req = urllib.request.Request(
            f"{self.url}/rest/v1/audit_entries",
            data=body, headers=self._headers(), method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            _ = r.read()

    def get_session(self, session_id: str) -> list[AuditEntry]:
        q = (f"{self.url}/rest/v1/audit_entries"
             f"?session_id=eq.{session_id}&order=seq.asc")
        req = urllib.request.Request(q, headers={
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
        })
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8"))
        return [AuditEntry(**{k: v for k, v in row.items() if k in AuditEntry.__dataclass_fields__})
                for row in data]

    def get_by_trace(self, trace_id: str) -> Optional[AuditEntry]:
        q = f"{self.url}/rest/v1/audit_entries?trace_id=eq.{trace_id}&limit=1"
        req = urllib.request.Request(q, headers={
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
        })
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8"))
        if not data: return None
        row = data[0]
        return AuditEntry(**{k: v for k, v in row.items() if k in AuditEntry.__dataclass_fields__})


def get_default_store():
    """Auto-pick: Supabase if configured, else in-memory."""
    if os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_KEY"):
        return SupabaseStore()
    return InMemoryStore()
