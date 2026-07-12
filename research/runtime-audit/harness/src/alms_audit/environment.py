"""Environment + reproducibility capture (DevSpec Sections 35, 83, 86).

Credential handling records presence booleans only — never values (DevSpec Section 83).
"""

from __future__ import annotations

import hashlib
import os
import platform
import re
import subprocess
import sys
from pathlib import Path

# Credential-shaped strings that must never appear in committed/evidence artifacts. Detecting
# by SHAPE means the harness never has to read a real credential value to scan for leaks
# (credential state stays presence-only outside the probe child).
_SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_\-]{16,}"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{12,}"),
)

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


def scan_for_secrets(directory: Path, secret_values: set[str]) -> list[str]:
    """Scan every file under `directory` for any secret value. Returns "path: hit" strings.

    A non-empty result is a HARD safety failure (DevSpec Section 83): the credential value
    must never appear in any evidence artifact. Empty/blank secret values are ignored so a
    run with no configured secret cannot trivially "pass" on an empty needle.
    """
    needles = {s for s in secret_values if s and s.strip()}
    hits: list[str] = []
    if not needles or not directory.is_dir():
        return hits
    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for needle in needles:
            if needle in text:
                hits.append(f"{path}: secret value present")
                break
    return hits


def scan_for_secret_shapes(directory: Path) -> list[str]:
    """Scan every file under `directory` for credential-SHAPED strings (no value needed).

    A non-empty result is a hard safety failure. This complements the probe's own redaction
    and lets the harness detect a leaked key without ever reading a real credential value.
    """
    hits: list[str] = []
    if not directory.is_dir():
        return hits
    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if any(pat.search(text) for pat in _SECRET_PATTERNS):
            hits.append(f"{path}: credential-shaped string present")
    return hits


def os_string() -> str:
    return f"{platform.system()} {platform.version()} ({sys.platform})"


def python_string() -> str:
    return platform.python_version()
