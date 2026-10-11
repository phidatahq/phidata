"""Standard-library command runner sent to a trusted Python image inside the sandbox."""

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from contextlib import suppress
from typing import Any, Dict


def _execute(request: Dict[str, Any]) -> Dict[str, Any]:
    limit = request["max_output_bytes"]
    timed_out = False
    output_limited = False
    # Output goes to bounded-monitor temporary files so pipe buffers cannot deadlock
    # execution. The provider also limits the container's /tmp filesystem.
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        try:
            process = subprocess.Popen(request["argv"], stdout=stdout, stderr=stderr, start_new_session=True)
        except OSError as error:
            return {"exit_code": 127, "stdout": "", "stderr": str(error), "timed_out": False, "output_limited": False}
        deadline = time.monotonic() + request["timeout"]
        try:
            while process.poll() is None:
                timed_out = time.monotonic() >= deadline
                output_limited = os.fstat(stdout.fileno()).st_size + os.fstat(stderr.fileno()).st_size > limit
                if timed_out or output_limited:
                    with suppress(ProcessLookupError):
                        os.killpg(process.pid, signal.SIGKILL)
                    break
                time.sleep(0.02)
            process.wait()
        finally:
            if process.poll() is None:
                with suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGKILL)
                process.wait()
        total = os.fstat(stdout.fileno()).st_size + os.fstat(stderr.fileno()).st_size
        stdout.seek(0)
        stderr.seek(0)
        out = stdout.read(limit)
        err = stderr.read(max(0, limit - len(out)))
        return {
            "exit_code": process.returncode,
            "stdout": out.decode("utf-8", errors="replace"),
            "stderr": err.decode("utf-8", errors="replace"),
            "timed_out": timed_out,
            "output_limited": output_limited or total > limit,
        }


if __name__ == "__main__":
    print(json.dumps(_execute(json.load(sys.stdin))))
