"""MCP server (stdio) for the curricula knowledge base.

A thin twin of kb_api.py: same calls, same data, same call log. Every tool is
annotated read-only, idempotent, non-destructive and closed-world.

    python mcp_server.py

Environment: CURRICULA_PACK, CURRICULA_DATA_DIR, CURRICULA_KB, CURRICULA_CALL_LOG
(see kb_api.py). Requires the Python MCP SDK 2.x (pip install -r requirements.txt).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Union

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mcp.server.mcpserver import MCPServer  # noqa: E402
from mcp.types import ToolAnnotations  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from kb_api import TOOLS, KBApi  # noqa: E402

INSTRUCTIONS = """German school curricula knowledge base (read-only).
Before writing any exercise (Aufgabe) for a pupil: call resolve_context, then
curriculum_status, then exercise_brief; write the exercise inside that frame;
then call check_exercise and revise until no finding is 'fail'. Cite the
curriculum version (document_id, title, evaluated date) in the exercise
metadata. Never present content as curriculum-backed without a node id from
`citations`. Answers carry `uncertainty`: pass it on, do not hide it."""

READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)


class PupilContext(BaseModel):
    land: str = Field(description="Land code or name, e.g. 'MV' or 'Mecklenburg-Vorpommern'")
    school_form: str = Field(description="School form as commonly named, e.g. 'Gymnasium'; normalised to the Land's official name")
    grade: Union[int, str] = Field(description="Grade 1 to 13, or a stage label such as 'E' or 'Q1'")
    subject: str = Field(description="Subject, e.g. 'Mathematik', 'Physik', 'Biologie'")
    course_level: Optional[str] = Field(default=None, description="Course level where the plan distinguishes them, e.g. 'LK', 'erhöht'")
    date: Optional[str] = Field(default=None, description="ISO date to evaluate for; default today")


def build_server(api: KBApi | None = None) -> MCPServer:
    api = api or KBApi()
    server = MCPServer(name="curricula-kb", instructions=INSTRUCTIONS)

    def ctx(c: PupilContext) -> dict:
        return c.model_dump()

    @server.tool(description=TOOLS["resolve_context"], annotations=READ_ONLY)
    def resolve_context(context: PupilContext) -> dict:
        return api.resolve_context(ctx(context))

    @server.tool(description=TOOLS["curriculum_status"], annotations=READ_ONLY)
    def curriculum_status(context: PupilContext) -> dict:
        return api.curriculum_status(ctx(context))

    @server.tool(description=TOOLS["topics_for"], annotations=READ_ONLY)
    def topics_for(context: PupilContext, query: str, limit: int = 10) -> dict:
        return api.topics_for(ctx(context), query, limit)

    @server.tool(description=TOOLS["topic_detail"], annotations=READ_ONLY)
    def topic_detail(topic_id: str, context: Optional[PupilContext] = None) -> dict:
        return api.topic_detail(topic_id, ctx(context) if context else None)

    @server.tool(description=TOOLS["exercise_brief"], annotations=READ_ONLY)
    def exercise_brief(context: PupilContext, topic_id: Optional[str] = None, query: Optional[str] = None) -> dict:
        return api.exercise_brief(ctx(context), topic_id, query)

    @server.tool(description=TOOLS["check_exercise"], annotations=READ_ONLY)
    def check_exercise(context: PupilContext, exercise_text: str) -> dict:
        return api.check_exercise(ctx(context), exercise_text)

    @server.tool(description=TOOLS["compare_lands"], annotations=READ_ONLY)
    def compare_lands(topic_id: str, date: Optional[str] = None) -> dict:
        return api.compare_lands(topic_id, date)

    @server.tool(description=TOOLS["coverage_gap"], annotations=READ_ONLY)
    def coverage_gap(context: PupilContext) -> dict:
        return api.coverage_gap(ctx(context))

    @server.tool(description=TOOLS["sources"], annotations=READ_ONLY)
    def sources(document_id: str) -> dict:
        return api.sources(document_id)

    @server.tool(description=TOOLS["get_node"], annotations=READ_ONLY)
    def get_node(node_id: str) -> dict:
        return api.get_node(node_id)

    @server.tool(description=TOOLS["neighbors"], annotations=READ_ONLY)
    def neighbors(topic_id: str) -> dict:
        return api.neighbors(topic_id)

    return server


if __name__ == "__main__":
    build_server().run("stdio")
