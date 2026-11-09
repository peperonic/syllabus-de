"""Proposer and judge providers for S5 and S6.

A provider is named in the pack as '<kind>:<arg>':

* fixture:<file>      deterministic, offline (tests and the toy pack); the judge passes unless told otherwise
* file:<file>         proposals or verdicts produced outside the build, by a model in a session
                      or by a person; the judge declines anything it was not explicitly asked to pass
* anthropic:<model>   Claude via the Anthropic API (needs a key; not built yet)

What each side may see is fixed here, not left to the provider:
the proposer gets nodes (id, kind, label, text, grades) and topics
(id, label, description, grade band); the judge gets one edge with the
verbatim node text and the topic. Neither ever sees the held-out gold set,
and the judge never sees the proposer's rationale.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class Proposal:
    src: str
    rel: str          # maps_to | requires
    dst: str
    confidence: float
    rationale: str = ""


@dataclass
class Verdict:
    verdict: str      # pass | decline
    reason: str


class FixtureProposer:
    def __init__(self, path: Path):
        self.items = yaml.safe_load(path.read_text(encoding="utf-8")) or []

    def propose(self, nodes: list[dict], topics: list[dict]) -> list[Proposal]:
        # Returns the fixture's proposals as written, including deliberately bad
        # ones, so that S6 has something to decline.
        return [Proposal(i["src"], i.get("rel", "maps_to"), i["dst"], float(i.get("confidence", 0.8)), i.get("rationale", ""))
                for i in self.items]


class FixtureJudge:
    """Passes every edge except those the fixture lists as declined."""

    def __init__(self, path: Path):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        self.declines = {(d["src"], d.get("rel", "maps_to"), d["dst"]): d.get("reason", "") for d in data.get("decline", [])}

    def judge(self, edge: dict, node: dict | None, topic: dict | None) -> Verdict:
        key = (edge["src"], edge["rel"], edge["dst"])
        if key in self.declines:
            return Verdict("decline", self.declines[key])
        return Verdict("pass", "fixture: kein Einwand")


class FileJudge:
    """Verdicts written by an independent judge (a separate agent or a person) to a file.

    Unlike the fixture judge, an edge the file does not mention is declined:
    a real mapping counts only after an explicit pass. Entries match by
    (src, rel, dst) or, for many nodes sharing one text, by (text_key, rel, dst)."""

    def __init__(self, path: Path):
        import json
        data = json.loads(path.read_text(encoding="utf-8")) if path.suffix == ".json" else yaml.safe_load(path.read_text(encoding="utf-8"))
        self.by_edge, self.by_text = {}, {}
        for v in data.get("verdicts", []):
            key = (v.get("rel", "maps_to"), v["dst"])
            if "src" in v:
                self.by_edge[(v["src"], *key)] = v
            if "text_key" in v:
                self.by_text[(v["text_key"], *key)] = v
        self.text_key_of = data.get("text_keys", {})  # node_id -> text_key

    def judge(self, edge: dict, node: dict | None, topic: dict | None) -> Verdict:
        k = (edge["src"], edge["rel"], edge["dst"])
        v = self.by_edge.get(k)
        if v is None and node is not None:
            tk = self.text_key_of.get(edge["src"]) or text_key(node.get("text"))
            v = self.by_text.get((tk, edge["rel"], edge["dst"]))
        if v is None:
            return Verdict("decline", "kein Urteil des Prüfers vorhanden")
        return Verdict("pass" if v["verdict"] == "pass" else "decline", v.get("reason", ""))


def text_key(text: str | None) -> str:
    """Stable key for a standard's wording: identical texts share one judgement."""
    import hashlib
    import re
    norm = re.sub(r"\s+", " ", (text or "").strip().casefold())
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]


class AnthropicNotReady:
    def __init__(self, model: str):
        self.model = model

    def _fail(self):
        raise NotImplementedError(
            f"anthropic:{self.model} is configured but the API provider is built in M1. "
            "Use fixture providers offline, or wait for M1.")

    def propose(self, nodes, topics):
        self._fail()

    def judge(self, edge, node, topic):
        self._fail()


def make(spec: str, pack):
    kind, _, arg = (spec or "").partition(":")
    if kind in ("fixture", "file"):
        return kind, pack.rel(arg)
    if kind == "anthropic":
        return AnthropicNotReady(arg)
    raise ValueError(f"unknown provider spec {spec!r}")


def proposer(pack):
    obj = make(pack.get("mapping.proposer"), pack)
    if isinstance(obj, tuple):
        return FixtureProposer(obj[1])   # same file format for fixture and real proposals
    return obj


def judge(pack):
    obj = make(pack.get("mapping.judge"), pack)
    if isinstance(obj, tuple):
        kind, path = obj
        return FixtureJudge(path) if kind == "fixture" else FileJudge(path)
    return obj
