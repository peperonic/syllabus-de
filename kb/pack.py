"""Domain pack loading. Everything field-specific lives in a pack YAML file.

Paths inside a pack are relative to the pack file. Data paths (raw downloads,
the SQLite file) are relative to a data directory, so tests can point a pack
at a temporary folder.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PACK = REPO_ROOT / "design" / "pack.yaml"
DEFAULT_DATA_DIR = REPO_ROOT / "data"


@dataclass
class Pack:
    path: Path
    raw: dict[str, Any]
    data_dir: Path = field(default=DEFAULT_DATA_DIR)

    # -- locations -------------------------------------------------------
    def rel(self, value: str | None) -> Path | None:
        """Resolve a path written in the pack, relative to the pack file."""
        if not value:
            return None
        p = Path(value)
        return p if p.is_absolute() else (self.path.parent / p).resolve()

    @property
    def inventory_path(self) -> Path:
        return self.rel(self.raw["inventory"])

    @property
    def db_path(self) -> Path:
        name = Path(self.raw.get("corpus", {}).get("knowledgebase", "data/kb.sqlite")).name
        return self.data_dir / name

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def extract_dir(self) -> Path:
        return self.data_dir / "extract"

    def files(self, key: str) -> list[Path]:
        """List of curated files under `curated.<key>` in the pack."""
        vals = (self.raw.get("curated") or {}).get(key) or []
        if isinstance(vals, str):
            vals = [vals]
        return [self.rel(v) for v in vals]

    # -- settings --------------------------------------------------------
    def get(self, dotted: str, default: Any = None) -> Any:
        cur: Any = self.raw
        for part in dotted.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return default
            cur = cur[part]
        return cur

    def parse_profile(self, land: str) -> str | None:
        profiles = self.get("parse.profiles", {}) or {}
        return profiles.get(land)

    # -- licence ---------------------------------------------------------
    def licence_class(self, licence: str | None) -> str:
        """full_text, structure_only or cross_check_only. Unknown licences are
        treated as structure_only, the safe default: label and link, no text."""
        if not licence:
            return "structure_only"
        lic = licence.casefold()
        policy = self.get("licence_policy", {}) or {}
        for cls in ("cross_check_only", "structure_only", "full_text"):
            for marker in policy.get(cls, []) or []:
                if marker.casefold() in lic:
                    return cls
        return "structure_only"


def load_pack(path: str | os.PathLike | None = None, data_dir: str | os.PathLike | None = None) -> Pack:
    path = Path(path or os.environ.get("CURRICULA_PACK") or DEFAULT_PACK).resolve()
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    ddir = Path(data_dir or os.environ.get("CURRICULA_DATA_DIR") or DEFAULT_DATA_DIR).resolve()
    return Pack(path=path, raw=raw, data_dir=ddir)
