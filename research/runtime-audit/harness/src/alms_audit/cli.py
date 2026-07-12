"""alms-audit — internal research CLI for the Phase 0 Runtime Audit Lab.

Commands: validate, list-fixtures, list-lanes, plan, run. Through P0.2 every command is
offline: `run` is dry-run by default and a live run is refused without both --live and
--confirm-live plus a valid budget. It performs NO live calls and is NOT part of the
public `alms` CLI.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import __version__, runner
from .budget import BudgetError
from .config import approved_fixtures, load_config, load_config_path, load_raw
from .environment import credential_presence, sha256_file
from .fixtures import duplicate_ids, load_fixtures
from .lanes import load_lanes
from .planner import build_plan
from .pricing import CostError, load_snapshots
from .schemas import SCHEMA_FILES, spec_dir, validation_errors, validator_for
from .selection import (
    SelectionError,
    parse_fixture_ids,
    resolve_model,
    select_fixtures,
    select_lane,
)


def _add_root(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--root",
        type=Path,
        default=None,
        help="research/runtime-audit directory (defaults to the one this package ships in)",
    )


def cmd_validate(args: argparse.Namespace) -> int:
    root: Path | None = args.root
    ok = True

    # 1. Every schema file must itself be a well-formed JSON Schema.
    missing = [f for f in SCHEMA_FILES.values() if not (spec_dir(root) / f).is_file()]
    if missing:
        print(f"FAIL schemas: missing files: {', '.join(missing)}")
        return 1
    for name in SCHEMA_FILES:
        try:
            validator_for(name, root)  # runs Draft202012Validator.check_schema
            print(f"ok   schema {name}")
        except Exception as exc:  # noqa: BLE001 - report any malformed schema
            ok = False
            print(f"FAIL schema {name}: {exc}")

    # 2. Every fixture must validate against the fixture schema.
    fixtures = load_fixtures(root)
    for fx in fixtures:
        errors = validation_errors("fixture", fx.data, root)
        if errors:
            ok = False
            print(f"FAIL fixture {fx.path.name}: {'; '.join(errors)}")
        else:
            print(f"ok   fixture {fx.id}")

    # 2b. Fixture IDs must be unique across the whole corpus.
    dups = duplicate_ids(fixtures)
    if dups:
        ok = False
        print(f"FAIL duplicate fixture ids: {', '.join(dups)}")

    # 3. Lane config sanity (three independent identifiers must be present).
    for lane in load_lanes(root):
        for field in ("lane_id", "runtime_layer", "provider"):
            if not lane.get(field):
                ok = False
                print(f"FAIL lane {lane.get('lane_id', '?')}: missing {field}")

    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


def cmd_list_fixtures(args: argparse.Namespace) -> int:
    fixtures = load_fixtures(args.root)  # already id-sorted (deterministic)
    if getattr(args, "feature", None):
        fixtures = [f for f in fixtures if f.feature == args.feature]
    if getattr(args, "tier", None):
        fixtures = [f for f in fixtures if f.tier == args.tier]
    if not fixtures:
        print("(no fixtures found)")
        return 0
    for fx in fixtures:
        print(f"{fx.id}\t{fx.feature}\t{fx.tier}\t{fx.summary}")
    return 0


def cmd_list_lanes(args: argparse.Namespace) -> int:
    lanes = load_lanes(args.root)
    if not lanes:
        print("(no lanes configured)")
        return 0
    for lane in lanes:
        print(
            f"{lane.get('lane_id', '?')}\t{lane.get('runtime_layer', '?')}\t{lane.get('provider', '?')}"
        )
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    root: Path | None = args.root
    config = load_config(root)
    fixtures = load_fixtures(root)
    lanes = load_lanes(root)
    providers = sorted({ln.get("provider", "?") for ln in lanes})
    creds = credential_presence(providers)
    # live=True so the preview reveals what a live run would skip (no calls are made).
    plan = build_plan(fixtures, lanes, live=True, credentials=creds)

    print(f"selected fixtures ({len(fixtures)}): {', '.join(f.id for f in fixtures) or '(none)'}")
    print(
        f"selected lanes ({len(lanes)}): {', '.join(ln.get('lane_id', '?') for ln in lanes) or '(none)'}"
    )
    print(f"expected live call count: {plan.expected_call_count}")
    print(f"skipped cases: {len(plan.skipped)}")
    for e in plan.skipped:
        print(f"  skip {e.fixture_id} x {e.lane_id}: {e.skip_reason}")
    missing = sorted(var for var, present in creds.items() if not present)
    print(f"missing credentials: {', '.join(missing) or '(none)'}")
    print("configured models: (supplied at run time; recorded in run manifest)")
    print(f"hard budget (USD): {config.hard_cap_usd}")
    print(f"max output tokens: {config.max_output_tokens}")
    print(f"default timeout (ms): {config.default_timeout_ms}")
    print("(no live calls were made by plan)")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    root: Path | None = args.root
    lanes = load_lanes(root)
    all_fixtures = load_fixtures(root)
    run_id = args.run_id or datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%SZ")
    command_line = "alms-audit " + " ".join(sys.argv[1:])

    execute = bool(args.live or args.offline_execute)
    kwargs: dict = {}

    try:
        if execute and not args.config:
            raise runner.RunError("missing configuration: an execution run requires --config")
        if args.config:
            config_path = Path(args.config)
            if not config_path.is_file():
                raise runner.RunError(f"unknown configuration path: {config_path}")
            config = load_config_path(config_path)
            raw = load_raw(config_path)
        else:
            config = load_config(root)
            config_path = None
            raw = {}

        if execute:
            # Bounded single-lane execution: explicit lane + model + fixture subset required.
            lane = resolve_model(select_lane(lanes, args.lane), args.model)
            ids = parse_fixture_ids(args.fixtures or "")
            selected = select_fixtures(
                all_fixtures, ids, lane=lane, approved_fixtures=approved_fixtures(raw)
            )
            pricing = load_snapshots(raw).get(args.model) if args.model else None
            kwargs = {
                "fixtures": selected,
                "selected_lane": lane,
                "model": args.model,
                "pricing": pricing,
                "offline_execute": args.offline_execute,
                "config_digest": sha256_file(config_path) if config_path else None,
            }
        else:
            kwargs = {"fixtures": all_fixtures}

        summary = runner.run(
            run_id=run_id,
            lanes=lanes,
            config=config,
            live=args.live,
            confirm_live=args.confirm_live,
            command_line=command_line,
            root=root,
            **kwargs,
        )
    except (runner.RunError, BudgetError, CostError, SelectionError) as exc:
        print(f"REFUSED: {exc}")
        return 2

    print(f"mode: {summary.mode}")
    print(f"run_id: {summary.run_id}")
    print(f"run_dir: {summary.run_dir}")
    print(f"expected live call count: {summary.expected_call_count}")
    print(f"manifest: {summary.manifest_path}")
    for e in summary.entries:
        print(f"  fixture {e['fixture_id']}: {e['status']}")
    if summary.summary_path:
        print(f"run summary: {summary.summary_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="alms-audit", description=__doc__)
    parser.add_argument("--version", action="version", version=f"alms-audit {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    for name, func in (
        ("validate", cmd_validate),
        ("list-lanes", cmd_list_lanes),
        ("plan", cmd_plan),
    ):
        p = sub.add_parser(name)
        _add_root(p)
        p.set_defaults(func=func)

    lf = sub.add_parser("list-fixtures")
    _add_root(lf)
    lf.add_argument("--feature", default=None, help="filter by feature family")
    lf.add_argument(
        "--tier", default=None, choices=["BASE", "STRESS", "OPTIONAL"], help="filter by tier"
    )
    lf.set_defaults(func=cmd_list_fixtures)

    run_p = sub.add_parser("run", help="dry-run by default; live requires --live --confirm-live")
    _add_root(run_p)
    run_p.add_argument("--run-id", default=None)
    run_p.add_argument(
        "--config", default=None, help="explicit config file (e.g. a first-live override)"
    )
    run_p.add_argument("--lane", default=None, help="single lane id to execute")
    run_p.add_argument("--model", default=None, help="explicit provider model id")
    run_p.add_argument("--fixtures", default=None, help="comma-separated fixture ids, in order")
    run_p.add_argument(
        "--offline-execute",
        action="store_true",
        help="run the full pipeline through the probe in mock mode (no network, no credential)",
    )
    run_p.add_argument(
        "--live",
        action="store_true",
        help="attempt a live run (still needs --confirm-live + budget + credential)",
    )
    run_p.add_argument(
        "--confirm-live", action="store_true", help="explicit confirmation for a live run"
    )
    run_p.set_defaults(func=cmd_run)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
