"""alms-audit — internal research CLI for the Phase 0 Runtime Audit Lab.

Read-only in P0.1: it validates schemas + fixtures and lists fixtures/lanes.
It performs NO live calls and is NOT part of the public `alms` CLI.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from . import __version__
from .fixtures import load_fixtures
from .lanes import load_lanes
from .schemas import SCHEMA_FILES, spec_dir, validation_errors, validator_for


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

    # 3. Lane config sanity (three independent identifiers must be present).
    for lane in load_lanes(root):
        for field in ("lane_id", "runtime_layer", "provider"):
            if not lane.get(field):
                ok = False
                print(f"FAIL lane {lane.get('lane_id', '?')}: missing {field}")

    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


def cmd_list_fixtures(args: argparse.Namespace) -> int:
    fixtures = load_fixtures(args.root)
    if not fixtures:
        print("(no fixtures found)")
        return 0
    for fx in fixtures:
        print(f"{fx.id}\t{fx.feature}\t{fx.summary}")
    return 0


def cmd_list_lanes(args: argparse.Namespace) -> int:
    lanes = load_lanes(args.root)
    if not lanes:
        print("(no lanes configured)")
        return 0
    for lane in lanes:
        print(f"{lane.get('lane_id', '?')}\t{lane.get('runtime_layer', '?')}\t{lane.get('provider', '?')}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="alms-audit", description=__doc__)
    parser.add_argument("--version", action="version", version=f"alms-audit {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    for name, func in (
        ("validate", cmd_validate),
        ("list-fixtures", cmd_list_fixtures),
        ("list-lanes", cmd_list_lanes),
    ):
        p = sub.add_parser(name)
        _add_root(p)
        p.set_defaults(func=func)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
