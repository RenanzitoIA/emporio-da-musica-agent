"""SQLite persistence: conversation history and support tickets.

SQLite keeps the project dependency-free; the same interface could be backed
by Postgres/Redis in production.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    message TEXT NOT NULL            -- OpenAI chat message as JSON
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id);
CREATE TABLE IF NOT EXISTS feedback (
    session_id TEXT NOT NULL,
    turn INTEGER NOT NULL,           -- 1-based index of the assistant answer in the session
    score INTEGER NOT NULL,          -- 1 = thumbs up, 0 = thumbs down
    created_at TEXT NOT NULL,
    PRIMARY KEY (session_id, turn)
);
CREATE TABLE IF NOT EXISTS tickets (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    session_id TEXT,
    kind TEXT NOT NULL,
    summary TEXT NOT NULL,
    order_id INTEGER,
    contact TEXT
);
"""


class Store:
    def __init__(self, path: Path | str):
        path = Path(path)
        if str(path) != ":memory:":
            path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.executescript(SCHEMA)
        self._lock = threading.Lock()

    # ------------------------------------------------------------ history
    @staticmethod
    def new_session_id() -> str:
        return uuid.uuid4().hex[:12]

    def load(self, session_id: str) -> list[dict[str, Any]]:
        rows = self._db.execute(
            "SELECT message FROM messages WHERE session_id = ? ORDER BY id", (session_id,)
        ).fetchall()
        return [json.loads(r[0]) for r in rows]

    def append(self, session_id: str, messages: list[dict[str, Any]]) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        with self._lock, self._db:
            self._db.executemany(
                "INSERT INTO messages (session_id, created_at, message) VALUES (?, ?, ?)",
                [(session_id, now, json.dumps(m, ensure_ascii=False)) for m in messages],
            )

    def clear(self, session_id: str) -> None:
        with self._lock, self._db:
            self._db.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))

    # ------------------------------------------------------------ feedback
    def save_feedback(self, session_id: str, turn: int, score: int) -> None:
        with self._lock, self._db:
            self._db.execute(
                "INSERT OR REPLACE INTO feedback VALUES (?, ?, ?, ?)",
                (session_id, turn, score, datetime.now().isoformat(timespec="seconds")),
            )

    def get_feedback(self, session_id: str) -> dict[int, int]:
        rows = self._db.execute(
            "SELECT turn, score FROM feedback WHERE session_id = ?", (session_id,)
        ).fetchall()
        return dict(rows)

    # ------------------------------------------------------------ tickets
    def create(self, kind: str, summary: str, order_id=None, contact=None, session_id=None) -> str:
        with self._lock, self._db:
            count = self._db.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
            ticket_id = f"EM-{count + 1:05d}"
            self._db.execute(
                "INSERT INTO tickets VALUES (?, ?, ?, ?, ?, ?, ?)",
                (ticket_id, datetime.now().isoformat(timespec="seconds"), session_id,
                 kind, summary, order_id, contact),
            )
        return ticket_id

    def list_tickets(self) -> list[dict[str, Any]]:
        cur = self._db.execute("SELECT * FROM tickets ORDER BY created_at")
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
