# Connecting the MCP server

The server speaks MCP over stdio and needs Python 3.11+ with `pip install -r requirements.txt`.

## Claude Code

Either copy `claude_code.json` into the project's `.mcp.json` (adjust the paths), or run:

```bash
claude mcp add curricula-kb --env CURRICULA_DATA_DIR=/ABSOLUTE/PATH/TO/syllabus-de/data --env CURRICULA_CALL_LOG=/ABSOLUTE/PATH/TO/syllabus-de/data/calls.jsonl -- python3 /ABSOLUTE/PATH/TO/syllabus-de/mcp_server.py
```

## Claude Desktop

Merge `claude_desktop_config.json` into the Desktop config file (Settings, Developer, Edit Config), adjust the paths, and restart the app.

## Trying it on the toy fixture

Point the server at the offline fixture instead of the real knowledge base:

```bash
python3 -m builder.run --pack tests/fixture/pack.yaml --data-dir /tmp/toykb
```

Then set `CURRICULA_PACK=/ABSOLUTE/PATH/TO/syllabus-de/tests/fixture/pack.yaml` and `CURRICULA_DATA_DIR=/tmp/toykb` in the `env` block. The fictional Länder are `ZA` (Zettland), `ZB` (Ypsland) and `ZC` (Xenland, placeholder).
