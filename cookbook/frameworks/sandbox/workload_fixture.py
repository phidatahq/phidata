"""Deterministic repository workload, executed only inside the sandbox by coding_workload.py."""

import hashlib
import json
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path("/workspace")
PROJECT = ROOT / "project"
PYTHON = ROOT / ".venv/bin/python"
SERVER = """
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from app import answer
with sqlite3.connect('app.db') as db:
    db.execute('create table if not exists visits(value integer)')
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        with sqlite3.connect('app.db') as db:
            count = db.execute('select count(*) from visits').fetchone()[0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(str(count).encode())
    def do_POST(self):
        with sqlite3.connect('app.db') as db:
            db.execute('insert into visits values (?)', (answer(),))
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'committed')
HTTPServer(('127.0.0.1', 8099), Handler).serve_forever()
"""


def run(*argv: str, cwd: Path = PROJECT) -> subprocess.CompletedProcess:
    return subprocess.run(argv, cwd=cwd, check=True, capture_output=True, text=True)


def exercise_server(expected_visits: int) -> None:
    # This application commits each write and is stopped before checkpointing.
    # A filesystem freeze alone is not a backup procedure for arbitrary databases.
    process = subprocess.Popen(
        [str(PYTHON), "-c", SERVER],
        cwd=PROJECT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(100):
            if process.poll() is not None:
                raise RuntimeError("Application exited before readiness")
            try:
                with urllib.request.urlopen(
                    "http://127.0.0.1:8099", timeout=1
                ) as response:
                    assert int(response.read()) == expected_visits
                break
            except OSError:
                time.sleep(0.05)
        else:
            raise RuntimeError("Application did not become ready")
        request = urllib.request.Request(
            "http://127.0.0.1:8099", data=b"", method="POST"
        )
        with urllib.request.urlopen(request, timeout=2) as response:
            assert response.read() == b"committed"
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def hashes() -> dict:
    names = ("app.py", "test_app.py", "app.db", "untracked.txt", ".cache/ignored.txt")
    return {
        name: hashlib.sha256((PROJECT / name).read_bytes()).hexdigest()
        for name in names
    }


def prepare() -> None:
    source = Path("/runtime/native/source")
    source.mkdir(parents=True)
    (source / "app.py").write_text(
        "from fixturelib import value\ndef answer(): return value + 1\n"
    )
    (source / "test_app.py").write_text(
        "import unittest\nfrom app import answer\nclass TestApp(unittest.TestCase):\n def test_answer(self): self.assertEqual(answer(), 42)\n"
    )
    (source / ".gitignore").write_text(".cache/\n__pycache__/\n")
    run("git", "init", "--initial-branch=main", cwd=source)
    run(
        "git",
        "-c",
        "user.name=Sandbox Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "add",
        ".",
        cwd=source,
    )
    run(
        "git",
        "-c",
        "user.name=Sandbox Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "-m",
        "Pinned deterministic fixture",
        cwd=source,
    )
    run("git", "clone", "--no-hardlinks", str(source), str(PROJECT), cwd=ROOT)
    # A tiny local wheel proves dependency installation without network or PyPI.
    wheel = Path("/runtime/native/fixturelib-1.0-py3-none-any.whl")
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("fixturelib/__init__.py", "value = 40\n")
        archive.writestr(
            "fixturelib-1.0.dist-info/METADATA",
            "Metadata-Version: 2.1\nName: fixturelib\nVersion: 1.0\n",
        )
        archive.writestr(
            "fixturelib-1.0.dist-info/WHEEL",
            "Wheel-Version: 1.0\nGenerator: fixture\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        )
        archive.writestr("fixturelib-1.0.dist-info/RECORD", "")
    # Copies avoid an absolute interpreter symlink escaping the managed roots.
    run(sys.executable, "-m", "venv", "--copies", str(PYTHON.parent.parent))
    run(
        str(PYTHON),
        "-m",
        "pip",
        "install",
        "--no-index",
        "--disable-pip-version-check",
        str(wheel),
    )
    failing = subprocess.run(
        [str(PYTHON), "-m", "unittest", "discover"],
        cwd=PROJECT,
        capture_output=True,
        text=True,
    )
    assert failing.returncode == 1 and "41 != 42" in failing.stderr
    (PROJECT / "app.py").write_text(
        "from fixturelib import value\ndef answer(): return value + 2\n"
    )
    # Ensure same-second Python bytecode caching cannot hide the source edit.
    run(
        str(PYTHON),
        "-c",
        "import shutil; shutil.rmtree('__pycache__', ignore_errors=True)",
    )
    run(str(PYTHON), "-m", "unittest", "discover")
    assert "app.py" in run("git", "diff", "--name-only").stdout
    (PROJECT / "untracked.txt").write_text("untracked data")
    (PROJECT / ".cache").mkdir()
    (PROJECT / ".cache/ignored.txt").write_text("ignored dependency cache")
    exercise_server(0)
    (ROOT / "acceptance.json").write_text(
        json.dumps(
            {"hashes": hashes(), "head": run("git", "rev-parse", "HEAD").stdout.strip()}
        )
    )
    print(
        "PASS: clone, install, failing test, code edit, passing test, HTTP application and database commit"
    )


def verify() -> None:
    expected = json.loads((ROOT / "acceptance.json").read_text())
    assert hashes() == expected["hashes"]
    assert run("git", "rev-parse", "HEAD").stdout.strip() == expected["head"]
    run(str(PYTHON), "-m", "unittest", "discover")
    exercise_server(1)
    print(
        "PASS: tracked/untracked/ignored files, installed dependency, Git state and database restored; application restarted"
    )


if __name__ == "__main__":
    if Path.cwd() != ROOT or not Path("/runtime/native").is_dir():
        raise RuntimeError(
            "Run coding_workload.py; this fixture belongs inside a session computer"
        )
    {"prepare": prepare, "verify": verify}[sys.argv[1]]()
