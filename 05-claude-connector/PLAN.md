# Project 5 — Claude Connector (MCP Server + Skill)

Connect the conversion suite to Claude: an MCP server so Claude (Code / Desktop / claude.ai connectors) can convert anything to Markdown mid-conversation, plus a Claude Code skill for a polished `/md` workflow.

Upstream already ships a minimal `markitdown-mcp` (one tool, `convert_to_markdown(uri)`). Ours is a superset with more tools, safer defaults, and suite integration.

## Stack
- **Python + FastMCP** (`mcp` SDK) — same pattern as `reference/markitdown/packages/markitdown-mcp`.
- Wraps markitdown **directly** (no HTTP hop) for local files; can optionally proxy to project 04's API for remote deployment.
- Transports: **stdio** (default — Claude Code & Claude Desktop) and **Streamable HTTP** (`--http`) for claude.ai custom connectors / remote use.

## MCP tools (v1)
```
convert_to_markdown(uri)            # file:, http(s):, data: URI → md (parity with upstream)
convert_file(path, output_path?)    # local path in, optionally WRITE .md next to it / to output_path
convert_url(url)                    # explicit web page → md
youtube_to_markdown(url, include_timestamps?)   # metadata + transcript
convert_directory(path, glob?, output_dir?)     # batch: every matching file → .md, returns summary + failures
list_supported_formats()            # from live converter registry + which extras are installed
```
- Every tool returns markdown text + a compact JSON-ish header (title, source, warnings) so Claude can cite it.
- Large outputs: tool results capped (~100 KB) with `output_path` written to disk and a truncation notice — keeps Claude context healthy.

## Security defaults
- stdio mode: file access limited to allowlisted roots (`--root`, default: cwd + home's Documents/Downloads; configurable).
- HTTP mode: bind 127.0.0.1 by default with the same non-localhost warning upstream prints; optional bearer token env `MD_MCP_TOKEN`.
- URL fetching goes through the same SSRF guard module as project 04 (shared `security.py`, copied or extracted to a tiny shared lib).

## Claude Code skill (`md-convert`)
- `.claude/skills/md-convert/SKILL.md` shipped in this folder + install instructions (copy to `~/.claude/skills/`).
- Skill teaches Claude: when user says "convert X to markdown / summarize this pdf / get this youtube transcript", prefer the MCP tools; naming conventions; where outputs land; batch etiquette (convert_directory for folders).
- Also ship ready-to-paste config snippets:
  - Claude Code: `claude mcp add md-suite -- python -m md_suite_mcp`
  - Claude Desktop `claude_desktop_config.json` block
  - claude.ai custom connector (HTTP URL) block

## Architecture
```
src/md_suite_mcp/
  __main__.py        # argparse: stdio | --http --host --port, --root, --api (proxy mode)
  server.py          # FastMCP tools
  engine.py          # MarkItDown singleton, kwargs (llm off by default), output capping
  security.py        # roots allowlist + SSRF guard
skill/md-convert/SKILL.md
pyproject.toml       # console script: md-suite-mcp
tests/               # pytest with mcp client-in-process, vectors from reference test_files
```

## Phases
1. **Server core** — stdio server with convert_to_markdown / convert_file / convert_url, roots allowlist, tests. Register into my own Claude Code config and dogfood.
2. **YouTube + directory batch + formats tools**, output capping.
3. **HTTP transport + token**, connector snippets, skill file.
4. **(optional) proxy mode** — `--api URL` flag routes conversions through project 04 for thin-client installs.

## Verification
- pytest in-process MCP client calling each tool over upstream test_files.
- Live: add to this machine's Claude Code (`claude mcp add`), run a real session converting a pdf + a YouTube link; confirm in `/context` or tool listing.

## Risks
- MCP SDK API churn (fastmcp versions) — pin `mcp` version.
- Path security is the whole game for a file-reading MCP server — roots check must be canonical-path based (resolve symlinks) with tests for `../` escapes.
