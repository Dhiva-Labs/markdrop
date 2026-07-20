from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

TEST_FILES = (
    Path(__file__).resolve().parents[3]
    / "reference/markitdown/packages/markitdown/tests/test_files"
)

client = TestClient(app)


def _convert(name: str, **form) -> dict:
    path = TEST_FILES / name
    with open(path, "rb") as fh:
        resp = client.post("/api/convert/file", files={"file": (name, fh)}, data=form)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    assert body["markdown"].startswith("---\n")
    return body


def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200 and resp.json()["ok"] is True


def test_formats():
    body = client.get("/api/formats").json()
    assert body["extras"]["pdf"] is True
    assert body["extras"]["docx"] is True


# Expected substrings mirror upstream's _test_vectors.py
@pytest.mark.parametrize(
    "name,must_include",
    [
        ("test.docx", ["314b0a30-5b04-470b-b9f7-eed2c2bec74a", "AutoGen: Enabling Next-Gen LLM Applications"]),
        ("test.xlsx", ["## 09060124-b5e7-4717-9d07-3c046eb"]),
        ("test.pptx", ["2cdda5c8-e50e-4db4-b5f0-9722a649f455"]),
        ("test.pdf", ["While there is contemporaneous exploration of multi-agent approaches"]),
        ("test_blog.html", ["Large language models (LLMs) are powerful tools that can generate"]),
        ("test_notebook.ipynb", ["# Test Notebook"]),
        ("test.epub", ["# Chapter 1: Test Content", "**Authors:** Test Author"]),
    ],
)
def test_file_vectors(name, must_include):
    body = _convert(name)
    for fragment in must_include:
        assert fragment in body["markdown"], f"missing {fragment!r} in {name} output"


def test_charset_hint_mskanji_csv():
    body = _convert("test_mskanji.csv", charset="cp932")
    assert "| 名前 | 年齢 | 住所 |" in body["markdown"]
    assert "| 佐藤太郎 | 30 | 東京 |" in body["markdown"]


def test_unsupported_binary():
    with open(TEST_FILES / "random.bin", "rb") as fh:
        resp = client.post("/api/convert/file", files={"file": ("random.bin", fh)})
    # random.bin converts as text via magika sniffing OR fails as unsupported;
    # either way the API must respond cleanly, never 500.
    assert resp.status_code in (200, 415, 422)


def test_empty_upload_rejected():
    resp = client.post("/api/convert/file", files={"file": ("empty.txt", b"")})
    assert resp.status_code == 400


def test_url_ssrf_blocked():
    for url in [
        "http://127.0.0.1/secret",
        "http://localhost:8080/",
        "http://169.254.169.254/latest/meta-data/",
        "file:///etc/passwd",
        "ftp://example.com/x",
    ]:
        resp = client.post("/api/convert/url", json={"url": url})
        assert resp.status_code == 400, f"{url} should be rejected, got {resp.status_code}"


def test_youtube_rejects_non_youtube():
    resp = client.post("/api/convert/youtube", json={"url": "https://example.com/watch?v=x"})
    assert resp.status_code == 400
