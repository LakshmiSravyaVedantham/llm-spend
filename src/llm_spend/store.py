"""
SQLite storage for LLM spend call logs.
"""

from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

DEFAULT_DB_DIR = Path.home() / ".llm-spend"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "spend.db"

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS calls (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp      TEXT    NOT NULL,
    provider       TEXT    NOT NULL,
    model          TEXT    NOT NULL,
    label          TEXT,
    file           TEXT,
    function       TEXT,
    input_tokens   INTEGER NOT NULL DEFAULT 0,
    output_tokens  INTEGER NOT NULL DEFAULT 0,
    cost_usd       REAL    NOT NULL DEFAULT 0.0,
    duration_ms    REAL    NOT NULL DEFAULT 0.0,
    metadata_json  TEXT
)
"""


class SpendStore:
    """Manages persistent storage of LLM API call logs in SQLite."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(_CREATE_TABLE)
            conn.commit()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def log_call(
        self,
        provider: str,
        model: str,
        label: Optional[str],
        file: Optional[str],
        function: Optional[str],
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        duration_ms: float,
        metadata: Optional[dict[str, Any]] = None,
    ) -> int:
        """Insert a new call record and return its id."""
        timestamp = datetime.now(timezone.utc).isoformat()
        metadata_json = json.dumps(metadata) if metadata else None
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO calls
                    (timestamp, provider, model, label, file, function,
                     input_tokens, output_tokens, cost_usd, duration_ms, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    provider,
                    model,
                    label,
                    file,
                    function,
                    input_tokens,
                    output_tokens,
                    cost_usd,
                    duration_ms,
                    metadata_json,
                ),
            )
            conn.commit()
            return cursor.lastrowid  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def _cutoff(self, days: int) -> str:
        return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    def get_total(self, days: int = 30) -> dict[str, float]:
        """Return total spend metrics over the last N days."""
        cutoff = self._cutoff(days)
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    COALESCE(SUM(cost_usd), 0.0)    AS total_cost,
                    COALESCE(SUM(input_tokens), 0)  AS total_input,
                    COALESCE(SUM(output_tokens), 0) AS total_output,
                    COUNT(*)                         AS total_calls
                FROM calls WHERE timestamp >= ?
                """,
                (cutoff,),
            ).fetchone()
        return dict(row)

    def get_by_file(self, days: int = 30) -> list[dict[str, Any]]:
        """Aggregate cost per source file."""
        cutoff = self._cutoff(days)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    COALESCE(file, '(unknown)') AS file,
                    COUNT(*)                    AS calls,
                    SUM(input_tokens)           AS input_tokens,
                    SUM(output_tokens)          AS output_tokens,
                    SUM(cost_usd)               AS cost_usd
                FROM calls
                WHERE timestamp >= ?
                GROUP BY file
                ORDER BY cost_usd DESC
                """,
                (cutoff,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_by_function(self, days: int = 30) -> list[dict[str, Any]]:
        """Aggregate cost per function."""
        cutoff = self._cutoff(days)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    COALESCE(function, '(unknown)')  AS function,
                    COALESCE(file, '(unknown)')      AS file,
                    COUNT(*)                          AS calls,
                    SUM(input_tokens)                 AS input_tokens,
                    SUM(output_tokens)                AS output_tokens,
                    SUM(cost_usd)                     AS cost_usd
                FROM calls
                WHERE timestamp >= ?
                GROUP BY function, file
                ORDER BY cost_usd DESC
                """,
                (cutoff,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_by_label(self, days: int = 30) -> list[dict[str, Any]]:
        """Aggregate cost per label."""
        cutoff = self._cutoff(days)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    COALESCE(label, '(unlabeled)') AS label,
                    COUNT(*)                        AS calls,
                    SUM(input_tokens)               AS input_tokens,
                    SUM(output_tokens)              AS output_tokens,
                    SUM(cost_usd)                   AS cost_usd
                FROM calls
                WHERE timestamp >= ?
                GROUP BY label
                ORDER BY cost_usd DESC
                """,
                (cutoff,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_by_model(self, days: int = 30) -> list[dict[str, Any]]:
        """Aggregate cost per model."""
        cutoff = self._cutoff(days)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    model,
                    provider,
                    COUNT(*)          AS calls,
                    SUM(input_tokens) AS input_tokens,
                    SUM(output_tokens)AS output_tokens,
                    SUM(cost_usd)     AS cost_usd
                FROM calls
                WHERE timestamp >= ?
                GROUP BY model, provider
                ORDER BY cost_usd DESC
                """,
                (cutoff,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_all_calls(self, days: int = 30) -> list[dict[str, Any]]:
        """Return raw call rows."""
        cutoff = self._cutoff(days)
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM calls WHERE timestamp >= ? ORDER BY timestamp DESC",
                (cutoff,),
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Management
    # ------------------------------------------------------------------

    def clear(self, days: Optional[int] = None) -> int:
        """Delete records.  If days is given, delete records older than N days."""
        with self._connect() as conn:
            if days is None:
                cursor = conn.execute("DELETE FROM calls")
            else:
                cutoff = self._cutoff(days)
                cursor = conn.execute("DELETE FROM calls WHERE timestamp < ?", (cutoff,))
            conn.commit()
            return cursor.rowcount

    def export_csv(self, path: str) -> int:
        """Export all calls to a CSV file.  Returns number of rows written."""
        rows = self.get_all_calls(days=365 * 10)  # effectively all
        if not rows:
            return 0
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        return len(rows)

    def export_json(self, path: str) -> int:
        """Export all calls to a JSON file.  Returns number of rows written."""
        rows = self.get_all_calls(days=365 * 10)
        with open(path, "w") as f:
            json.dump(rows, f, indent=2)
        return len(rows)
