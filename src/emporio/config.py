"""Runtime configuration, read from environment variables / .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

# The dataset ends in March 2026, so "today" is simulated to keep order
# statuses, delivery estimates and return windows coherent.
DEFAULT_NOW = "2026-03-23T10:30"


@dataclass(frozen=True)
class Settings:
    model: str
    reasoning_effort: str
    store_now: datetime | None
    history_db: Path

    @classmethod
    def from_env(cls) -> "Settings":
        raw_now = os.getenv("STORE_NOW", DEFAULT_NOW).strip()
        return cls(
            model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
            reasoning_effort=os.getenv("OPENAI_REASONING_EFFORT", "low"),
            # STORE_NOW=real -> use the machine clock.
            store_now=None if raw_now.lower() == "real" else datetime.fromisoformat(raw_now),
            history_db=ROOT / os.getenv("HISTORY_DB", "var/history.sqlite3"),
        )

    def now(self) -> datetime:
        return self.store_now or datetime.now()
