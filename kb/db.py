"""SQLite access. The schema lives in design/schema.sql."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from .pack import REPO_ROOT

SCHEMA_PATH = REPO_ROOT / "design" / "schema.sql"


def connect(path: str | Path, *, read_only: bool = False) -> sqlite3.Connection:
    path = Path(path)
    if read_only:
        if not path.exists():
            raise FileNotFoundError(f"knowledge base not found: {path} (run builder/run.py first)")
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()


def rows(conn: sqlite3.Connection, sql: str, params: tuple | list = ()) -> list[dict]:
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def one(conn: sqlite3.Connection, sql: str, params: tuple | list = ()) -> dict | None:
    r = conn.execute(sql, params).fetchone()
    return dict(r) if r else None
