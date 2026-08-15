"""
Simple Lead persistence: whole-object JSON blobs in SQLite, keyed by id.
Good enough for a hackathon (no migrations to manage as the schema evolves —
just re-validate through Pydantic on read). Swap for a real Postgres table
with proper columns post-hackathon if the team wants queryable fields.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Optional

from shared.schema import Lead

def _normalize_name(name: str) -> str:
    """Lowercase + strip, so 'Tabani Real Estate' and 'tabani real estate ' match."""
    return name.strip().lower()

DB_PATH = "nexaflow_leads.db"


class LeadStore:
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
                CREATE TABLE IF NOT EXISTS leads (
                    id TEXT PRIMARY KEY,
                    company_name TEXT NOT NULL,
                    pipeline_stage TEXT NOT NULL,
                    data TEXT NOT NULL
                )
                """
            )

    def save(self, lead: Lead) -> None:
        existing = self.find_by_company_name(lead.company_name)
        if existing and existing.id != lead.id:
            lead.id = existing.id  # reuse the existing record instead of duplicating

        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO leads (id, company_name, pipeline_stage, data)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    company_name=excluded.company_name,
                    pipeline_stage=excluded.pipeline_stage,
                    data=excluded.data
                """,
                (lead.id, lead.company_name, lead.pipeline_stage.value, lead.model_dump_json()),
            )

    def get(self, lead_id: str) -> Optional[Lead]:
        with self._conn() as conn:
            row = conn.execute("SELECT data FROM leads WHERE id = ?", (lead_id,)).fetchone()
        return Lead.model_validate_json(row[0]) if row else None

    def find_by_company_name(self, company_name: str) -> Optional[Lead]:
        normalized = _normalize_name(company_name)
        with self._conn() as conn:
            rows = conn.execute("SELECT data FROM leads").fetchall()
        for row in rows:
            lead = Lead.model_validate_json(row[0])
            if _normalize_name(lead.company_name) == normalized:
                return lead
        return None

    def all(self) -> list[Lead]:
        with self._conn() as conn:
            rows = conn.execute("SELECT data FROM leads").fetchall()
        return [Lead.model_validate_json(r[0]) for r in rows]

    def by_stage(self, stage) -> list[Lead]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT data FROM leads WHERE pipeline_stage = ?", (stage.value if hasattr(stage, "value") else stage,)
            ).fetchall()
        return [Lead.model_validate_json(r[0]) for r in rows]

    def delete_all(self) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM leads")


lead_store = LeadStore()
