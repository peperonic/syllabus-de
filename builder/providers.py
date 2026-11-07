"""Proposer and judge providers for S5 and S6.

A provider is named in the pack as '<kind>:<arg>':

* fixture:<file>      deterministic, offline (tests and the toy pack)
* anthropic:<model>   Claude via the Anthropic API (implemented in M1)

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
    if kind == "fixture":
        path = pack.rel(arg)
        return path
    if kind == "anthropic":
        return AnthropicNotReady(arg)
    raise ValueError(f"unknown provider spec {spec!r}")


def proposer(pack):
    spec = pack.get("mapping.proposer")
    obj = make(spec, pack)
    return FixtureProposer(obj) if isinstance(obj, Path) else obj


def judge(pack):
    spec = pack.get("mapping.judge")
    obj = make(spec, pack)
    return FixtureJudge(obj) if isinstance(obj, Path) else obj
