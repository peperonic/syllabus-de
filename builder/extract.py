"""S2 extract: raw file to page-level text, cached as JSON next to the raw cache.

PDF via PyMuPDF (page numbers are the PDF's physical pages, 1-based), HTML via
the standard library parser, plain text split on form feeds (the fixture).
"""
from __future__ import annotations

import html.parser
import json

from .common import StageContext
from .fetch import _raw_path


class _TextOnly(html.parser.HTMLParser):
    SKIP = {"script", "style", "nav", "header", "footer"}

    def __init__(self):
        super().__init__()
        self.out: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif tag in ("p", "br", "li", "h1", "h2", "h3", "h4", "tr", "div"):
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.out.append(data)


def extract_pages(path) -> list[dict]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        try:
            import fitz  # PyMuPDF
        except ImportError as e:
            raise RuntimeError("PDF extraction needs PyMuPDF: pip install -r requirements.txt") from e
        with fitz.open(path) as pdf:
            return [{"page": i + 1, "text": p.get_text("text")} for i, p in enumerate(pdf)]
    if path.name.endswith(".bundle.json"):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        out = []
        for i, pg in enumerate(manifest["pages"], 1):
            src = path.parent / f"{pg['sha256']}.html"
            html_text = src.read_bytes().decode("utf-8", "replace")
            p = _TextOnly()
            p.feed(html_text)
            # HTML plans keep their markup: the parser profile needs the structure.
            out.append({"page": i, "url": pg["url"], "html": html_text, "text": "".join(p.out)})
        return out
    raw = path.read_bytes().decode("utf-8", "replace")
    if suffix in (".html", ".htm"):
        p = _TextOnly()
        p.feed(raw)
        return [{"page": 1, "text": "".join(p.out)}]
    return [{"page": i + 1, "text": t} for i, t in enumerate(raw.split("\f"))]


def s2_extract(sc: StageContext) -> dict:
    conn, pack = sc.conn, sc.pack
    pack.extract_dir.mkdir(parents=True, exist_ok=True)
    where, params = sc.scope.doc_where("d")
    stats = {"extracted": 0, "cached": 0, "errors": 0}
    for d in conn.execute(f"SELECT document_id, sha256 FROM document d WHERE sha256 IS NOT NULL AND {where}", params):
        out = pack.extract_dir / f"{d['sha256']}.json"
        if out.exists():
            stats["cached"] += 1
            continue
        raw = _raw_path(pack, d["sha256"])
        if raw is None:
            stats["errors"] += 1
            sc.say(f"S2: raw file missing for {d['document_id']}")
            continue
        try:
            pages = extract_pages(raw)
        except Exception as e:  # noqa: BLE001
            stats["errors"] += 1
            sc.say(f"S2: {d['document_id']}: {e}")
            continue
        out.write_text(json.dumps(pages, ensure_ascii=False), encoding="utf-8")
        stats["extracted"] += 1
    sc.say(f"S2: {stats}")
    return stats
