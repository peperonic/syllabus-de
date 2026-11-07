"""Shared helpers for builder stages."""
from __future__ import annotations

import datetime as dt
import json
import sqlite3
from dataclasses import dataclass, field

from kb.pack import Pack


@dataclass
class Scope:
    """Optional filters so one Land or one subject can be built end to end."""
    lands: list[str] = field(default_factory=list)
    subjects: list[str] = field(default_factory=list)

    def doc_where(self, alias: str = "d") -> tuple[str, list]:
        clauses, params = [], []
        if self.lands:
            clauses.append(f"{alias}.land IN ({','.join('?' * len(self.lands))})")
            params += self.lands
        if self.subjects:
            clauses.append(f"{alias}.subject IN ({','.join('?' * len(self.subjects))})")
            params += self.subjects
        return (" AND ".join(clauses) or "1=1"), params


@dataclass
class StageContext:
    conn: sqlite3.Connection
    pack: Pack
    scope: Scope
    log: list[str] = field(default_factory=list)

    def say(self, msg: str) -> None:
        self.log.append(msg)
        print(f"  {msg}")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def dumps(x) -> str:
    return json.dumps(x, ensure_ascii=False, sort_keys=True)
