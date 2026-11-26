"""SQLite-backed persistence for requirements, risks, approvals and the audit
log — the "relational database for structured requirements" from the spec's
suggested stack. Each table stores the pydantic model as JSON plus a couple
of indexed columns, which is enough for a single-project prototype and keeps
every model change from requiring a schema migration.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing

from finreq.models import ApprovalRecord, AuditEvent, Requirement, RiskItem

_SCHEMA = """
CREATE TABLE IF NOT EXISTS requirements (
    id TEXT PRIMARY KEY,
    approval_status TEXT NOT NULL,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS risks (
    id TEXT PRIMARY KEY,
    related_requirement_id TEXT NOT NULL,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS approvals (
    id TEXT PRIMARY KEY,
    target_id TEXT NOT NULL,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS analyses (
    id TEXT PRIMARY KEY,
    started REAL NOT NULL,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_log (
    id TEXT PRIMARY KEY,
    agent TEXT NOT NULL,
    event_type TEXT NOT NULL,
    data TEXT NOT NULL
);
"""


class Store:
    def __init__(self, db_path: str):
        self.db_path = db_path
        # check_same_thread=False: the API serves requests and runs analyses
        # on worker threads, so one Store is used from several threads.
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # -- requirements ---------------------------------------------------
    def save_requirement(self, req: Requirement) -> None:
        with closing(self._conn.cursor()) as cur:
            cur.execute(
                "INSERT INTO requirements (id, approval_status, data) VALUES (?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET approval_status=excluded.approval_status, data=excluded.data",
                (req.id, req.approval_status.value, req.model_dump_json()),
            )
        self._conn.commit()

    def get_requirement(self, req_id: str) -> Requirement | None:
        with closing(self._conn.cursor()) as cur:
            row = cur.execute("SELECT data FROM requirements WHERE id = ?", (req_id,)).fetchone()
        return Requirement.model_validate_json(row[0]) if row else None

    def all_requirements(self) -> list[Requirement]:
        with closing(self._conn.cursor()) as cur:
            rows = cur.execute("SELECT data FROM requirements ORDER BY id").fetchall()
        return [Requirement.model_validate_json(r[0]) for r in rows]

    # -- risks ------------------------------------------------------------
    def save_risk(self, risk: RiskItem) -> None:
        with closing(self._conn.cursor()) as cur:
            cur.execute(
                "INSERT INTO risks (id, related_requirement_id, data) VALUES (?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET data=excluded.data",
                (risk.id, risk.related_requirement_id, risk.model_dump_json()),
            )
        self._conn.commit()

    def all_risks(self) -> list[RiskItem]:
        with closing(self._conn.cursor()) as cur:
            rows = cur.execute("SELECT data FROM risks ORDER BY id").fetchall()
        return [RiskItem.model_validate_json(r[0]) for r in rows]

    # -- approvals ----------------------------------------------------
    def save_approval(self, record: ApprovalRecord) -> None:
        with closing(self._conn.cursor()) as cur:
            cur.execute(
                "INSERT INTO approvals (id, target_id, data) VALUES (?, ?, ?)",
                (record.id, record.target_id, record.model_dump_json()),
            )
        self._conn.commit()

    def approvals_for(self, target_id: str) -> list[ApprovalRecord]:
        with closing(self._conn.cursor()) as cur:
            rows = cur.execute(
                "SELECT data FROM approvals WHERE target_id = ? ORDER BY id", (target_id,)
            ).fetchall()
        return [ApprovalRecord.model_validate_json(r[0]) for r in rows]

    def approvals_all(self) -> list[ApprovalRecord]:
        with closing(self._conn.cursor()) as cur:
            rows = cur.execute("SELECT data FROM approvals").fetchall()
        return sorted((ApprovalRecord.model_validate_json(r[0]) for r in rows), key=lambda a: a.timestamp)

    # -- analyses (one per transcript run: the web UI's project list) ----
    def save_analysis(self, analysis_id: str, started: float, data: dict) -> None:
        with closing(self._conn.cursor()) as cur:
            cur.execute(
                "INSERT INTO analyses (id, started, data) VALUES (?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET data=excluded.data",
                (analysis_id, started, json.dumps(data)),
            )
        self._conn.commit()

    def all_analyses(self) -> list[dict]:
        """Newest first; each dict is the saved data plus its `id`."""
        with closing(self._conn.cursor()) as cur:
            rows = cur.execute("SELECT id, data FROM analyses ORDER BY started DESC").fetchall()
        return [{**json.loads(data), "id": analysis_id} for analysis_id, data in rows]

    def delete_analysis(self, analysis_id: str) -> None:
        """Drops the project-list entry only: its requirements, approvals and
        audit events stay, so the audit trail outlives the project."""
        with closing(self._conn.cursor()) as cur:
            cur.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))
        self._conn.commit()

    # -- audit log ------------------------------------------------------
    def log_event(self, event: AuditEvent) -> None:
        with closing(self._conn.cursor()) as cur:
            cur.execute(
                "INSERT INTO audit_log (id, agent, event_type, data) VALUES (?, ?, ?, ?)",
                (event.id, event.agent, event.event_type, event.model_dump_json()),
            )
        self._conn.commit()

    def all_events(self) -> list[AuditEvent]:
        with closing(self._conn.cursor()) as cur:
            rows = cur.execute("SELECT data FROM audit_log ORDER BY rowid").fetchall()  # insertion order; ids are random
        return [AuditEvent.model_validate_json(r[0]) for r in rows]


def in_memory_store() -> Store:
    """A fresh :memory: store — used by tests and by the pipeline's
    per-run scratch state."""
    return Store(":memory:")
