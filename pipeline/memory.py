"""
Memory: short-term (active task/conversation state, in-process) + long-term
(persisted per-lead history). Kept generic/JSON-able now; the long-term store
will write into `Lead.memory_log` once we bind to the real schema — for now
it's a standalone store you can point at a Lead's id.

Backing store: SQLite via stdlib sqlite3 (hackathon-simple, zero extra infra).
Swap DATABASE_URL later if the team moves to Postgres for the shared DB.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

DB_PATH = "nexaflow_memory.db"


# ---------- Short-term memory (in-process, per active task/conversation) ----------

class ShortTermMemory:
    """
    Ephemeral state for whatever the agent is actively doing right now
    (e.g. mid-way through drafting an email, waiting on a classification).
    Not persisted — cleared on restart. Thread-safe for simple concurrent
    FastAPI request handling.
    """

    def __init__(self):
        self._store: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def set(self, lead_id: str, key: str, value: Any) -> None:
        with self._lock:
            self._store.setdefault(lead_id, {})[key] = value

    def get(self, lead_id: str, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._store.get(lead_id, {}).get(key, default)

    def get_all(self, lead_id: str) -> dict[str, Any]:
        with self._lock:
            return dict(self._store.get(lead_id, {}))

    def clear(self, lead_id: str) -> None:
        with self._lock:
            self._store.pop(lead_id, None)


# ---------- Long-term memory (persisted, append-only per-lead history) ----------

@dataclass
class MemoryEntry:
    lead_id: str
    entry_type: str          # e.g. "email_sent", "reply_received", "classification",
                              # "follow_up_sent", "meeting_scheduled", "stage_change"
    payload: dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class LongTermMemory:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lead_id TEXT NOT NULL,
                    entry_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_lead ON memory_log(lead_id)")

    def append(self, entry: MemoryEntry) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO memory_log (lead_id, entry_type, payload, timestamp) VALUES (?, ?, ?, ?)",
                (entry.lead_id, entry.entry_type, json.dumps(entry.payload), entry.timestamp.isoformat()),
            )

    def history(self, lead_id: str, entry_type: Optional[str] = None) -> list[MemoryEntry]:
        with self._conn() as conn:
            if entry_type:
                rows = conn.execute(
                    "SELECT lead_id, entry_type, payload, timestamp FROM memory_log "
                    "WHERE lead_id = ? AND entry_type = ? ORDER BY timestamp ASC",
                    (lead_id, entry_type),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT lead_id, entry_type, payload, timestamp FROM memory_log "
                    "WHERE lead_id = ? ORDER BY timestamp ASC",
                    (lead_id,),
                ).fetchall()
        return [
            MemoryEntry(
                lead_id=r[0],
                entry_type=r[1],
                payload=json.loads(r[2]),
                timestamp=datetime.fromisoformat(r[3]),
            )
            for r in rows
        ]

    def last(self, lead_id: str, entry_type: Optional[str] = None) -> Optional[MemoryEntry]:
        hist = self.history(lead_id, entry_type)
        return hist[-1] if hist else None


# Module-level singletons — simple and sufficient for a hackathon single-process app.
short_term = ShortTermMemory()
long_term = LongTermMemory()
