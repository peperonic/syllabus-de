"""S1 fetch: download each document once, cache by sha256, log every request.

Polite by construction: robots.txt is honoured per host, requests are spaced
by the pack's rate limit, and the User-Agent names the project and a contact.
`file:` URLs (relative to the inventory file) serve the offline test fixture.
Länder listed under fetch.headless_browser_for are skipped here; a
Playwright fetcher for them comes later.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import mimetypes
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from pathlib import Path

from .common import StageContext, now

BUNDLE_TYPE = "application/x-curricula-html-bundle+json"

EXT_BY_TYPE = {"application/pdf": ".pdf", "text/html": ".html", "text/plain": ".txt",
               BUNDLE_TYPE: ".bundle.json"}


class Fetcher:
    def __init__(self, sc: StageContext):
        self.sc = sc
        self.user_agent = sc.pack.get("fetch.user_agent", "curricula-kb research crawler")
        if "set before running" in self.user_agent:
            raise RuntimeError("fetch.user_agent has no contact address; set it in the pack first")
        self.delay = 1.0 / float(sc.pack.get("fetch.rate_limit_per_second", 1) or 1)
        self.respect_robots = bool(sc.pack.get("fetch.respect_robots_txt", True))
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self._last = 0.0

    def _wait(self):
        dt_ = time.monotonic() - self._last
        if dt_ < self.delay:
            time.sleep(self.delay - dt_)
        self._last = time.monotonic()

    def allowed(self, url: str) -> bool:
        if not self.respect_robots:
            return True
        parts = urllib.parse.urlsplit(url)
        base = f"{parts.scheme}://{parts.netloc}"
        if base not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                self._wait()
                req = urllib.request.Request(base + "/robots.txt", headers={"User-Agent": self.user_agent})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    rp.parse(resp.read().decode("utf-8", "replace").splitlines())
            except urllib.error.HTTPError as e:
                rp = None if e.code in (401, 403) else _allow_all()
            except Exception:
                rp = _allow_all()
            self._robots[base] = rp
        rp = self._robots[base]
        if rp is not None:
            cd = rp.crawl_delay(self.user_agent) or rp.crawl_delay("*")
            if cd:
                self.delay = max(self.delay, float(cd))  # the site's own request spacing wins
        return False if rp is None else rp.can_fetch(self.user_agent, url)

    def get(self, url: str) -> tuple[int, str, bytes]:
        self._wait()
        req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status, resp.headers.get_content_type(), resp.read()


def _allow_all():
    rp = urllib.robotparser.RobotFileParser()
    rp.parse([])
    return rp


def s1_fetch(sc: StageContext) -> dict:
    conn, pack = sc.conn, sc.pack
    pack.raw_dir.mkdir(parents=True, exist_ok=True)
    headless = set(pack.get("fetch.headless_browser_for", []) or [])
    ttl = dt.timedelta(days=int(pack.get("corpus.cache_ttl_days", 30)))
    where, params = sc.scope.doc_where("d")
    docs = [dict(r) for r in conn.execute(f"SELECT d.* FROM document d WHERE {where}", params)]
    inv_dir = pack.inventory_path.parent
    fetcher = None
    bundles = set(pack.get("fetch.html_bundles", []) or [])
    stats = {"fetched": 0, "cached": 0, "skipped": 0, "errors": 0, "robots_disallowed": 0, "subpages": 0}
    for d in docs:
        url = (d.get("source_url") or "").strip()
        if not url or url.lower().startswith(("unverified", "unknown", "none")) or " " in url:
            stats["skipped"] += 1
            continue
        if d.get("sha256") and d.get("retrieved_at"):
            age = dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(d["retrieved_at"])
            if age < ttl and _raw_path(pack, d["sha256"]) is not None:
                stats["cached"] += 1
                continue
        try:
            if url.startswith("file:"):
                path = (inv_dir / url[len("file:"):]).resolve()
                data = path.read_bytes()
                status, ctype = 200, mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            else:
                if d["land"] in headless:
                    stats["skipped"] += 1
                    continue
                fetcher = fetcher or Fetcher(sc)
                if not fetcher.allowed(url):
                    stats["robots_disallowed"] += 1
                    conn.execute("INSERT INTO fetch_log(url, retrieved_at, error) VALUES (?,?,?)", (url, now(), "robots.txt disallows"))
                    continue
                status, ctype, data = fetcher.get(url)
                if d["land"] in bundles and ctype == "text/html":
                    data, ctype = _fetch_bundle(sc, fetcher, url, data, stats)
        except Exception as e:  # noqa: BLE001 - every failure is logged, the run continues
            stats["errors"] += 1
            conn.execute("INSERT INTO fetch_log(url, retrieved_at, error) VALUES (?,?,?)", (url, now(), f"{type(e).__name__}: {e}"[:500]))
            continue
        sha = hashlib.sha256(data).hexdigest()
        ext = EXT_BY_TYPE.get(ctype) or Path(urllib.parse.urlsplit(url).path).suffix or ".bin"
        target = pack.raw_dir / f"{sha}{ext}"
        if not target.exists():
            target.write_bytes(data)
        conn.execute("INSERT INTO fetch_log(url, sha256, http_status, content_type, bytes, retrieved_at) VALUES (?,?,?,?,?,?)",
                     (url, sha, status, ctype, len(data), now()))
        conn.execute("UPDATE document SET sha256 = ?, retrieved_at = ? WHERE document_id = ?", (sha, now(), d["document_id"]))
        stats["fetched"] += 1
    conn.commit()
    sc.say(f"S1: {stats}")
    return stats


def _fetch_bundle(sc: StageContext, fetcher: Fetcher, url: str, index_html: bytes, stats: dict) -> tuple[bytes, str]:
    """A plan published as an index page plus sub-pages (BW Bildungsplanplattform).

    Sub-pages are the links whose path starts with the index page's own id plus
    an underscore, e.g. /,Lde/BP2016BW_ALLG_SEK1_M.V2 -> /,Lde/BP2016BW_ALLG_SEK1_M.V2_IK_7-8-9_01_00.
    Each page is cached by its own sha256; the document's raw file is a JSON
    manifest listing them in order, so the document hash changes when any page does.
    A single-page plan (no such links) yields a manifest with one page."""
    import json
    import re
    parts = urllib.parse.urlsplit(url)
    base = f"{parts.scheme}://{parts.netloc}"
    own = urllib.parse.unquote(parts.path)
    pages = [(url, index_html)]
    seen = {own}
    for href in re.findall(r'href="(/,Lde/[^"#?]+)"', index_html.decode("utf-8", "replace")):
        p = urllib.parse.unquote(href)
        if p in seen or not p.startswith(own + "_"):
            continue
        seen.add(p)
        sub = base + href
        if not fetcher.allowed(sub):
            stats["robots_disallowed"] += 1
            continue
        status, ctype, data = fetcher.get(sub)
        sc.conn.execute("INSERT INTO fetch_log(url, sha256, http_status, content_type, bytes, retrieved_at) VALUES (?,?,?,?,?,?)",
                        (sub, hashlib.sha256(data).hexdigest(), status, ctype, len(data), now()))
        pages.append((sub, data))
        stats["subpages"] += 1
    manifest = []
    for u, data in pages:
        sha = hashlib.sha256(data).hexdigest()
        target = sc.pack.raw_dir / f"{sha}.html"
        if not target.exists():
            target.write_bytes(data)
        manifest.append({"url": u, "sha256": sha})
    sc.conn.commit()
    return json.dumps({"index": url, "pages": manifest}, ensure_ascii=False, indent=1).encode("utf-8"), BUNDLE_TYPE


def _raw_path(pack, sha: str) -> Path | None:
    hits = list(pack.raw_dir.glob(f"{sha}.*"))
    return hits[0] if hits else None
