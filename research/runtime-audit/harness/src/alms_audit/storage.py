"""Evidence storage (DevSpec Sections 30, 35, 46).

`runs/<run_id>/` holds complete local execution output and is gitignored. The run
manifest is validated against the schema before it is written and is treated as
immutable once written. Failed runs are preserved, never deleted.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .schemas import default_root, validation_errors

RUN_MANIFEST_SPEC = "alms.dev/runtime-audit-run-manifest/v0"


def runs_root(root: Path | None = None) -> Path:
    return (root or default_root()) / "runs"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def prepare_run_dir(run_id: str, root: Path | None = None) -> Path:
    run_dir = runs_root(root) / run_id
    (run_dir / "raw").mkdir(parents=True, exist_ok=True)
    return run_dir


def write_json_atomic(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def build_run_manifest(
    *,
    run_id: str,
    git_sha: str,
    harness_lock_hash: str,
    probe_lock_hashes: dict[str, str],
    fixture_corpus_hash: str,
    os_string: str,
    python: str,
    selected_lanes: list[str],
    selected_fixtures: list[str],
    model_configuration: dict,
    credential_presence: dict[str, bool],
    hard_cap_usd: float | None,
    max_calls: int | None,
    command_line: str,
    started_at: str,
    ended_at: str | None,
) -> dict:
    return {
        "spec": RUN_MANIFEST_SPEC,
        "run_id": run_id,
        "git_sha": git_sha,
        "harness_lock_hash": harness_lock_hash,
        "probe_lock_hashes": probe_lock_hashes,
        "fixture_corpus_hash": fixture_corpus_hash,
        "os": os_string,
        "python": python,
        "selected_lanes": selected_lanes,
        "selected_fixtures": selected_fixtures,
        "model_configuration": model_configuration,
        "credential_presence": credential_presence,
        "budget": {"hard_cap_usd": hard_cap_usd, "max_calls": max_calls},
        "command_line": command_line,
        "started_at": started_at,
        "ended_at": ended_at,
    }


def write_run_manifest(run_dir: Path, manifest: dict, root: Path | None = None) -> Path:
    errors = validation_errors("run-manifest", manifest, root)
    if errors:
        raise ValueError(f"run manifest failed schema validation: {'; '.join(errors)}")
    path = run_dir / "run-manifest.json"
    write_json_atomic(path, manifest)
    return path
