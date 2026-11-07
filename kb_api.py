"""Read-only Python API and CLI for the curricula knowledge base.

The same calls are exposed by mcp_server.py, so every client sees the same
data. Every call is logged as one JSON line to $CURRICULA_CALL_LOG when set.

Python:
    from kb_api import KBApi
    api = KBApi()                      # pack and db from env or defaults
    api.curriculum_status({"land": "MV", "school_form": "Gymnasium", "grade": 8,
                           "subject": "Mathematik", "date": "2026-11-07"})

CLI:
    python kb_api.py curriculum_status --context '{"land":"MV","school_form":"Gymnasium","grade":8,"subject":"Mathematik"}'
    python kb_api.py check_exercise --context '{...}' --text "Berechne ..."
    python kb_api.py sources --document-id MV:...
    python kb_api.py tools

Environment:
    CURRICULA_PACK      pack file (default design/pack.yaml)
    CURRICULA_DATA_DIR  data directory (default data/)
    CURRICULA_KB        explicit path to the SQLite file (overrides the two above)
    CURRICULA_CALL_LOG  JSONL file for the call log
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kb.pack import load_pack  # noqa: E402
from kb.service import KnowledgeBase  # noqa: E402

TOOLS = {
    "resolve_context": "Normalised context and the binding curriculum versions for the date, with reasons; both versions in a transition year.",
    "curriculum_status": "Call first. Topics taught before, current (verbatim text, node, page), not yet; competences, operators, conventions, uncertainty, citations.",
    "topics_for": "Search inside the documents that apply to this pupil (full-text search), with backbone topics and their relation to the grade.",
    "topic_detail": "A topic's definition, prerequisites, what follows, where it appears in every Land, and its nodes for the context.",
    "exercise_brief": "Compact brief for writing an exercise: learning goal from the curriculum text, allowed and missing prerequisites, concepts to avoid, operators, conventions.",
    "check_exercise": "Check a drafted exercise against the context: not-yet concepts, missing prerequisites, operators, conventions. pass, warn or fail per finding, each with node ids.",
    "compare_lands": "Grade and track where a topic appears in each Land.",
    "coverage_gap": "Topics expected up to this grade that the assistant's own content does not cover yet.",
    "sources": "Provenance, licence and legal basis of a document, with a citation line.",
    "get_node": "One curriculum node with its path, document and topics.",
    "neighbors": "Prerequisites, follow-up topics, parent and children of a topic.",
}


class KBApi:
    """Thin logging wrapper; all logic lives in kb.service.KnowledgeBase."""

    def __init__(self, db_path: str | None = None, pack_path: str | None = None, data_dir: str | None = None,
                 call_log: str | None = None):
        pack = load_pack(pack_path, data_dir)
        self.kb = KnowledgeBase(db_path or os.environ.get("CURRICULA_KB") or pack.db_path, pack)
        self.call_log = call_log or os.environ.get("CURRICULA_CALL_LOG")

    def _call(self, tool: str, **kwargs) -> dict:
        t0 = time.perf_counter()
        ok, out, err = True, None, None
        try:
            out = getattr(self.kb, tool)(**kwargs)
            ok = "error" not in out
            return out
        except Exception as e:  # logged, then raised
            ok, err = False, f"{type(e).__name__}: {e}"
            raise
        finally:
            if self.call_log:
                args = {k: (v[:2000] if isinstance(v, str) else v) for k, v in kwargs.items()}
                line = {"ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "tool": tool, "args": args,
                        "ok": ok, "ms": round((time.perf_counter() - t0) * 1000, 1),
                        "citations": len(out.get("citations", [])) if isinstance(out, dict) else 0}
                if err:
                    line["error"] = err
                Path(self.call_log).parent.mkdir(parents=True, exist_ok=True)
                with open(self.call_log, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(line, ensure_ascii=False) + "\n")

    def resolve_context(self, context: dict) -> dict:
        return self._call("resolve_context", context=context)

    def curriculum_status(self, context: dict) -> dict:
        return self._call("curriculum_status", context=context)

    def topics_for(self, context: dict, query: str, limit: int = 10) -> dict:
        return self._call("topics_for", context=context, query=query, limit=limit)

    def topic_detail(self, topic_id: str, context: dict | None = None) -> dict:
        return self._call("topic_detail", topic_id=topic_id, context=context)

    def exercise_brief(self, context: dict, topic_id: str | None = None, query: str | None = None) -> dict:
        return self._call("exercise_brief", context=context, topic_id=topic_id, query=query)

    def check_exercise(self, context: dict, exercise_text: str) -> dict:
        return self._call("check_exercise", context=context, exercise_text=exercise_text)

    def compare_lands(self, topic_id: str, date: str | None = None) -> dict:
        return self._call("compare_lands", topic_id=topic_id, date=date)

    def coverage_gap(self, context: dict) -> dict:
        return self._call("coverage_gap", context=context)

    def sources(self, document_id: str) -> dict:
        return self._call("sources", document_id=document_id)

    def get_node(self, node_id: str) -> dict:
        return self._call("get_node", node_id=node_id)

    def neighbors(self, topic_id: str) -> dict:
        return self._call("neighbors", topic_id=topic_id)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Read-only curricula knowledge base CLI")
    ap.add_argument("tool", choices=sorted(TOOLS) + ["tools"])
    ap.add_argument("--context", help="pupil context as JSON")
    ap.add_argument("--query")
    ap.add_argument("--topic-id")
    ap.add_argument("--document-id")
    ap.add_argument("--node-id")
    ap.add_argument("--date")
    ap.add_argument("--text", help="exercise text (or - to read stdin)")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--pack")
    ap.add_argument("--data-dir")
    ap.add_argument("--db")
    a = ap.parse_args(argv)
    if a.tool == "tools":
        for k, v in TOOLS.items():
            print(f"{k:18} {v}")
        return 0
    api = KBApi(a.db, a.pack, a.data_dir)
    ctx = json.loads(a.context) if a.context else None
    text = sys.stdin.read() if a.text == "-" else a.text
    calls = {
        "resolve_context": lambda: api.resolve_context(ctx),
        "curriculum_status": lambda: api.curriculum_status(ctx),
        "topics_for": lambda: api.topics_for(ctx, a.query or "", a.limit),
        "topic_detail": lambda: api.topic_detail(a.topic_id, ctx),
        "exercise_brief": lambda: api.exercise_brief(ctx, a.topic_id, a.query),
        "check_exercise": lambda: api.check_exercise(ctx, text or ""),
        "compare_lands": lambda: api.compare_lands(a.topic_id, a.date),
        "coverage_gap": lambda: api.coverage_gap(ctx),
        "sources": lambda: api.sources(a.document_id),
        "get_node": lambda: api.get_node(a.node_id),
        "neighbors": lambda: api.neighbors(a.topic_id),
    }
    print(json.dumps(calls[a.tool](), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
