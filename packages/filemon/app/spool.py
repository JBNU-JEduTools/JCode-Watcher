import json
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SpoolRecord:
    event_id: str
    event_type: str
    payload: dict
    attempts: int


class EventSpool:
    """Small durable delivery queue; this is not the Watcher event database."""

    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=30)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        return connection

    def _initialize(self):
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS pending_event (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    next_attempt_at REAL NOT NULL DEFAULT 0,
                    created_at REAL NOT NULL
                )
                """
            )

    def enqueue(self, event_type: str, payload: dict):
        event_id = str(payload["event_id"])
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO pending_event
                    (event_id, event_type, payload_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (event_id, event_type, json.dumps(payload), time.time()),
            )

    def pending(self, limit: int) -> list[SpoolRecord]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT event_id, event_type, payload_json, attempts
                FROM pending_event
                WHERE next_attempt_at <= ?
                ORDER BY created_at, event_id
                LIMIT ?
                """,
                (time.time(), limit),
            ).fetchall()
        return [
            SpoolRecord(row[0], row[1], json.loads(row[2]), row[3]) for row in rows
        ]

    def acknowledge(self, event_ids: list[str]):
        if not event_ids:
            return
        with self._lock, self._connect() as connection:
            connection.executemany(
                "DELETE FROM pending_event WHERE event_id = ?",
                [(event_id,) for event_id in event_ids],
            )

    def retry_later(self, event_ids: list[str], retry_seconds: float):
        if not event_ids:
            return
        with self._lock, self._connect() as connection:
            connection.executemany(
                """
                UPDATE pending_event
                SET attempts = attempts + 1, next_attempt_at = ?
                WHERE event_id = ?
                """,
                [(time.time() + retry_seconds, event_id) for event_id in event_ids],
            )

    def contains(self, event_id: str) -> bool:
        with self._lock, self._connect() as connection:
            return (
                connection.execute(
                    "SELECT 1 FROM pending_event WHERE event_id = ?", (event_id,)
                ).fetchone()
                is not None
            )
