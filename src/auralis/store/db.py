"""
SQLite persistence for call records.

Deliberately simple: one table, JSON columns for the structured payloads,
synchronous sqlite3 guarded by a lock. At single-tenant SMB volume this is
the right tool; the migration path to Postgres is swapping this module.
"""

import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel

from auralis.config import get_settings
from auralis.models import (
    CallRecord,
    CallScorecard,
    CallStatus,
    CRMStatus,
    CustomerProfile,
    EmailStatus,
    FollowUpEmail,
    GroundingReport,
    Insights,
    Summary,
)

_lock = threading.Lock()
_conn: Optional[sqlite3.Connection] = None


_SCHEMA = """
CREATE TABLE IF NOT EXISTS calls (
    call_id            TEXT PRIMARY KEY,
    status             TEXT NOT NULL,
    failed_step        TEXT,
    error              TEXT,
    customer_json      TEXT NOT NULL,
    transcript         TEXT NOT NULL,
    summary_json       TEXT,
    insights_json      TEXT,
    grounding_json     TEXT,
    followup_json      TEXT,
    scorecard_json     TEXT,
    followup_approved  INTEGER NOT NULL DEFAULT 0,
    email_status       TEXT NOT NULL DEFAULT 'not_sent',
    crm_status         TEXT NOT NULL DEFAULT 'pending',
    created_at         TEXT NOT NULL,
    updated_at         TEXT NOT NULL
);
"""


def _migrate(conn: sqlite3.Connection) -> None:
    """Add columns introduced after a database file was created."""
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(calls)")}
    for column in ("grounding_json", "scorecard_json"):
        if column not in existing:
            conn.execute(f"ALTER TABLE calls ADD COLUMN {column} TEXT")
    if "email_status" not in existing:
        conn.execute(
            "ALTER TABLE calls ADD COLUMN email_status TEXT NOT NULL DEFAULT 'not_sent'"
        )
    conn.commit()


def _connect() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(
            get_settings().database_path, check_same_thread=False
        )
        _conn.row_factory = sqlite3.Row
        _conn.execute(_SCHEMA)
        _migrate(_conn)
        _conn.commit()
    return _conn


def reset_for_tests(path: str = ":memory:") -> None:
    """Point the store at a fresh database. Test helper only."""
    global _conn
    if _conn is not None:
        _conn.close()
    _conn = sqlite3.connect(path, check_same_thread=False)
    _conn.row_factory = sqlite3.Row
    _conn.execute(_SCHEMA)
    _conn.commit()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Writes ─────────────────────────────────────────────────────────────────


def create_call(transcript: str, customer: CustomerProfile) -> str:
    call_id = uuid.uuid4().hex[:12]
    with _lock:
        conn = _connect()
        conn.execute(
            """INSERT INTO calls
               (call_id, status, customer_json, transcript, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                call_id,
                CallStatus.QUEUED.value,
                customer.model_dump_json(),
                transcript,
                _now(),
                _now(),
            ),
        )
        conn.commit()
    return call_id


def set_status(call_id: str, status: CallStatus) -> None:
    with _lock:
        conn = _connect()
        conn.execute(
            "UPDATE calls SET status = ?, updated_at = ? WHERE call_id = ?",
            (status.value, _now(), call_id),
        )
        conn.commit()


def set_failed(call_id: str, failed_step: str, error: str) -> None:
    with _lock:
        conn = _connect()
        conn.execute(
            """UPDATE calls SET status = ?, failed_step = ?, error = ?, updated_at = ?
               WHERE call_id = ?""",
            (CallStatus.FAILED.value, failed_step, error[:2000], _now(), call_id),
        )
        conn.commit()


def save_result(call_id: str, column: str, payload: BaseModel) -> None:
    """Persist one step's structured result (summary/insights/followup)."""
    assert column in (
        "summary_json",
        "insights_json",
        "grounding_json",
        "followup_json",
        "scorecard_json",
    )
    with _lock:
        conn = _connect()
        conn.execute(
            f"UPDATE calls SET {column} = ?, updated_at = ? WHERE call_id = ?",
            (payload.model_dump_json(), _now(), call_id),
        )
        conn.commit()


def set_crm_status(call_id: str, crm_status: CRMStatus) -> None:
    with _lock:
        conn = _connect()
        conn.execute(
            "UPDATE calls SET crm_status = ?, updated_at = ? WHERE call_id = ?",
            (crm_status.value, _now(), call_id),
        )
        conn.commit()


def set_email_status(call_id: str, email_status: EmailStatus) -> None:
    with _lock:
        conn = _connect()
        conn.execute(
            "UPDATE calls SET email_status = ?, updated_at = ? WHERE call_id = ?",
            (email_status.value, _now(), call_id),
        )
        conn.commit()


def set_followup_approved(call_id: str) -> bool:
    with _lock:
        conn = _connect()
        cur = conn.execute(
            """UPDATE calls SET followup_approved = 1, updated_at = ?
               WHERE call_id = ? AND followup_json IS NOT NULL""",
            (_now(), call_id),
        )
        conn.commit()
        return cur.rowcount > 0


# ── Reads ──────────────────────────────────────────────────────────────────


def _row_to_record(row: sqlite3.Row) -> CallRecord:
    return CallRecord(
        call_id=row["call_id"],
        status=CallStatus(row["status"]),
        failed_step=row["failed_step"],
        error=row["error"],
        customer=CustomerProfile.model_validate_json(row["customer_json"]),
        transcript=row["transcript"],
        summary=Summary.model_validate_json(row["summary_json"]) if row["summary_json"] else None,
        insights=Insights.model_validate_json(row["insights_json"]) if row["insights_json"] else None,
        grounding=GroundingReport.model_validate_json(row["grounding_json"]) if row["grounding_json"] else None,
        followup=FollowUpEmail.model_validate_json(row["followup_json"]) if row["followup_json"] else None,
        scorecard=CallScorecard.model_validate_json(row["scorecard_json"]) if row["scorecard_json"] else None,
        followup_approved=bool(row["followup_approved"]),
        email_status=EmailStatus(row["email_status"]),
        crm_status=CRMStatus(row["crm_status"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def get_call(call_id: str) -> Optional[CallRecord]:
    with _lock:
        conn = _connect()
        row = conn.execute(
            "SELECT * FROM calls WHERE call_id = ?", (call_id,)
        ).fetchone()
    return _row_to_record(row) if row else None


def list_calls(limit: int = 50) -> list[CallRecord]:
    with _lock:
        conn = _connect()
        rows = conn.execute(
            "SELECT * FROM calls ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_row_to_record(r) for r in rows]
