# markdrop-mcp — Claude Connector

MCP server exposing the md-files-dhivalabs conversion suite (MarkItDown) to Claude. Superset of Microsoft's `markitdown-mcp`: file/url/YouTube/directory tools, path-allowlist security, output capping, stdio + Streamable HTTP transports, optional bearer token.

## Install
```bash
cd 05-claude-connector
uv venv .venv && uv pip install -p .venv/bin/python -e ".[dev]"
```

## Tools
| Tool | Purpose |
|---|---|
| `convert_file(path, output_path?)` | local file → md (optionally saved to disk) |
| `convert_url(url, output_path?)` | SSRF-guarded page / file-link → md |
| `convert_to_markdown(uri)` | `file:`/`http(s):`/`data:` URI (markitdown-mcp compatible) |
| `youtube_to_markdown(url, include_timestamps?, output_path?)` | metadata + transcript, optional `[hh:mm:ss]` stamps |
| `convert_directory(path, glob?, output_dir?)` | batch folder → .md files + summary |
| `list_supported_formats()` | live formats + allowed roots |

## Security
- File access limited to allowed roots (default: cwd, `~/Documents`, `~/Downloads`). Widen with repeated `--root DIR` or `MD_MCP_ROOTS=/a:/b`. Checks are canonical-path based (symlink escapes blocked, tested).
- URL fetching validates every redirect hop against private/reserved IP ranges; 50 MB cap.
- Inline output capped at 100 KB (`MD_MCP_MAX_INLINE_CHARS`) — complete files always written when `output_path` given.
- HTTP mode: set `MD_MCP_TOKEN` to require `Authorization: Bearer <token>`.

## Hook it up to Claude

**Claude Code** (from this directory):
```bash
claude mcp add markdrop -- /home/dhivakar/dhiva-labs/md-files-dhivalabs/05-claude-connector/.venv/bin/python -m markdrop_mcp --root ~/dhiva-labs
```

**Claude Desktop** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "markdrop": {
      "command": "/home/dhivakar/dhiva-labs/md-files-dhivalabs/05-claude-connector/.venv/bin/python",
      "args": ["-m", "markdrop_mcp", "--root", "/home/dhivakar/dhiva-labs"]
    }
  }
}
```

**claude.ai custom connector / remote** (Streamable HTTP):
```bash
MD_MCP_TOKEN=<token> .venv/bin/python -m markdrop_mcp --http --host 0.0.0.0 --port 3002
# endpoint: http://<host>:3002/mcp  (Authorization: Bearer <token>)
```

**Claude Code skill** (optional, teaches Claude the workflow):
```bash
cp -r skill/md-convert ~/.claude/skills/
```

## Tests
```bash
.venv/bin/python -m pytest tests/ -q   # includes a real stdio client round-trip
```
