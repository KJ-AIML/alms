"""Environment + reproducibility capture (DevSpec Sections 35, 83, 86).

Credential handling records presence booleans only — never values (DevSpec Section 83).
"""

from __future__ import annotations

import hashlib
import os
import platform
import subprocess
import sys
from pathlib import Path

PROVIDER_ENV = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GEMINI_API_KEY",
}


def provider_env_var(provider: str) -> str:
    return PROVIDER_ENV.get(provider, f"{provider.upper()}_API_KEY")


def credential_presence(
    providers: list[str], environ: dict[str, str] | None = None
) -> dict[str, bool]:
    """Map required env var name -> present boolean. Values are never read out."""
    env = os.environ if environ is None else environ
    out: dict[str, bool] = {}
    for provider in providers:
        var = provider_env_var(provider)
        out[var] = bool(env.get(var))
    return out


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def fixture_corpus_hash(fixture_paths: list[Path]) -> str:
    h = hashlib.sha256()
    for p in sorted(fixture_paths, key=lambda x: x.as_posix()):
        h.update(p.name.encode("utf-8"))
        h.update(Path(p).read_bytes())
    return "sha256:" + h.hexdigest()


def _run(cmd: list[str], cwd: Path | None = None) -> str:
    try:
        out = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=15, check=False)
        return out.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def uv_version() -> str:
    return _run(["uv", "--version"])


def git_sha(repo: Path) -> str:
    return _run(["git", "rev-parse", "HEAD"], cwd=repo)


def os_string() -> str:
    return f"{platform.system()} {platform.version()} ({sys.platform})"


def python_string() -> str:
    return platform.python_version()
