"""Run orchestration (DevSpec Sections 37, 40, 41).

Three modes:
  * dry-run (default): plan + immutable manifest only, no subprocess, no calls.
  * offline: the FULL harness -> probe -> raw -> normalize -> result pipeline through a real
    subprocess in the probe's mock mode. Zero provider calls, zero credential, zero network
    (a probe-side tripwire enforces this). Offline evidence is labelled, never called live.
  * live: identical pipeline WITHOUT mock mode, only after every gate passes. Fail-closed:
    a live run is refused before any subprocess if confirmation, budget, credential, model,
    pricing, or the call cap is not satisfied. NOT exercised in the P0.4B session.

Evidence transaction order per fixture: the probe writes raw artifacts first; the harness
verifies they exist before writing any normalized interpretation or result record. Raw
artifacts are never rewritten. One fixture failure never erases earlier fixture evidence.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from . import budget as budget_mod
from .config import AuditConfig
from .environment import (
    credential_presence,
    fixture_corpus_hash,
    git_sha,
    os_string,
    provider_env_var,
    python_string,
    scan_for_secret_shapes,
    sha256_file,
)
from .fixtures import Fixture
from .normalizers import select as select_normalizer
from .planner import LivePlan, Plan, build_live_plan, build_plan
from .pricing import PricingSnapshot, gate_cost
from .protocol import build_probe_request
from .results import interpret
from .schemas import default_root, validation_errors
from .storage import (
    build_run_manifest,
    now_iso,
    prepare_run_dir,
    write_json_atomic,
    write_run_manifest,
)
from .subprocess_runner import run_probe

BLOCK_NETWORK_ENV = "ALMS_PROBE_BLOCK_NETWORK"

# Each lane's runtime layer maps to the isolated probe project that owns that runtime's SDK.
# A lane never launches another lane's probe env (DevSpec Sections 20, 25, 29).
_PROBE_BY_RUNTIME = {
    "openai": "openai-native",
    "langchain": "langchain",
    "anthropic": "anthropic-native",
    "google-genai": "gemini-native",
    "litellm-sdk": "litellm-sdk",
}


def _probe_id_for_lane(lane: dict) -> str:
    runtime = lane.get("runtime_layer", "")
    return _PROBE_BY_RUNTIME.get(runtime, runtime or "openai-native")


class RunError(RuntimeError):
    """Raised to refuse an unsafe or unavailable run, or abort on a hard safety failure."""


def _probe_python(probe_dir: Path) -> Path:
    """The probe project's own venv interpreter (created by `uv sync` in the probe dir)."""
    candidate = (
        probe_dir / ".venv" / "Scripts" / "python.exe"
        if os.name == "nt"
        else probe_dir / ".venv" / "bin" / "python"
    )
    if not candidate.is_file():
        raise RunError(
            f"probe interpreter not found at {candidate}. Run "
            f"`uv sync --frozen` in {probe_dir} before an execution run."
        )
    return candidate


@dataclass
class RunSummary:
    run_id: str
    mode: str  # "dry-run" | "offline" | "live"
    run_dir: Path
    plan: Plan | LivePlan
    manifest_path: Path
    entries: list[dict] = field(default_factory=list)
    summary_path: Path | None = None

    @property
    def expected_call_count(self) -> int:
        return self.plan.expected_call_count


def _plan_dict(plan: Plan) -> dict:
    return {
        "expected_call_count": plan.expected_call_count,
        "planned": [
            {"fixture_id": e.fixture_id, "lane_id": e.lane_id, "will_call": e.will_call}
            for e in plan.planned
        ],
        "skipped": [
            {"fixture_id": e.fixture_id, "lane_id": e.lane_id, "reason": e.skip_reason}
            for e in plan.skipped
        ],
    }


def run(
    *,
    run_id: str,
    fixtures: list[Fixture],
    lanes: list[dict],
    config: AuditConfig,
    live: bool = False,
    confirm_live: bool = False,
    offline_execute: bool = False,
    selected_lane: dict | None = None,
    model: str | None = None,
    pricing: PricingSnapshot | None = None,
    config_digest: str | None = None,
    model_configuration: dict | None = None,
    command_line: str = "",
    root: Path | None = None,
    probe_dir: Path | None = None,
) -> RunSummary:
    root = root or default_root()

    if live or offline_execute:
        return _run_execution(
            run_id=run_id,
            fixtures=fixtures,
            config=config,
            live=live,
            confirm_live=confirm_live,
            selected_lane=selected_lane,
            model=model,
            pricing=pricing,
            config_digest=config_digest,
            command_line=command_line,
            root=root,
            probe_dir=probe_dir,
        )

    # --- dry-run (default): safety gates preview + immutable manifest, no subprocess ---
    providers = sorted({ln.get("provider", "?") for ln in lanes})
    creds = credential_presence(providers)
    plan = build_plan(fixtures, lanes, live=False, credentials=creds)

    started = now_iso()
    run_dir = prepare_run_dir(run_id, root)
    manifest_path = _write_manifest(
        run_dir=run_dir,
        run_id=run_id,
        root=root,
        fixtures=fixtures,
        selected_lanes=[ln.get("lane_id", "?") for ln in lanes],
        selected_fixtures=[f.id for f in fixtures],
        model_configuration=model_configuration or {},
        creds=creds,
        config=config,
        command_line=command_line,
        started=started,
        probe_lock_hashes={},
    )
    write_json_atomic(run_dir / "plan.json", _plan_dict(plan))
    return RunSummary(
        run_id=run_id, mode="dry-run", run_dir=run_dir, plan=plan, manifest_path=manifest_path
    )


def _run_execution(
    *,
    run_id: str,
    fixtures: list[Fixture],
    config: AuditConfig,
    live: bool,
    confirm_live: bool,
    selected_lane: dict | None,
    model: str | None,
    pricing: PricingSnapshot | None,
    config_digest: str | None,
    command_line: str,
    root: Path,
    probe_dir: Path | None,
) -> RunSummary:
    if selected_lane is None or not model:
        raise RunError("execution requires a selected lane and an explicit model")
    mode = "live" if live else "offline"
    provider = selected_lane.get("provider", "?")
    env_var = provider_env_var(provider)
    creds = credential_presence([provider])

    # --- Fail-closed gates BEFORE constructing any client or launching any subprocess ---
    if live:
        if not confirm_live:
            raise RunError("live run refused: --confirm-live is required alongside --live")
        budget_mod.check_live_budget(config)
        if not creds.get(env_var, False):
            # Credential-presence gate: refuse (fail closed) before any provider execution.
            raise RunError(
                f"live run refused: credential {env_var} is not present (presence-only check)"
            )

    probe_id = _probe_id_for_lane(selected_lane)
    probe_dir = probe_dir or root / "probes" / probe_id
    probe_python = _probe_python(probe_dir)
    # Invoke the probe's OWN locked interpreter directly (not a nested `uv run`, which can
    # hang when launched from inside the harness's own `uv run`). The probe env is the only
    # place the OpenAI SDK lives; the harness process never imports it.
    base_cmd = [str(probe_python), "-m", "probe"]

    run_dir = root / "runs" / run_id
    # Immutable run: a repeated run id must fail BEFORE any provider execution.
    if run_dir.exists():
        raise RunError(f"run id {run_id!r} already has evidence at {run_dir} (immutable)")

    plan = build_live_plan(
        mode=mode,
        lane=selected_lane,
        model=model,
        fixtures=fixtures,
        config=config,
        credentials=creds,
        run_dir=run_dir,
        probe_project_dir=probe_dir,
        probe_run_command=base_cmd,
        pricing=pricing,
    )

    # Cost + call-cap gates bound LIVE provider spend and derive from the planner's expected
    # call count (no second counter). Offline mock makes ZERO provider calls, so they do not
    # apply there — this lets a lane without a committed pricing snapshot still be exercised
    # offline. The live path is unchanged and still fully gated.
    if live:
        gate_cost(
            pricing,
            model_id=model,
            expected_calls=plan.expected_call_count,
            hard_cap_usd=config.hard_cap_usd,
        )
        budget_mod.check_call_cap(plan.expected_call_count, config)

    run_dir.mkdir(parents=True)
    started = now_iso()

    entries: list[dict] = []
    for fx, fx_plan in zip(fixtures, plan.fixtures):
        entries.append(
            _execute_one(
                fx=fx,
                fx_plan=fx_plan,
                lane=selected_lane,
                run_id=run_id,
                mode=mode,
                base_cmd=base_cmd,
                root=root,
                pricing=pricing,
            )
        )

    # Run-level secret scan BEFORE declaring the run complete. Shape-based, so the harness
    # never reads the credential value; any hit is a hard abort.
    hits = scan_for_secret_shapes(run_dir)
    if hits:
        raise RunError(f"SECRET LEAK DETECTED (hard abort): {'; '.join(hits[:3])}")

    model_configuration = {
        "model": model,
        "execution_mode": mode,
        "config_digest": config_digest,
        "pricing_snapshot": plan.pricing,
        "estimated_upper_bound_cost_usd": plan.estimated_upper_bound_cost_usd,
    }
    probe_lock = probe_dir / "uv.lock"
    manifest_path = _write_manifest(
        run_dir=run_dir,
        run_id=run_id,
        root=root,
        fixtures=fixtures,
        selected_lanes=[selected_lane.get("lane_id", "?")],
        selected_fixtures=[f.fixture_id for f in plan.fixtures],
        model_configuration=model_configuration,
        creds=creds,
        config=config,
        command_line=command_line,
        started=started,
        probe_lock_hashes={probe_id: sha256_file(probe_lock)} if probe_lock.is_file() else {},
    )

    summary = {
        "run_id": run_id,
        "mode": mode,
        "lane_id": selected_lane.get("lane_id"),
        "model": model,
        "expected_call_count": plan.expected_call_count,
        "maximum_call_count": plan.maximum_call_count,
        "estimated_upper_bound_cost_usd": plan.estimated_upper_bound_cost_usd,
        "secret_scan": "clean",
        "fixtures": entries,
    }
    summary_path = run_dir / "run-summary.json"
    write_json_atomic(summary_path, summary)
    write_json_atomic(run_dir / "plan.json", plan.as_dict())

    return RunSummary(
        run_id=run_id,
        mode=mode,
        run_dir=run_dir,
        plan=plan,
        manifest_path=manifest_path,
        entries=entries,
        summary_path=summary_path,
    )


def _execute_one(
    *,
    fx: Fixture,
    fx_plan,
    lane: dict,
    run_id: str,
    mode: str,
    base_cmd: list[str],
    root: Path,
    pricing: PricingSnapshot | None,
) -> dict:
    """Run one fixture through the probe subprocess and interpret its evidence.

    Every terminal state is recorded distinctly. A failure here is isolated to this fixture.
    """
    out_dir = Path(fx_plan.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    lane_id = lane.get("lane_id", "?")

    if fx_plan.skip_reason:
        # Blocked (e.g. live credential absent): recorded, no launch, no call.
        result = {
            "spec": "alms.dev/runtime-audit-result/v0",
            "run_id": run_id,
            "fixture_id": fx.id,
            "lane_id": lane_id,
            "status": "BLOCKED_CONFIGURATION",
            "raw_manifest": "(none: blocked before launch)",
            "normalized_transcript": None,
            "notes": [fx_plan.skip_reason],
        }
        write_json_atomic(out_dir / "result.json", result)
        return {
            "fixture_id": fx.id,
            "status": "BLOCKED_CONFIGURATION",
            "reason": fx_plan.skip_reason,
        }

    request = build_probe_request(
        run_id=run_id,
        fixture_path=str(fx.path),
        lane=lane,
        output_dir=str(out_dir),
        timeout_ms=fx_plan.timeout_ms,
        max_attempts=1,
        max_output_tokens=fx_plan.max_output_tokens,
        stream=fx_plan.stream,
        mock_mode=(mode == "offline"),
    )
    req_errors = validation_errors("probe-request", request, root)
    if req_errors:
        raise RunError(f"internal probe-request invalid for {fx.id}: {'; '.join(req_errors)}")
    request_path = out_dir / "probe-request.json"
    write_json_atomic(request_path, request)

    env = dict(os.environ)
    if mode == "offline":
        env[BLOCK_NETWORK_ENV] = "1"  # child must not open a socket in a mock run

    raw = run_probe(
        base_cmd + [str(request_path)],
        timeout_ms=fx_plan.timeout_ms,
        capture_dir=out_dir,
        cwd=root,
        env=env,
    )

    stdout_text = raw.stdout_path.read_text(encoding="utf-8").strip()
    # Probe process failure / timeout / blocked: distinct statuses, diagnostics preserved.
    if raw.exit_code != 0 or not stdout_text:
        blocked = out_dir / "blocked.json"
        if blocked.is_file():
            info = json.loads(blocked.read_text(encoding="utf-8"))
            status = "BLOCKED_CONFIGURATION"
            note = f"{info.get('reason')}: {info.get('detail')}"
        elif raw.timed_out:
            status, note = "ERROR_RUNTIME", "probe timeout"
        else:
            status, note = "ERROR_RUNTIME", f"probe exit {raw.exit_code}"
        result = {
            "spec": "alms.dev/runtime-audit-result/v0",
            "run_id": run_id,
            "fixture_id": fx.id,
            "lane_id": lane_id,
            "status": status,
            "raw_manifest": str(raw.stdout_path),
            "normalized_transcript": None,
            "notes": [note],
        }
        write_json_atomic(out_dir / "result.json", result)
        return {"fixture_id": fx.id, "status": status, "reason": note}

    try:
        manifest = json.loads(stdout_text)
    except json.JSONDecodeError as exc:
        return _inconclusive(out_dir, run_id, fx.id, lane_id, f"unparseable probe response: {exc}")

    mf_errors = validation_errors("probe-response", manifest, root)
    if mf_errors:
        return _inconclusive(
            out_dir, run_id, fx.id, lane_id, f"invalid probe response: {mf_errors[0]}"
        )

    # Verify raw artifacts exist (written by the child) BEFORE any normalization.
    response_path = Path(manifest["response_path"])
    request_artifact = Path(manifest["request_path"])
    if not response_path.is_file() or not request_artifact.is_file():
        return _inconclusive(out_dir, run_id, fx.id, lane_id, "missing raw artifact")

    manifest_path = out_dir / "probe-response.json"
    write_json_atomic(manifest_path, manifest)

    raw_obj = json.loads(response_path.read_text(encoding="utf-8"))
    normalized_path = out_dir / "normalized-transcript.json"
    interp = interpret(
        capture_kind=manifest.get("capture_kind", "response"),
        raw_obj=raw_obj,
        run_id=run_id,
        fixture_id=fx.id,
        lane_id=lane_id,
        raw_manifest_ref=str(manifest_path),
        response_ref=str(response_path),
        normalized_ref=str(normalized_path),
        pricing=pricing,
        root=root,
        normalizer=select_normalizer(lane.get("runtime_layer")),
        requested_model=manifest.get("model"),
        execution_mode=manifest.get("execution_mode"),
    )
    if interp.normalized is not None:
        write_json_atomic(normalized_path, interp.normalized)

    res_errors = validation_errors("result", interp.result, root)
    if res_errors:
        raise RunError(f"internal result invalid for {fx.id}: {'; '.join(res_errors)}")
    write_json_atomic(out_dir / "result.json", interp.result)

    return {
        "fixture_id": fx.id,
        "status": interp.status,
        "execution_mode": manifest.get("execution_mode"),
        "notes": interp.notes,
    }


def _inconclusive(out_dir: Path, run_id: str, fixture_id: str, lane_id: str, note: str) -> dict:
    result = {
        "spec": "alms.dev/runtime-audit-result/v0",
        "run_id": run_id,
        "fixture_id": fixture_id,
        "lane_id": lane_id,
        "status": "INCONCLUSIVE",
        "raw_manifest": str(out_dir / "stdout.txt"),
        "normalized_transcript": None,
        "notes": [note],
    }
    write_json_atomic(out_dir / "result.json", result)
    return {"fixture_id": fixture_id, "status": "INCONCLUSIVE", "reason": note}


def _write_manifest(
    *,
    run_dir: Path,
    run_id: str,
    root: Path,
    fixtures: list[Fixture],
    selected_lanes: list[str],
    selected_fixtures: list[str],
    model_configuration: dict,
    creds: dict[str, bool],
    config: AuditConfig,
    command_line: str,
    started: str,
    probe_lock_hashes: dict[str, str],
) -> Path:
    harness_lock = root / "harness" / "uv.lock"
    fixture_paths = [f.path for f in fixtures]
    manifest = build_run_manifest(
        run_id=run_id,
        git_sha=git_sha(root.parents[1]) if len(root.parents) >= 2 else "unknown",
        harness_lock_hash=sha256_file(harness_lock) if harness_lock.is_file() else "absent",
        probe_lock_hashes=probe_lock_hashes,
        fixture_corpus_hash=fixture_corpus_hash(fixture_paths) if fixture_paths else "empty",
        os_string=os_string(),
        python=python_string(),
        selected_lanes=selected_lanes,
        selected_fixtures=selected_fixtures,
        model_configuration=model_configuration,
        credential_presence=creds,
        hard_cap_usd=config.hard_cap_usd,
        max_calls=config.max_live_calls,
        command_line=command_line,
        started_at=started,
        ended_at=now_iso(),
    )
    return write_run_manifest(run_dir, manifest, root)
