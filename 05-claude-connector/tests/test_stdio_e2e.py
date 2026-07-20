"""End-to-end: launch the server as a subprocess over stdio and call tools
through a real MCP client session."""

import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

TEST_FILES = (
    Path(__file__).resolve().parents[2]
    / "reference/markitdown/packages/markitdown/tests/test_files"
)


@pytest.mark.anyio
async def test_stdio_roundtrip(tmp_path):
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "markdrop_mcp", "--root", str(TEST_FILES), "--root", str(tmp_path)],
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            names = {t.name for t in tools.tools}
            assert names == {
                "convert_file",
                "convert_url",
                "convert_to_markdown",
                "youtube_to_markdown",
                "convert_directory",
                "list_supported_formats",
            }

            result = await session.call_tool(
                "convert_file", {"path": str(TEST_FILES / "test.docx")}
            )
            assert not result.isError
            text = result.content[0].text
            assert "AutoGen: Enabling Next-Gen LLM Applications" in text

            # Denied path comes back as a tool error, not a crash
            result = await session.call_tool("convert_file", {"path": "/etc/passwd"})
            assert result.isError
            assert "outside the allowed roots" in result.content[0].text

            result = await session.call_tool("list_supported_formats", {})
            assert "pdf: yes" in result.content[0].text


@pytest.fixture
def anyio_backend():
    return "asyncio"
