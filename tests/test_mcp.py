"""The MCP server over real stdio: tool list, annotations, and parity with kb_api."""
import asyncio
import json
import os
import sys

import pytest

from tests.conftest import FIXTURE_PACK, ROOT, ctx

mcp = pytest.importorskip("mcp")


async def _session(toy_dir, fn):
    from mcp.client.session import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client
    env = dict(os.environ, CURRICULA_PACK=str(FIXTURE_PACK), CURRICULA_DATA_DIR=str(toy_dir))
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "mcp_server.py")], env=env)
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            return await fn(s)


def test_tools_are_read_only_and_closed_world(toy_dir):
    async def go(s):
        return (await s.list_tools()).tools
    tools = asyncio.run(_session(toy_dir, go))
    names = {t.name for t in tools}
    assert {"resolve_context", "curriculum_status", "topics_for", "topic_detail", "exercise_brief",
            "check_exercise", "compare_lands", "coverage_gap", "sources"} <= names
    for t in tools:
        assert t.annotations.read_only_hint is True
        assert t.annotations.open_world_hint is False
        assert t.annotations.destructive_hint is False


def test_mcp_matches_kb_api(toy_dir, api):
    c = ctx(8, "2027-11-07")

    async def go(s):
        res = await s.call_tool("curriculum_status", {"context": c})
        return res.structured_content or json.loads(res.content[0].text)
    via_mcp = asyncio.run(_session(toy_dir, go))
    direct = api.curriculum_status(c)
    via_mcp.pop("result", None)
    assert via_mcp["citations"] == direct["citations"]
    assert via_mcp["summary_de"] == direct["summary_de"]
