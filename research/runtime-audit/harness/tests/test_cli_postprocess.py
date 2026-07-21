"""P0.7D-harness-cli: normalize / evaluate / summarize / verify-evidence (offline only)."""

from __future__ import annotations

from pathlib import Path

from alms_audit.cli import main
from alms_audit.postprocess import evaluate_run, normalize_run, summarize_run, verify_evidence
from alms_audit.storage import write_json_atomic


def _minimal_run(run_dir: Path) -> None:
    """Synthetic recorded run: blocked fixture + one result without raw (normalize skip)."""
    fx = run_dir / "fixtures" / "GEN-001"
    fx.mkdir(parents=True)
    write_json_atomic(
        fx / "result.json",
        {
            "spec": "alms.dev/runtime-audit-result/v0",
            "run_id": run_dir.name,
            "fixture_id": "GEN-001",
            "lane_id": "openai-native",
            "status": "BLOCKED_CONFIGURATION",
            "raw_manifest": "(none: blocked before launch)",
            "normalized_transcript": None,
            "notes": ["offline test blocked"],
            "usage": {
                "input_tokens": None,
                "output_tokens": None,
                "total_tokens": None,
                "cached_input_tokens": None,
                "cache_read_input_tokens": None,
                "cache_creation_input_tokens": None,
                "reasoning_tokens": None,
                "provenance": "absent",
                "source": "unavailable",
                "cost_reported": None,
                "cost_estimated": None,
            },
        },
    )
    write_json_atomic(
        run_dir / "run-summary.json",
        {
            "run_id": run_dir.name,
            "mode": "offline",
            "lane_id": "openai-native",
            "model": "gpt-synthetic",
            "expected_call_count": 0,
            "maximum_call_count": 0,
            "estimated_upper_bound_cost_usd": 0.0,
            "secret_scan": "clean",
            "fixtures": [{"fixture_id": "GEN-001", "status": "BLOCKED_CONFIGURATION"}],
        },
    )


def test_verify_evidence_p0e1_absent_is_honest(capsys) -> None:
    assert main(["verify-evidence", "--revision", "P0-E1"]) == 2
    out = capsys.readouterr().out
    assert "status: NOT_FOUND" in out
    assert "not_started" in out


def test_verify_evidence_with_manifest(tmp_path: Path, corpus_root: Path) -> None:
    rev = corpus_root / "evidence" / "TEST-REV"
    rev.mkdir(parents=True)
    artifact = rev / "note.txt"
    artifact.write_text("hello", encoding="utf-8")
    from alms_audit.environment import sha256_file

    digest = sha256_file(artifact)
    write_json_atomic(
        rev / "manifest.json",
        {"artifacts": [{"path": "note.txt", "sha256": digest}]},
    )
    report = verify_evidence("TEST-REV", corpus_root)
    assert report["status"] == "PASS"
    assert main(["verify-evidence", "--root", str(corpus_root), "--revision", "TEST-REV"]) == 0


def test_summarize_and_normalize_skip_without_raw(corpus_root: Path, capsys) -> None:
    run_id = "cli-post-1"
    run_dir = corpus_root / "runs" / run_id
    _minimal_run(run_dir)

    assert main(["summarize", "--root", str(corpus_root), "--run", run_id]) == 0
    out = capsys.readouterr().out
    assert "run_id: cli-post-1" in out
    assert "GEN-001" in out

    assert main(["normalize", "--root", str(corpus_root), "--run", run_id]) == 0
    out = capsys.readouterr().out
    assert "SKIPPED" in out
    assert (run_dir / "normalize-report.json").is_file()

    assert main(["evaluate", "--root", str(corpus_root), "--run", run_id]) == 0
    report = evaluate_run(run_id, corpus_root)
    assert report["fixtures"][0]["fixture_id"] == "GEN-001"
    assert (run_dir / "evaluate-report.json").is_file()
    assert (run_dir / "fixtures" / "GEN-001" / "invariant-results.json").is_file()


def test_normalize_unknown_run_refused(capsys) -> None:
    assert main(["normalize", "--run", "does-not-exist"]) == 2
    assert "REFUSED" in capsys.readouterr().out


def test_postprocess_helpers_roundtrip_summary(corpus_root: Path) -> None:
    run_id = "cli-post-2"
    _minimal_run(corpus_root / "runs" / run_id)
    summary = summarize_run(run_id, corpus_root)
    assert summary["secret_scan"] == "clean"
    norm = normalize_run(run_id, corpus_root)
    assert norm["fixtures"][0]["status"] == "SKIPPED"
