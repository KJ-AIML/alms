"""Offline post-run CLI helpers: normalize, evaluate, summarize, verify-evidence.

DevSpec Section 38. These commands operate on recorded run/evidence directories only.
They perform no provider calls and do not require credentials.
"""

from __future__ import annotations

import json
from pathlib import Path

from .environment import sha256_file
from .fixtures import load_fixtures
from .invariants import evaluate_invariants
from .lanes import load_lanes
from .normalizers import select as select_normalizer
from .results import interpret
from .schemas import default_root, validation_errors
from .storage import write_json_atomic


class PostprocessError(Exception):
    """User-facing refusal for missing run/evidence inputs."""


def _root(root: Path | None) -> Path:
    return root or default_root()


def resolve_run_dir(run_id: str, root: Path | None = None) -> Path:
    run_dir = _root(root) / "runs" / run_id
    if not run_dir.is_dir():
        raise PostprocessError(f"unknown run directory: {run_dir}")
    return run_dir


def _fixture_dirs(run_dir: Path) -> list[Path]:
    fixtures = run_dir / "fixtures"
    if not fixtures.is_dir():
        return []
    return sorted(p for p in fixtures.iterdir() if p.is_dir())


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _lane_by_id(root: Path, lane_id: str) -> dict:
    for lane in load_lanes(root):
        if lane.get("lane_id") == lane_id:
            return lane
    # Probe ids often match matrix keys (langchain) while configs/lanes.json may use
    # langchain-openai; fall back to runtime_layer match on the probe id.
    for lane in load_lanes(root):
        if lane.get("runtime_layer") == lane_id or lane.get("lane_id", "").startswith(lane_id):
            return lane
    raise PostprocessError(f"unknown lane_id in run artifacts: {lane_id}")


def normalize_run(run_id: str, root: Path | None = None) -> dict:
    """Re-normalize raw probe evidence for every fixture in a recorded run."""
    root = _root(root)
    run_dir = resolve_run_dir(run_id, root)
    entries: list[dict] = []

    for fx_dir in _fixture_dirs(run_dir):
        fixture_id = fx_dir.name
        manifest_path = fx_dir / "probe-response.json"
        result_path = fx_dir / "result.json"
        if not manifest_path.is_file():
            entries.append(
                {
                    "fixture_id": fixture_id,
                    "status": "SKIPPED",
                    "reason": "no probe-response.json (blocked/dry-run/incomplete)",
                }
            )
            continue

        manifest = _load_json(manifest_path)
        response_path = Path(manifest["response_path"])
        if not response_path.is_file():
            entries.append(
                {
                    "fixture_id": fixture_id,
                    "status": "INCONCLUSIVE",
                    "reason": f"missing raw response: {response_path}",
                }
            )
            continue

        lane_id = (
            (_load_json(result_path).get("lane_id") if result_path.is_file() else None)
            or manifest.get("probe_id")
            or "?"
        )
        lane = _lane_by_id(root, lane_id)
        raw_obj = _load_json(response_path)
        normalized_path = fx_dir / "normalized-transcript.json"
        interp = interpret(
            capture_kind=manifest.get("capture_kind", "response"),
            raw_obj=raw_obj,
            run_id=run_id,
            fixture_id=fixture_id,
            lane_id=lane.get("lane_id", lane_id),
            raw_manifest_ref=str(manifest_path),
            response_ref=str(response_path),
            normalized_ref=str(normalized_path),
            pricing=None,
            root=root,
            normalizer=select_normalizer(lane.get("runtime_layer")),
            requested_model=manifest.get("model"),
            execution_mode=manifest.get("execution_mode"),
        )
        if interp.normalized is not None:
            write_json_atomic(normalized_path, interp.normalized)
        res_errors = validation_errors("result", interp.result, root)
        if res_errors:
            raise PostprocessError(f"result invalid for {fixture_id}: {'; '.join(res_errors)}")
        write_json_atomic(fx_dir / "result.json", interp.result)
        entries.append(
            {
                "fixture_id": fixture_id,
                "status": interp.status,
                "notes": interp.notes,
            }
        )

    report = {"run_id": run_id, "command": "normalize", "fixtures": entries}
    write_json_atomic(run_dir / "normalize-report.json", report)
    return report


def evaluate_run(run_id: str, root: Path | None = None) -> dict:
    """Evaluate deterministic invariants for every fixture that has result+transcript."""
    root = _root(root)
    run_dir = resolve_run_dir(run_id, root)
    by_id = {fx.id: fx for fx in load_fixtures(root)}
    entries: list[dict] = []

    for fx_dir in _fixture_dirs(run_dir):
        fixture_id = fx_dir.name
        result_path = fx_dir / "result.json"
        transcript_path = fx_dir / "normalized-transcript.json"
        if not result_path.is_file():
            entries.append(
                {
                    "fixture_id": fixture_id,
                    "status": "SKIPPED",
                    "reason": "no result.json",
                    "invariants": [],
                }
            )
            continue
        if fixture_id not in by_id:
            entries.append(
                {
                    "fixture_id": fixture_id,
                    "status": "SKIPPED",
                    "reason": "fixture id not in corpus",
                    "invariants": [],
                }
            )
            continue

        result = _load_json(result_path)
        transcript = _load_json(transcript_path) if transcript_path.is_file() else None
        fixture_data = by_id[fixture_id].data
        invariants = evaluate_invariants(fixture_data, result, transcript)
        write_json_atomic(fx_dir / "invariant-results.json", {"invariants": invariants})

        failed = [i for i in invariants if i.get("passed") is False]
        pending = [i for i in invariants if i.get("passed") is None]
        if failed:
            status = "FAIL"
        elif pending:
            status = "PASS_WITH_PENDING"
        else:
            status = "PASS"
        entries.append(
            {
                "fixture_id": fixture_id,
                "status": status,
                "invariants": invariants,
                "failed": [i["name"] for i in failed],
                "pending": [i["name"] for i in pending],
            }
        )

    report = {"run_id": run_id, "command": "evaluate", "fixtures": entries}
    write_json_atomic(run_dir / "evaluate-report.json", report)
    return report


def summarize_run(run_id: str, root: Path | None = None) -> dict:
    """Load and return the recorded run summary (plus optional evaluate report)."""
    run_dir = resolve_run_dir(run_id, root)
    summary_path = run_dir / "run-summary.json"
    if not summary_path.is_file():
        raise PostprocessError(f"missing run-summary.json for run {run_id}")
    summary = _load_json(summary_path)
    evaluate_path = run_dir / "evaluate-report.json"
    if evaluate_path.is_file():
        summary = {**summary, "evaluate_report": _load_json(evaluate_path)}
    return summary


def verify_evidence(revision: str, root: Path | None = None) -> dict:
    """Verify a committed evidence revision directory and optional hash manifest.

    P0-E1 does not exist yet (G7 not_started). This command reports that honestly rather
    than fabricating a revision.
    """
    root = _root(root)
    evidence_dir = root / "evidence" / revision
    report: dict = {
        "revision": revision,
        "path": str(evidence_dir),
        "status": "NOT_FOUND",
        "files": [],
        "hash_checks": [],
    }
    if not evidence_dir.is_dir():
        report["detail"] = (
            f"evidence/{revision}/ is absent. G7 (P0-E1) remains not_started until "
            "required live evidence exists and a sanitized revision is published."
        )
        return report

    files = sorted(p for p in evidence_dir.rglob("*") if p.is_file())
    report["files"] = [str(p.relative_to(evidence_dir)).replace("\\", "/") for p in files]

    manifest_path = evidence_dir / "manifest.json"
    if not manifest_path.is_file():
        report["status"] = "INCOMPLETE"
        report["detail"] = "revision directory exists but manifest.json is missing"
        return report

    manifest = _load_json(manifest_path)
    artifacts = manifest.get("artifacts") or manifest.get("files") or []
    checks: list[dict] = []
    ok = True
    for item in artifacts:
        if isinstance(item, str):
            rel, expected = item, None
        else:
            rel = item.get("path") or item.get("file")
            expected = item.get("sha256") or item.get("hash")
        if not rel:
            continue
        path = evidence_dir / rel
        if not path.is_file():
            checks.append({"path": rel, "ok": False, "detail": "missing"})
            ok = False
            continue
        actual = sha256_file(path)
        expected_norm = (expected or "").removeprefix("sha256:")
        actual_norm = actual.removeprefix("sha256:")
        if expected and expected_norm != actual_norm:
            checks.append({"path": rel, "ok": False, "detail": "hash mismatch", "actual": actual})
            ok = False
        else:
            checks.append({"path": rel, "ok": True, "hash": actual})

    report["hash_checks"] = checks
    report["status"] = "PASS" if ok else "FAIL"
    report["detail"] = "all listed artifacts verified" if ok else "one or more artifacts failed"
    return report
