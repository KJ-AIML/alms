"""Probe subprocess invocation with timeout + diagnostic capture (DevSpec Section 41).

The harness captures stdout, stderr, exit code, and wall-clock duration. On timeout the
child is killed and whatever was captured is still written to disk — failed and
timed-out runs preserve diagnostics (DevSpec Section 40 / harness test category).
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

TIMEOUT_EXIT = -9  # sentinel exit code recorded when the child is killed on timeout


@dataclass(frozen=True)
class RawResult:
    command: list[str]
    exit_code: int
    duration_ms: int
    timed_out: bool
    stdout_path: Path
    stderr_path: Path


def run_probe(
    command: list[str],
    *,
    timeout_ms: int,
    capture_dir: Path,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> RawResult:
    capture_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = capture_dir / "stdout.txt"
    stderr_path = capture_dir / "stderr.txt"

    start = time.monotonic()
    timed_out = False
    try:
        proc = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=max(timeout_ms, 1) / 1000.0,
            check=False,
        )
        stdout, stderr, exit_code = proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = exc.stdout or ""
        stderr = (exc.stderr or "") + f"\n[harness] probe killed after {timeout_ms} ms timeout\n"
        exit_code = TIMEOUT_EXIT
    duration_ms = int((time.monotonic() - start) * 1000)

    # Preserve diagnostics regardless of success/failure/timeout.
    stdout_path.write_text(stdout if isinstance(stdout, str) else "", encoding="utf-8")
    stderr_path.write_text(stderr if isinstance(stderr, str) else "", encoding="utf-8")

    return RawResult(
        command=command,
        exit_code=exit_code,
        duration_ms=duration_ms,
        timed_out=timed_out,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )
