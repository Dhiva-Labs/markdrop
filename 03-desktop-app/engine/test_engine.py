"""Golden tests for the sidecar: one-shot CLI and serve-stdio protocol."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
PY = HERE / ".venv/bin/python"
TEST_FILES = (
    HERE.parents[1] / "reference/markitdown/packages/markitdown/tests/test_files"
)


def run_convert(source, *extra):
    out = subprocess.run(
        [PY, HERE / "md_engine.py", "convert", str(source), *extra],
        capture_output=True, text=True, timeout=120,
    )
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def test_oneshot_docx():
    body = run_convert(TEST_FILES / "test.docx")
    assert body["ok"] and "AutoGen: Enabling Next-Gen LLM Applications" in body["markdown"]
    assert body["markdown"].startswith("---\n")


def test_oneshot_missing_file():
    body = run_convert(TEST_FILES / "nope.docx")
    assert body["ok"] is False and "No such file" in body["error"]


def test_oneshot_output_file(tmp_path):
    target = tmp_path / "out.md"
    body = run_convert(TEST_FILES / "test.xlsx", "--output", str(target))
    assert body["ok"] and body["output"] == str(target)
    assert "09060124-b5e7-4717-9d07-3c046eb" in target.read_text()


def test_serve_protocol():
    proc = subprocess.Popen(
        [PY, HERE / "md_engine.py", "serve"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
    )
    try:
        assert json.loads(proc.stdout.readline())["ready"] is True

        def rpc(obj):
            proc.stdin.write(json.dumps(obj) + "\n")
            proc.stdin.flush()
            return json.loads(proc.stdout.readline())

        assert rpc({"id": 1, "cmd": "ping"})["pong"] is True

        r = rpc({"id": 2, "cmd": "convert", "source": str(TEST_FILES / "test.pdf")})
        assert r["id"] == 2 and r["ok"]
        assert "While there is contemporaneous exploration" in r["markdown"]

        r = rpc({"id": 3, "cmd": "convert", "source": str(TEST_FILES / "test.pptx")})
        assert r["ok"] and "2cdda5c8-e50e-4db4-b5f0-9722a649f455" in r["markdown"]

        r = rpc({"id": 4, "cmd": "formats"})
        assert r["extras"]["pdf"] is True

        r = rpc({"id": 5, "cmd": "convert", "source": str(TEST_FILES / "random.bin")})
        assert "ok" in r  # clean answer either way, never a crash

        assert rpc({"id": 6, "cmd": "quit"})["bye"] is True
        proc.wait(timeout=10)
    finally:
        proc.kill()
