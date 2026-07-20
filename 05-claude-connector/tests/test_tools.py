"""Direct tests of the tool functions (engine + security), no MCP transport."""

from pathlib import Path

import pytest

from markdrop_mcp import engine, server
from markdrop_mcp.security import AccessDeniedError, Roots, UnsafeUrlError, validate_url

TEST_FILES = (
    Path(__file__).resolve().parents[2]
    / "reference/markitdown/packages/markitdown/tests/test_files"
)


@pytest.fixture(autouse=True)
def widen_roots(tmp_path):
    old = server.roots
    server.roots = Roots([TEST_FILES, tmp_path])
    yield tmp_path
    server.roots = old


def test_convert_file_docx():
    out = server.convert_file(str(TEST_FILES / "test.docx"))
    assert "AutoGen: Enabling Next-Gen LLM Applications" in out
    assert out.startswith("---\n") or out.startswith("[")


def test_convert_file_pdf():
    out = server.convert_file(str(TEST_FILES / "test.pdf"))
    assert "While there is contemporaneous exploration" in out


def test_convert_file_writes_output(widen_roots):
    target = widen_roots / "out.md"
    out = server.convert_file(str(TEST_FILES / "test.xlsx"), output_path=str(target))
    assert target.exists()
    assert "09060124-b5e7-4717-9d07-3c046eb" in target.read_text()
    assert "Saved" in out


def test_roots_block_outside_paths():
    with pytest.raises(AccessDeniedError):
        server.convert_file("/etc/passwd")


def test_roots_block_symlink_escape(widen_roots):
    link = widen_roots / "sneaky"
    link.symlink_to("/etc")
    with pytest.raises(AccessDeniedError):
        server.convert_file(str(link / "passwd"))


def test_convert_directory(widen_roots):
    src = widen_roots / "batch"
    src.mkdir()
    for name in ["test.docx", "test.csv" if (TEST_FILES / "test.csv").exists() else "test.json"]:
        (src / name).write_bytes((TEST_FILES / name).read_bytes())
    summary = server.convert_directory(str(src))
    assert "Converted 2/2" in summary
    assert (src / "test.docx").with_suffix(".md").exists()


def test_output_capping(monkeypatch):
    monkeypatch.setattr(engine, "MAX_INLINE_CHARS", 500)
    out = server.convert_file(str(TEST_FILES / "test.docx"))
    assert "characters; showing the first" in out
    # 500 chars of content + the notice line
    assert len(out) < 800


def test_validate_url_rejects_private():
    for url in [
        "http://127.0.0.1/x",
        "http://localhost/x",
        "http://169.254.169.254/latest",
        "file:///etc/passwd",
    ]:
        with pytest.raises(UnsafeUrlError):
            validate_url(url)


def test_youtube_rejects_non_youtube():
    with pytest.raises(ValueError):
        server.youtube_to_markdown("https://example.com/watch?v=abc")


def test_list_supported_formats():
    out = server.list_supported_formats()
    assert "pdf: yes" in out
    assert "docx: yes" in out
